#!/usr/bin/env python3
"""Non-admin physical Settings smoke test; no credentials or evidence are published."""
import argparse,base64,concurrent.futures,json,pathlib,time,urllib.request,urllib.error
BASE='http://127.0.0.1:4727'
def request(method,path,body=None):
    data=None if body is None else json.dumps(body).encode()
    r=urllib.request.Request(BASE+path,data=data,method=method,headers={'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(r,timeout=180) as response:return json.load(response).get('value')
    except urllib.error.HTTPError as e:
        d=json.load(e).get('value',{});raise RuntimeError(d.get('message',str(d))[:2000])
def probe(device,root,team):
    platform=device['platform'];folder=root/('appium-'+platform);folder.mkdir(mode=0o700,exist_ok=True)
    caps={'platformName':platform,'appium:udid':device['id'],'appium:noReset':True,'appium:newCommandTimeout':60}
    if platform=='android':caps.update({'appium:automationName':'UiAutomator2','appium:appPackage':'com.android.settings','appium:appActivity':'.Settings','appium:systemPort':8210})
    else:caps.update({'appium:automationName':'XCUITest','appium:bundleId':'com.apple.Preferences','appium:wdaLocalPort':8110,'appium:showXcodeLog':True,'appium:xcodeOrgId':team,'appium:xcodeSigningId':'Apple Development','appium:derivedDataPath':str(folder/'wda-build')})
    sid=None;events=[]
    def check(name,fn):
        start=time.monotonic()
        try:
            value=fn();events.append({'check':name,'status':'passed','seconds':round(time.monotonic()-start,3)});return value
        except Exception as e:events.append({'check':name,'status':'failed','seconds':round(time.monotonic()-start,3),'error':str(e)});return None
    try:
        result=check('create-physical-session',lambda:request('POST','/session',{'capabilities':{'alwaysMatch':caps}}))
        if result:
            sid=result['sessionId']
            source=check('read-ui-elements',lambda:request('GET',f'/session/{sid}/source'))
            if source:(folder/'source.xml').write_text(source)
            shot=check('screenshot',lambda:request('GET',f'/session/{sid}/screenshot'))
            if shot:(folder/'screen.png').write_bytes(base64.b64decode(shot))
            if platform=='android':
                check('back-button',lambda:request('POST',f'/session/{sid}/back',{}))
    finally:
        if sid:check('close-session',lambda:request('DELETE',f'/session/{sid}'))
    (folder/'results.json').write_text(json.dumps(events,indent=2));return {'platform':platform,'checks':events}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--team',default='');p.add_argument('--platform',choices=['android','ios']);a=p.parse_args()
    root=pathlib.Path(a.output);devices=json.loads((root/'devices-private.json').read_text())
    if a.platform:devices=[d for d in devices if d['platform']==a.platform]
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda d:probe(d,root,a.team),devices[:2]))
    (root/('appium-'+(a.platform or 'all')+'-results.json')).write_text(json.dumps(results,indent=2));print(json.dumps(results,indent=2))
