#!/usr/bin/env python3
"""Host-owned disposable OpenBao TLS lifecycle; never prints generated credentials."""
import argparse
import json
import os
import subprocess


def run(*args, capture=False):
    return subprocess.run(['docker', *args], check=True, text=True,
                          stdout=subprocess.PIPE if capture else None).stdout


def main():
    p = argparse.ArgumentParser()
    p.add_argument('action', choices=['up', 'install', 'ready', 'down', 'clean'])
    args = p.parse_args()
    name = os.getenv('OPENBAO_TLS_CONTAINER', 'go-agent-openbao-tls')
    volume = name + '-private'
    network = os.getenv('AGENT_INTERNAL_NETWORK', 'go-agent-internal-net')
    image = os.getenv('OPENBAO_IMAGE', 'quay.io/openbao/openbao:2.7.1')
    helper = os.getenv('AGENT_IMAGE', 'go-agent-all')
    home = os.getenv('AGENTHOME', 'agenthome')
    uid, gid = str(os.getuid()), str(os.getgid())
    if not all(c.isalnum() or c in '.-' for c in name) or not name:
        raise SystemExit('Invalid TLS container/DNS name')
    label = 'io.fenced.disposable-openbao'
    existing = subprocess.run(['docker', 'volume', 'inspect', volume], capture_output=True, text=True)
    if existing.returncode == 0 and (json.loads(existing.stdout)[0].get('Labels') or {}).get(label) != 'tls':
        raise SystemExit('Refusing private volume not labeled as this disposable TLS extra')
    if args.action != 'up' and existing.returncode != 0:
        raise SystemExit('Disposable TLS private volume does not exist')
    if args.action == 'up':
        run('network', 'inspect', network, capture=True)
        present = subprocess.run(['docker', 'container', 'inspect', name], capture_output=True)
        if present.returncode == 0:
            raise SystemExit('Container already exists; refusing to replace disposable state')
        run('volume', 'create', '--label', label+'=tls', volume, capture=True)
        setup = r'''set -eu
umask 077
if [ ! -f /private/ready ]; then
  test -z "$(ls -A /private)" || { echo 'Incomplete TLS material; inspect before cleanup' >&2; exit 1; }
  openssl req -x509 -newkey rsa:2048 -nodes -days 30 -subj /CN=Fenced-OpenBao-Test-CA -keyout /private/ca.key -out /private/ca.crt >/dev/null 2>&1
  openssl req -newkey rsa:2048 -nodes -subj "/CN=$1" -keyout /private/server.key -out /private/server.csr >/dev/null 2>&1
  printf 'subjectAltName=DNS:%s\nbasicConstraints=CA:FALSE\nkeyUsage=digitalSignature,keyEncipherment\nextendedKeyUsage=serverAuth\n' "$1" > /private/server.ext
  openssl x509 -req -in /private/server.csr -CA /private/ca.crt -CAkey /private/ca.key -CAcreateserial -days 30 -extfile /private/server.ext -out /private/server.crt >/dev/null 2>&1
  openssl rand -hex 32 > /private/root-token
  printf 'disable_mlock = true\nlistener "tcp" {\n address = "0.0.0.0:8443"\n tls_cert_file = "/private/server.crt"\n tls_key_file = "/private/server.key"\n}\n' > /private/server.hcl
  touch /private/ready
fi
openssl verify -CAfile /private/ca.crt -verify_hostname "$1" /private/server.crt >/dev/null
chown -R "$2:$3" /private
chmod 0700 /private
chmod 0600 /private/*
chmod 0644 /private/ca.crt /private/server.crt
'''
        run('run', '--rm', '--network', 'none', '--user', '0:0', '--mount',
            f'type=volume,src={volume},dst=/private', helper, 'sh', '-ec', setup,
            'setup', name, uid, gid)
        start = 'export BAO_DEV_ROOT_TOKEN_ID="$(cat /private/root-token)"; exec bao server -dev -config=/private/server.hcl > /tmp/server.log 2>&1'
        run('run', '-d', '--name', name, '--label', label+'=tls', '--network', network, '--user', uid+':'+gid,
            '--read-only', '--cap-drop=ALL', '--security-opt=no-new-privileges',
            '--tmpfs', '/tmp:rw,mode=1777', '-e', 'HOME=/tmp', '--mount',
            f'type=volume,src={volume},dst=/private,readonly', '--entrypoint', 'sh', image, '-ec', start,
            capture=True)
        print('Started disposable TLS service; run ready, then install')
    elif args.action == 'install':
        # Explicit selective credential delivery, not part of the public docs installer.
        run('volume', 'inspect', home, capture=True)
        script = '''set -eu
install -d -m 0700 -o "$1" -g "$2" /home/agent/.openbao-test
install -m 0644 -o "$1" -g "$2" /private/ca.crt /home/agent/.openbao-test/ca.crt
install -m 0600 -o "$1" -g "$2" /private/root-token /home/agent/.openbao-test/token
'''
        run('run', '--rm', '--network', 'none', '--user', '0:0', '--mount',
            f'type=volume,src={volume},dst=/private,readonly', '--mount',
            f'type=volume,src={home},dst=/home/agent', helper, 'sh', '-ec', script, 'install', uid, gid)
        print('Installed public CA and mode-0600 disposable token in agenthome/.openbao-test')
    elif args.action == 'ready':
        run('run', '--rm', '--network', network, '--user', uid+':'+gid,
            '--mount', f'type=volume,src={volume},dst=/private,readonly', '--entrypoint', 'bao',
            '-e', f'BAO_ADDR=https://{name}:8443', '-e', 'BAO_CACERT=/private/ca.crt', image, 'status')
    elif args.action == 'down':
        metadata = json.loads(run('inspect', name, capture=True))[0]
        if (metadata['Config'].get('Labels') or {}).get(label) != 'tls':
            raise SystemExit('Refusing to remove an unlabelled container')
        run('rm', '-f', '-v', name)
    elif args.action == 'clean':
        # Volume removal refuses while referenced by a container. Never broad-clean Docker.
        run('volume', 'rm', volume)
        print('Removed private TLS material. Installed agent CA/token are now stale; remove or replace them explicitly.')


if __name__ == '__main__':
    main()
