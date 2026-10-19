import argparse
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backtesting.research_protocol import register
from ops.reproduce_research import create_run, reproduce, _safe_write, main


class ResearchReproductionTests(unittest.TestCase):
    def test_no_data_run_reproduces_and_tamper_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);envelope=register(root/"protocol.json")
            args=argparse.Namespace(history=root/"absent.sqlite",sessions=5,option_manifest=root/"absent-options.json",output=root/"runs")
            result=create_run(args,envelope);run=Path(result["run_directory"])
            self.assertEqual(result["option_data_status"],"UNAVAILABLE")
            self.assertEqual(reproduce(run)["status"],"REPRODUCTION_VERIFIED")
            self.assertFalse(json.loads((run/"analysis.json").read_text())["strategy_validated"])
            (run/"underlying_input.jsonl").write_text("{}\n")
            with self.assertRaisesRegex(ValueError,"INPUT_CHANGED"):reproduce(run)

    def test_source_and_protocol_tamper_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);envelope=register(root/"protocol.json")
            args=argparse.Namespace(history=root/"absent.sqlite",sessions=5,option_manifest=root/"absent-options.json",output=root/"runs")
            run=Path(create_run(args,envelope)["run_directory"]);path=run/"manifest.json"
            original=json.loads(path.read_text());bad=json.loads(json.dumps(original))
            bad["source_hashes"]["core/sessions.py"]="0"*64;path.write_text(json.dumps(bad))
            with self.assertRaisesRegex(ValueError,"SOURCE_CODE_CHANGED"):reproduce(run)
            bad=json.loads(json.dumps(original));bad["protocol"]["trial_count"]=999;path.write_text(json.dumps(bad))
            with self.assertRaisesRegex(ValueError,"PROTOCOL_HASH_MISMATCH"):reproduce(run)

    def test_output_secret_refusal_is_before_write(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"report.md"
            with self.assertRaisesRegex(ValueError,"SECRET_PATTERN"):
                _safe_write(path,"123456789:"+"A"*30)
            self.assertFalse(path.exists())

    def test_registration_only_does_not_read_database(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch("backtesting.underlying_study.load_bars",side_effect=AssertionError("must not read")):
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(main(["--register-only","--protocol",str(Path(folder)/"protocol.json")]),0)


if __name__=="__main__":unittest.main()
