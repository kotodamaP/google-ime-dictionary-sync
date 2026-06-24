from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_dictionary import BuildError, BuildOptions, build_from_file, build_from_markdown, main  # noqa: E402


def table(rows: list[str], *, header: str | None = None, crlf: bool = False) -> str:
    header = header or "| 正式表記 | alias | 読み | memo | scope候補 | 出典 | status |"
    lines = [
        header,
        "|---|---|---|---|---|---|---|",
        *rows,
    ]
    return ("\r\n" if crlf else "\n").join(lines) + ("\r\n" if crlf else "\n")


class BuildDictionaryTests(unittest.TestCase):
    def test_builds_sorted_canonical_tsv(self) -> None:
        markdown = table(
            [
                "| 星野 | Star Field | ほしの | memo b | shared | sample | reviewed |",
                "| 青空 | Blue Sky | あおぞら | memo a | shared | sample | candidate |",
            ]
        )
        result = build_from_markdown(markdown, BuildOptions())
        self.assertEqual(
            result.canonical_tsv,
            "あおぞら\t青空\t固有名詞\tmemo a\nほしの\t星野\t固有名詞\tmemo b\n",
        )

    def test_alias_is_metadata_by_default(self) -> None:
        markdown = table(["| 七海 | Nanami | ななみ | memo | shared | sample | reviewed |"])
        result = build_from_markdown(markdown, BuildOptions())
        self.assertNotIn("Nanami", result.canonical_tsv)

    def test_emit_aliases_is_experimental_single_value(self) -> None:
        markdown = table(["| 七海 | Nanami, Nana | ななみ | memo | shared | sample | reviewed |"])
        result = build_from_markdown(markdown, BuildOptions(emit_aliases=True))
        self.assertIn("ななみ\tNanami, Nana\t固有名詞\tmemo\n", result.canonical_tsv)

    def test_duplicate_strict_fails(self) -> None:
        markdown = table(
            [
                "| 七海 | Nanami | ななみ | memo | shared | sample | reviewed |",
                "| 七海 | Nanami2 | ななみ | memo | shared | sample | reviewed |",
            ]
        )
        with self.assertRaises(BuildError):
            build_from_markdown(markdown, BuildOptions())

    def test_duplicate_lenient_keeps_first_and_warns(self) -> None:
        markdown = table(
            [
                "| 七海 | Nanami | ななみ | memo | shared | sample | reviewed |",
                "| 七海 | Nanami2 | ななみ | later | shared | sample | reviewed |",
            ]
        )
        result = build_from_markdown(markdown, BuildOptions(strict=False))
        self.assertEqual(result.canonical_tsv, "ななみ\t七海\t固有名詞\tmemo\n")
        self.assertTrue(result.warnings)

    def test_alias_duplicate_strict_fails(self) -> None:
        markdown = table(["| 七海 | 七海 | ななみ | memo | shared | sample | reviewed |"])
        with self.assertRaises(BuildError):
            build_from_markdown(markdown, BuildOptions(emit_aliases=True))

    def test_invalid_status_strict_fails(self) -> None:
        markdown = table(["| 七海 | Nanami | ななみ | memo | shared | sample | maybe |"])
        with self.assertRaises(BuildError):
            build_from_markdown(markdown, BuildOptions())

    def test_disabled_status_is_ignored(self) -> None:
        markdown = table(["| 七海 | Nanami | ななみ | memo | shared | sample | rejected |"])
        result = build_from_markdown(markdown, BuildOptions())
        self.assertEqual(result.canonical_tsv, "")

    def test_reading_rejects_katakana_by_default(self) -> None:
        markdown = table(["| 七海 | Nanami | ナナミ | memo | shared | sample | reviewed |"])
        with self.assertRaises(BuildError):
            build_from_markdown(markdown, BuildOptions())

    def test_long_vowel_mark_is_optional(self) -> None:
        markdown = table(["| コーヒー | coffee | こーひー | memo | shared | sample | reviewed |"])
        with self.assertRaises(BuildError):
            build_from_markdown(markdown, BuildOptions())
        result = build_from_markdown(markdown, BuildOptions(allow_long_vowel_mark=True))
        self.assertIn("こーひー\tコーヒー", result.canonical_tsv)

    def test_tabs_in_fields_fail(self) -> None:
        markdown = table(["| 七海 | Nanami | ななみ | bad\tmemo | shared | sample | reviewed |"])
        with self.assertRaises(BuildError):
            build_from_markdown(markdown, BuildOptions())

    def test_pipe_in_memo_can_be_escaped(self) -> None:
        markdown = table(["| 七海 | Nanami | ななみ | memo with \\| pipe | shared | sample | reviewed |"])
        result = build_from_markdown(markdown, BuildOptions())
        self.assertIn("memo with | pipe", result.canonical_tsv)

    def test_reordered_columns_are_supported(self) -> None:
        markdown = table(
            ["| reviewed | sample | shared | memo | ななみ | Nanami | 七海 |"],
            header="| status | 出典 | scope候補 | memo | 読み | alias | 正式表記 |",
        )
        result = build_from_markdown(markdown, BuildOptions())
        self.assertEqual(result.canonical_tsv, "ななみ\t七海\t固有名詞\tmemo\n")

    def test_utf8_bom_and_crlf_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "terms.md"
            source.write_text(
                "\ufeff" + table(["| 七海 | Nanami | ななみ | memo | shared | sample | reviewed |"], crlf=True),
                encoding="utf-8",
                newline="",
            )
            result = build_from_file(source, BuildOptions())
            self.assertEqual(result.canonical_tsv, "ななみ\t七海\t固有名詞\tmemo\n")

    def test_custom_pos_and_options_hash(self) -> None:
        markdown = table(["| 七海 | Nanami | ななみ | memo | shared | sample | reviewed |"])
        proper = build_from_markdown(markdown, BuildOptions(pos="固有名詞"))
        noun = build_from_markdown(markdown, BuildOptions(pos="名詞"))
        self.assertNotEqual(proper.options_hash, noun.options_hash)
        self.assertIn("\t名詞\t", noun.canonical_tsv)

    def test_empty_required_column_fails(self) -> None:
        markdown = table(["|  | Nanami | ななみ | memo | shared | sample | reviewed |"])
        with self.assertRaises(BuildError):
            build_from_markdown(markdown, BuildOptions())

    def test_cli_pos_rejects_tab(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "terms.md"
            source.write_text(table(["| 七海 | Nanami | ななみ | memo | shared | sample | reviewed |"]), encoding="utf-8")
            self.assertEqual(main(["--source", str(source), "--build-dir", tmp, "--pos", "名\t詞", "--check"]), 2)

    def test_cli_output_name_must_not_be_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "terms.md"
            source.write_text(table(["| 七海 | Nanami | ななみ | memo | shared | sample | reviewed |"]), encoding="utf-8")
            self.assertEqual(
                main(["--source", str(source), "--build-dir", tmp, "--output-name", "nested/name.tsv"]),
                2,
            )

    def test_public_text_does_not_contain_private_project_terms(self) -> None:
        forbidden = [
            "Her" + "mesian",
            "Codex" + "Memory",
            "C:" + "\\" + "Users",
            "/Us" + "ers/",
            "ir" + "oid",
            "obsidian" + "Va" + "ult",
            "Va" + "ult",
            "Compute" + " Use",
        ]
        suffixes = {".md", ".py", ".yaml", ".yml", ".tsv"}
        for path in ROOT.rglob("*"):
            if ".git" in path.parts or "__pycache__" in path.parts:
                continue
            if path.is_file() and path.suffix in suffixes:
                text = path.read_text(encoding="utf-8")
                for word in forbidden:
                    self.assertNotIn(word, text, f"{word!r} found in {path}")


if __name__ == "__main__":
    unittest.main()
