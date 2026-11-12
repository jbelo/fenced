import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('build_images',Path(__file__).parents[1]/'build-images.py')
build=importlib.util.module_from_spec(spec);spec.loader.exec_module(build)

class BuildTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);(self.root/'scripts').mkdir();(self.root/'host/images').mkdir(parents=True)
        for file in ('Dockerfile','Dockerfile.squid','scripts/ssh.sh','host/images/apt-snapshot.sh','host/images/package.json','host/images/package-lock.json'):(self.root/file).write_text('public')
        for filename in ('package.json','package-lock.json'):
            (self.root/'host/images'/filename).write_bytes((Path(__file__).parents[1]/'images'/filename).read_bytes())
        (self.root/'private-key').write_text('never send')
        self.out=self.root/'result'
    def invoke(self,apply=False,existing='',failure=False,inputs=None):
        args=['build-images','--context','default','--agent-tag','test-agent:v1','--proxy-tag','test-proxy:v1','--output',str(self.out)]
        if inputs: args+=['--inputs',str(inputs)]
        if apply:args+=['--apply']
        with patch.object(sys,'argv',args),patch.object(build,'ROOT',self.root),\
             patch.object(build.doctor,'host_platform',return_value=('ubuntu-24.04-arm64','arm64')),\
             patch.object(build.doctor,'check_context'),patch.object(build.doctor,'check_daemon'),\
             patch.object(build.subprocess,'check_output',return_value=existing),\
             patch.object(build.subprocess,'run',side_effect=subprocess.CalledProcessError(1,['docker'])) as mutation,\
             contextlib.redirect_stdout(io.StringIO()):
            if failure:
                with self.assertRaises(subprocess.CalledProcessError):build.main()
            else:build.main()
            return mutation.call_count
    def test_plan_does_not_pull_or_create_output(self):
        self.assertEqual(self.invoke(),0);self.assertFalse(self.out.exists())
    def test_existing_tag_refused(self):
        with self.assertRaisesRegex(ValueError,'already exists'):self.invoke(existing='test-agent:v1')
        self.assertFalse(self.out.exists())
    def test_symlink_source_refused(self):
        (self.root/'Dockerfile').unlink();(self.root/'Dockerfile').symlink_to(self.root/'private-key')
        with self.assertRaisesRegex(ValueError,'regular file'):self.invoke()
        self.assertFalse(self.out.exists())
    def test_failed_pull_retains_minimal_context_and_incomplete_receipt(self):
        self.assertEqual(self.invoke(apply=True,failure=True),1)
        with tarfile.open(self.out/'context.tar') as archive:
            self.assertEqual(set(archive.getnames()),{'Dockerfile','Dockerfile.squid','scripts/ssh.sh','host/images/apt-snapshot.sh','host/images/package.json','host/images/package-lock.json'})
        self.assertFalse(json.loads((self.out/'receipt.json').read_text())['complete'])

    def test_recorded_inputs_are_preserved_in_failure_receipt(self):
        inputs=Path(__file__).parents[1]/'image-inputs.json'
        self.assertEqual(self.invoke(apply=True,failure=True,inputs=inputs),1)
        receipt=json.loads((self.out/'receipt.json').read_text())
        self.assertEqual(receipt['inputs'],json.loads(inputs.read_text()))
    def test_missing_native_input_refused_before_output(self):
        filename=self.root/'inputs.json'
        filename.write_text(json.dumps({'version':1,'platforms':{}}))
        with self.assertRaisesRegex(ValueError,'native platform'):
            self.invoke(inputs=filename)
        self.assertFalse(self.out.exists())

    def test_npm_integrity_and_version_mismatch_refused(self):
        inputs=json.loads((Path(__file__).parents[1]/'image-inputs.json').read_text())
        manifest=json.loads((self.root/'host/images/package.json').read_text())
        lock=json.loads((self.root/'host/images/package-lock.json').read_text())
        contents={'host/images/package.json':json.dumps(manifest),
                  'host/images/package-lock.json':json.dumps(lock)}
        build.validate_npm_lock(contents, inputs['build_args'])
        del lock['packages']['node_modules/@openai/codex']['integrity']
        contents['host/images/package-lock.json']=json.dumps(lock)
        with self.assertRaisesRegex(ValueError,'integrity'):build.validate_npm_lock(contents, inputs['build_args'])
        manifest['dependencies']['@openai/codex']='latest'
        contents['host/images/package.json']=json.dumps(manifest)
        with self.assertRaisesRegex(ValueError,'versions'):build.validate_npm_lock(contents, inputs['build_args'])
