#!/usr/bin/env python3
"""Explicit agent-image migration for an existing profile; running sessions are retained."""
import argparse
import copy
import fcntl
import importlib.machinery
import importlib.util
import json
from pathlib import Path

loader = importlib.machinery.SourceFileLoader('harness', str(Path(__file__).parent / 'bin/fenced-harness'))
spec = importlib.util.spec_from_loader(loader.name, loader)
h = importlib.util.module_from_spec(spec)
loader.exec_module(h)


def validate_change(old, new):
    expected = copy.deepcopy(old)
    expected['profile']['image'] = new['profile']['image']
    expected['images']['agent'] = new['images']['agent']
    h.require(expected == new, 'unrelated configuration changed; agent upgrade refused')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', required=True)
    parser.add_argument('--state-dir', required=True)
    parser.add_argument('--source', required=True)
    parser.add_argument('--image', required=True)
    args = parser.parse_args()
    profile = Path(args.profile).resolve(strict=True)
    state = Path(args.state_dir).resolve(strict=True)
    receipt_path = state / 'receipt.json'
    h.require(not receipt_path.is_symlink() and not (state/'lock').is_symlink(), 'state symlink refused')
    h.require(state.stat().st_uid == h.os.getuid() and state.stat().st_mode & 0o077 == 0, 'private operator-owned state required')
    h.require(profile.stat().st_uid == h.os.getuid() and profile.stat().st_nlink == 1, 'operator-owned profile required')
    h.require(profile.name != 'development-profile.json', 'generated settings require a coordinated settings migration; use an explicit profile')
    with (state / 'lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        receipt = h.read_json(receipt_path)
        h.require(receipt.get('complete') and not any(receipt.get(k) for k in ('stopped','transition','service_refresh')), 'running stable environment required')
        h.require(receipt['directory'] == str(state), 'state directory mismatch')
        old = receipt['binding']
        current = h.load_profile(profile)
        pending = receipt.get('agent_upgrade')
        if pending:
            h.require(pending['profile_path'] == str(profile) and pending['image'] == args.image, 'retry the pending image upgrade unchanged')
            h.require(current in (old['profile'], pending['binding']['profile']), 'profile changed during upgrade')
            target = pending['binding']['profile']
        else:
            h.require(current == old['profile'], 'profile drift; upgrade refused')
            target = copy.deepcopy(current)
            target['image']['reference'] = args.image
        docker = h.Docker(target['runtime']['context'])
        runtime = h.readiness(target, docker)
        # Bind future launches to the resolved immutable ID, never a mutable tag.
        target['image']['reference'] = runtime['images']['agent']
        binding = {'profile': target, 'uid': h.os.getuid(), 'gid': h.os.getgid(), **runtime}
        validate_change(old, binding)
        if pending: h.require(binding == pending['binding'], 'pending image changed')
        _, squid = h.assets(args.source)
        h.require((state/'squid.conf').read_bytes() == squid, 'proxy configuration drift')
        config = receipt.get('infrastructure_config', h.digest(h.encoded(old)))
        h.inspect_resources(old['profile'], docker, receipt, config, old)
        h.services.verify_clients(docker, runtime)
        docker.call('run','--rm','--network=none','--read-only','--tmpfs','/tmp:rw,mode=1777',
                    '--user',f'{h.os.getuid()}:{h.os.getgid()}','--env','HOME=/tmp',
                    '--entrypoint','sh',runtime['images']['agent'],'-ec',
                    'go version; node --version; command -v tmux; command -v rsync; command -v ssh')
        receipt['infrastructure_config'] = config
        receipt['agent_upgrade'] = {'profile_path': str(profile), 'image': args.image, 'binding': binding}
        h.atomic_json(receipt_path, receipt)
        h.atomic_json(profile, target)
        receipt['binding'] = binding
        receipt.pop('agent_upgrade')
        h.atomic_json(receipt_path, receipt)
        print(json.dumps({'agent_image':runtime['images']['agent'], 'running_sessions':'unchanged', 'profile':str(profile)}))

if __name__ == '__main__':
    try: main()
    except (h.Error, OSError, ValueError, KeyError, TypeError) as exc:
        raise SystemExit(str(exc))
