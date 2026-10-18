import copy
import json
from pathlib import Path
import tempfile
import unittest
from tools.function_inventory import TARGET
from tools.function_supplements import enumeration,module
class FunctionSupplementTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.directory=self.root/'docs/recovery';self.directory.mkdir(parents=True)
        (self.root/'source.cpp').write_text('fixture')
        self.row=dict(address='0x400020',end_exclusive='0x400030',name='callback',evidence='registered and executed',sources=['source.cpp'],direct_callees=['0x400000'])
        self.base=dict(target_sha256=TARGET,procedure_count=1,functions=[dict(address='0x400000',name='base')])
    def write(self,rows=None,target=TARGET):
        (self.directory/'function-supplements.json').write_text(json.dumps(dict(schema=1,modules={target:rows if rows is not None else [self.row]})))
    def test_merge_preserves_base_and_does_not_certify_recovery(self):
        self.row['direct_callees']=['0x00400000']
        self.write();before=copy.deepcopy(self.base);result=enumeration(self.base,self.directory)
        self.assertEqual(self.base,before);self.assertEqual(result['procedure_count'],2)
        self.assertEqual(result['base_procedure_count'],1);self.assertEqual(result['supplemental_entries'],1)
        self.assertEqual(result['functions'][-1]['boundary_origin'],'supplement')
        self.assertNotIn('translation',result['functions'][-1])
        original=dict(target_sha256=TARGET,provenance={'enumeration_sha256':'base-digest'},summary={'function_entries':1,'internal_entries':1,'decompilation':{'success':1}},functions=[dict(address='0x400000',name='base',direct_callees=[])])
        updated=module(original,self.directory)
        self.assertEqual(updated['provenance']['enumeration_sha256'],'base-digest')
        self.assertEqual(updated['summary']['internal_entries'],2)
        self.assertEqual(updated['functions'][-1]['translation'],'unreviewed')
        self.assertEqual(updated['functions'][-1]['direct_callees'],['0x400000'])
        self.assertEqual(updated['functions'][-1]['decompilation'],'not-exported-supplement')
    def test_target_scope_and_absent_file(self):
        self.assertIs(enumeration(self.base,self.directory),self.base)
        self.write(target='a'*64);self.assertIs(enumeration(self.base,self.directory),self.base)
    def test_duplicate_base_and_supplement_are_rejected(self):
        self.write([self.row,self.row])
        with self.assertRaises(ValueError):enumeration(self.base,self.directory)
        self.write([self.row|dict(address='0x400000')])
        with self.assertRaisesRegex(ValueError,'conflicts'):enumeration(self.base,self.directory)
        with self.assertRaisesRegex(ValueError,'incomplete'):enumeration(self.base|dict(procedure_count=2),self.directory)
    def test_bad_boundaries_evidence_and_sources_are_rejected(self):
        for change in (dict(end_exclusive='0x400020'),dict(address='EXTERNAL:0x1'),dict(evidence=''),dict(sources=['../outside']),dict(sources=['missing']),dict(direct_callees=['bad']),dict(name=4)):
            with self.subTest(change=change),self.assertRaises(ValueError):
                self.write([self.row|change]);enumeration(self.base,self.directory)
        self.write([self.row,self.row|dict(address='0x400028',end_exclusive='0x400040')])
        with self.assertRaisesRegex(ValueError,'overlapping'):enumeration(self.base,self.directory)
if __name__=='__main__':unittest.main()
