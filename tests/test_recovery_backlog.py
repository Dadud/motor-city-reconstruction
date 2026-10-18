import json
from pathlib import Path
import tempfile
import unittest

from tools.function_inventory import TARGET, load_reviews
from tools.recovery_backlog import module_work, strongly_connected


class RecoveryBacklogTests(unittest.TestCase):
    def test_cycles_are_grouped_without_losing_dependencies(self):
        graph = {'a': ['b'], 'b': ['a', 'c'], 'c': [], 'd': ['c']}
        groups = {frozenset(group) for group in strongly_connected(graph)}
        self.assertEqual(groups, {frozenset('ab'), frozenset('c'), frozenset('d')})

    def test_long_graph_does_not_require_recursive_python_calls(self):
        graph = {str(i): [str(i+1)] if i < 2999 else [] for i in range(3000)}
        self.assertEqual(len(strongly_connected(graph)), 3000)

    def test_unknown_calls_stay_visible_and_do_not_become_functions(self):
        module = dict(target_sha256=TARGET, provenance={'enumeration_sha256': 'fixture'},
                      summary={'function_entries': 2}, functions=[
                          dict(address='0x400000', direct_callees=['0x400010', '0xdeadbeef']),
                          dict(address='0x400010', direct_callees=[])])
        result = module_work(module, {})
        self.assertEqual(result['summary']['explicitly_reviewed'], 0)
        self.assertEqual(result['unresolved_direct_edges'],
                         [dict(caller='0x400000', callee='0xdeadbeef')])
        self.assertEqual(sum(len(c['members']) for c in result['components']), 2)
        with self.assertRaises(ValueError):
            module_work(module, {'0xbad': {}})

    def test_reviews_are_hash_scoped_and_cannot_silently_replace_claims(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            directory = root/'docs/recovery'
            batches = directory/'review-batches'
            batches.mkdir(parents=True)
            (root/'source.cpp').write_text('authored fixture')
            review = dict(translation='partial', verification='bounded', scope='supplied child',
                          sources=['source.cpp'])
            (directory/'function-reviews.json').write_text(json.dumps({'0x400000': review}))
            batch = dict(target_sha256='a'*64, functions={'0x400000': review})
            (batches/'other.json').write_text(json.dumps(batch))
            self.assertEqual(len(load_reviews(root)), 1)
            self.assertEqual(len(load_reviews(root, 'a'*64)), 1)
            batch['target_sha256'] = TARGET
            (batches/'other.json').write_text(json.dumps(batch))
            with self.assertRaisesRegex(ValueError, 'duplicate review'):
                load_reviews(root)

    def test_missing_claim_needs_no_implementation_but_completed_claim_does(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            directory = root/'docs/recovery'
            directory.mkdir(parents=True)
            missing = dict(translation='missing', verification='static-analysis-only', scope='unresolved')
            path = directory/'function-reviews.json'
            path.write_text(json.dumps({'0x400000': missing}))
            self.assertEqual(load_reviews(root)['0x400000']['sources'], [])
            missing['translation'] = 'python-and-native-bounded'
            path.write_text(json.dumps({'0x400000': missing}))
            with self.assertRaisesRegex(ValueError, 'requires sources'):
                load_reviews(root)


if __name__ == '__main__':
    unittest.main()
