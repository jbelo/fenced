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
    check(type(value['secrets']) is dict, 'secrets must map names to host file paths')
    root = Path(profile['workspace']['root'])
    def private_file(value, secret=False):
        check(type(value) is str and value, 'invalid file path')
        raw = directory / value
        resolved = raw.resolve(strict=True)
        check(raw.absolute() == resolved and resolved.is_file(), 'files must be regular, without symlink components')
        check(root != resolved and root not in resolved.parents, 'runtime files must be outside the agent workspace')
        check(not any(c in str(resolved) for c in ',:\n\r'), 'invalid mount path')
        parent = resolved.parent.stat(); info = resolved.stat()
        check(parent.st_uid == os.getuid() and stat.S_IMODE(parent.st_mode) == 0o700, 'runtime file parent must be operator-owned mode 0700')
        check(info.st_uid == (10001 if secret else os.getuid()) and stat.S_IMODE(info.st_mode) == (0o400 if secret else 0o444) and info.st_nlink == 1,
              'config/policy require operator ownership and 0444; secrets require UID 10001 and 0400; one hard link only')
        return str(resolved)
    result['config'] = private_file(value['config'])
    result['policy'] = private_file(value['policy'])
    result['secrets'] = {}
    for name, filename in value['secrets'].items():
        check(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}', name), 'invalid secret name')
        result['secrets'][name] = private_file(filename, secret=True)
    address = ipaddress.IPv4Address(value['address'])
    subnet = ipaddress.IPv4Network(profile['network']['subnet'])
    check(address in subnet and address not in (subnet.network_address, subnet.broadcast_address, subnet.network_address + 1), 'address must be a usable reserved address in network.subnet')
    config = json.loads(Path(result['config']).read_text())
    check(set(config) == {'version','mode','listen_address','policy_file','providers'}, 'invalid gateway configuration fields')
    check(config['version'] == 1 and config['mode'] in ('mock','live'), 'unsupported gateway mode')
    check(config['listen_address'] == str(address)+':8080' and config['policy_file'] == '/etc/agent-gateway/policy.json', 'config must bind the selected internal address and policy path')
    check(type(config['providers']) is dict and set(config['providers']) == {'github','shortcut'}, 'unsupported providers')
    referenced = set()
    def token(v):
        check(type(v) is str and re.fullmatch(r'/run/secrets/[A-Za-z0-9][A-Za-z0-9_-]{0,63}', v), 'invalid token file reference')
        referenced.add(v.rsplit('/',1)[1])
    for provider, item in config['providers'].items():
        allowed = {'enabled','token_file'} if provider == 'github' else {'enabled','workspaces'}
        check(type(item) is dict and set(item) <= allowed and type(item.get('enabled')) is bool, 'invalid provider fields; inline credentials are not accepted')
        if provider == 'github':
            if 'token_file' in item: token(item['token_file'])
            check(config['mode'] != 'live' or not item['enabled'] or 'token_file' in item, 'live GitHub requires a token file')
        else:
            check(type(item.get('workspaces',[])) is list, 'invalid workspaces')
            for ws in item.get('workspaces',[]):
                check(type(ws) is dict and set(ws) == {'alias','workspace_id','token_file'}, 'invalid workspace fields')
                token(ws['token_file'])
    check((config['mode'] == 'mock' and not result['secrets']) or referenced == set(result['secrets']), 'live secrets must exactly match config references; mock must mount no secrets')
    return result


def describe(value):
    return {'name':value['container'], 'image':value['image'], 'address':value['address'],
            'alias':'agent-gateway', 'user':'10001:10001',
            'files':[(value['config'],'/etc/agent-gateway/config.json',False),
                     (value['policy'],'/etc/agent-gateway/policy.json',False)] +
                    [(path,'/run/secrets/'+key,True) for key,path in sorted(value['secrets'].items())],
            "client_probe": ['node', '-e', "const fs=require('fs'); if(process.env.AGENTCTL_CONFIG!=='/etc/agentctl/config.json'||JSON.parse(fs.readFileSync('/etc/agentctl/config.json')).gateway_url!=='http://agent-gateway:8080')process.exit(1);fs.accessSync('/usr/local/bin/agentctl',fs.constants.X_OK)"],
            'health':['/usr/local/bin/gateway-healthcheck']}
