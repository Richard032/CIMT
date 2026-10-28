"""CIMT's single-objective run worker, invoked only by the public .NET CLI."""
import concurrent.futures, hashlib, html, json, os, pathlib, re, subprocess, sys, threading, time, zipfile, plistlib
from agent import Agent, Budget, InfrastructureError, LimitReached
from mobile import Mobile, Redactor


def atomic(path, value):
    path = pathlib.Path(path); tmp = path.with_suffix(path.suffix + '.partial')
    tmp.write_text(json.dumps(value, indent=2)); tmp.replace(path)


class CrashCounter:
    def __init__(self): self.point, self.count = None, 0

    def record(self, point, crashed):
        if crashed:
            self.count = self.count + 1 if point == self.point else 1
            self.point = point
        elif point == self.point:
            self.point, self.count = None, 0
        return self.count


def element_key(element):
    return json.dumps([element.get(x, '') for x in ['identifier', 'type', 'label', 'text', 'name']], sort_keys=True)


def screen_key(elements):
    return hashlib.sha256(json.dumps([element_key(e) for e in elements], sort_keys=True).encode()).hexdigest()[:16]


def records(value):
    if isinstance(value, list): return [x for x in value if isinstance(x, dict)]
    if isinstance(value, dict):
        for key in ['crashes', 'reports', 'items']:
            if isinstance(value.get(key), list): return records(value[key])
    return []


def record_key(row):
    return str(row.get('id', row.get('name', row.get('path', json.dumps(row, sort_keys=True)))))


class Execution:
    def __init__(self, context):
        self.context = context; self.config = context['config']
        self.root = pathlib.Path(context['report']); self.redactor = Redactor(self.config)
        self.budget = Budget(self.config['ai-model']['name'], self.config['ai-budget']['amount'], self.config['ai-budget']['currency'])
        self.stop = threading.Event(); self.lock = threading.RLock(); self.results = []
        self.budget.journal = self.journal_budget
        self.journal_budget()

    def journal_budget(self):
        with self.lock: atomic(self.root / 'ai-budget.json', self.budget.snapshot())

    def save(self):
        with self.lock:
            value = {'devices': self.redactor.object(self.results), 'budget': self.budget.snapshot()}
            atomic(self.root / 'ui-results.json', value)

    def publish(self, result):
        # Workers publish deep, redacted snapshots; another worker never
        # serializes a result dictionary while its owner is mutating it.
        safe = self.redactor.object(result)
        with self.lock:
            self.results = [r for r in self.results if r['index'] != result['index']] + [safe]
            self.save()

    def check(self):
        if self.stop.is_set(): raise LimitReached('Run stopped after another worker reached a blocking condition')
        if time.time() >= self.context['deadline']:
            self.stop.set(); raise LimitReached('Whole-run time limit reached')

    def execute_action(self, mobile, action, elements):
        mobile.readiness()
        kind = action['action']; current = {e.get('ref'): e for e in elements}
        if kind == 'credential' and (action['credential'] not in self.config.get('credentials', {}) or action['field'] not in ['username', 'password']):
            raise ValueError('Requested credential alias/field is not configured')
        if kind == 'credential' or (kind == 'tap' and action['ref']):
            if action['ref'] not in current or current[action['ref']].get('enabled') is False:
                raise ValueError('Action ref is absent or disabled on the current screen')
            if kind == 'credential':
                identifier = current[action['ref']].get('identifier')
                if not identifier: raise InfrastructureError('Credential entry requires a stable element ID for reliable masking')
                self.redactor.ids.add(identifier)
            mobile.call('mobile_click_on_screen_at_coordinates', ref=action['ref'])
        elif kind == 'tap':
            size = next(e for e in elements if e.get('type') == 'CimtScreenInfo')
            x, y = action['x'], action['y']
            if type(x) is not int or type(y) is not int or not 0 <= x < size['screenWidth'] or not 0 <= y < size['screenHeight']:
                raise ValueError('Coordinate tap is outside the current device screen')
            mobile.call('mobile_click_on_screen_at_coordinates', x=x, y=y)
        if kind == 'credential':
            alias, field = action['credential'], action['field']
            if alias not in self.config.get('credentials', {}) or field not in ['username', 'password']:
                raise ValueError('Requested credential alias/field is not configured')
            # The response may echo the value; it stays in memory and is never
            # recorded or passed to AI. Both adapter stderr and errors redact it.
            mobile.call('mobile_type_keys', text=self.config['credentials'][alias][field], submit=False)
        elif kind == 'text':
            if len(action['text']) > 1000: raise ValueError('Synthetic text action is too long')
            mobile.call('mobile_type_keys', text=action['text'], submit=False)
        elif kind == 'swipe':
            if action['direction'] not in ['up', 'down', 'left', 'right']: raise ValueError('Invalid swipe direction')
            mobile.call('mobile_swipe_on_screen', direction=action['direction'])
        elif kind == 'back':
            if mobile.device['platform'] != 'android': raise ValueError('On iOS choose an observed back-button ref')
            mobile.call('mobile_press_button', button='BACK')
        elif kind == 'wait': time.sleep(min(2, max(0, self.context['deadline'] - time.time())))
        elif kind not in ['tap', 'credential']: raise ValueError('Unsupported action')

    def scenario(self, mobile, build, result, agent):
        app_id = build['app-id']; target = build['target']
        folder = mobile.folder / ('target-' + re.sub(r'[^A-Za-z0-9_.-]', '_', target)[:60] + '-' + hashlib.sha256(target.encode()).hexdigest()[:8])
        folder.mkdir(mode=0o700, exist_ok=True)
        scenario = {'target': target, 'appId': app_id, 'verdict': 'inconclusive', 'completion': 'incomplete',
                    'steps': [], 'remaining': [], 'crashes': [], 'coverage': {}, 'reset': 'not-started'}
        result['scenarios'].append(scenario); self.publish(result)
        executable = app_id
        if mobile.device['platform'] == 'ios':
            with zipfile.ZipFile(build['artifact']) as archive:
                info = next(n for n in archive.namelist() if re.match(r'^Payload/[^/]+\.app/Info.plist$', n))
                plist = plistlib.loads(archive.read(info)); executable = plist['CFBundleExecutable']
                if plist['CFBundleIdentifier'] != app_id: raise InfrastructureError('IPA identity differs from build metadata')
        self.check()
        mobile.reset(build['artifact'], app_id, target)
        scenario['reset'] = ('app-container-reinstall-verified; Keychain/backend state needs app hooks'
                             if mobile.device['platform'] == 'ios' else 'install-and-platform-data-clear-verified')
        try: baseline = {record_key(row) for row in records(mobile.crashes())}
        except InfrastructureError:
            baseline = set(); scenario['diagnostics'] = 'Native crash listing unavailable; process/foreground checks remain active'
        elements, image = mobile.snapshot()
        (folder / 'step-0000.png').write_bytes(image)
        scenario['steps'].append({'step': 0, 'action': 'reset/install/launch', 'observation': scenario['reset'],
                                  'screenshot': str((folder / 'step-0000.png').relative_to(self.root))})
        observed, attempted, history = {}, set(), []
        counter = CrashCounter()
        startup_failures = 0
        while True:
            self.check()
            active = mobile.foreground()
            if active != app_id and not mobile.running(app_id, executable):
                startup_failures += 1
                path = folder / ('startup-crash-' + str(startup_failures) + '.png'); path.write_bytes(image)
                scenario['crashes'].append({'kind': 'unexpected startup termination / suspected crash', 'matchingAttempt': startup_failures})
                scenario['verdict'] = 'failed'
                scenario['steps'].append({'action': 'startup/relaunch check', 'screenshot': str(path.relative_to(self.root))})
                self.publish(result)
                if startup_failures >= 3:
                    scenario['remaining'].append('Scenario cancelled after three matching startup terminations'); return
                mobile.call('mobile_launch_app', packageName=app_id)
                elements, image = mobile.snapshot(); continue
            startup_failures = 0
            if active not in [app_id, 'com.apple.springboard', 'com.android.permissioncontroller', 'com.google.android.permissioncontroller', 'com.android.packageinstaller']:
                scenario['remaining'].append('Application opened another app; that external workflow was not explored')
                self.publish(result); return
            state = screen_key(elements)
            candidates = [e for e in elements if e.get('enabled') is not False and
                          any(t in e.get('type', '').lower() for t in ['button', 'switch', 'checkbox', 'tab', 'radio', 'cell'])]
            for e in candidates: observed[state + ':' + element_key(e)] = e.get('label') or e.get('text') or e.get('identifier') or e.get('type')
            outstanding = {k: v for k, v in observed.items() if k not in attempted}
            coverage = {'observedControls': len(observed), 'attemptedControls': len(attempted),
                        'outstandingObservedControls': len(outstanding), 'outstandingExamples': list(outstanding.values())[:40]}
            scenario['coverage'] = coverage; self.publish(result)
            action = agent.choose(self.context['inputs']['instructions'], self.context['inputs'].get('requirements', ''),
                                  self.context['inputs'].get('setup', ''), elements, image, history,
                                  list(self.config.get('credentials', {})), coverage)
            self.check()
            if action['action'] == 'done':
                scenario['remaining'] = action['remaining']
                if outstanding: scenario['remaining'].append(str(len(outstanding)) + ' observed control/state combinations were not activated')
                scenario['interpretation'] = action['observation']
                complete = action['completion'] == 'complete' and not scenario['remaining']
                scenario['completion'] = 'complete' if complete else 'incomplete'
                scenario['verdict'] = 'failed' if scenario['crashes'] else 'passed' if complete else 'inconclusive'
                self.publish(result); return
            index = len(scenario['steps'])
            ref_element = next((e for e in elements if e.get('ref') == action['ref']), {})
            point = target + ':' + (ref_element.get('identifier') or state + ':' + (element_key(ref_element) if ref_element else action['action'] + action.get('direction', '') + str((action['x'], action['y']))))
            entry = {'step': index, 'action': self.redactor.object(action), 'observation': action['observation']}
            attempted_key = state + ':' + element_key(ref_element)
            try:
                self.execute_action(mobile, action, elements)
                if action['action'] in ['tap', 'credential'] and attempted_key in observed: attempted.add(attempted_key)
            except ValueError as error:
                entry['actionError'] = str(error)
            time.sleep(min(.4, max(0, self.context['deadline'] - time.time())))
            foreground = mobile.foreground()
            died = foreground != app_id and not mobile.running(app_id, executable)
            fresh = []
            try:
                for row in records(mobile.crashes()):
                    key = record_key(row)
                    if key not in baseline and (app_id in json.dumps(row) or executable in json.dumps(row)):
                        fresh.append(row); baseline.add(key)
            except InfrastructureError: pass
            explicit_exit = bool(re.search(r'\b(quit|exit|close app|beenden)\b', ' '.join(str(ref_element.get(k, '')) for k in ['text', 'label', 'identifier']), re.I))
            crashed = bool(fresh) or (died and not explicit_exit)
            elements, image = mobile.snapshot()
            path = folder / ('step-' + str(index).zfill(4) + '.png'); path.write_bytes(image)
            ui_path = folder / ('step-' + str(index).zfill(4) + '-ui.json'); atomic(ui_path, elements)
            entry.update(screenshot=str(path.relative_to(self.root)), ui=str(ui_path.relative_to(self.root)))
            if crashed:
                signature = 'unknown'
                if fresh:
                    signature = json.dumps({k: v for k, v in fresh[0].items() if k in ['exceptionType', 'exceptionCode', 'terminationReason', 'signature']}, sort_keys=True)
                    signature = re.sub(r'0x[0-9a-fA-F]+', '<address>', signature)
                matching = point + ':' + signature
                count = counter.record(matching, True)
                crash = {'step': index, 'kind': 'confirmed crash report' if fresh else 'unexpected termination / suspected crash',
                         'point': point, 'matchingAttempt': count, 'diagnostics': self.redactor.object(fresh),
                         'reproductionSteps': self.redactor.object(history + [action])}
                scenario['crashes'].append(crash); scenario['verdict'] = 'failed'
                entry['crash'] = crash['kind']; entry['matchingAttempt'] = count
                if count >= 3:
                    scenario['remaining'].append('Scenario cancelled after three matching crashing attempts')
                    scenario['steps'].append(entry); self.publish(result); return
                mobile.call('mobile_launch_app', packageName=app_id)
                elements, image = mobile.snapshot()
                entry['recovery'] = 'relaunch succeeded'
            else:
                if counter.point and counter.point.startswith(point + ':'): counter.record(counter.point, False)
                if foreground != app_id:
                    entry['navigation'] = 'Explicit exit or background/external navigation; no matching crash diagnostic'
                    mobile.call('mobile_launch_app', packageName=app_id)
                    elements, image = mobile.snapshot()
            scenario['steps'].append(self.redactor.object(entry)); history.append(self.redactor.object(dict(action, result=entry.get('crash', entry.get('actionError', 'action completed')))))
            self.publish(result)

    def device(self, device, index):
        folder = self.root / 'devices' / ('device-' + str(index))
        folder.mkdir(mode=0o700, parents=True, exist_ok=True)
        result = {'index': index, 'device': self.redactor.object(device), 'scenarios': [], 'error': None, 'stoppingReason': None}
        self.publish(result)
        mobile = Mobile(self.context['nativeBinary'], device, folder, self.context, self.redactor)
        try:
            mobile.connect()
            agent = Agent(self.config, self.budget, self.context['deadline'])
            for build in self.context['builds']:
                if build['platform'] == device['platform']:
                    self.scenario(mobile, build, result, agent)
        except LimitReached as error:
            result['stoppingReason'] = str(error)
            if 'locked' not in str(error): self.stop.set()
        except Exception as error:
            result['error'] = self.redactor.text(str(error) if isinstance(error, InfrastructureError) else type(error).__name__ + ': ' + str(error))
            self.stop.set()
        finally:
            mobile.close(); self.publish(result)

    def run(self):
        if '--preflight' in sys.argv:
            Agent(self.config, self.budget, self.context['deadline']).check_access()
            print('Model access and local runtime/pricing checks passed. No inference request made.')
            return 0
        self.root.joinpath('devices').mkdir(exist_ok=True)
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(lambda item: self.device(item[1], item[0]), enumerate(self.context['devices'], 1)))
        self.save()
        if any(d['error'] for d in self.results): return 3
        if any(s['crashes'] for d in self.results for s in d['scenarios']): return 1
        if not self.results or any(d['stoppingReason'] or not d['scenarios'] or any(s['completion'] != 'complete' for s in d['scenarios']) for d in self.results): return 2
        return 0


if __name__ == '__main__':
    try:
        context = json.load(sys.stdin)
        raise SystemExit(Execution(context).run())
    except (InfrastructureError, LimitReached) as error:
        print('CIMT execution stopped: ' + str(error), file=sys.stderr)
        raise SystemExit(3 if isinstance(error, InfrastructureError) else 2)
    except Exception as error:
        print('CIMT execution infrastructure failed: ' + type(error).__name__, file=sys.stderr)
        raise SystemExit(3)
