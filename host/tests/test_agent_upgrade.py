import copy
import importlib.util
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location('upgrade',Path(__file__).parents[1]/'upgrade-agent.py')
u=importlib.util.module_from_spec(spec)
spec.loader.exec_module(u)
class UpgradeTests(unittest.TestCase):
    def test_only_agent_image_can_change(self):
        old={'profile':{'image':{'reference':'old'},'state':{'agenthome':'same'}},'images':{'agent':'old','proxy':'proxy'},'services':{'gateway':'same'}}
        new=copy.deepcopy(old)
        new['profile']['image']['reference']='new'
        new['images']['agent']='new'
        u.validate_change(old,new)
        for where in ('profile','proxy','services'):
            bad=copy.deepcopy(new)
            if where=='profile':bad['profile']['state']['agenthome']='other'
            elif where=='proxy':bad['images']['proxy']='other'
            else:bad['services']['gateway']='other'
            with self.subTest(where=where),self.assertRaises(u.h.Error):u.validate_change(old,bad)
