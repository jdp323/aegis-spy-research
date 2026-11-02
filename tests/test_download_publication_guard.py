import hashlib,unittest
from unittest.mock import patch
from ops.release_guard import inspect,path_problem,REVIEWED_DOWNLOADS

class DownloadPublicationGuard(unittest.TestCase):
    def test_exact_attestation_allows_binary_but_mutation_fails(self):
        path='reports/downloads/AEGIS_FREE_ONLY_IMPLEMENTATION_2026-11-01.pdf'
        fixture=b'%PDF-ISOLATED-FIXTURE\x00not-a-real-report'
        with patch.dict(REVIEWED_DOWNLOADS,{path:hashlib.sha256(fixture).hexdigest()}):
            self.assertEqual(inspect({path:fixture},require_report=False),[])
            failures=inspect({path:fixture+b'changed'},require_report=False)
            self.assertEqual(failures[0]['reason'],'reviewed download digest mismatch')

    def test_renamed_or_unknown_binaries_have_no_exemption(self):
        self.assertIsNotNone(path_problem('reports/downloads/private.zip'))
        self.assertTrue(inspect({'reports/downloads/unknown.pdf':b'%PDF-ascii-without-nul'},require_report=False))
        self.assertTrue(inspect({'runtime/AEGIS_FREE_ONLY_IMPLEMENTATION_2026-11-01.pdf':b'%PDF\x00'},require_report=False))

    def test_attested_name_does_not_allow_replacement_text(self):
        path=next(iter(REVIEWED_DOWNLOADS))
        self.assertTrue(inspect({path:b'replacement'},require_report=False))
        self.assertEqual(len(REVIEWED_DOWNLOADS),4)

if __name__=='__main__':unittest.main()
