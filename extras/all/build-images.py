#!/usr/bin/env python3
"""Build the all-tools image from recorded native base/gateway builds and pinned inputs."""
import argparse,hashlib,importlib.machinery,importlib.util,json,os,pathlib,re,shutil,subprocess,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[2]
loader=importlib.machinery.SourceFileLoader('doctor',str(ROOT/'host/bin/fenced-doctor'))
spec=importlib.util.spec_from_loader(loader.name,loader);doctor=importlib.util.module_from_spec(spec);loader.exec_module(doctor)

def require(ok,msg):
 if not ok:raise ValueError(msg)

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('context','base-image','gateway-image','base-receipt','gateway-receipt','terraform-tag','all-tag','output'):p.add_argument('--'+name,required=True)
 p.add_argument('--inputs',type=pathlib.Path,default=ROOT/'extras/all/image-inputs.json')
 a=p.parse_args();out=pathlib.Path(a.output)
 require(not out.exists(),'output directory exists; inspect previous evidence')
 for value in (a.context,a.base_image,a.gateway_image,a.terraform_tag,a.all_tag):require(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:/@-]*',value),'invalid name')
 _,arch=doctor.host_platform();doctor.check_context(a.context);doctor.check_daemon(a.context,arch)
 inputs=json.loads(a.inputs.read_text());require(inputs.get('version')==1 and arch in inputs.get('platforms',{}),'missing native input entry')
 selected=inputs['platforms'][arch]
 require(set(selected)=={'images','fdb_version','fdb_sha256'} and set(selected['images'])=={'java','redpanda','openbao'},'invalid input fields')
 for value in selected['images'].values():require(re.fullmatch(r'[A-Za-z0-9./_-]+@sha256:[0-9a-f]{64}',value),'immutable registry digest required')
 require(re.fullmatch(r'[0-9.]+',selected['fdb_version']) and re.fullmatch(r'[0-9a-f]{64}',selected['fdb_sha256']),'invalid FDB input')
 command=['docker','--context',a.context]
 def capture(*args):return subprocess.check_output(command+list(args),text=True).strip()
 def inspect(ref):return json.loads(capture('image','inspect',ref))[0]
 existing=capture('image','ls','--format','{{.Repository}}:{{.Tag}}').splitlines()
 require(a.terraform_tag!=a.all_tag,'output tags must differ')
 for tag in (a.terraform_tag,a.all_tag):require(tag not in existing and ':' in tag.rsplit('/',1)[-1] and '@' not in tag,'use unused explicit output tags')
 base=inspect(a.base_image);gateway=inspect(a.gateway_image)
 for image in (base,gateway):require(image['Architecture']==arch and image['Os']=='linux','image architecture mismatch')
 br=json.loads(pathlib.Path(a.base_receipt).read_text());gr=json.loads(pathlib.Path(a.gateway_receipt).read_text())
 require(br.get('complete') and br['images']['agent']['id']==base['Id'],'base receipt mismatch')
 require(gr.get('complete') and gr['agent_image']==gateway['Id'] and gr['base_image']==base['Id'],'gateway receipt mismatch')
 require(br.get('inputs',{}).get('build_args',{}).get('DEBIAN_SNAPSHOT'),'base must use recorded Debian snapshot inputs')
 sources={name:(ROOT/name).read_bytes() for name in ['extras/all/Dockerfile','extras/terraform/Dockerfile']}
 report={'version':1,'architecture':arch,'inputs':selected,'base_image':base['Id'],'gateway_image':gateway['Id'],
         'sources':{k:hashlib.sha256(v).hexdigest() for k,v in sources.items()},'complete':False}
 out.mkdir(mode=0o700)
 def save():(out/'receipt.json').write_text(json.dumps(report,indent=2)+'\n')
 save()
 with (out/'build.log').open('w') as log,tempfile.TemporaryDirectory() as tmp:
  def logged(*args):subprocess.run(command+list(args),stdout=log,stderr=subprocess.STDOUT,check=True)
  for ref in selected['images'].values():
   logged('pull','--platform','linux/'+arch,ref)
   image=inspect(ref);require(image['Architecture']==arch and image['Os']=='linux','external image architecture mismatch')
  ctx=pathlib.Path(tmp)
  for name,data in sources.items():(ctx/(name.split('/')[-2]+'.Dockerfile')).write_bytes(data)
  logged('build','--no-cache','--platform','linux/'+arch,'--build-arg','BASE_IMAGE='+a.base_image,'--tag',a.terraform_tag,'--file',str(ctx/'terraform.Dockerfile'),str(ctx))
  report['terraform_image']=inspect(a.terraform_tag)['Id'];save()
  args=['BASE_IMAGE='+a.base_image,'AGENT_GATEWAY_IMAGE='+a.gateway_image,'TERRAFORM_IMAGE='+a.terraform_tag,
        'JAVA_IMAGE='+selected['images']['java'],'REDPANDA_IMAGE='+selected['images']['redpanda'],
        'OPENBAO_IMAGE='+selected['images']['openbao'],'FDB_VERSION='+selected['fdb_version'],'FDB_SHA256='+selected['fdb_sha256']]
  logged('build','--no-cache','--platform','linux/'+arch,*[v for arg in args for v in ('--build-arg',arg)],'--tag',a.all_tag,'--file',str(ctx/'all.Dockerfile'),str(ctx))
  require(inspect(a.base_image)['Id']==base['Id'] and inspect(a.gateway_image)['Id']==gateway['Id'],'input tag changed during build')
  require(inspect(a.terraform_tag)['Id']==report['terraform_image'],'Terraform tag changed during build')
  image=inspect(a.all_tag);require(image['Architecture']==arch,'output architecture mismatch');report['all_image']=image['Id'];save()
  check='''set -eu
java -version; go version; bao version; rsync --version | head -1
pkg-config --modversion openssl; fdbcli --version; rpk --version; terraform version
mkdir /tmp/tf-check; cd /tmp/tf-check
printf 'terraform { required_version = ">= 1.11" }\n' > main.tf
terraform init -backend=false; terraform validate
sha256sum /usr/local/bin/agentctl
'''
  result=capture('run','--rm','--network=none','--read-only','--cap-drop=ALL','--security-opt=no-new-privileges','--user',f'{os.getuid()}:{os.getgid()}',
                 '--tmpfs','/tmp:rw,mode=1777','--env','HOME=/tmp','--env','CHECKPOINT_DISABLE=1','--entrypoint','sh',image['Id'],'-ec',check)
  (out/'tools.txt').write_text(result+'\n')
  manifest=(ROOT/'extras/agent-gateway/portable/SHA256SUMS').read_text().splitlines()
  expected=next(line.split()[0] for line in manifest if line.endswith('agentctl-linux-'+arch))
  require(expected+'  /usr/local/bin/agentctl' in result,'gateway client checksum mismatch')
  packages=capture('run','--rm','--network=none','--read-only','--entrypoint','dpkg-query',image['Id'],'-W','-f=${Package}\t${Version}\n')
  (out/'packages.tsv').write_text(packages+'\n');report['complete']=True;save()
 print(json.dumps(report,indent=2))
if __name__=='__main__':
 try:main()
 except (ValueError,OSError,KeyError,TypeError,StopIteration,doctor.CheckError,subprocess.CalledProcessError) as e:raise SystemExit(str(e))
