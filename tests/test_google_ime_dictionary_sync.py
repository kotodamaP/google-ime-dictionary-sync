from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from google_ime_dictionary_sync import merge_export, parse_args, prepare, record_success  # noqa: E402


SAMPLE = """| 正式表記 | alias | 読み | memo | scope候補 | 出典 | status |
|---|---|---|---|---|---|---|
| 七海 | Nanami | ななみ | memo | shared | sample | reviewed |
"""


class GoogleImeDictionarySyncTests(unittest.TestCase):
    def test_prepare_no_baseline_then_unchanged_after_record_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "term-candidates.md"
            source.write_text(SAMPLE, encoding="utf-8")
            backup_root = root / "runs"
            state_root = root / "state"

            first_args = parse_args(
                [
                    "prepare",
                    "--source-md",
                    str(source),
                    "--backup-root",
                    str(backup_root),
                    "--state-root",
                    str(state_root),
                ]
            )
            first = prepare(first_args)
            self.assertEqual(first["status"], "no_previous_baseline")

            record_args = parse_args(["record-success", "--run-dir", str(first["runDir"]), "--state-root", str(state_root)])
            record = record_success(record_args)
            self.assertEqual(record["buildIdentity"], first["buildIdentity"])

            second_args = parse_args(
                [
                    "prepare",
                    "--source-md",
                    str(source),
                    "--backup-root",
                    str(backup_root),
                    "--state-root",
                    str(state_root),
                ]
            )
            second = prepare(second_args)
            self.assertEqual(second["status"], "unchanged")
            self.assertFalse(second["googleImeChanged"])

    def test_prepare_changed_when_build_options_change(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "term-candidates.md"
            source.write_text(SAMPLE, encoding="utf-8")
            backup_root = root / "runs"
            state_root = root / "state"

            first = prepare(
                parse_args(
                    [
                        "prepare",
                        "--source-md",
                        str(source),
                        "--backup-root",
                        str(backup_root),
                        "--state-root",
                        str(state_root),
                    ]
                )
            )
            record_success(parse_args(["record-success", "--run-dir", str(first["runDir"]), "--state-root", str(state_root)]))
            changed = prepare(
                parse_args(
                    [
                        "prepare",
                        "--source-md",
                        str(source),
                        "--backup-root",
                        str(backup_root),
                        "--state-root",
                        str(state_root),
                        "--pos",
                        "名詞",
                    ]
                )
            )
            self.assertEqual(changed["status"], "changed")

    def test_prepare_does_not_modify_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "term-candidates.md"
            source.write_text(SAMPLE, encoding="utf-8")
            state_root = root / "state"
            prepare(
                parse_args(
                    [
                        "prepare",
                        "--source-md",
                        str(source),
                        "--backup-root",
                        str(root / "runs"),
                        "--state-root",
                        str(state_root),
                    ]
                )
            )
            self.assertFalse(any(state_root.glob("*")))

    def test_merge_export_normalizes_katakana_and_drops_blank_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            generated = root / "generated.tsv"
            generated.write_text("ななみ\t七海\t固有名詞\tgenerated\n", encoding="utf-8")
            export = root / "export.tsv"
            export.write_text("ナナミ\t七海\t固有名詞\told\n\t\t固有名詞\tblank\n", encoding="utf-8")
            payload = merge_export(
                parse_args(
                    [
                        "merge-export",
                        "--generated-tsv",
                        str(generated),
                        "--ime-export",
                        str(export),
                        "--backup-root",
                        str(root / "runs"),
                    ]
                )
            )
            output = Path(str(payload["outputTsv"])).read_text(encoding="utf-8")
            self.assertEqual(output, "ななみ\t七海\t固有名詞\tgenerated\n")
            self.assertEqual(payload["stats"]["invalidExportRows"], 1)
            self.assertEqual(payload["stats"]["replacedByGeneratedRows"], 1)


if __name__ == "__main__":
    unittest.main()
