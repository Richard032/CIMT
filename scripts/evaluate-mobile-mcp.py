#!/usr/bin/env python3
"""Local physical-device probe. Evidence remains outside the source repository."""
import argparse, base64, concurrent.futures, json, os, pathlib, selectors, subprocess, time

class Mcp:
    def __init__(self, log):
        self.log = open(log, 'wb')
        self.p = subprocess.Popen(['mcp-server-mobile', '--stdio'], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=self.log)
        self.sel = selectors.DefaultSelector(); self.sel.register(self.p.stdout, selectors.EVENT_READ)
        self.buffer = b''; self.id = 0
        self.request('initialize', {'protocolVersion':'2025-06-18','capabilities':{},
            'clientInfo':{'name':'cimt-device-evaluation','version':'0.1'}})
        self.p.stdin.write(b'{"jsonrpc":"2.0","method":"notifications/initialized"}\n'); self.p.stdin.flush()
    def request(self, method, params, timeout=45):
        self.id += 1; rid = self.id
        self.p.stdin.write((json.dumps({'jsonrpc':'2.0','id':rid,'method':method,'params':params})+'\n').encode()); self.p.stdin.flush()
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            for _,_ in self.sel.select(1):
                chunk=os.read(self.p.stdout.fileno(),65536)
                if not chunk: raise RuntimeError('MCP server exited')
                self.buffer+=chunk
                while b'\n' in self.buffer:
                    line,self.buffer=self.buffer.split(b'\n',1)
                    try: response=json.loads(line)
                    except ValueError: continue
                    if response.get('id')==rid:
                        if 'error' in response: raise RuntimeError(str(response['error']))
                        return response['result']
        raise TimeoutError(method)
    def call(self, tool, args):
        r=self.request('tools/call',{'name':tool,'arguments':args})
        if r.get('isError'): raise RuntimeError(' '.join(c.get('text','') for c in r.get('content',[])))
        return r
    def close(self):
        self.p.terminate()
        try:self.p.wait(5)
        except subprocess.TimeoutExpired:self.p.kill();self.p.wait()
        self.log.close()

def probe(device, output):
    platform=device['platform']; folder=output/platform; folder.mkdir(mode=0o700,exist_ok=True)
    events=[]
    def check(name, fn):
        start=time.monotonic()
        try:
            value=fn(); events.append({'check':name,'status':'passed','seconds':round(time.monotonic()-start,3)}); return value
        except Exception as e:
            events.append({'check':name,'status':'failed','seconds':round(time.monotonic()-start,3),'error':str(e)[:1800]}); return None
    args={'device':device['id']}
    if platform=='ios':
        def unlocked():
            path=folder/'lock-state-private.json'
            subprocess.run(['xcrun','devicectl','device','info','lockState','--device',device['id'],'--timeout','15','--json-output',str(path)],capture_output=True,check=True,timeout=20)
            if json.loads(path.read_text()).get('result',{}).get('passcodeRequired') is not False:
                raise RuntimeError('iPhone must be unlocked before application control checks')
            return True
        if not check('device-unlocked',unlocked):
            (folder/'results.json').write_text(json.dumps(events,indent=2))
            return {'platform':platform,'checks':events}
    client=Mcp(folder/'mcp.log')
    def screenshot(name):
        result=client.call('mobile_take_screenshot',args)
        images=[c for c in result.get('content',[]) if c.get('type')=='image']
        if not images:raise RuntimeError('Screenshot response contained no image')
        (folder/name).write_bytes(base64.b64decode(images[0]['data']))
        return result
    try:
        app='com.android.settings' if platform=='android' else 'com.apple.Preferences'
        check('launch-settings',lambda:client.call('mobile_launch_app',dict(args,packageName=app)))
        result=check('read-ui-elements',lambda:client.call('mobile_list_elements_on_screen',dict(args,format='json')))
        if result: (folder/'elements.json').write_text(json.dumps(result))
        check('screenshot',lambda:screenshot('screen.jpg'))
        check('swipe',lambda:client.call('mobile_swipe_on_screen',dict(args,direction='up')))
        check('home-button',lambda:client.call('mobile_press_button',dict(args,button='HOME')))
        result=check('read-home-ui',lambda:client.call('mobile_list_elements_on_screen',dict(args,format='json')))
        if result:(folder/'home-elements.json').write_text(json.dumps(result))
        check('home-screenshot',lambda:screenshot('home.jpg'))
    finally:client.close()
    (folder/'results.json').write_text(json.dumps(events,indent=2))
    return {'platform':platform,'checks':events}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--platform',choices=['android','ios']);a=p.parse_args()
    output=pathlib.Path(a.output);output.mkdir(mode=0o700,parents=True,exist_ok=True)
    root=pathlib.Path(os.environ['CIMT_INSTALL_ROOT'])
    module=root/'tools/node-packages/lib/node_modules/@mobilenext/mobile-mcp/lib/mobilecli.js'
    code='const {Mobilecli}=require(process.argv[1]); console.log(JSON.stringify(new Mobilecli().getDevices({type:"real"})));'
    d=json.loads(subprocess.check_output(['node','-e',code,str(module)],text=True))
    devices=[x for x in d.get('data',{}).get('devices',[]) if x.get('state')=='online']
    if a.platform:devices=[x for x in devices if x['platform']==a.platform]
    if not devices:raise RuntimeError('No matching physical device is online')
    (output/'devices-private.json').write_text(json.dumps(devices,indent=2))
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda x:probe(x,output),devices[:2]))
    (output/'mobile-mcp-results.json').write_text(json.dumps(results,indent=2))
    print(json.dumps(results,indent=2))
