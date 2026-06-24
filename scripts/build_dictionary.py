#!/usr/bin/env python3
"""Build Google Japanese Input TSV files from a Markdown term table."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import sys
import unicodedata


EXPECTED_COLUMNS = ["正式表記", "alias", "読み", "memo", "scope候補", "出典", "status"]
INCLUDED_STATUSES = {"candidate", "reviewed"}
DISABLED_STATUSES = {"draft", "rejected", "hold", "private", "archived"}
NORMALIZATION_VERSION = "1"
DEFAULT_POS = "固有名詞"
DEFAULT_OUTPUT_NAME = "google-ime-dictionary.tsv"


class BuildError(Exception):
    """Raised when the input table cannot be rendered safely."""


@dataclass(frozen=True)
class BuildOptions:
    pos: str = DEFAULT_POS
    emit_aliases: bool = False
    allow_long_vowel_mark: bool = False
    strict: bool = True
    normalization_version: str = NORMALIZATION_VERSION

    def as_identity_dict(self) -> dict[str, object]:
        return {
            "pos": self.pos,
            "emit_aliases": self.emit_aliases,
            "allow_long_vowel_mark": self.allow_long_vowel_mark,
            "strict": self.strict,
            "normalizationVersion": self.normalization_version,
        }

    def identity_hash(self) -> str:
        payload = json.dumps(self.as_identity_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class SourceTerm:
    term: str
    alias: str
    reading: str
    memo: str
    scope: str
    source: str
    status: str
    line_number: int


@dataclass(frozen=True)
class ImeEntry:
    reading: str
    surface: str
    pos: str
    memo: str
    line_number: int
    source_kind: str


@dataclass(frozen=True)
class BuildResult:
    entries: list[ImeEntry]
    canonical_tsv: str
    canonical_sha256: str
    options_hash: str
    warnings: list[str]


def normalize_field(value: str) -> str:
    value = value.replace("\u3000", " ")
    return unicodedata.normalize("NFC", value).strip()


def reject_unsafe_field(value: str, *, label: str, line_number: int) -> None:
    if "\t" in value or "\r" in value or "\n" in value:
        raise BuildError(f"line {line_number}: {label} must not contain tabs or newlines")


def split_markdown_row(line: str) -> list[str]:
    stripped = line.lstrip("\ufeff").strip()
    if not stripped.startswith("|"):
        return []
    body = stripped[1:]
    if body.endswith("|"):
        body = body[:-1]

    cells: list[str] = []
    current: list[str] = []
    escaped = False
    for char in body:
        if escaped:
            current.append(char)
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == "|":
            cells.append("".join(current).strip())
            current = []
            continue
        current.append(char)
    if escaped:
        current.append("\\")
    cells.append("".join(current).strip())
    return cells


def is_separator_row(cells: list[str]) -> bool:
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in cells)


def find_table(lines: list[str]) -> tuple[int, dict[str, int]]:
    expected = set(EXPECTED_COLUMNS)
    for index, line in enumerate(lines):
        cells = [normalize_field(cell) for cell in split_markdown_row(line)]
        if set(cells) == expected and len(cells) == len(EXPECTED_COLUMNS):
            return index, {name: cells.index(name) for name in EXPECTED_COLUMNS}
    raise BuildError("required Markdown table header was not found")


def parse_markdown_table(markdown: str) -> list[SourceTerm]:
    lines = markdown.splitlines()
    header_index, column_index = find_table(lines)
    separator_index = header_index + 1
    if separator_index >= len(lines) or not is_separator_row(split_markdown_row(lines[separator_index])):
        raise BuildError(f"line {header_index + 2}: Markdown table separator row is missing or invalid")

    terms: list[SourceTerm] = []
    for index in range(separator_index + 1, len(lines)):
        line = lines[index]
        if not line.strip():
            break
        if line.lstrip().startswith("<!--"):
            continue
        if not line.lstrip().startswith("|"):
            break
        cells = split_markdown_row(line)
        if is_separator_row(cells):
            continue
        if len(cells) != len(EXPECTED_COLUMNS):
            raise BuildError(f"line {index + 1}: expected {len(EXPECTED_COLUMNS)} columns, got {len(cells)}")

        normalized = [normalize_field(cell) for cell in cells]
        for column_name, raw_value in zip(EXPECTED_COLUMNS, normalized):
            reject_unsafe_field(raw_value, label=column_name, line_number=index + 1)

        terms.append(
            SourceTerm(
                term=normalized[column_index["正式表記"]],
                alias=normalized[column_index["alias"]],
                reading=normalized[column_index["読み"]],
                memo=normalized[column_index["memo"]],
                scope=normalized[column_index["scope候補"]].lower(),
                source=normalized[column_index["出典"]],
                status=normalized[column_index["status"]].lower(),
                line_number=index + 1,
            )
        )
    return terms


def validate_reading(reading: str, *, allow_long_vowel_mark: bool) -> bool:
    if not reading:
        return False
    for char in reading:
        codepoint = ord(char)
        if 0x3041 <= codepoint <= 0x3096:
            continue
        if allow_long_vowel_mark and char == "ー":
            continue
        return False
    return True


def add_or_warn(errors: list[str], warnings: list[str], message: str, *, strict: bool) -> None:
    if strict:
        errors.append(message)
    else:
        warnings.append(message)


def build_entries(terms: list[SourceTerm], options: BuildOptions) -> tuple[list[ImeEntry], list[str]]:
    entries: list[ImeEntry] = []
    warnings: list[str] = []
    errors: list[str] = []

    for term in terms:
        if not term.term:
            add_or_warn(errors, warnings, f"line {term.line_number}: 正式表記 is required", strict=options.strict)
            continue
        if not term.reading:
            add_or_warn(errors, warnings, f"line {term.line_number}: 読み is required", strict=options.strict)
            continue
        if not term.status:
            add_or_warn(errors, warnings, f"line {term.line_number}: status is required", strict=options.strict)
            continue
        if term.status not in INCLUDED_STATUSES and term.status not in DISABLED_STATUSES:
            add_or_warn(errors, warnings, f"line {term.line_number}: unknown status: {term.status}", strict=options.strict)
            continue
        if term.status not in INCLUDED_STATUSES:
            continue
        if not validate_reading(term.reading, allow_long_vowel_mark=options.allow_long_vowel_mark):
            add_or_warn(errors, warnings, f"line {term.line_number}: invalid 読み: {term.reading}", strict=options.strict)
            continue

        entries.append(ImeEntry(term.reading, term.term, options.pos, term.memo, term.line_number, "term"))
        if options.emit_aliases and term.alias:
            entries.append(ImeEntry(term.reading, term.alias, options.pos, term.memo, term.line_number, "alias"))

    deduped: list[ImeEntry] = []
    seen: dict[tuple[str, str], ImeEntry] = {}
    for entry in entries:
        key = (entry.reading, entry.surface)
        if key in seen:
            first = seen[key]
            message = (
                f"line {entry.line_number}: duplicate 読み + surface '{entry.reading} + {entry.surface}' "
                f"(first seen at line {first.line_number})"
            )
            add_or_warn(errors, warnings, message, strict=options.strict)
            continue
        seen[key] = entry
        deduped.append(entry)

    if errors:
        raise BuildError("\n".join(errors))

    deduped.sort(key=lambda item: (item.reading, item.surface, item.pos, item.memo))
    return deduped, warnings


def render_tsv(entries: list[ImeEntry]) -> str:
    lines = [
        "\t".join([entry.reading, entry.surface, entry.pos, entry.memo])
        for entry in entries
    ]
    return "\n".join(lines) + ("\n" if lines else "")


def build_from_markdown(markdown: str, options: BuildOptions) -> BuildResult:
    terms = parse_markdown_table(markdown)
    entries, warnings = build_entries(terms, options)
    canonical_tsv = render_tsv(entries)
    canonical_sha256 = hashlib.sha256(canonical_tsv.encode("utf-8")).hexdigest()
    return BuildResult(
        entries=entries,
        canonical_tsv=canonical_tsv,
        canonical_sha256=canonical_sha256,
        options_hash=options.identity_hash(),
        warnings=warnings,
    )


def build_from_file(source: Path, options: BuildOptions) -> BuildResult:
    markdown = source.read_text(encoding="utf-8-sig")
    return build_from_markdown(markdown, options)


def write_outputs(result: BuildResult, build_dir: Path, output_name: str) -> Path:
    build_dir.mkdir(parents=True, exist_ok=True)
    output_path = build_dir / output_name
    output_path.write_text(result.canonical_tsv, encoding="utf-8", newline="\n")
    return output_path


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a Google Japanese Input TSV from a Markdown term table.")
    parser.add_argument("--source", type=Path, required=True, help="Markdown term table path")
    parser.add_argument("--build-dir", type=Path, default=Path("build"), help="directory for generated output")
    parser.add_argument("--output-name", default=DEFAULT_OUTPUT_NAME, help="generated TSV file name")
    parser.add_argument("--pos", default=DEFAULT_POS, help="Google Japanese Input part-of-speech label")
    parser.add_argument("--emit-aliases", action="store_true", help="experimental: emit alias cells as extra entries")
    parser.add_argument("--allow-long-vowel-mark", action="store_true", help="allow ー in source readings")
    parser.add_argument("--lenient", action="store_true", help="warn and skip invalid rows where possible")
    parser.add_argument("--check", action="store_true", help="validate and render in memory without writing files")
    parser.add_argument("--json", action="store_true", help="print JSON summary")
    return parser.parse_args(argv)


def payload_for(result: BuildResult, *, source: Path, output_path: Path | None, options: BuildOptions) -> dict[str, object]:
    return {
        "source": str(source),
        "outputPath": str(output_path) if output_path else None,
        "entryCount": len(result.entries),
        "canonicalSha256": result.canonical_sha256,
        "buildOptionsHash": result.options_hash,
        "buildOptions": options.as_identity_dict(),
        "warnings": result.warnings,
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    options = BuildOptions(
        pos=normalize_field(args.pos),
        emit_aliases=args.emit_aliases,
        allow_long_vowel_mark=args.allow_long_vowel_mark,
        strict=not args.lenient,
    )
    try:
        result = build_from_file(args.source, options)
        output_path = None if args.check else write_outputs(result, args.build_dir, args.output_name)
        payload = payload_for(result, source=args.source, output_path=output_path, options=options)
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            for warning in result.warnings:
                print(f"[warn] {warning}", file=sys.stderr)
            action = "checked" if args.check else "generated"
            location = "" if output_path is None else f" -> {output_path}"
            print(f"[ok] {action} {len(result.entries)} entries{location}")
            print(f"[ok] canonical SHA256: {result.canonical_sha256}")
        return 0
    except BuildError as error:
        print(f"[error] {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
