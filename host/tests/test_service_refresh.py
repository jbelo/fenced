import copy
import importlib.machinery
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

loader = importlib.machinery.SourceFileLoader('refresh_harness', str(Path(__file__).parents[1] / 'bin/fenced-harness'))
spec = importlib.util.spec_from_loader(loader.name, loader)
h = importlib.util.module_from_spec(spec)
loader.exec_module(h)


class RefreshTests(unittest.TestCase):
    def setUp(self):
        self.old = {'profile': {'network': 'same'}, 'images': {'agent': 'image'}, 'services': {
            'gateway': {'name': 'gateway', 'files': [{'source': '/policy', 'target': '/policy', 'identity': [1], 'sha256': 'old'}]}}}
        self.new = copy.deepcopy(self.old)
        self.new['services']['gateway']['files'][0].update(identity=[2], sha256='new')

    def test_only_selected_file_changes_allowed(self):
        h.services.refresh_binding(h.api(), self.old, self.new, 'gateway')
        for change in ('profile', 'image', 'mount', 'secret'):
            candidate = copy.deepcopy(self.new)
            if change == 'profile': candidate['profile']['network'] = 'other'
            if change == 'image': candidate['images']['agent'] = 'other'
            if change == 'mount': candidate['services']['gateway']['files'][0]['source'] = '/elsewhere'
            if change == 'secret': candidate['services']['gateway']['files'][0]['sha256'] = None
            with self.subTest(change=change), self.assertRaises(h.Error):
                h.services.refresh_binding(h.api(), self.old, candidate, 'gateway')

    def test_interrupted_replacement_resumes_and_preserves_infrastructure(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory)
            (state / 'squid.conf').write_bytes(b'proxy')
            receipt = {'complete': True, 'directory': directory, 'owner': 'owner',
                       'binding': self.old, 'resources': {'service:gateway': 'old', 'internal': 'network-id'}}
            h.atomic_json(state / 'receipt.json', receipt)
            config = h.digest(h.encoded(self.old))
            item = {'Id': 'old', 'State': {'Running': True}, 'Config': {'Labels': {
                h.LABEL: 'owner', h.LABEL+'.role': 'service:gateway', h.LABEL+'.config': config}}}
            docker = Mock()
            current = [item]
            docker.inspect.side_effect = lambda *args: current[0]
            def call(*args):
                if args[0] == 'rm': current[0] = None
            docker.call.side_effect = call
            def started(api, p, d, r, runtime, cfg, save):
                r['resources']['service:gateway'] = 'new'
                save()
            with patch.object(h, 'inspect_resources') as inspect, patch.object(h.services, 'inspect'), \
                 patch.object(h.services, 'prepare', return_value=self.new['services']), \
                 patch.object(h.services, 'verify_clients'), patch.object(h.services, 'start', side_effect=h.Error('interrupted')):
                with self.assertRaises(h.Error):
                    h.services.refresh(h.api(), {}, docker, receipt, self.new, self.new, state, b'proxy', 'gateway')
            pending = h.read_json(state / 'receipt.json')
            self.assertIn('service_refresh', pending)
            self.assertEqual(pending['binding'], self.old)
            with patch.object(h, 'inspect_resources'), patch.object(h.services, 'prepare', return_value=self.new['services']), \
                 patch.object(h.services, 'start', side_effect=started):
                result = h.services.refresh(h.api(), {}, docker, pending, self.new, self.new, state, b'proxy', 'gateway')
            final = h.read_json(state / 'receipt.json')
            self.assertTrue(result['refreshed'])
            self.assertEqual(final['infrastructure_config'], config)
            self.assertEqual(final['resources']['internal'], 'network-id')
            self.assertEqual(final['binding'], self.new)
            self.assertNotIn('service_refresh', final)
            self.assertEqual(docker.call.call_args_list[0].args, ('stop', '--time', '25', 'gateway'))
            self.assertEqual(docker.call.call_args_list[1].args, ('rm', 'gateway'))
