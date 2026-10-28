#!/usr/bin/env python3
"""Build-result contract checks using a simulated dotnet process, not a demo app."""
import json,os,pathlib,shutil,subprocess,tempfile
source=pathlib.Path(__file__).resolve().parents[1]
real_dotnet=shutil.which('dotnet')
worker=source/'tools/Cimt.BuildWorker/bin/Release/net10.0/cimt-build.dll'
with tempfile.TemporaryDirectory(prefix='cimt-build-contract-') as tmp:
 root=pathlib.Path(tmp);bin=root/'bin';bin.mkdir();(root/'App.csproj').write_text('<Project />')
 fake=bin/'dotnet'
 fake.write_text('''#!/usr/bin/env python3
import os,sys,pathlib
args=sys.argv[1:]
if args[0]=='msbuild':print('com.example.fixture');sys.exit(0)
assert args[0]=='publish'
assert '-c' in args and '-f' in args
platform=os.environ['FIXTURE_PLATFORM']
if platform=='ios':assert '-p:RuntimeIdentifier=ios-arm64' in args and '-p:BuildIpa=true' in args
else:assert '-p:AndroidPackageFormats=apk' in args
print('fixture credential: synthetic-signing-secret')
if os.environ['FIXTURE_MODE']=='fail':sys.exit(42)
out=pathlib.Path(args[args.index('--output')+1]);out.mkdir(exist_ok=True)
(out/('app-Signed.apk' if platform=='android' else 'app.ipa')).write_bytes(b'contract-fixture')
if os.environ['FIXTURE_MODE']=='ambiguous':(out/'other-Signed.apk').write_bytes(b'contract-fixture')
''')
 fake.chmod(0o700)
 for platform,mode,expected in [('android','success',0),('ios','success',0),('android','fail',42),('android','ambiguous',3)]:
  request=root/'request.json';result=root/'result.json'
  request.write_text(json.dumps({'project':'App.csproj','configuration':'Release','framework':'net10.0-'+platform,'properties':{'AndroidSigningStorePass':'synthetic-signing-secret'}}))
  result.write_text('{"artifact":"stale.apk","app-id":"stale"}')
  env=os.environ.copy();env.update(PATH=str(bin)+os.pathsep+env['PATH'],CIMT_DOTNET_EXECUTABLE=str(fake),CIMT_REPOSITORY_ROOT=str(root),CIMT_BUILD_REQUEST=str(request),CIMT_BUILD_RESULT=str(result),FIXTURE_PLATFORM=platform,FIXTURE_MODE=mode)
  r=subprocess.run([real_dotnet,str(worker),platform],env=env,capture_output=True,text=True)
  assert r.returncode==expected,(platform,mode,r.returncode,r.stdout[-1200:],r.stderr[-1200:])
  assert 'synthetic-signing-secret' not in r.stdout+r.stderr,'Signing value leaked'
  if expected==0:
   d=json.loads(result.read_text());assert pathlib.Path(d['artifact']).is_absolute() and pathlib.Path(d['artifact']).exists();assert d['app-id']=='com.example.fixture'
  else:assert not result.exists(),'Stale result survived failure'
  print('PASS',platform,mode)
print('4 simulated build-contract checks passed; real application builds are separate.')
