"""Publish application guides as GitHub pull requests without changing the worktree."""

import base64
import hashlib
import json
import os
from pathlib import Path
import re
import ssl
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from urllib.parse import urlparse
import truststore
from errors import InfrastructureError


class RejectRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise InfrastructureError('Unexpected redirect from the GitHub API')


class KnowledgeGit:
    """Owns the configured shared branch, isolated Git commits and PR publication."""

    def __init__(self, settings, deadline, run_command=subprocess.run, http=None, interrupted=None):
        self.repository = Path(settings['repository']).resolve()
        self.remote = settings['remote']
        self.branch = settings['baseBranch']
        self.deadline = deadline
        self.run_command = run_command
        self.http = http
        self.interrupted = interrupted or (lambda: False)
        self.base = None
        self.github = None
        self.env = dict(os.environ, GIT_TERMINAL_PROMPT='0', GCM_INTERACTIVE='never',
                        GIT_TRACE='0', GIT_TRACE_CURL='0', GIT_CURL_VERBOSE='0')
        self.env.pop('OPENAI_API_KEY', None)

    def _git(self, *arguments, input=None, env=None):
        if self.interrupted():
            raise InfrastructureError('Knowledge publication interrupted; proposals remain in the report')
        remaining = self.deadline - time.time()
        if remaining <= 0:
            raise InfrastructureError('Knowledge operation reached the run deadline')
        try:
            result = self.run_command(['git', '-C', str(self.repository), *arguments], input=input,
                capture_output=True, text=True, env=env or self.env, timeout=min(30, remaining))
        except (OSError, subprocess.SubprocessError):
            raise InfrastructureError('Knowledge Git operation could not complete') from None
        if result.returncode:
            # Git error text can echo remote credentials or generated guide content.
            operation = arguments[2] if arguments[0] == '-c' else arguments[0]
            raise InfrastructureError('Knowledge Git operation failed: ' + operation)
        return result.stdout.strip()

    @staticmethod
    def github_name(remote):
        if remote.startswith('git@github.com:'):
            name = remote[len('git@github.com:'):]
        else:
            url = urlparse(remote)
            if url.hostname != 'github.com' or url.scheme not in ['https', 'ssh']:
                raise InfrastructureError('Knowledge PR publication currently requires a GitHub remote')
            if url.scheme == 'https' and (url.username or url.password):
                raise InfrastructureError('Knowledge remote URLs must not contain credentials')
            name = url.path.lstrip('/')
        if name.endswith('.git'):
            name = name[:-4]
        if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', name):
            raise InfrastructureError('Knowledge GitHub repository name is invalid')
        return name

    def prepare(self):
        if not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]*', self.remote):
            raise InfrastructureError('Knowledge remote name is invalid')
        self._git('check-ref-format', 'refs/heads/' + self.branch)
        if Path(self._git('rev-parse', '--show-toplevel')).resolve() != self.repository:
            raise InfrastructureError('Knowledge repository must name its Git worktree root')
        self.github = self.github_name(self._git('remote', 'get-url', self.remote))
        ref = 'refs/remotes/' + self.remote + '/' + self.branch
        self._git('fetch', '--no-recurse-submodules', self.remote, '+refs/heads/' + self.branch + ':' + ref)
        self.base = self._git('rev-parse', ref)

    def read(self, path):
        if not self._git('ls-tree', '--name-only', self.base, '--', path):
            return None
        try:
            return json.loads(self._git('show', self.base + ':' + path))
        except ValueError:
            raise InfrastructureError('Shared app knowledge is not valid JSON') from None

    def token(self):
        token = self.env.get('GH_TOKEN') or self.env.get('GITHUB_TOKEN')
        if token:
            return token
        try:
            credential = self._git('credential', 'fill', input='protocol=https\nhost=github.com\n\n')
        except InfrastructureError:
            return None
        return dict(line.split('=', 1) for line in credential.splitlines() if '=' in line).get('password')

    def commit(self, changes):
        """Use a temporary index so existing staged/unstaged work stays untouched."""
        with tempfile.TemporaryDirectory(prefix='cimt-knowledge-index-') as folder:
            env = dict(self.env, GIT_INDEX_FILE=str(Path(folder) / 'index'))
            self._git('read-tree', self.base, env=env)
            for path, document in sorted(changes.items()):
                if not re.fullmatch(r'knowledge/apps/(ios|android)/[A-Za-z0-9][A-Za-z0-9_.-]*\.json', path):
                    raise InfrastructureError('Knowledge commits may contain only application guide files')
                blob = self._git('hash-object', '-w', '--stdin', input=json.dumps(document, ensure_ascii=False, indent=2) + '\n', env=env)
                self._git('update-index', '--add', '--cacheinfo', '100644,' + blob + ',' + path, env=env)
            tree = self._git('write-tree', env=env)
            if tree == self._git('rev-parse', self.base + '^{tree}'):
                return None
            return self._git('commit-tree', tree, '-p', self.base,
                             input='knowledge: update application operation guides\n', env=env)

    def publish(self, changes, run_id):
        branch = 'knowledge/app-guide-' + hashlib.sha256(run_id.encode()).hexdigest()[:16]
        result = dict(status='not-published', baseBranch=self.branch, branch=branch)
        try:
            token = self.token()
            if not token:
                raise InfrastructureError('GitHub authentication unavailable; configure GH_TOKEN, GITHUB_TOKEN or the Git HTTPS credential helper')
            commit = self.commit(changes)
            if commit is None:
                return dict(status='unchanged', baseBranch=self.branch)
            result['commit'] = commit
            env = dict(self.env)
            try:
                count = int(env.get('GIT_CONFIG_COUNT', '0'))
                if count < 0:
                    raise ValueError()
            except ValueError:
                raise InfrastructureError('Git environment has an invalid GIT_CONFIG_COUNT') from None
            env['GIT_CONFIG_COUNT'] = str(count + 1)
            env['GIT_CONFIG_KEY_' + str(count)] = 'http.https://github.com/.extraheader'
            basic = base64.b64encode(('x-access-token:' + token).encode()).decode()
            env['GIT_CONFIG_VALUE_' + str(count)] = 'Authorization: Basic ' + basic
            env.setdefault('GIT_SSH_COMMAND', 'ssh -o BatchMode=yes')
            self._git('-c', 'push.recurseSubmodules=no', 'push',
                '--force-with-lease=refs/heads/' + branch + ':', self.remote,
                commit + ':refs/heads/' + branch, env=env)
            result['status'] = 'branch-pushed'
            result['url'] = self._create_pr(token, branch, changes, run_id)
            result['status'] = 'pr-created'
        except InfrastructureError as error:
            result['error'] = str(error)
        return result

    def _create_pr(self, token, branch, changes, run_id):
        body = dict(title='knowledge: update application operation guides', head=branch, base=self.branch,
            body='AI-generated application guidance from CIMT run `' + run_id + '`.\n\n'
                 'Review observed navigation facts before merging. Current test instructions take priority. '
                 'This guide is not a test verdict.\n\n' + '\n'.join('- `' + path + '`' for path in sorted(changes)))
        request = urllib.request.Request('https://api.github.com/repos/' + self.github + '/pulls',
            data=json.dumps(body).encode(), headers={'Authorization': 'Bearer ' + token,
                'Accept': 'application/vnd.github+json', 'Content-Type': 'application/json',
                'X-GitHub-Api-Version': '2026-03-10'})
        http = self.http or urllib.request.build_opener(
            urllib.request.HTTPSHandler(context=truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)), RejectRedirects())
        if self.interrupted():
            raise InfrastructureError('Knowledge publication interrupted; proposals remain in the report')
        remaining = self.deadline - time.time()
        if remaining <= 0:
            raise InfrastructureError('Knowledge PR creation reached the run deadline')
        try:
            with http.open(request, timeout=min(30, remaining)) as response:
                data = json.load(response)
            url = data.get('html_url', '')
            if not re.fullmatch(r'https://github\.com/' + re.escape(self.github) + r'/pull/\d+', url):
                raise InfrastructureError('GitHub returned an invalid knowledge PR URL')
            return url
        except urllib.error.HTTPError as error:
            error.close()
            raise InfrastructureError('Knowledge PR creation failed with HTTP ' + str(error.code)) from None
        except (OSError, ValueError, AttributeError):
            raise InfrastructureError('Knowledge PR response could not be read') from None
