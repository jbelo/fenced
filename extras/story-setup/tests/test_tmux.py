import importlib.machinery
import importlib.util
import json
import subprocess
import uuid
from unittest.mock import patch
from test_setup import SetupTests, SCRIPT

loader = importlib.machinery.SourceFileLoader('story_setup', str(SCRIPT))
spec = importlib.util.spec_from_loader(loader.name, loader)
setup = importlib.util.module_from_spec(spec); loader.exec_module(setup)

class TmuxTests(SetupTests):
    def setUp(self):
        super().setUp()
        self.socket = 'story-setup-test-' + uuid.uuid4().hex
        self.tmux('new-session', '-d', '-s', 'review', '/bin/bash')
        self.addCleanup(lambda: subprocess.run(['tmux','-L',self.socket,'kill-server'],capture_output=True))
        self.request.write_text(json.dumps({'version':1,'tmux':{'session':'review','window':'rv-test'},'worktrees':[self.row]}))
    def tmux(self,*args):
        p=subprocess.run(['tmux','-L',self.socket,'-f','/dev/null',*args],capture_output=True,text=True)
        if p.returncode:raise setup.SetupError(p.stderr)
        return p.stdout.strip()
    def test_window_and_directory(self):
        with patch.object(setup,'tmux',self.tmux):setup.apply(self.root,self.request)
        result=json.loads(self.request.with_name('setup.json.result.json').read_text())
        self.assertEqual(result['status'],'complete')
        window=result['tmux'];self.assertEqual(window['session'],'review')
        self.assertEqual(self.tmux('display-message','-p','-t',window['pane_id'],'#{pane_current_path}'),str(self.workspace))
        with patch.object(setup,'tmux',self.tmux),self.assertRaises(setup.SetupError):setup.retry_window(self.root,self.request)
    def test_collision_before_git(self):
        self.tmux('new-window','-d','-t','review:','-n','rv-test')
        with patch.object(setup,'tmux',self.tmux),self.assertRaises(setup.SetupError):setup.apply(self.root,self.request)
        self.assertFalse((self.workspace/'branch').exists())
        self.assertFalse(self.request.with_name('setup.json.result.json').exists())
    def test_window_retry_without_fetch(self):
        with patch.object(setup,'tmux',self.tmux),patch.object(setup,'create_window',side_effect=setup.SetupError('simulated tmux failure')),self.assertRaises(setup.SetupError):
            setup.apply(self.root,self.request)
        receipt=self.request.with_name('setup.json.result.json')
        self.assertEqual(json.loads(receipt.read_text())['status'],'tmux_failed')
        original=setup.git
        def no_fetch(repo,*args,**kwargs):
            self.assertNotIn('fetch',args)
            self.assertNotIn('add',args)
            return original(repo,*args,**kwargs)
        with patch.object(setup,'tmux',self.tmux),patch.object(setup,'git',no_fetch):setup.retry_window(self.root,self.request)
        self.assertEqual(json.loads(receipt.read_text())['status'],'complete')

    def test_legacy_migration_and_retry(self):
        self.assertEqual(self.run_setup().returncode,0)
        receipt=self.request.with_name('setup.json.result.json')
        data=json.loads(receipt.read_text());data.pop('git_status',None)
        receipt.write_text(json.dumps(data))
        original_request=self.request.read_bytes();original_git=setup.git
        def readonly_git(repo,*args,**kwargs):
            self.assertEqual(args[0],'rev-parse' if args[0]=='rev-parse' else 'symbolic-ref')
            return original_git(repo,*args,**kwargs)
        with patch.object(setup,'git',readonly_git),patch.object(setup,'create_window',side_effect=setup.SetupError('temporary failure')),self.assertRaises(setup.SetupError):
            setup.retry_window(self.root,self.request,'review','rv-migrated')
        failed=json.loads(receipt.read_text())
        self.assertEqual(failed['git_status'],'complete')
        self.assertEqual(failed['window_request'],{'session':'review','window':'rv-migrated'})
        with patch.object(setup,'git',readonly_git),patch.object(setup,'tmux',self.tmux):
            setup.retry_window(self.root,self.request)
        self.assertEqual(self.request.read_bytes(),original_request)
        result=json.loads(receipt.read_text())
        self.assertEqual(result['request_sha256'],data['request_sha256'])
        self.assertEqual(result['status'],'complete')
        self.assertEqual(result['tmux']['window'],'rv-migrated')
        with patch.object(setup,'tmux',self.tmux),self.assertRaises(setup.SetupError):
            setup.retry_window(self.root,self.request,'review','rv-other')

    def test_migration_rejects_changed_request(self):
        self.assertEqual(self.run_setup().returncode,0)
        self.request.write_text(self.request.read_text()+' ')
        with patch.object(setup,'create_window') as create,self.assertRaises(setup.SetupError):
            setup.retry_window(self.root,self.request,'review','rv-migrated')
        create.assert_not_called()
