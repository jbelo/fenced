#!/usr/bin/env python3
"""Build native gateway/client images from the verified portable delivery."""
import argparse,hashlib,json,os,pathlib,platform,re,subprocess,tarfile,tempfile,shutil
root=pathlib.Path(__file__).resolve().parent

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for flag in ('context','go-image','base-image','gateway-tag','agent-tag','output'):p.add_argument('--'+flag,required=True)
 a=p.parse_args();out=pathlib.Path(a.output)
 def require(ok,msg):
  if not ok:raise ValueError(msg)
 def docker(*args):return subprocess.check_output(['docker','--context',a.context,*args],text=True).strip()
 for v in (a.context,a.go_image,a.base_image,a.gateway_tag,a.agent_tag):require(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:/@-]*',v),'invalid name')
 require(re.fullmatch(r'.+@sha256:[0-9a-f]{64}',a.go_image),'supply an immutable Go image digest')
 require(not out.exists(),'output directory exists')
 require(a.agent_tag!=a.gateway_tag,'output tags must differ')
 for key in ('DOCKER_HOST','DOCKER_TLS_VERIFY','DOCKER_CERT_PATH','DOCKER_API_VERSION'):require(not os.environ.get(key),'unset Docker overrides')
 require(os.environ.get('DOCKER_CONTEXT',a.context)==a.context,'context conflict')
 endpoint=json.loads(docker('context','inspect',a.context,'--format','{{json .Endpoints.docker.Host}}'))
 require(endpoint.startswith('unix:///'),'local Docker socket required')
 arch={'aarch64':'arm64','arm64':'arm64','x86_64':'amd64'}.get(platform.machine())
 info=json.loads(docker('info','--format','{{json .}}'))
 require(arch and info['OSType']=='linux' and {'aarch64':'arm64','x86_64':'amd64'}.get(info['Architecture'],info['Architecture'])==arch,'native architecture mismatch')
 existing=docker('image','ls','--format','{{.Repository}}:{{.Tag}}').splitlines()
 for tag in (a.agent_tag,a.gateway_tag):require(':' in tag.rsplit('/',1)[-1] and tag not in existing and '@' not in tag,'use unused explicit output tags')
 expected={'source-snapshot.tar.gz':'0511e56f774d806a2db21a27cd3e9c77741b1e28ed98b7599bbb36867f4f1268','source-manifest.json':'1124ede0ed55b639730d57e69c19b4e1d5d357e06a3db08e0a50cf512409a9b6'}
 for name,digest in expected.items():require(hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,'source identity mismatch')
 manifest=json.loads((root/'source-manifest.json').read_text())
 with tarfile.open(root/'source-snapshot.tar.gz') as archive:
  files={m.name.removeprefix('agent-gateway/'):m for m in archive.getmembers() if m.isfile()}
  require(set(files)==set(manifest['source_files'])|{'source-manifest.json'},'source file set mismatch')
  for name,digest in manifest['source_files'].items():require(hashlib.sha256(archive.extractfile(files[name]).read()).hexdigest()==digest,'source file mismatch')
 base=json.loads(docker('image','inspect',a.base_image))[0]
 require(base['Architecture']==arch and base['Os']=='linux','base image mismatch')
 out.mkdir(mode=0o700)
 receipt={'architecture':arch,'source':expected,'base_image':base['Id'],'go_image':a.go_image,'complete':False}
 def save():(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
 save()
 with (out/'build.log').open('w') as log,tempfile.TemporaryDirectory() as tmp:
  context=pathlib.Path(tmp)
  def build(tag,file,args):
   subprocess.run(['docker','--context',a.context,'build','--no-cache','--platform','linux/'+arch,'--tag',tag,'--file',str(context/file),*args,str(context)],stdout=log,stderr=subprocess.STDOUT,check=True)
  subprocess.run(['docker','--context',a.context,'pull','--platform','linux/'+arch,a.go_image],stdout=log,stderr=subprocess.STDOUT,check=True)
  for name in ('source-snapshot.tar.gz','SHA256SUMS','Dockerfile.gateway'):shutil.copyfile(root/name,context/name)
  build(a.gateway_tag,'Dockerfile.gateway',['--build-arg','GO_IMAGE='+a.go_image])
  receipt['gateway_image']=json.loads(docker('image','inspect',a.gateway_tag))[0]['Id'];save()
  (context/'source-snapshot.tar.gz').unlink()
  shutil.copyfile(root/'Dockerfile.agent',context/'Dockerfile.agent');shutil.copyfile(root.parent/'agentctl.json',context/'agentctl.json')
  build(a.agent_tag,'Dockerfile.agent',['--build-arg','BASE_IMAGE='+a.base_image,'--build-arg','GATEWAY_IMAGE='+a.gateway_tag])
  require(json.loads(docker('image','inspect',a.base_image))[0]['Id']==base['Id'],'base tag changed during build')
  require(json.loads(docker('image','inspect',a.gateway_tag))[0]['Id']==receipt['gateway_image'],'gateway tag changed during build')
  receipt['agent_image']=json.loads(docker('image','inspect',a.agent_tag))[0]['Id'];receipt['complete']=True;save()
 print(json.dumps(receipt,indent=2))
if __name__=='__main__':
 try:main()
 except (ValueError,OSError,KeyError,subprocess.CalledProcessError) as e:raise SystemExit(str(e))
