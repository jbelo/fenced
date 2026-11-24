"""Generic receipt-owned service lifecycle for extra-owned profile adapters."""
import hashlib
import importlib.util
import ipaddress
import json
from pathlib import Path
import time


def adapter(filename):
    spec = importlib.util.spec_from_file_location('fenced_extra', filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prepare(h, p, docker, catalog):
    result = {}
    for key, value in p.get('services', {}).items():
        spec = adapter(catalog[key]['adapter']).describe(value)
        image = docker.data('image', 'inspect', spec.pop('image'))[0]
        h.require(image['Os'] == 'linux' and h.arch(image['Architecture']) == p['platform'].rsplit('-',1)[1], 'service image architecture mismatch')
        h.require(image['Config'].get('User') == spec['user'], 'service image user mismatch')
        h.require(not image['Config'].get('Volumes'), 'service image must not declare volumes')
        spec['image'] = image['Id']
        spec['defaults'] = {k:image['Config'].get(k) for k in ('Entrypoint','Cmd','Env','User','WorkingDir','Healthcheck')}
        files = []
        for source, target, secret in spec['files']:
            info = Path(source).stat()
            # Secrets are never read, hashed, copied into state or printed.
            identity = [info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns]
            files.append({'source':source,'target':target,'identity':identity,
                          'sha256':None if secret else hashlib.sha256(Path(source).read_bytes()).hexdigest()})
        spec['files'] = files
        for volume in spec.get('volumes', []):
            info = docker.inspect('volume', volume['name'])
            h.require(info and info.get('Driver') == 'local' and not info.get('Options') and
                      all((info.get('Labels') or {}).get(k) == v for k,v in volume['required_label'].items()),
                      'missing or incompatible externally staged service volume')
            volume['identity'] = {k:info.get(k) for k in ('Name','CreatedAt','Mountpoint','Driver','Options','Labels')}
            helper = docker.data('image','inspect',volume['helper_image'])[0]
            h.require(helper['Os'] == 'linux' and h.arch(helper['Architecture']) == p['platform'].rsplit('-',1)[1], 'credential helper architecture mismatch')
            volume['helper_image'] = helper['Id']
        result[key] = spec
    return result


def specs(runtime):
    return [('container',spec['name'],'service:'+key) for key,spec in runtime.get('services',{}).items()]


def inspect(h, p, item, spec, allow_stopped=False):
    h.require(item['Image'] == spec['image'], 'service image changed')
    h.require(all((item['Config'].get(k) or None) == (v or None) for k,v in spec['defaults'].items()), 'service command/environment/healthcheck changed')
    hc = item['HostConfig']
    h.require(hc['ReadonlyRootfs'] and not hc['Privileged'] and hc.get('CapDrop') == ['ALL']
              and set(hc.get('SecurityOpt') or []) <= {'no-new-privileges','no-new-privileges:true'} and hc.get('SecurityOpt')
              and not any(hc.get(k) for k in ('PortBindings','Binds','CapAdd','Devices','DeviceRequests','PidMode','VolumesFrom','ExtraHosts','Tmpfs'))
              and hc.get('RestartPolicy',{}).get('Name') == 'no'
              and hc['NetworkMode'] == p['network']['upstream']
              and hc.get('Sysctls') == {'net.ipv4.ip_forward':'0','net.ipv6.conf.all.forwarding':'0'}, 'service hardening changed')
    actual = sorted((v['Type'],v.get('Name') if v['Type']=='volume' else v['Source'],v['Destination'],v['RW']) for v in item['Mounts'])
    expected = sorted([('bind',v['source'],v['target'],False) for v in spec['files']] + [('volume',v['name'],v['target'],False) for v in spec.get('volumes',[])])
    h.require(actual == expected, 'service mount conflict')
    nets = item['NetworkSettings']['Networks']
    h.require(set(nets) <= {p['network']['internal'],p['network']['upstream']} and p['network']['upstream'] in nets, 'service network conflict')
    internal = nets.get(p['network']['internal'])
    if internal:
        h.require((internal.get('IPAMConfig') or {}).get('IPv4Address') == spec['address'] and spec['alias'] in (internal.get('Aliases') or []), 'service address/alias changed')
    h.require(allow_stopped or (internal and item['State']['Running']), 'service stopped or disconnected; use explicit start or repair')


def ready(h, docker, spec):
    # Bounded readiness; raw logs and credentials never enter diagnostics.
    for _ in range(30):
        item = docker.inspect('container',spec['name'])
        h.require(item and item['State']['Running'], 'service did not remain running; inspect locally')
        try:
            docker.call('exec',spec['name'],*spec['health'])
            return
        except h.Error:
            time.sleep(1)
    raise h.Error('service readiness failed; inspect locally before retrying')


def start(h, p, docker, receipt, runtime, config, save):
    for key,spec in runtime.get('services',{}).items():
        role = 'service:'+key
        item = docker.inspect('container',spec['name'])
        if not item:
            args = ['create','--pull=never','--name',spec['name'],'--network',p['network']['upstream'],
                    '--label',h.LABEL+'='+receipt['owner'],'--label',h.LABEL+'.role='+role,
                    '--label',h.LABEL+'.config='+receipt.get('resource_configs', {}).get(role, config),'--read-only','--cap-drop=ALL',
                    '--security-opt=no-new-privileges','--sysctl','net.ipv4.ip_forward=0',
                    '--sysctl','net.ipv6.conf.all.forwarding=0']
            for mount in spec['files']:
                args += ['--mount','type=bind,src='+mount['source']+',target='+mount['target']+',readonly']
            for volume in spec.get('volumes', []):
                args += ['--mount','type=volume,src='+volume['name']+',target='+volume['target']+',readonly,volume-nocopy']
            docker.call(*args,spec['image'])
            item = docker.inspect('container',spec['name'])
        inspect(h,p,item,spec,True)
        receipt['resources'][role] = item['Id'];save()
        if p['network']['internal'] not in item['NetworkSettings']['Networks']:
            docker.call('network','connect','--ip',spec['address'],'--alias',spec['alias'],p['network']['internal'],spec['name'])
        if not item['State']['Running']:
            docker.call('start',spec['name'])
        inspect(h,p,docker.inspect('container',spec['name']),spec)
        ready(h,docker,spec)


def verify_clients(docker, runtime):
    verify_volumes(docker, runtime)
    for spec in runtime.get('services', {}).values():
        docker.call('run','--rm','--pull=never','--network=none','--read-only',
                    '--cap-drop=ALL','--security-opt=no-new-privileges',
                    '--user','10001:10001','--entrypoint',spec['client_probe'][0],
                    runtime['images']['agent'],*spec['client_probe'][1:])


def verify_volumes(docker, runtime):
    for spec in runtime.get('services', {}).values():
        for volume in spec.get('volumes', []):
            docker.call('run','--rm','--pull=never','--network=none','--read-only',
                        '--cap-drop=ALL','--security-opt=no-new-privileges','--log-driver=none',
                        '--user','10001:10001','--mount',
                        'type=volume,src='+volume['name']+',target='+volume['target']+',readonly,volume-nocopy',
                        '--entrypoint',volume['probe'][0],volume['helper_image'],*volume['probe'][1:])


def refresh_binding(h, old, new, key):
    """Only the chosen service's non-secret file identities/content may change."""
    import copy
    expected = copy.deepcopy(old)
    h.require(key in old.get('services', {}) and key in new.get('services', {}), 'unknown service')
    before = expected['services'][key]['files']
    after = new['services'][key]['files']
    h.require(len(before) == len(after), 'service mount set changed')
    for a, b in zip(before, after):
        h.require(a['source'] == b['source'] and a['target'] == b['target'] and
                  a['sha256'] is not None and b['sha256'] is not None,
                  'only existing non-secret service files can be refreshed')
    expected['services'][key]['files'] = after
    h.require(expected == new, 'unrelated configuration changed; service refresh refused')


def refresh(h, p, docker, receipt, binding, runtime, state, squid, key):
    import copy
    import fcntl
    h.require(receipt and receipt.get('complete') and not receipt.get('stopped') and
              not receipt.get('transition') and not receipt.get('agent_upgrade'), 'refresh requires a running initialized environment')
    h.require(receipt['directory'] == str(state) and (state / 'squid.conf').read_bytes() == squid,
              'state/proxy configuration changed')
    path = state / 'receipt.json'
    with (state / 'lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        h.require(h.read_json(path) == receipt, 'receipt changed during preflight')
        refresh_binding(h, receipt['binding'], binding, key)
        h.require(prepare(h, p, docker, h.capabilities()) == runtime['services'], 'service inputs changed during preflight')
        pending = receipt.get('service_refresh')
        role = 'service:' + key
        config = receipt.get('infrastructure_config', h.digest(h.encoded(receipt['binding'])))
        spec = runtime['services'][key]
        if pending:
            h.require(pending['service'] == key and pending['binding'] == binding,
                      'pending refresh differs; restore its inputs and retry')
        else:
            h.inspect_resources(p, docker, receipt, config, receipt['binding'])
            verify_clients(docker, {'images': runtime['images'], 'services': {key: spec}})
            if receipt['binding'] == binding:
                ready(h, docker, spec)
                return {'refreshed': False, 'service': key}
            pending = {'service': key, 'binding': binding, 'old_id': receipt['resources'][role]}
            receipt['service_refresh'] = pending
            receipt['infrastructure_config'] = config
            h.atomic_json(path, receipt)
        # On retry, inspect every unrelated resource with its original binding.
        others = copy.deepcopy(receipt)
        others['binding']['services'].pop(key)
        h.inspect_resources(p, docker, others, config, others['binding'])
        item = docker.inspect('container', spec['name'])
        if item and item['Id'] == pending['old_id']:
            labels = item['Config'].get('Labels', {})
            h.require(labels.get(h.LABEL) == receipt['owner'] and labels.get(h.LABEL+'.role') == role and
                      labels.get(h.LABEL+'.config') == receipt.get('resource_configs', {}).get(role, config),
                      'old service ownership changed')
            inspect(h, p, item, receipt['binding']['services'][key], True)
            if item['State']['Running']:
                docker.call('stop', '--time', '25', spec['name'])
            docker.call('rm', spec['name'])
        new_config = h.digest(h.encoded(spec))
        receipt.setdefault('resource_configs', {})[role] = new_config
        item = docker.inspect('container', spec['name'])
        if item:
            labels = item['Config'].get('Labels', {})
            h.require(labels.get(h.LABEL) == receipt['owner'] and labels.get(h.LABEL+'.role') == role and
                      labels.get(h.LABEL+'.config') == new_config, 'replacement service conflict')
        h.atomic_json(path, receipt)
        start(h, p, docker, receipt, {'services': {key: spec}}, config, lambda: h.atomic_json(path, receipt))
        h.require(prepare(h, p, docker, h.capabilities()) == runtime['services'], 'service inputs changed during refresh')
        receipt['binding'] = binding
        receipt.pop('service_refresh')
        h.atomic_json(path, receipt)
        return {'refreshed': True, 'service': key, 'container': spec['name']}
