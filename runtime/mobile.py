"""Local Mobile MCP boundary and secret-safe evidence capture."""
import base64, io, json, os, pathlib, re, selectors, subprocess, threading, time
from PIL import Image, ImageDraw
from agent import InfrastructureError, LimitReached


class Redactor:
    def __init__(self, config):
        self.secrets = set()
        def visit(value, sensitive=False):
            if isinstance(value, dict):
                for key, item in value.items():
                    visit(item, sensitive or key == 'credentials' or any(x in key.lower() for x in ['pass', 'secret', 'token', 'key']))
            elif isinstance(value, list):
                for item in value: visit(item, sensitive)
            elif sensitive and str(value): self.secrets.add(str(value))
        visit(config)
        self.ids = {rule['element-id'] for rule in config.get('masking', {}).get('rules', [])}

    def text(self, text):
        text = str(text)
        for secret in sorted(self.secrets, key=len, reverse=True): text = text.replace(secret, '<redacted>')
        return text

    def object(self, value):
        if isinstance(value, dict): return {key: self.object(item) for key, item in value.items()}
        if isinstance(value, list): return [self.object(item) for item in value]
        return self.text(value) if isinstance(value, str) else value

    def sensitive(self, element):
        if element.get('identifier') in self.ids: return True
        if any(x in (element.get('identifier', '') + element.get('type', '')).lower() for x in ['password', 'securetext', 'token', 'secret']): return True
        value = json.dumps(element)
        return any(secret in value for secret in self.secrets)

    def capture(self, raw_elements, image_bytes, size):
        image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
        width, height = size['width'], size['height']
        if width <= 0 or height <= 0: raise InfrastructureError('Screen coordinate size is unavailable')
        sx, sy = image.width / width, image.height / height
        if abs(sx / sy - 1) > .03: raise InfrastructureError('Screen/image coordinate mapping is ambiguous')
        draw = ImageDraw.Draw(image)
        safe = []
        for element in raw_elements:
            item = self.object(element)
            if self.sensitive(element):
                rect = element.get('coordinates', {})
                try:
                    x, y, w, h = [float(rect[key]) for key in ['x', 'y', 'width', 'height']]
                    if w <= 0 or h <= 0: raise ValueError()
                except (KeyError, TypeError, ValueError):
                    raise InfrastructureError('Required element mask has no reliable bounds') from None
                draw.rectangle((max(0, (x - 2) * sx), max(0, (y - 2) * sy),
                                min(image.width, (x + w + 2) * sx), min(image.height, (y + h + 2) * sy)), fill='black')
                for key in ['text', 'label', 'name', 'value']:
                    if key in item: item[key] = '<masked>'
            safe.append(item)
        output = io.BytesIO(); image.save(output, format='PNG')
        return safe, output.getvalue()


class Mcp:
    def __init__(self, folder, env, redactor, deadline):
        self.deadline, self.redactor = deadline, redactor
        self.log = (folder / 'adapter.log').open('w')
        env = dict(env)
        env.pop('OPENAI_API_KEY', None)
        self.p = subprocess.Popen(['mcp-server-mobile', '--stdio'], stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        def drain():
            for line in iter(self.p.stderr.readline, b''):
                self.log.write(redactor.text(line.decode(errors='replace'))); self.log.flush()
        self.reader = threading.Thread(target=drain, daemon=True); self.reader.start()
        self.sel = selectors.DefaultSelector(); self.sel.register(self.p.stdout, selectors.EVENT_READ)
        self.buffer, self.id = b'', 0
        self.request('initialize', {'protocolVersion': '2025-06-18', 'capabilities': {},
                                   'clientInfo': {'name': 'cimt', 'version': '0.1'}})
        self.p.stdin.write(b'{"jsonrpc":"2.0","method":"notifications/initialized"}\n'); self.p.stdin.flush()

    def request(self, method, params, timeout=45):
        if time.time() >= self.deadline: raise LimitReached('Whole-run time limit reached')
        self.id += 1; rid = self.id
        self.p.stdin.write((json.dumps({'jsonrpc': '2.0', 'id': rid, 'method': method, 'params': params}) + '\n').encode()); self.p.stdin.flush()
        until = min(self.deadline, time.time() + timeout)
        while time.time() < until:
            for _, _ in self.sel.select(min(1, max(.01, until - time.time()))):
                chunk = os.read(self.p.stdout.fileno(), 65536)
                if not chunk: raise InfrastructureError('Mobile MCP exited')
                self.buffer += chunk
                while b'\n' in self.buffer:
                    line, self.buffer = self.buffer.split(b'\n', 1)
                    try: response = json.loads(line)
                    except ValueError: continue
                    if response.get('id') == rid:
                        if 'error' in response: raise InfrastructureError('Mobile MCP protocol error')
                        return response['result']
        if time.time() >= self.deadline: raise LimitReached('Whole-run time limit reached')
        raise InfrastructureError('Mobile MCP operation timed out')

    def call(self, name, arguments, timeout=45):
        value = self.request('tools/call', {'name': name, 'arguments': arguments}, timeout)
        if value.get('isError'):
            raise InfrastructureError(self.redactor.text(' '.join(x.get('text', '') for x in value.get('content', []))))
        return value

    def close(self):
        self.p.terminate()
        try: self.p.wait(5)
        except subprocess.TimeoutExpired: self.p.kill(); self.p.wait()
        self.reader.join(2); self.sel.close(); self.log.close()


class Mobile:
    def __init__(self, binary, device, folder, context, redactor):
        self.binary, self.device, self.folder = binary, device, folder
        self.context, self.redactor = context, redactor
        self.env = dict(os.environ, MOBILECLI_HOME=context['nativeHome'])
        self.env.pop('OPENAI_API_KEY', None)
        self.client = None

    def native(self, arguments, timeout=30):
        remaining = self.context['deadline'] - time.time()
        if remaining <= 0: raise LimitReached('Whole-run time limit reached')
        try:
            r = subprocess.run([self.binary] + arguments + ['--device', self.device['id']],
                               capture_output=True, text=True, env=self.env, timeout=min(timeout, remaining))
        except subprocess.TimeoutExpired: raise InfrastructureError('Device command timed out') from None
        if r.returncode != 0: raise InfrastructureError(self.redactor.text(r.stderr[-1000:] or 'Device command failed'))
        try: return json.loads(r.stdout)
        except ValueError: raise InfrastructureError('Device command returned invalid JSON') from None

    def readiness(self):
        if self.device['platform'] == 'ios':
            path = pathlib.Path(self.context['work']) / ('lock-' + self.folder.name + '.json')
            try:
                subprocess.run(['xcrun', 'devicectl', 'device', 'info', 'lockState', '--device', self.device['id'],
                                '--timeout', '15', '--json-output', str(path)], capture_output=True, check=True, timeout=20)
                if json.loads(path.read_text()).get('result', {}).get('passcodeRequired') is not False:
                    raise LimitReached('iPhone is locked; application interaction was not started')
            except (OSError, subprocess.SubprocessError, ValueError):
                raise InfrastructureError('iPhone readiness could not be verified') from None
            finally: path.unlink(missing_ok=True)
        else:
            result = subprocess.run(['adb', '-s', self.device['id'], 'shell', 'dumpsys', 'window', 'policy'], capture_output=True, text=True, timeout=15)
            states = re.findall(r'^\s*showing=(true|false)\s*$', result.stdout, re.M)
            if result.returncode or len(states) != 1:
                raise InfrastructureError('Android lock readiness could not be verified')
            if states[0] != 'false': raise LimitReached('Android phone is locked; application interaction was not started')

    def connect(self):
        self.readiness()
        self.client = Mcp(self.folder, self.env, self.redactor, self.context['deadline'])

    def call(self, name, timeout=45, **arguments):
        return self.client.call(name, dict(device=self.device['id'], **arguments), timeout)

    def app_present(self, app_id):
        data = self.native(['apps', 'list']).get('data', [])
        return any(x.get('packageName') == app_id for x in data)

    def reset(self, artifact, app_id, target):
        if app_id.startswith(('com.apple.', 'com.android.', 'com.mobilenext.')):
            raise InfrastructureError('Refusing to replace a system or automation-helper application')
        # A physical iOS reinstall resets its app container. Keychain/backend
        # state requires an application-specific reset/verification hook.
        if self.app_present(app_id):
            self.call('mobile_uninstall_app', packageName=app_id, timeout=120)
            if self.app_present(app_id): raise InfrastructureError('App removal/reset could not be verified')
        self.call('mobile_install_app', path=artifact, timeout=180)
        if not self.app_present(app_id): raise InfrastructureError('Installed app identifier was not verified')
        if self.device['platform'] == 'android':
            r = subprocess.run(['adb', '-s', self.device['id'], 'shell', 'pm', 'clear', app_id],
                               capture_output=True, text=True, timeout=30)
            if r.returncode or r.stdout.strip() != 'Success': raise InfrastructureError('Android data reset failed')
        for key in ['command', 'verify-command']:
            if key in self.context['config'].get('reset', {}):
                env = dict(self.env, CIMT_TARGET=target, CIMT_DEVICE=self.device['id'], CIMT_APP_ID=app_id)
                r = subprocess.run(self.context['config']['reset'][key], env=env, cwd=self.context.get('resetDirectories', {}).get(key), capture_output=True, text=True, timeout=60)
                if r.returncode: raise InfrastructureError('Configured reset/verification command failed')
        self.call('mobile_launch_app', packageName=app_id)

    def raw_elements(self):
        result = self.call('mobile_list_elements_on_screen', format='json')
        for content in result.get('content', []):
            if content.get('type') == 'text':
                text = content.get('text', ''); start = text.find('[')
                if start >= 0:
                    try: value = json.loads(text[start:])
                    except ValueError: continue
                    if isinstance(value, list): return value
        raise InfrastructureError('No structured UI elements were returned')

    def snapshot(self):
        self.readiness()
        raw = self.raw_elements()
        result = self.call('mobile_take_screenshot')
        image = next((base64.b64decode(c['data']) for c in result.get('content', []) if c.get('type') == 'image'), None)
        if not image: raise InfrastructureError('Step screenshot collection failed')
        size = self.native(['device', 'info']).get('data', {}).get('device', {}).get('screenSize', {})
        # Recheck mask geometry after capturing the image. Never retain an
        # unmasked image when required fields moved while it was captured.
        if any(self.redactor.sensitive(e) for e in raw):
            after = self.raw_elements()
            a = [(e.get('identifier'), e.get('coordinates')) for e in raw if self.redactor.sensitive(e)]
            b = [(e.get('identifier'), e.get('coordinates')) for e in after if self.redactor.sensitive(e)]
            if a != b: raise InfrastructureError('Required mask geometry changed during screenshot capture')
            raw = after
        safe, encoded = self.redactor.capture(raw, image, size)
        with Image.open(io.BytesIO(encoded)) as picture:
            safe.append({'type': 'CimtScreenInfo', 'screenWidth': size['width'], 'screenHeight': size['height'],
                         'imageWidth': picture.width, 'imageHeight': picture.height})
        return safe, encoded

    def foreground(self):
        return self.native(['apps', 'foreground']).get('data', {}).get('packageName')

    def running(self, app_id, executable):
        if self.device['platform'] == 'android':
            r = subprocess.run(['adb', '-s', self.device['id'], 'shell', 'pidof', app_id], capture_output=True, timeout=15)
            return r.returncode == 0 and bool(r.stdout.strip())
        path = pathlib.Path(self.context['work']) / ('processes-' + self.folder.name + '.json')
        try:
            subprocess.run(['xcrun', 'devicectl', 'device', 'info', 'processes', '--device', self.device['id'],
                            '--timeout', '15', '--json-output', str(path)], capture_output=True, check=True, timeout=20)
            data = json.loads(path.read_text()).get('result', {})
            return executable in json.dumps(data)
        finally: path.unlink(missing_ok=True)

    def crashes(self):
        return self.native(['device', 'crashes', 'list'], timeout=30).get('data', [])

    def close(self):
        if self.client: self.client.close()
