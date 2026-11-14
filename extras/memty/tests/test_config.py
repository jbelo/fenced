import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
loader = importlib.machinery.SourceFileLoader('memty', str(ROOT / 'extras/memty/host-bin/fenced-memty'))
spec = importlib.util.spec_from_loader(loader.name, loader)
m = importlib.util.module_from_spec(spec)
loader.exec_module(m)


class TemplateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name).resolve()
        self.source = self.home / 'template with spaces'
        (self.source / 'brief').mkdir(parents=True)
        (self.source / 'AGENTS.md').write_text('fixture')
        (self.source / 'brief/STORY_TEMPLATE.md').write_text('fixture')
        self.mock = patch.object(m.Path, 'home', return_value=self.home)
        self.mock.start();self.addCleanup(self.mock.stop)

    def hook(self, **env):
        script = 'docker_args=(); agent_home=/home/agent; launcher_dir="$1/bin"; source "$1/extras/memty/run-shell.d/memty.sh"; printf "%s\\0" "${docker_args[@]}"'
        return subprocess.run(['bash', '-ec', script, 'test', str(ROOT)],
                              env=dict(os.environ, HOME=str(self.home), **env), capture_output=True)

    def test_setting_and_readonly_profile_mount(self):
        m.write(m.validate(self.source))
        result = self.hook(FENCED_PROFILE_LAUNCH='1', MEMTY_SOURCE='/untrusted-override')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(('type=bind,src='+str(self.source)+',target=/home/agent/memty,readonly').encode(), result.stdout.split(b'\0'))
        self.assertEqual(m.setting_file().stat().st_mode & 0o777, 0o600)
        self.assertEqual(set(json.loads(m.setting_file().read_text())), {'source'})

    def test_absent_and_off_do_not_use_legacy_default(self):
        for configured in (False, True):
            if configured:m.write(None)
            result = self.hook(FENCED_PROFILE_LAUNCH='1', MEMTY_SOURCE=str(self.source))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn(b'--mount', result.stdout)

    def test_invalid_setting_fails_before_launch(self):
        m.write(str(self.source))
        (self.source / 'brief/STORY_TEMPLATE.md').unlink()
        self.assertNotEqual(self.hook(FENCED_PROFILE_LAUNCH='1').returncode, 0)

    def test_bad_paths_and_symlink_setting_rejected(self):
        with self.assertRaises(OSError):m.validate(self.home / 'missing')
        path = self.home / 'comma,path';path.mkdir()
        with self.assertRaises(ValueError):m.validate(path)
        m.setting_file().parent.mkdir(parents=True)
        m.setting_file().symlink_to(self.home / 'absent')
        with self.assertRaises(ValueError):m.write(str(self.source))
        with self.assertRaises(ValueError):m.read()

    def test_legacy_override_is_unchanged(self):
        result = self.hook(MEMTY_SOURCE=str(self.source), MEMTY_ENABLE='1', FENCED_PROFILE_LAUNCH='0')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(b'--mount', result.stdout)


if __name__ == '__main__':unittest.main()
