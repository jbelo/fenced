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
        module=h.services.adapter(h.capabilities()['agent-gateway']['adapter'])
        self.assertNotIn('volumes',module.describe(self.load()['services']['agent-gateway']))
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
    def live_volume(self):
        config=json.loads(self.config.read_text());config['mode']='live'
        config['providers']['github']['token_file']='/run/secrets/github_token'
        self.config.chmod(0o644);self.config.write_text(json.dumps(config));self.config.chmod(0o444)
        self.p['services']['agent-gateway']['secrets']={'volume':'private-credentials','helper_image':'helper:test'}
        return self.load()

    def test_staged_volume_metadata_and_readonly_probe(self):
        class Docker:
            calls=[]
            def data(self,*args):
                return [{'Os':'linux','Architecture':'arm64','Id':'sha256:'+'a'*64,'Config':{'User':'10001:10001'}}]
            def inspect(self,*args):
                return {'Name':'private-credentials','Driver':'local','Labels':{'agent-gateway.credentials':'true'},'CreatedAt':'stable'}
            def call(self,*args):self.calls.append(args)
        docker=Docker();result=h.services.prepare(h,self.live_volume(),docker,h.capabilities())
        self.assertEqual(len(result['agent-gateway']['files']),2)
        self.assertEqual(result['agent-gateway']['volumes'][0]['identity']['CreatedAt'],'stable')
        h.services.verify_volumes(docker,{'services':result})
        self.assertIn('--network=none',docker.calls[0]);self.assertIn('--log-driver=none',docker.calls[0])
        self.assertTrue(any('readonly,volume-nocopy' in arg for arg in docker.calls[0]))
        self.assertNotIn('never-read-this',json.dumps(result))

    def test_unlabeled_external_volume_rejected_before_probe(self):
        class Docker:
            def data(self,*args):return [{'Os':'linux','Architecture':'arm64','Id':'sha256:'+'a'*64,'Config':{'User':'10001:10001'}}]
            def inspect(self,*args):return {'Driver':'local','Labels':{}}
        with self.assertRaisesRegex(h.Error,'externally staged'):
            h.services.prepare(h,self.live_volume(),Docker(),h.capabilities())

    def test_agent_home_cannot_be_used_for_credentials(self):
        self.live_volume();self.p['services']['agent-gateway']['secrets']['volume']='home'
        with self.assertRaises(ValueError):self.load()

    def test_direct_host_secret_paths_are_rejected(self):
        self.live_volume();self.p['services']['agent-gateway']['secrets']={'github_token':'/private/token'}
        with self.assertRaisesRegex(ValueError,'staged volume'):self.load()

    def test_service_image_mismatch_fails_preparation(self):
        class Docker:
            def data(self,*args):return [{'Os':'linux','Architecture':'amd64'}]
        with self.assertRaisesRegex(h.Error,'architecture'):
            h.services.prepare(h,self.load(),Docker(),h.capabilities())

if __name__=='__main__':unittest.main()
