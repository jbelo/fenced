"""Gateway-specific host profile contract; never reads credential contents."""
import ipaddress
import json
import os
from pathlib import Path
import re
import stat


def check(ok, message):
    if not ok:
        raise ValueError('agent-gateway: ' + message)


def normalize(value, directory, profile):
    check(type(value) is dict and set(value) == {'container', 'image', 'address', 'config', 'policy', 'secrets'}, 'invalid service fields')
    result = dict(value)
    check(type(value['secrets']) is dict, 'secrets must describe a staged credential volume')
    root = Path(profile['workspace']['root'])
    def private_file(value):
        check(type(value) is str and value, 'invalid file path')
        raw = directory / value
        resolved = raw.resolve(strict=True)
        check(raw.absolute() == resolved and resolved.is_file(), 'files must be regular, without symlink components')
        check(root != resolved and root not in resolved.parents, 'runtime files must be outside the agent workspace')
        check(not any(c in str(resolved) for c in ',:\n\r'), 'invalid mount path')
        parent = resolved.parent.stat(); info = resolved.stat()
        check(parent.st_uid == os.getuid() and stat.S_IMODE(parent.st_mode) == 0o700, 'runtime file parent must be operator-owned mode 0700')
        check(info.st_uid == os.getuid() and stat.S_IMODE(info.st_mode) == 0o444 and info.st_nlink == 1,
              'config/policy require operator ownership and 0444; one hard link only')
        return str(resolved)
    result['config'] = private_file(value['config'])
    result['policy'] = private_file(value['policy'])
    if value['secrets']:
        check(set(value['secrets']) == {'volume','helper_image'}, 'use a dedicated staged volume and trusted local helper_image; host secret paths are unsupported')
        volume = value['secrets']['volume']
        check(type(volume) is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}', volume), 'invalid credential volume')
        check(volume not in profile['state'].values(), 'credential volume must be separate from agent state')
        check(type(value['secrets']['helper_image']) is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._/:@-]*', value['secrets']['helper_image']), 'invalid helper image')
    address = ipaddress.IPv4Address(value['address'])
    subnet = ipaddress.IPv4Network(profile['network']['subnet'])
    check(address in subnet and address not in (subnet.network_address, subnet.broadcast_address, subnet.network_address + 1), 'address must be a usable reserved address in network.subnet')
    config = json.loads(Path(result['config']).read_text())
    check(set(config) == {'version','mode','listen_address','policy_file','providers'}, 'invalid gateway configuration fields')
    check(config['version'] == 1 and config['mode'] in ('mock','live'), 'unsupported gateway mode')
    check(config['listen_address'] == str(address)+':8080' and config['policy_file'] == '/etc/agent-gateway/policy.json', 'config must bind the selected internal address and policy path')
    check(type(config['providers']) is dict and set(config['providers']) == {'github','shortcut'}, 'unsupported providers')
    referenced = set()
    def token(v, enabled):
        check(type(v) is str and re.fullmatch(r'/run/secrets/[A-Za-z0-9][A-Za-z0-9_-]{0,63}', v), 'invalid token file reference')
        if enabled: referenced.add(v.rsplit('/',1)[1])
    for provider, item in config['providers'].items():
        allowed = {'enabled','token_file'} if provider == 'github' else {'enabled','workspaces'}
        check(type(item) is dict and set(item) <= allowed and type(item.get('enabled')) is bool, 'invalid provider fields; inline credentials are not accepted')
        if provider == 'github':
            if 'token_file' in item:
                check(item['token_file'] == '/run/secrets/github_token', 'invalid GitHub token path')
                token(item['token_file'], item['enabled'])
            check(config['mode'] != 'live' or not item['enabled'] or 'token_file' in item, 'live GitHub requires a token file')
        else:
            check(type(item.get('workspaces',[])) is list, 'invalid workspaces')
            for ws in item.get('workspaces',[]):
                check(type(ws) is dict and set(ws) == {'alias','workspace_id','token_file'}, 'invalid workspace fields')
                check(type(ws['alias']) is str and re.fullmatch(r'[a-z0-9][a-z0-9-]*',ws['alias']) and ws['token_file'] == '/run/secrets/shortcut_'+ws['alias'], 'invalid Shortcut token path')
                token(ws['token_file'], item['enabled'])
    check(not result['secrets'] if config['mode'] == 'mock' else bool(result['secrets']) == bool(referenced), 'mock mounts no secrets; enabled live credentials require a staged volume')
    return result


def describe(value):
    config = json.loads(Path(value['config']).read_text())
    names = set()
    for provider in config['providers'].values():
        if provider.get('enabled'):
            if provider.get('token_file'): names.add(provider['token_file'].rsplit('/',1)[1])
            names.update(ws['token_file'].rsplit('/',1)[1] for ws in provider.get('workspaces',[]))
    volumes = []
    if value['secrets']:
        volumes.append({'name':value['secrets']['volume'], 'target':'/run/secrets',
                        'required_label':{'agent-gateway.credentials':'true'},
                        'helper_image':value['secrets']['helper_image'],
                        'probe':['/bin/sh','-ec',VOLUME_CHECK,'credential-volume',*sorted(names)]})
    return {'name':value['container'], 'image':value['image'], 'address':value['address'],
            'alias':'agent-gateway', 'user':'10001:10001',
            'files':[(value['config'],'/etc/agent-gateway/config.json',False),
                     (value['policy'],'/etc/agent-gateway/policy.json',False)],
            **({'volumes': volumes} if volumes else {}),
            "client_probe": ['node', '-e', "const fs=require('fs'); if(process.env.AGENTCTL_CONFIG!=='/etc/agentctl/config.json'||JSON.parse(fs.readFileSync('/etc/agentctl/config.json')).gateway_url!=='http://agent-gateway:8080')process.exit(1);fs.accessSync('/usr/local/bin/agentctl',fs.constants.X_OK)"],
            'health':['/usr/local/bin/gateway-healthcheck']}


# Same read/discard checks as the delivered scripts/credential_volume.py.
# No credential bytes or hashes are emitted; run as gateway UID with no network.
VOLUME_CHECK = """test "$(stat -c '%u:%g:%a' /run/secrets)" = '10001:10001:700'
test "$(find /run/secrets -mindepth 1 -maxdepth 1 | wc -l)" -eq "$#"
for name do
  file="/run/secrets/$name"
  test ! -L "$file"
  test -f "$file"
  test "$(stat -c '%u:%g:%a' "$file")" = '10001:10001:400'
  size=$(stat -c '%s' "$file")
  test "$size" -gt 0
  test "$size" -le 8192
  cat "$file" > /dev/null
done
"""
