import contextlib
import hashlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from my_big_brother import config, readers, runner
from my_big_brother import __main__ as cli
from my_big_brother.paths import Paths


READER = '''from my_big_brother.sources import SourceResult

def collect(path, start, end):
    return SourceResult(rows=[{"timestamp": start.isoformat(), "role": "user",
                               "content": path.read_text(encoding="utf-8")}])
'''


class PersonalReaderTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.paths = Paths(self.root / "config", self.root / "data")
        self.settings = config.initialize(self.paths, sources=[])
        self.settings["notifications"]["enabled"] = False
        config.write_json(self.paths.config / "config.json", self.settings)
        self.history = self.root / "history.txt"
        self.history.write_text("Synthetic user request", encoding="utf-8")
        self.reader = self.paths.config / "readers" / "some-agent" / "reader.py"
        self.reader.parent.mkdir(parents=True)
        self.reader.write_text(READER, encoding="utf-8")
        self.settings["sources"] = {"some-agent": {
            "enabled": True, "path": str(self.history), "reader": str(self.reader)}}

    def save(self):
        config.write_json(self.paths.config / "config.json", self.settings)
        self.settings = config.load(self.paths)

    def prepare(self):
        self.save()
        result = runner.prepare_run(self.paths, self.settings, "2020-01-15")
        run = Path(result["run_dir"])
        return result, run, runner.read_object(run / "context.json")

    def stage(self, run, context):
        for name in context["output_paths"]:
            path = Path(name)
            if path.suffix == ".md":
                path.write_text("# Synthetic review\n", encoding="utf-8")
            else:
                key = "samples" if path.name == "time-estimates.json" else "segments"
                config.write_json(path, {"date": context["date"], key: []})
        config.write_json(run / "completion.json", context["completion_example"])

    def test_unknown_reader_can_prepare_and_finish_without_registration(self):
        result, run, context = self.prepare()
        self.assertEqual((result["status"], result["entries"]), ("prepared", 1))
        selected = {"path": str(self.reader), "sha256": hashlib.sha256(self.reader.read_bytes()).hexdigest()}
        self.assertEqual(context["review_configuration"]["readers"], {"some-agent": selected})
        manifest = runner.read_object(run / "manifest.json")
        self.assertEqual(manifest["sources"]["some-agent"]["reader"], selected)
        row = json.loads((run / "indexes" / "some-agent.jsonl").read_text())
        self.assertEqual(row["role"], "user")
        self.assertEqual(Path(row["excerpt"]).read_text(), self.history.read_text())
        self.stage(run, context)
        self.assertEqual(runner.finish_run(self.paths, self.settings, run)["status"], "completed")
        self.assertTrue(runner.completed(self.paths, self.settings, "2020-01-15"))
        self.assertFalse(list(self.paths.config.rglob("__pycache__")))

    def test_explicit_binding_wins_over_same_name_builtin(self):
        self.settings["sources"]["codex"] = self.settings["sources"].pop("some-agent")
        with patch("my_big_brother.sources.codex.collect", side_effect=AssertionError("builtin called")) as builtin:
            result, run, _ = self.prepare()
        builtin.assert_not_called()
        self.assertEqual(result["entries"], 1)
        self.assertEqual(set(runner.read_object(run / "manifest.json")["sources"]), {"codex"})

    def test_later_official_support_preserves_personal_code_and_binding(self):
        self.save()
        before = (self.paths.config / "config.json").read_bytes()
        with patch.object(config, "SOURCES", config.SOURCES + ("some-agent",)), \
             patch.object(readers.importlib, "import_module", side_effect=AssertionError("builtin called")) as builtin:
            self.settings = config.initialize(self.paths)
            result = runner.prepare_run(self.paths, self.settings, "2020-01-15")
        builtin.assert_not_called()
        self.assertEqual(result["entries"], 1)
        self.assertEqual((self.paths.config / "config.json").read_bytes(), before)
        self.assertEqual(self.reader.read_text(), READER)

    def test_explicit_switch_uses_only_builtin_and_retains_local_code(self):
        from my_big_brother.sources import SourceResult
        spec = self.settings["sources"].pop("some-agent")
        self.settings["sources"]["codex"] = spec
        spec["required"] = True
        del spec["reader"]
        with patch("my_big_brother.sources.codex.collect", return_value=SourceResult()) as builtin:
            result, _, _ = self.prepare()
        builtin.assert_called_once()
        self.assertEqual(result["status"], "empty")
        self.assertEqual(spec["path"], str(self.history))
        self.assertTrue(spec["required"])
        self.assertEqual(self.reader.read_text(), READER)

    def test_broken_local_reader_never_falls_back(self):
        self.settings["sources"]["codex"] = self.settings["sources"].pop("some-agent")
        for code in ("this is invalid Python !", "raise RuntimeError('broken reader')",
                     "collect = None", "def collect(*args): return {}",
                     "from my_big_brother.sources import SourceResult\n"
                     "def collect(*args): return SourceResult(rows=[{'invalid': object()}])"):
            with self.subTest(code=code):
                self.reader.write_text(code, encoding="utf-8")
                with patch("my_big_brother.sources.codex.collect") as builtin:
                    result, run, _ = self.prepare()
                builtin.assert_not_called()
                self.assertEqual(result["status"], "blocked")
                source = runner.read_object(run / "manifest.json")["sources"]["codex"]
                self.assertEqual(source["status"], "unavailable")
                self.assertTrue(source["gaps"])
                self.assertTrue(Path(source["diagnostic"]).is_file())

    def test_missing_optional_reader_is_gap_and_required_reader_blocks(self):
        from my_big_brother.sources import SourceResult
        self.settings["sources"]["some-agent"]["reader"] = str(self.reader.parent / "missing.py")
        self.settings["sources"]["codex"] = {"path": str(self.history)}
        with patch("my_big_brother.sources.codex.collect", return_value=SourceResult()):
            result, run, _ = self.prepare()
            self.assertEqual(result["status"], "empty")
            source = runner.read_object(run / "manifest.json")["sources"]["some-agent"]
            self.assertEqual(source["status"], "unavailable")
            self.settings["sources"]["some-agent"]["required"] = True
            result, _, _ = self.prepare()
            self.assertEqual(result["status"], "blocked")

    def test_doctor_and_config_do_not_execute_readers_or_scan_directory(self):
        self.reader.write_text("raise RuntimeError('must not execute')", encoding="utf-8")
        (self.reader.parent / "other.py").write_text("raise RuntimeError('must not scan')", encoding="utf-8")
        self.save()
        with patch.object(cli, "discover", return_value=self.paths), \
             contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(cli.main(["doctor"]), 0)
        source = json.loads(output.getvalue())["sources"]["some-agent"]
        self.assertEqual(source["reader"], {"path": str(self.reader), "exists": True})
        self.reader.write_text(READER, encoding="utf-8")
        self.assertEqual(self.prepare()[0]["status"], "prepared")

    def test_config_rejects_ambiguous_bindings(self):
        for source, spec in (
                ("some-agent", {"path": str(self.history)}),
                ("../unsafe", {"path": str(self.history), "reader": str(self.reader)}),
                ("Agent", {"path": str(self.history), "reader": str(self.reader)}),
                ("some-agent", {"path": str(self.history), "reader": "relative.py"}),
                ("some-agent", {"path": str(self.history), "reader": None}),
                ("some-agent", {"reader": str(self.reader)})):
            with self.subTest(source=source, spec=spec):
                self.settings["sources"] = {source: spec}
                config.write_json(self.paths.config / "config.json", self.settings)
                with self.assertRaises(ValueError):
                    config.load(self.paths)

    def test_same_size_same_mtime_edits_are_not_cached(self):
        self.reader.write_text(READER.replace('"user"', '"aaaa"'), encoding="utf-8")
        original_stat = self.reader.stat()
        result, _, _ = self.prepare()
        self.assertEqual(result["entries"], 1)
        self.reader.write_text(READER.replace('"user"', '"bbbb"'), encoding="utf-8")
        os.utime(self.reader, (original_stat.st_atime, original_stat.st_mtime))
        _, run, _ = self.prepare()
        row = json.loads((run / "indexes" / "some-agent.jsonl").read_text())
        self.assertEqual(row["role"], "bbbb")
        self.assertFalse(list(self.paths.config.rglob("__pycache__")))

    def test_reader_edit_invalidates_finish_and_completed_reuse(self):
        _, run, context = self.prepare()
        self.stage(run, context)
        self.reader.write_text(READER + "\n# Changed\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "configuration changed"):
            runner.finish_run(self.paths, self.settings, run)
        _, run, context = self.prepare()
        self.stage(run, context)
        runner.finish_run(self.paths, self.settings, run)
        self.assertTrue(runner.completed(self.paths, self.settings, "2020-01-15"))
        self.reader.write_text(READER, encoding="utf-8")
        self.assertFalse(runner.completed(self.paths, self.settings, "2020-01-15"))

    def test_identity_is_frozen_before_collection(self):
        code = READER.replace('    return SourceResult',
                              '    from pathlib import Path\n'
                              '    Path(__file__).write_text("changed", encoding="utf-8")\n'
                              '    return SourceResult')
        self.reader.write_text(code, encoding="utf-8")
        _, run, context = self.prepare()
        self.assertEqual(context["review_configuration"]["readers"]["some-agent"]["sha256"],
                         hashlib.sha256(code.encode()).hexdigest())
        self.stage(run, context)
        with self.assertRaisesRegex(ValueError, "configuration changed"):
            runner.finish_run(self.paths, self.settings, run)

    def test_edit_between_identity_and_load_reports_unavailable(self):
        expected = readers.identities(self.settings["sources"])["some-agent"]
        self.reader.write_text(READER + "\n# Changed\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "changed during preparation"):
            readers.load("some-agent", self.settings["sources"]["some-agent"], expected)

    def test_optional_asset_interface_is_shared(self):
        self.reader.write_text(READER + '''
def prepare_assets(rows, directory):
    directory.mkdir()
    return {"status": "ok", "gaps": [], "count": len(rows)}
''', encoding="utf-8")
        result, run, _ = self.prepare()
        source = runner.read_object(run / "manifest.json")["sources"]["some-agent"]
        self.assertEqual(result["status"], "prepared")
        self.assertEqual(source["assets"]["count"], 1)
        self.assertTrue(Path(source["assets"]["root"]).is_dir())


if __name__ == "__main__":
    unittest.main()
