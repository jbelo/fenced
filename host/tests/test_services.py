import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from test_harness import h


class ServiceProfileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        (self.root/'workspace/stories').mkdir(parents=True)
        runtime = self.root/'runtime'; runtime.mkdir(mode=0o700)
        self.config = runtime/'config.json'
        self.config.write_text(json.dumps({'version':1,'mode':'mock','listen_address':'172.29.240.10:8080',
                                           'policy_file':'/etc/agent-gateway/policy.json','providers':{'github':{'enabled':True},'shortcut':{'enabled':False,'workspaces':[]}}}))
        self.policy = runtime/'policy.json';self.policy.write_text('{"version":1}')
        self.config.chmod(0o444);self.policy.chmod(0o444)
        self.p={'version':1,'platform':'ubuntu-26.04-arm64','runtime':{'context':'default'},
                'workspace':{'root':'workspace','writable':['stories']},'image':{'reference':'client:test'},
                'state':{'agenthome':'home','gomodcache':'go'},'network':{'internal':'internal','upstream':'upstream','subnet':'172.29.240.0/24'},
                'proxy':{'image':'proxy:test','container':'proxy'},'extras':['agent-gateway'],
                'services':{'agent-gateway':{'container':'gateway','image':'gateway:test','address':'172.29.240.10',
                'config':str(self.config),'policy':str(self.policy),'secrets':{}}}}
    def load(self):
        path=self.root/'profile.json';path.write_text(json.dumps(self.p));return h.load_profile(path)
    def test_valid_service_and_legacy_catalog(self):
        self.assertEqual(self.load()['services']['agent-gateway']['config'],str(self.config))
        self.assertEqual(h.capabilities()['story-setup']['kind'],'host-handoff')
    def test_selection_and_subnet_must_match(self):
        self.p['extras']=[]
        with self.assertRaises(h.Error):self.load()
        self.p['extras']=['agent-gateway'];self.p['services']['agent-gateway']['address']='172.29.241.10'
        with self.assertRaises(ValueError):self.load()
    def test_private_files_and_workspace_separation(self):
        self.config.parent.chmod(0o755)
        with self.assertRaises(ValueError):self.load()
        self.config.parent.chmod(0o700);self.p['workspace']['root']=str(self.root)
        (self.root/'stories').mkdir()
        with self.assertRaises(ValueError):self.load()
    def test_symlink_and_writable_runtime_rejected(self):
        self.config.chmod(0o644)
        with self.assertRaises(ValueError):self.load()
        self.config.chmod(0o444);link=self.config.parent/'alias';link.symlink_to(self.config)
        self.p['services']['agent-gateway']['config']=str(link)
        with self.assertRaises(ValueError):self.load()
    def test_inline_credentials_rejected(self):
        value=json.loads(self.config.read_text());value['providers']['github']['token']='must-not-leak'
        self.config.chmod(0o644);self.config.write_text(json.dumps(value));self.config.chmod(0o444)
        with self.assertRaises(ValueError) as caught:self.load()
        self.assertNotIn('must-not-leak',str(caught.exception))
    def test_mock_cannot_mount_credentials(self):
        self.p['services']['agent-gateway']['secrets']={'github_token':str(self.policy)}
        with self.assertRaises(ValueError):self.load()
    def test_credentials_are_fingerprinted_without_reading_contents(self):
        token = self.config.parent/'github_token'; token.write_text('never-read-this'); token.chmod(0o400)
        config = json.loads(self.config.read_text()); config['mode']='live'
        config['providers']['github']['token_file']='/run/secrets/github_token'
        self.config.chmod(0o644); self.config.write_text(json.dumps(config)); self.config.chmod(0o444)
        self.p['services']['agent-gateway']['secrets']={'github_token':str(token)}
        original_stat, original_read = Path.stat, Path.read_bytes
        def stat(path, *args, **kwargs):
            value=original_stat(path,*args,**kwargs)
            if path == token:
                fields={key:getattr(value,key) for key in dir(value) if key.startswith('st_')}
                fields['st_uid']=10001
                return h.SimpleNamespace(**fields)
            return value
        def read(path):
            if path == token: raise AssertionError('credential contents read')
            return original_read(path)
        class Docker:
            def data(self,*args):
                return [{'Os':'linux','Architecture':'arm64','Id':'sha256:'+'a'*64,
                         'Config':{'User':'10001:10001'}}]
        with patch.object(Path,'stat',stat), patch.object(Path,'read_bytes',read):
            result=h.services.prepare(h,self.load(),Docker(),h.capabilities())
        self.assertNotIn('never-read-this',json.dumps(result))
        self.assertIsNone(result['agent-gateway']['files'][-1]['sha256'])

    def test_service_image_mismatch_fails_preparation(self):
        class Docker:
            def data(self,*args):return [{'Os':'linux','Architecture':'amd64'}]
        with self.assertRaisesRegex(h.Error,'architecture'):
            h.services.prepare(h,self.load(),Docker(),h.capabilities())

if __name__=='__main__':unittest.main()
