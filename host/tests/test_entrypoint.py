"""Check launcher argument/cwd boundaries without Nix, Docker or network access."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[2] / 'fenced'


class EntrypointTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.checkout = self.root / 'checkout with spaces'
        self.checkout.mkdir()
        shutil.copy2(SOURCE, self.checkout / 'fenced')
        (self.checkout / 'flake.lock').write_text('{}')
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        nix = self.bin / 'nix'
        nix.write_text('#!/usr/bin/env python3\nimport json,os,sys\nprint(json.dumps({"args":sys.argv[1:],"cwd":os.getcwd()}))\nsys.exit(int(os.environ.get("FAKE_EXIT",0)))\n')
        nix.chmod(0o755)
        self.env = dict(os.environ, PATH=str(self.bin) + os.pathsep + os.environ['PATH'])

    def run_entry(self, *args, entry=None):
        return subprocess.run([str(entry or self.checkout / 'fenced'), *args],
                              cwd=self.root, env=self.env, text=True, capture_output=True)

    def test_harness_paths_and_cwd(self):
        r = self.run_entry('plan', '--profile', 'profile with spaces.json', '--state-dir', 'state dir')
        self.assertEqual(r.returncode, 0, r.stderr)
        data = json.loads(r.stdout)
        self.assertEqual(data['cwd'], str(self.root.resolve()))
        self.assertEqual(data['args'], ['--extra-experimental-features', 'nix-command flakes',
            'develop', '--no-update-lock-file', str(self.checkout.resolve()) + '#host',
            '--command', 'fenced-harness', 'plan', '--source', str(self.checkout.resolve()),
            '--profile', 'profile with spaces.json', '--state-dir', 'state dir'])

    def test_exec_preserves_arguments_and_exit(self):
        self.env['FAKE_EXIT'] = '17'
        r = self.run_entry('exec', 'printf', '%s', '$(touch unsafe); two words')
        self.assertEqual(r.returncode, 17)
        self.assertEqual(json.loads(r.stdout)['args'][-3:], ['printf', '%s', '$(touch unsafe); two words'])
        self.assertFalse((self.root / 'unsafe').exists())

    def test_relative_symlink(self):
        link = self.root / 'shortcut'
        link.symlink_to('checkout with spaces/fenced')
        r = self.run_entry('doctor', '--help', entry=link)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn(str(self.checkout.resolve()) + '#host', json.loads(r.stdout)['args'])

    def test_help_and_invalid_commands_do_not_enter_nix(self):
        self.assertIn('Usage:', self.run_entry('--help').stdout)
        for args in [('wrong',), ('exec',), ('shell', 'unexpected')]:
            self.assertEqual(self.run_entry(*args).returncode, 2)

    def test_shell_and_validate(self):
        shell = json.loads(self.run_entry('shell').stdout)['args']
        self.assertNotIn('--command', shell)
        validate = json.loads(self.run_entry('validate', '--profile', 'p.json').stdout)['args']
        self.assertEqual(validate[-4:], ['fenced-harness', 'validate', '--profile', 'p.json'])

    def test_normal_commands_select_actions_without_requiring_apply(self):
        for action in ('init', 'start', 'stop'):
            r = self.run_entry(action)
            args = json.loads(r.stdout)['args']
            self.assertEqual(args[-5:], ['fenced-harness', action, '--source', str(self.checkout.resolve()), '--apply'])
        args = json.loads(self.run_entry('meta').stdout)['args']
        self.assertEqual(args[-4:], ['fenced-harness', 'launch', '--source', str(self.checkout.resolve())])
        args = json.loads(self.run_entry('story', 'stories/a b', '--no-tmux').stdout)['args']
        self.assertEqual(args[-5:], ['--session-kind', 'story', '--start-dir', 'stories/a b', '--no-tmux'])


if __name__ == '__main__':
    unittest.main()
