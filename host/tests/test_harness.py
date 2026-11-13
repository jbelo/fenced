import contextlib
import copy
import importlib.machinery
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

loader = importlib.machinery.SourceFileLoader('harness', str(Path(__file__).parents[1] / 'bin/fenced-harness'))
spec = importlib.util.spec_from_loader(loader.name, loader)
h = importlib.util.module_from_spec(spec)
loader.exec_module(h)


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        (self.root / 'workspace/stories').mkdir(parents=True)
        self.filename = self.root / 'profile.json'
        self.profile = {'version': 1, 'platform': 'ubuntu-26.04-arm64', 'runtime': {'context': 'default'},
                        'workspace': {'root': 'workspace', 'writable': ['stories']},
                        'image': {'reference': 'agent:test'}, 'state': {'agenthome': 'test-home', 'gomodcache': 'test-go'},
                        'network': {'internal': 'test-internal', 'upstream': 'test-upstream'},
                        'proxy': {'image': 'proxy:test', 'container': 'test-proxy'}, 'extras': []}

    def load(self, value=None):
        self.filename.write_text(json.dumps(value or self.profile))
        return h.load_profile(self.filename)

    def test_relative_root_resolved_against_profile(self):
        self.assertEqual(self.load()['workspace']['root'], str(self.root / 'workspace'))

    def test_invalid_profiles_fail_before_any_subprocess(self):
        variants = []
        for key, value in [('version', True), ('version', 2), ('platform', 'linux'), ('secret', 'no'),
                           ('extras', ['gateway']), ('extras', ['x', 'x']), ('extras', 'x')]:
            variant = copy.deepcopy(self.profile)
            variant[key] = value
            variants.append(variant)
        for group, key, value in [('workspace', 'writable', ['.']), ('workspace', 'writable', []),
                                  ('workspace', 'writable', ['stories', 'stories']),
                                  ('runtime', 'context', '--help'), ('image', 'reference', 'x; touch /tmp/no'),
                                  ('state', 'gomodcache', 'test-home'), ('network', 'upstream', 'test-internal')]:
            variant = copy.deepcopy(self.profile)
            variant[group][key] = value
            variants.append(variant)
        with patch.object(h, 'run') as run:
            for variant in variants:
                with self.subTest(profile=variant), self.assertRaises(h.Error):
                    self.load(variant)
            run.assert_not_called()

    def test_selected_host_handoff_checks_tools_and_skills(self):
        self.profile['extras'] = ['story-setup']
        p = self.load()
        bundle = {'.agents/skills/' + name + '/SKILL.md': '' for name in
                  ('story-implementation-setup', 'story-review-setup')}
        with patch.object(h.shutil, 'which', return_value='/tools/tool'):
            self.assertEqual(h.check_extras(p, bundle)[0]['status'], 'ready')
            with self.assertRaises(h.Error): h.check_extras(p, {})
        with patch.object(h.shutil, 'which', return_value=None), self.assertRaises(h.Error):
            h.check_extras(p, bundle)

    def test_duplicate_fields(self):
        self.filename.write_text('{"version":1,"version":1}')
        with self.assertRaises(h.Error):
            h.load_profile(self.filename)

    def test_symlink_escape(self):
        (self.root / 'workspace/escape').symlink_to(self.root)
        self.profile['workspace']['writable'].append('escape')
        with self.assertRaises(h.Error):
            self.load()

    def test_remote_context_and_overrides_fail_before_daemon(self):
        p = self.load()
        with patch.object(h, 'host_platform', return_value=p['platform']), patch.dict(os.environ, {}, clear=True):
            class Remote:
                context = 'default'
                calls = []
                def data(self, *args):
                    self.calls.append(args)
                    return 'ssh://host'
            docker = Remote()
            with self.assertRaises(h.Error):
                h.readiness(p, docker)
            self.assertEqual(len(docker.calls), 1)
            docker.calls.clear()
            with patch.dict(os.environ, {'DOCKER_HOST': 'tcp://host'}), self.assertRaises(h.Error):
                h.readiness(p, docker)
            self.assertEqual(docker.calls, [])

    def test_unowned_resources_never_mutated(self):
        p = self.load()
        class Existing:
            def inspect(self, kind, name):
                return {'Labels': {}, 'Name': name}
        with self.assertRaisesRegex(h.Error, 'unowned'):
            h.inspect_resources(p, Existing(), None, 'config', {})

    def test_plan_does_not_create_state(self):
        p = self.load()
        class Missing:
            def __init__(self, context):
                pass
            def inspect(self, kind, resource):
                return None
        state = self.root / 'state'
        runtime = {'endpoint': 'unix:///socket', 'daemon': 'test', 'images': {'agent': 'a', 'proxy': 'p'}}
        with patch.object(h, 'Docker', Missing), patch.object(h, 'readiness', return_value=runtime), \
             patch.object(h, 'assets', return_value=({}, b'config')):
            plan = h.execute(p, '.', state)
        self.assertEqual(len(plan['resources']), 5)
        self.assertFalse(state.exists())

    def test_complete_receipt_does_not_recreate_missing_resource(self):
        class Missing:
            def inspect(self, kind, resource):
                return None
        with self.assertRaisesRegex(h.Error, 'explicit repair'):
            h.inspect_resources(self.load(), Missing(), {'complete': True}, 'config', {})


@unittest.skipUnless(shutil.which('node'), 'Node required for managed-file helper tests')
class SeedTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        source = (Path(__file__).parents[1] / 'lib/fenced-seed.js').read_text()
        self.source = source.replace("const home = '/home/agent';", 'const home = ' + json.dumps(str(self.root)) + ';')

    def seed(self, files):
        import base64
        bundle = {key: base64.b64encode(value.encode()).decode() for key, value in files.items()}
        return subprocess.run(['node', '-e', self.source], input=json.dumps(bundle), text=True, capture_output=True)

    def test_repeat_preserves_programs_tmux_and_updates_untouched_files(self):
        self.assertEqual(self.seed({'context': 'one', '.tmux.conf': 'original'}).returncode, 0)
        (self.root / '.tmux.conf').write_text('custom')
        (self.root / 'pi').write_text('keep')
        self.assertEqual(self.seed({'context': 'two', '.tmux.conf': 'new'}).returncode, 0)
        self.assertEqual((self.root / 'context').read_text(), 'two')
        self.assertEqual((self.root / '.tmux.conf').read_text(), 'custom')
        self.assertEqual((self.root / 'pi').read_text(), 'keep')

    def test_all_conflicts_checked_before_write(self):
        self.assertEqual(self.seed({'context': 'one'}).returncode, 0)
        (self.root / 'context').write_text('user edit')
        self.assertNotEqual(self.seed({'new': 'no', 'context': 'two'}).returncode, 0)
        self.assertFalse((self.root / 'new').exists())
        self.assertEqual((self.root / 'context').read_text(), 'user edit')

    def test_symlink_parent_rejected(self):
        with tempfile.TemporaryDirectory() as outside:
            (self.root / 'link').symlink_to(outside)
            self.assertNotEqual(self.seed({'link/file': 'no'}).returncode, 0)
            self.assertFalse((Path(outside) / 'file').exists())

    def test_interruption_after_file_before_ledger_recovers(self):
        self.assertEqual(self.seed({'context': 'old'}).returncode, 0)
        (self.root / 'context').write_text('new')
        self.assertEqual(self.seed({'context': 'new'}).returncode, 0)
        self.assertEqual(self.seed({'context': 'next'}).returncode, 0)



class EverydayInterfaceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name).resolve()
        self.workspace = self.home / 'workspace'
        (self.workspace / 'stories/rv-example').mkdir(parents=True)
        self.home_patch = patch.object(h.Path, 'home', return_value=self.home)
        self.home_patch.start()
        self.addCleanup(self.home_patch.stop)

    def args(self, **kw):
        from argparse import Namespace
        values = dict(profile=None, state_dir=None, workspace=str(self.workspace),
                      extra=['story-setup'], context='default', image='agent:test',
                      proxy_image='proxy:test')
        values.update(kw)
        return Namespace(**values)

    def test_configure_derives_infrastructure_without_docker_mutation(self):
        with patch.object(h, 'host_platform', return_value='ubuntu-26.04-amd64'), patch.object(h, 'run') as run:
            h.configure(self.args())
            run.assert_not_called()
        filename = h.configured_profile()
        p = h.load_profile(filename)
        self.assertEqual(p['platform'], 'ubuntu-26.04-amd64')
        self.assertEqual(p['workspace']['root'], str(self.workspace))
        self.assertEqual(p['extras'], ['story-setup'])
        self.assertNotEqual(p['network']['internal'], p['network']['upstream'])
        settings = json.loads((self.home / '.config/fenced/settings.json').read_text())
        self.assertNotIn('platform', settings)
        self.assertNotIn('network', settings)
        self.assertNotIn('state', settings)
        before = filename.read_bytes()
        with self.assertRaises(h.Error):
            h.configure(self.args())
        self.assertEqual(filename.read_bytes(), before)

    def test_existing_development_profile_is_used_without_rewriting(self):
        p = self.home / '.config/fenced/development.json'
        p.parent.mkdir(parents=True)
        p.write_text('{"existing":true}')
        self.assertEqual(h.configured_profile(), p)
        self.assertEqual(p.read_text(), '{"existing":true}')
        self.assertFalse((self.home / '.local/state/fenced').exists())

    def test_custom_profile_never_defaults_to_development_state(self):
        with patch.object(h, 'load_profile') as load, contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(h.main(['plan', '--profile', '/custom.json', '--source', '/source']), 1)
            load.assert_not_called()

    def test_modified_settings_require_explicit_migration(self):
        with patch.object(h, 'host_platform', return_value='ubuntu-26.04-amd64'):
            h.configure(self.args())
        settings = self.home / '.config/fenced/settings.json'
        data = json.loads(settings.read_text());data['image'] = 'other:test'
        settings.write_text(json.dumps(data))
        with self.assertRaises(h.Error):
            h.configured_profile()

    def test_unenrolled_service_cannot_be_selected_as_host_capability(self):
        with self.assertRaises(h.Error):
            h.configure(self.args(extra=['agent-gateway']))
        self.assertFalse((self.home / '.config/fenced/settings.json').exists())

    def test_story_mount_is_only_the_selected_story_and_blocks_escapes(self):
        from argparse import Namespace
        p = {'workspace': {'root': str(self.workspace), 'writable': ['stories']}}
        story = self.workspace / 'stories/rv-example'
        args = Namespace(source=str(Path(__file__).resolve().parents[2]),
                         session_kind='story', start_dir=str(story), no_tmux=True)
        command = h.launch_command(p, args, {'agent': 'sha256:abc'})
        self.assertTrue(command[0].endswith('/story-shell'))
        self.assertEqual(command[command.index('--workspace-rw') + 1], str(story))
        self.assertEqual(command[-1], str(story))
        self.assertIn('--no-tmux', command)
        for start in (self.workspace, self.workspace / 'stories', self.home):
            args.start_dir = str(start)
            with self.assertRaises(h.Error):
                h.launch_command(p, args, {'agent': 'sha256:abc'})
        (self.workspace / 'stories/escape').symlink_to(self.home, target_is_directory=True)
        args.start_dir = str(self.workspace / 'stories/escape')
        with self.assertRaises(h.Error):
            h.launch_command(p, args, {'agent': 'sha256:abc'})


if __name__ == '__main__':
    unittest.main()
