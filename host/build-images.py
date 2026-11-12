#!/usr/bin/env python3
"""Build native base images from a minimal public-source context and record provenance."""
import argparse
import hashlib
import importlib.machinery
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]
loader = importlib.machinery.SourceFileLoader('doctor', str(ROOT/'host/bin/fenced-doctor'))
spec = importlib.util.spec_from_loader(loader.name, loader)
doctor = importlib.util.module_from_spec(spec)
loader.exec_module(doctor)


def validate_npm_lock(contents, build_args):
    package = json.loads(contents['host/images/package.json'])
    lock = json.loads(contents['host/images/package-lock.json'])
    expected = {'@openai/codex': build_args['CODEX_VERSION'],
                '@anthropic-ai/claude-code': build_args['CLAUDE_VERSION']}
    if package.get('dependencies') != expected or lock.get('lockfileVersion') != 3:
        raise ValueError('npm package versions do not match recorded inputs')
    packages = lock['packages']
    if packages[''].get('dependencies') != expected:
        raise ValueError('npm lock root differs from package manifest')
    for key, item in packages.items():
        if not key: continue
        if not item.get('resolved', '').startswith('https://registry.npmjs.org/') or not re.fullmatch(r'sha512-[A-Za-z0-9+/=]+', item.get('integrity', '')):
            raise ValueError('npm lock entry lacks registry URL or SHA-512 integrity')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--context', required=True)
    parser.add_argument('--agent-tag', required=True)
    parser.add_argument('--proxy-tag', required=True)
    parser.add_argument('--output', required=True, type=Path, help='new directory for source context, log and receipt')
    parser.add_argument('--go-image', default='golang:1.27.3-bookworm')
    parser.add_argument('--debian-image', default='debian:12-slim')
    parser.add_argument('--inputs', type=Path, help='versioned base digest and tool input file')
    parser.add_argument('--apply', action='store_true', help='pull/build; default only checks and prints plan')
    args = parser.parse_args()
    def require(ok, msg):
        if not ok: raise ValueError(msg)
    require(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', args.context), 'invalid context')
    for value in (args.agent_tag, args.proxy_tag, args.go_image, args.debian_image):
        require(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_./:@-]*', value), 'invalid image reference')
    require(args.agent_tag != args.proxy_tag, 'output image names must differ')
    require(not args.output.exists(), 'output directory already exists; inspect previous receipt')
    _, arch = doctor.host_platform()
    build_args = {}
    inputs = None
    if args.inputs:
        inputs = json.loads(args.inputs.read_text())
        require(inputs.get('version') == 1 and arch in inputs.get('platforms', {}), 'input file has no native platform entry')
        bases = inputs['platforms'][arch]
        for key in ('go','debian'):
            require(re.fullmatch(r'[A-Za-z0-9./_-]+@sha256:[0-9a-f]{64}', bases[key]), 'inputs require immutable base digests')
        require(args.go_image == 'golang:1.27.3-bookworm' and args.debian_image == 'debian:12-slim', 'do not combine input file with base overrides')
        args.go_image, args.debian_image = bases['go'], bases['debian']
        build_args = inputs['build_args']
        require(set(build_args) == {'GIT_VERSION','GIT_SHA256','TMUX_VERSION','TMUX_SHA256','NODE_VERSION','CODEX_VERSION','CLAUDE_VERSION','DEBIAN_SNAPSHOT','NODE_DIST_VERSION','NODE_SHA256','LOCKED_NPM'}, 'unexpected build input fields')
        for key,value in build_args.items():
            require(type(value) is str and re.fullmatch(r'[A-Za-z0-9.+_-]+',value), 'invalid build input')
            if key.endswith('SHA256'): require(re.fullmatch(r'[0-9a-f]{64}',value), 'invalid archive checksum')
    if inputs:
        require(build_args['LOCKED_NPM'] == '1', 'recorded inputs must enable npm lock')
        require(re.fullmatch(r'[0-9]{8}T[0-9]{6}Z', build_args['DEBIAN_SNAPSHOT']), 'invalid Debian snapshot timestamp')
    doctor.check_context(args.context)
    doctor.check_daemon(args.context, arch)
    command = ['docker', '--context', args.context]
    def capture(*parts):
        return subprocess.check_output(command + list(parts), text=True).strip()
    existing = capture('image','ls','--format','{{.Repository}}:{{.Tag}}').splitlines()
    for tag in (args.agent_tag, args.proxy_tag):
        require('@' not in tag and ':' in tag.rsplit('/',1)[-1], 'output names require an explicit tag')
        require(tag not in existing, 'output tag already exists: '+tag)
    files = ['Dockerfile', 'Dockerfile.squid', 'scripts/ssh.sh', 'host/images/apt-snapshot.sh', 'host/images/package.json', 'host/images/package-lock.json']
    contents = {}
    for filename in files:
        source = ROOT/filename
        require(source.is_file() and not source.is_symlink(), 'source must be a regular file: '+filename)
        contents[filename] = source.read_bytes()
    if inputs: validate_npm_lock(contents, build_args)
    manifest = {name:hashlib.sha256(data).hexdigest() for name,data in contents.items()}
    report = {'version':1,'architecture':arch,'context':args.context,'sources':manifest,
              'images':{},'bases':{},'complete':False,'inputs':inputs,
              'limitation':('Recorded inputs freeze acquisition dependencies; no bit-for-bit OCI image reproducibility claim.' if inputs else 'Without --inputs, dependency acquisition follows legacy rolling defaults.')}
    print(json.dumps({'agent':args.agent_tag,'proxy':args.proxy_tag,'source_files':files,
                      'architecture':arch,'apply':args.apply},indent=2),flush=True)
    if not args.apply: return
    args.output.mkdir(mode=0o700)
    receipt=args.output/'receipt.json'
    def save(): receipt.write_text(json.dumps(report,indent=2)+'\n')
    save()
    archive=args.output/'context.tar'
    with tarfile.open(archive,'w') as tar:
        for filename,data in contents.items():
            item=tarfile.TarInfo(filename);item.size=len(data);item.mode=0o755 if filename.endswith('.sh') else 0o644
            tar.addfile(item,io.BytesIO(data))
    report['context_sha256']=hashlib.sha256(archive.read_bytes()).hexdigest();save()
    with (args.output/'build.log').open('w') as log:
        def logged(*parts, stdin=None):
            subprocess.run(command+list(parts),stdin=stdin,stdout=log,stderr=subprocess.STDOUT,check=True)
            log.flush()
        for role,base in [('go',args.go_image),('debian',args.debian_image)]:
            logged('pull','--platform','linux/'+arch,base)
            info=json.loads(capture('image','inspect',base))[0]
            require(info['Architecture']==arch and info['Os']=='linux','base architecture mismatch')
            require(info.get('RepoDigests'),'base has no registry digest')
            report['bases'][role]={'requested':base,'digest':info['RepoDigests'][0],'id':info['Id']};save()
        extra_args = [part for key,value in build_args.items() for part in ('--build-arg',key+'='+value)]
        for role,tag,filename,key,arg in [('agent',args.agent_tag,'Dockerfile','go','GO_IMAGE'),
                                        ('proxy',args.proxy_tag,'Dockerfile.squid','debian','DEBIAN_IMAGE')]:
            with archive.open('rb') as stream:
                logged('build','--no-cache','--pull','--platform','linux/'+arch,'--tag',tag,
                       '--build-arg',arg+'='+report['bases'][key]['digest'],*(extra_args if role=='agent' else ['--build-arg','DEBIAN_SNAPSHOT='+build_args.get('DEBIAN_SNAPSHOT','')]),'--file',filename,'-',stdin=stream)
            image_id=doctor.check_image(args.context,tag,arch)
            packages=capture('run','--rm','--network=none','--read-only','--cap-drop=ALL',
                             '--security-opt=no-new-privileges','--entrypoint','dpkg-query',image_id,
                             '-W','-f=${Package}\t${Version}\n')
            (args.output/(role+'-packages.tsv')).write_text(packages+'\n')
            report['images'][role]={'reference':tag,'id':image_id};save()
            if role=='agent':
                versions=capture('run','--rm','--network=none','--read-only','--tmpfs','/tmp',
                    '--cap-drop=ALL','--security-opt=no-new-privileges','--entrypoint','sh',image_id,
                    '-ec','git --version; tmux -V; go version; node --version; npm --version; codex --version; claude --version; rsync --version | head -1')
                (args.output/'agent-versions.txt').write_text(versions+'\n')
        report['complete']=True;save()
    print('Build complete: '+str(receipt))


if __name__=='__main__':
    try: main()
    except (ValueError,OSError,KeyError,TypeError,subprocess.CalledProcessError,doctor.CheckError) as exc:
        raise SystemExit('build-images: '+str(exc)+'; inspect the retained build log/receipt before retrying')
