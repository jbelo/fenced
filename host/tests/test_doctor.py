import contextlib
import importlib.machinery
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

loader = importlib.machinery.SourceFileLoader('doctor', str(Path(__file__).parents[1] / 'bin/fenced-doctor'))
spec = importlib.util.spec_from_loader(loader.name, loader)
doctor = importlib.util.module_from_spec(spec)
loader.exec_module(doctor)


class DoctorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'stories').mkdir()
        self.calls = []
        self.endpoint = 'unix:///var/run/docker.sock'
        self.daemon_arch = 'aarch64'
        self.image_arch = 'arm64'
        self.security = []

    def docker(self, args):
        self.calls.append(args)
        self.assertEqual(args[:3], ['docker', '--context', 'default'])
        command = args[3:]
        if command[:2] == ['context', 'inspect']:
            return json.dumps(self.endpoint)
        if command[0] == 'info':
            return json.dumps({'arch': self.daemon_arch, 'os': 'linux',
                               'security': self.security, 'root': str(self.root)})
        if command[:2] == ['image', 'inspect']:
            return json.dumps({'arch': self.image_arch, 'os': 'linux', 'id': 'sha256:' + 'a' * 64})
        self.fail('Unexpected or mutating Docker command: ' + repr(command))

    def invoke(self, env=None, images=False):
        args = ['--context', 'default', '--workspace', str(self.root),
                '--writable', 'stories', '--min-free-gib', '0', '--json']
        if images:
            args += ['--image', 'example:local']
        with patch.dict(os.environ, env or {}, clear=True), \
             patch.object(doctor, 'host_platform', return_value=('ubuntu-24.04-arm64', 'arm64')), \
             patch.object(doctor.platform, 'system', return_value='Linux'), \
             patch.object(doctor.shutil, 'which', return_value='/tools/bin/tool'), \
             patch.object(doctor, 'run', side_effect=self.docker), \
             contextlib.redirect_stdout(io.StringIO()) as output:
            status = doctor.main(args)
        return status, json.loads(output.getvalue())

    def test_success_uses_only_inspection(self):
        before = sorted(self.root.rglob('*'))
        status, report = self.invoke(images=True)
        self.assertEqual(status, 0)
        self.assertTrue(report['ok'])
        self.assertEqual(len(self.calls), 3)
        self.assertEqual(before, sorted(self.root.rglob('*')))

    def test_remote_endpoint_rejected_before_daemon_contact(self):
        for endpoint in ('ssh://user@server', 'tcp://server:2376'):
            self.endpoint = endpoint
            self.calls.clear()
            status, _ = self.invoke(images=True)
            self.assertEqual(status, 1)
            self.assertEqual(len(self.calls), 1)

    def test_environment_conflict_never_contacts_docker(self):
        for env in ({'DOCKER_HOST': 'ssh://secret@example'}, {'DOCKER_CONTEXT': 'other'},
                    {'DOCKER_API_VERSION': '1.24'}, {'DOCKER_CERT_PATH': '/private'}):
            self.calls.clear()
            status, report = self.invoke(env)
            self.assertEqual(status, 1)
            self.assertEqual(self.calls, [])
            self.assertNotIn('secret@example', json.dumps(report))

    def test_daemon_and_image_architecture_must_match(self):
        self.daemon_arch = 'x86_64'
        self.assertEqual(self.invoke(images=True)[0], 1)
        self.assertEqual(len(self.calls), 2)
        self.daemon_arch = 'aarch64'
        self.image_arch = 'amd64'
        self.assertEqual(self.invoke(images=True)[0], 1)

    def test_rootless_rejected(self):
        self.security = ['name=rootless']
        self.assertEqual(self.invoke()[0], 1)

    def test_symlink_escape_and_whole_root_rejected(self):
        with tempfile.TemporaryDirectory() as outside:
            (self.root / 'escape').symlink_to(outside)
            for child in ('escape', '.', '..'):
                with self.assertRaises(doctor.CheckError):
                    doctor.check_workspace(self.root, [child], 0)

    def test_insufficient_space(self):
        with self.assertRaises(doctor.CheckError):
            doctor.check_workspace(self.root, [], 10 ** 12)

    def test_command_errors_do_not_disclose_stderr(self):
        failed = subprocess.CompletedProcess(['docker'], 1, '', 'secret-token')
        with patch.object(doctor.subprocess, 'run', return_value=failed):
            with self.assertRaises(doctor.CheckError) as result:
                doctor.run(['docker', 'info'])
        self.assertNotIn('secret-token', str(result.exception))
        with patch.object(doctor.subprocess, 'run', side_effect=subprocess.TimeoutExpired('docker', 15)):
            with self.assertRaises(doctor.CheckError):
                doctor.run(['docker', 'info'])

    def test_platform_matrix(self):
        with patch.object(doctor.platform, 'system', return_value='Linux'), \
             patch.object(doctor.platform, 'freedesktop_os_release', return_value={'ID': 'ubuntu', 'VERSION_ID': '24.04'}):
            for machine, arch in (('aarch64', 'arm64'), ('x86_64', 'amd64')):
                with patch.object(doctor.platform, 'machine', return_value=machine):
                    self.assertEqual(doctor.host_platform(), ('ubuntu-24.04-' + arch, arch))
        with patch.object(doctor.platform, 'system', return_value='Linux'), \
             patch.object(doctor.platform, 'machine', return_value='aarch64'), \
             patch.object(doctor.platform, 'freedesktop_os_release', return_value={'ID': 'ubuntu', 'VERSION_ID': '22.04'}):
            with self.assertRaises(doctor.CheckError):
                doctor.host_platform()

    def test_ubuntu_2604_both_architectures(self):
        with patch.object(doctor.platform, 'system', return_value='Linux'), \
             patch.object(doctor.platform, 'freedesktop_os_release', return_value={'ID': 'ubuntu', 'VERSION_ID': '26.04'}):
            for machine, arch in (('aarch64', 'arm64'), ('x86_64', 'amd64')):
                with patch.object(doctor.platform, 'machine', return_value=machine):
                    self.assertEqual(doctor.host_platform(), ('ubuntu-26.04-' + arch, arch))


if __name__ == '__main__':
    unittest.main()
