import json
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'host-bin/story-setup'

class SetupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve(); self.repo = self.root/'kms'
        self.git(self.root, 'init', '--bare', str(self.root/'origin.git'))
        self.git(self.root, 'clone', str(self.root/'origin.git'), str(self.repo))
        self.git(self.repo, 'config', 'user.name', 'Test'); self.git(self.repo, 'config', 'user.email', 'test@example.invalid')
        self.git(self.repo, 'checkout', '-b', 'main'); (self.repo/'file').write_text('test')
        self.git(self.repo, 'add', 'file'); self.git(self.repo, 'commit', '-m', 'initial')
        self.git(self.repo, 'push', 'origin', 'main')
        self.workspace = self.root/'stories/sc-1-test'; self.workspace.mkdir(parents=True)
        self.request = self.workspace/'setup.json'
        self.row = dict(repository='kms',destination='stories/sc-1-test/branch',branch='feature',base='main',mode='new')
    def git(self, root, *args):
        return subprocess.run(['git','-c','commit.gpgsign=false','-c','core.hooksPath=/dev/null','-C',str(root),*args],check=True,capture_output=True,text=True).stdout.strip()
    def run_setup(self, rows=None):
        self.request.write_text(json.dumps({'version':1,'worktrees':rows or [self.row]}))
        return subprocess.run([str(SCRIPT),'apply',str(self.request),'--workspace-root',str(self.root)],capture_output=True,text=True)
    def test_new_portable_replay(self):
        (self.repo/'untracked').write_text('preserve')
        r=self.run_setup(); self.assertEqual(r.returncode,0,r.stderr)
        work=self.workspace/'branch'; self.assertEqual(self.git(work,'branch','--show-current'),'feature')
        self.assertTrue((work/'.git').read_text().startswith('gitdir: ../../'))
        self.assertEqual((self.repo/'untracked').read_text(),'preserve')
        moved=self.root/'moved'; moved.mkdir()
        # Relocate the complete root without rewriting metadata, exercising forward-pointer portability.
        import shutil
        shutil.copytree(self.repo,moved/'kms'); shutil.copytree(self.root/'stories',moved/'stories')
        self.assertEqual(self.git(moved/'stories/sc-1-test/branch','rev-parse','HEAD'),self.git(work,'rev-parse','HEAD'))
        self.assertNotEqual(self.run_setup().returncode,0)
    def test_existing_and_pin(self):
        self.git(self.repo,'branch','review'); self.git(self.repo,'push','origin','review')
        self.row.update(branch='review',base='review',mode='existing',expected_commit=self.git(self.repo,'rev-parse','HEAD'))
        r=self.run_setup();self.assertEqual(r.returncode,0,r.stderr)
        self.assertEqual(self.git(self.workspace/'branch','rev-parse','--abbrev-ref','@{upstream}'),'origin/review')
    def test_reject_escape_and_symlink(self):
        self.row['destination']='../escape';self.assertNotEqual(self.run_setup().returncode,0)
        self.row['destination']='stories/sc-1-test/branch';(self.workspace/'branch').symlink_to(self.root/'missing')
        self.assertNotEqual(self.run_setup().returncode,0)
    def test_validate_batch_before_creation(self):
        other=dict(self.row,branch='main',destination='stories/sc-1-test/other')
        self.assertNotEqual(self.run_setup([self.row,other]).returncode,0)
        self.assertFalse((self.workspace/'branch').exists())
    def test_stale_pin(self):
        self.row['expected_commit']='0'*40;self.assertNotEqual(self.run_setup().returncode,0)
        self.assertFalse((self.workspace/'branch').exists())

if __name__=='__main__':unittest.main()
