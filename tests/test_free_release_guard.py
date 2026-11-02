import unittest
from ops.release_guard import path_problem, inspect

class FreeReleaseGuard(unittest.TestCase):
    def test_frozen_evidence_is_explicit_and_still_scanned(self):
        path='reports/FREE_PROVIDER_CAPABILITIES_2026-11-01.json'
        self.assertIsNone(path_problem(path))
        self.assertEqual(path_problem('reports/arbitrary.json'),'unapproved JSON payload')
        bad=b'C:'+b'/Users/'+b'Auto/'+b'private'
        self.assertTrue(inspect({path:bad},require_report=False))
        self.assertEqual(inspect({path:b'{"secrets":false}'},require_report=False),[])

if __name__=='__main__':unittest.main()
