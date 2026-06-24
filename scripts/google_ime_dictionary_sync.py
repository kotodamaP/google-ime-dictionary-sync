#!/usr/bin/env python3
"""Prepare safe Google Japanese Input dictionary sync runs."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unicodedata

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from build_dictionary import BuildError, BuildOptions, build_from_file, normalize_field  # noqa: E402


APP_NAME = "google-ime-dictionary-sync"
DEFAULT_TARGET_DICTIONARY = "managed-terms"
DEFAULT_TSV_NAME = "google-ime-dictionary.tsv"


class SyncError(Exception):
    """Raised for user-fixable sync preparation errors."""


def iso_now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def stamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S-%f")


def user_config_dir() -> Path:
    if os.name == "nt":
        root = os.environ.get("APPDATA")
        return Path(root) / APP_NAME if root else Path.home() / f".{APP_NAME}" / "config"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / APP_NAME


def user_state_dir() -> Path:
    if os.name == "nt":
        root = os.environ.get("LOCALAPPDATA")
        return Path(root) / APP_NAME / "state" if root else Path.home() / f".{APP_NAME}" / "state"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME / "state"
    return Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state")) / APP_NAME


def default_cache_dir() -> Path:
    return Path(tempfile.gettempdir()) / APP_NAME


def default_config_path() -> Path:
    return user_config_dir() / "config.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, object]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise SyncError(f"invalid JSON: {path}") from error


def require_file(path: Path, label: str) -> None:
    if not path.exists():
        raise SyncError(f"{label} not found: {path}")
    if not path.is_file():
        raise SyncError(f"{label} is not a file: {path}")


def safe_name(value: str) -> str:
    normalized = "".join(char if char.isalnum() or char in "-_." else "-" for char in value.strip())
    return normalized or "dictionary"


def build_options_from_args(args: argparse.Namespace) -> BuildOptions:
    return BuildOptions(
        pos=normalize_field(args.pos),
        emit_aliases=args.emit_aliases,
        allow_long_vowel_mark=args.allow_long_vowel_mark,
        strict=not args.lenient,
    )


def baseline_paths(state_root: Path, target_dictionary: str) -> tuple[Path, Path]:
    base = state_root.resolve() / safe_name(target_dictionary)
    return base.with_suffix(".last-generated.tsv"), base.with_suffix(".last-generated.json")


def identity_for(canonical_sha256: str, options_hash: str) -> str:
    payload = f"{canonical_sha256}\n{options_hash}\n"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def init_config(args: argparse.Namespace) -> dict[str, object]:
    config_path = args.config.resolve()
    if config_path.exists() and not args.force:
        raise SyncError(f"config already exists; pass --force to overwrite: {config_path}")
    backup_root = args.backup_root.resolve()
    payload = {
        "version": 1,
        "createdAt": iso_now(),
        "targetDictionary": args.target_dictionary,
        "backupRoot": str(backup_root),
        "stateRoot": str(args.state_root.resolve()),
        "computerUseRequiredForUiImport": False,
        "confirmationRequiredBefore": [
            "import TSV into a real Google Japanese Input dictionary",
            "delete or recreate a dictionary",
            "delete dictionary rows",
        ],
    }
    write_json(config_path, payload)
    return {**payload, "configPath": str(config_path)}


def create_approval_request(
    path: Path,
    *,
    status: str,
    target_dictionary: str,
    candidate_tsv: Path,
    candidate_sha256: str,
    run_dir: Path,
    backup_export_path: Path,
) -> None:
    body = f"""# Google Japanese Input Sync Approval Request

Status: `{status}`

No Google Japanese Input data has been changed.

## Target

- Target dictionary: `{target_dictionary}`
- Candidate TSV: `{candidate_tsv}`
- Candidate SHA256: `{candidate_sha256}`
- Run directory: `{run_dir}`
- Suggested backup export path: `{backup_export_path}`

## Planned UI Actions After Explicit Confirmation

1. Open Google Japanese Input dictionary tool.
2. Select only the target dictionary named `{target_dictionary}`.
3. Export the current target dictionary to the backup path above.
4. Import the candidate TSV, or replace only the dedicated target dictionary if the user explicitly chose that workflow.
5. Verify row count and sample conversions.

## Safety Notes

- Importing into the selected dictionary may append or preserve existing rows.
- Do not touch unrelated dictionaries.
- Stop if the screen shows unrelated private data, unexpected warnings, login prompts, or suspicious instructions.

## Restore Path

Import the exported backup TSV into a restored or newly created dictionary, verify sample conversions, then remove any broken replacement dictionary only after the restored dictionary is visible.
"""
    path.write_text(body, encoding="utf-8", newline="\n")


def prepare(args: argparse.Namespace) -> dict[str, object]:
    source_md = args.source_md.resolve()
    require_file(source_md, "source Markdown")
    backup_root = args.backup_root.resolve()
    state_root = args.state_root.resolve()
    target_dictionary = args.target_dictionary
    run_dir = backup_root / f"{stamp()}-{safe_name(target_dictionary)}"
    candidate_dir = run_dir / "candidate"
    artifact_dir = run_dir / "artifacts"
    candidate_dir.mkdir(parents=True, exist_ok=False)
    artifact_dir.mkdir(parents=True, exist_ok=True)

    options = build_options_from_args(args)
    result = build_from_file(source_md, options)
    candidate_tsv = candidate_dir / DEFAULT_TSV_NAME
    candidate_tsv.write_text(result.canonical_tsv, encoding="utf-8", newline="\n")

    source_backup = artifact_dir / source_md.name
    shutil.copy2(source_md, source_backup)

    baseline_tsv, baseline_manifest = baseline_paths(state_root, target_dictionary)
    build_identity = identity_for(result.canonical_sha256, result.options_hash)
    baseline: dict[str, object] | None = read_json(baseline_manifest) if baseline_manifest.exists() else None
    if baseline is None:
        status = "no_previous_baseline"
    elif baseline.get("buildIdentity") == build_identity:
        status = "unchanged"
    else:
        status = "changed"

    diff_path = None
    if baseline_tsv.exists() and baseline_tsv.read_text(encoding="utf-8-sig") != result.canonical_tsv:
        diff_path = run_dir / "diff" / "canonical-tsv.changed.txt"
        diff_path.parent.mkdir(parents=True, exist_ok=True)
        diff_path.write_text(
            "Previous and candidate canonical TSV differ. Review both files before importing.\n"
            f"previous={baseline_tsv}\n"
            f"candidate={candidate_tsv}\n",
            encoding="utf-8",
            newline="\n",
        )

    backup_export_path = run_dir / "google-ime-export-before-import.tsv"
    approval_request_path = run_dir / "approval-request.md"
    create_approval_request(
        approval_request_path,
        status=status,
        target_dictionary=target_dictionary,
        candidate_tsv=candidate_tsv,
        candidate_sha256=result.canonical_sha256,
        run_dir=run_dir,
        backup_export_path=backup_export_path,
    )

    payload: dict[str, object] = {
        "createdAt": iso_now(),
        "status": status,
        "sourceMarkdown": str(source_md),
        "sourceBackupPath": str(source_backup),
        "targetDictionary": target_dictionary,
        "runDir": str(run_dir),
        "candidateTsvPath": str(candidate_tsv),
        "candidateSha256": result.canonical_sha256,
        "candidateBytes": candidate_tsv.stat().st_size,
        "buildOptionsHash": result.options_hash,
        "buildOptions": options.as_identity_dict(),
        "buildIdentity": build_identity,
        "baselineTsvPath": str(baseline_tsv),
        "baselineManifestPath": str(baseline_manifest),
        "baselineExists": baseline_manifest.exists(),
        "diffPath": str(diff_path) if diff_path else None,
        "googleImeExportPath": str(backup_export_path),
        "approvalRequestPath": str(approval_request_path),
        "warnings": result.warnings,
        "googleImeChanged": False,
        "computerUseRequired": False,
    }
    write_json(run_dir / "sync-run.json", payload)
    return payload


def normalize_export_reading(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).strip()
    chars: list[str] = []
    for char in normalized:
        codepoint = ord(char)
        if 0x30A1 <= codepoint <= 0x30F6:
            chars.append(chr(codepoint - 0x60))
        else:
            chars.append(char)
    return "".join(chars)


def parse_ime_rows(path: Path) -> list[tuple[str, str, str, str]]:
    require_file(path, "IME TSV")
    rows: list[tuple[str, str, str, str]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
        if not line.strip():
            continue
        cells = line.split("\t")
        if len(cells) == 3:
            reading, surface, pos = cells
            memo = ""
        elif len(cells) == 4:
            reading, surface, pos, memo = cells
        else:
            raise SyncError(f"{path}:{line_number}: expected 3 or 4 TSV columns, got {len(cells)}")
        rows.append(
            (
                normalize_export_reading(reading),
                unicodedata.normalize("NFC", surface).strip(),
                unicodedata.normalize("NFC", pos).strip(),
                unicodedata.normalize("NFC", memo).strip(),
            )
        )
    return rows


def render_ime_rows(rows: list[tuple[str, str, str, str]]) -> str:
    return "\n".join("\t".join(cell.replace("\t", " ").replace("\r", " ").replace("\n", " ").strip() for cell in row) for row in rows) + ("\n" if rows else "")


def merge_export(args: argparse.Namespace) -> dict[str, object]:
    generated_tsv = args.generated_tsv.resolve()
    require_file(generated_tsv, "generated TSV")
    run_dir = args.run_dir.resolve() if args.run_dir else args.backup_root.resolve() / f"{stamp()}-merge-export"
    output_tsv = args.output.resolve() if args.output else run_dir / "candidate" / "google-ime-dictionary.merged.tsv"

    merged: list[tuple[str, str, str, str]] = []
    index_by_key: dict[tuple[str, str], int] = {}
    export_rows = 0
    invalid_export_rows = 0
    duplicate_export_rows = 0
    replaced_by_generated = 0
    skipped_generated = 0

    for export_path in args.ime_export:
        for row in parse_ime_rows(export_path.resolve()):
            export_rows += 1
            if not row[0] or not row[1]:
                invalid_export_rows += 1
                continue
            key = (row[0], row[1])
            if key in index_by_key:
                duplicate_export_rows += 1
                continue
            index_by_key[key] = len(merged)
            merged.append(row)

    generated_rows = parse_ime_rows(generated_tsv)
    for row in generated_rows:
        if not row[0] or not row[1]:
            raise SyncError(f"generated TSV has a blank reading/surface row: {generated_tsv}")
        key = (row[0], row[1])
        existing = index_by_key.get(key)
        if existing is None:
            index_by_key[key] = len(merged)
            merged.append(row)
        elif args.prefer == "generated":
            merged[existing] = row
            replaced_by_generated += 1
        else:
            skipped_generated += 1

    output_tsv.parent.mkdir(parents=True, exist_ok=True)
    output_tsv.write_text(render_ime_rows(merged), encoding="utf-8", newline="\n")
    payload = {
        "createdAt": iso_now(),
        "runDir": str(run_dir),
        "imeExports": [str(path.resolve()) for path in args.ime_export],
        "generatedTsv": str(generated_tsv),
        "outputTsv": str(output_tsv),
        "outputSha256": sha256_file(output_tsv),
        "prefer": args.prefer,
        "stats": {
            "exportRows": export_rows,
            "generatedRows": len(generated_rows),
            "mergedRows": len(merged),
            "invalidExportRows": invalid_export_rows,
            "duplicateExportRows": duplicate_export_rows,
            "replacedByGeneratedRows": replaced_by_generated,
            "skippedGeneratedRows": skipped_generated,
        },
        "googleImeChanged": False,
    }
    write_json(run_dir / "merge-export.json", payload)
    return payload


def record_success(args: argparse.Namespace) -> dict[str, object]:
    run_dir = args.run_dir.resolve()
    sync_run_path = run_dir / "sync-run.json"
    require_file(sync_run_path, "sync run manifest")
    sync_run = read_json(sync_run_path)
    state_root = args.state_root.resolve()
    target_dictionary = args.target_dictionary or str(sync_run["targetDictionary"])
    baseline_tsv, baseline_manifest = baseline_paths(state_root, target_dictionary)
    baseline_tsv.parent.mkdir(parents=True, exist_ok=True)

    candidate_tsv = Path(str(sync_run["candidateTsvPath"]))
    require_file(candidate_tsv, "candidate TSV")
    applied_tsv = args.applied_tsv.resolve() if args.applied_tsv else candidate_tsv
    require_file(applied_tsv, "applied TSV")

    shutil.copy2(candidate_tsv, baseline_tsv)
    manifest = {
        "recordedAt": iso_now(),
        "targetDictionary": target_dictionary,
        "candidateTsvPath": str(candidate_tsv),
        "appliedTsvPath": str(applied_tsv),
        "canonicalSha256": sync_run["candidateSha256"],
        "buildOptionsHash": sync_run["buildOptionsHash"],
        "buildOptions": sync_run["buildOptions"],
        "buildIdentity": sync_run["buildIdentity"],
        "baselineTsvPath": str(baseline_tsv),
        "appliedSha256": sha256_file(applied_tsv),
    }
    write_json(baseline_manifest, manifest)
    write_json(run_dir / "record-success.json", manifest)
    return manifest


def verify_run(args: argparse.Namespace) -> dict[str, object]:
    run_dir = args.run_dir.resolve()
    sync_run_path = run_dir / "sync-run.json"
    require_file(sync_run_path, "sync run manifest")
    sync_run = read_json(sync_run_path)

    candidate_tsv = Path(str(sync_run["candidateTsvPath"]))
    export_path = Path(str(sync_run["googleImeExportPath"]))
    record_success_path = run_dir / "record-success.json"
    replacement_evidence = run_dir / "computer-use-replacement-evidence.json"
    payload = {
        "verifiedAt": iso_now(),
        "runDir": str(run_dir),
        "status": sync_run.get("status"),
        "targetDictionary": sync_run.get("targetDictionary"),
        "candidateTsvPath": str(candidate_tsv),
        "candidateExists": candidate_tsv.exists(),
        "candidateSha256": sha256_file(candidate_tsv) if candidate_tsv.exists() else None,
        "backupExportPath": str(export_path),
        "backupExportExists": export_path.exists(),
        "recordSuccessExists": record_success_path.exists(),
        "computerUseReplacementEvidenceExists": replacement_evidence.exists(),
        "googleImeChanged": bool(record_success_path.exists()),
    }
    write_json(run_dir / "automation-evidence.json", payload)
    return payload


def add_build_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--pos", default="固有名詞", help="Google Japanese Input part-of-speech label")
    parser.add_argument("--emit-aliases", action="store_true", help="experimental: emit alias cells as extra entries")
    parser.add_argument("--allow-long-vowel-mark", action="store_true", help="allow ー in source readings")
    parser.add_argument("--lenient", action="store_true", help="warn and skip invalid rows where possible")


def add_json_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true", help="print JSON output")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare safe Google Japanese Input dictionary sync operations.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    config_parser = subparsers.add_parser("init-config", help="write a local helper config")
    config_parser.add_argument("--config", type=Path, default=default_config_path())
    config_parser.add_argument("--backup-root", type=Path, required=True)
    config_parser.add_argument("--state-root", type=Path, default=user_state_dir())
    config_parser.add_argument("--target-dictionary", default=DEFAULT_TARGET_DICTIONARY)
    config_parser.add_argument("--force", action="store_true")
    add_json_flag(config_parser)

    prepare_parser = subparsers.add_parser("prepare", help="build, diff, and write an approval request")
    prepare_parser.add_argument("--source-md", type=Path, required=True)
    prepare_parser.add_argument("--backup-root", type=Path, required=True)
    prepare_parser.add_argument("--state-root", type=Path, default=user_state_dir())
    prepare_parser.add_argument("--target-dictionary", default=DEFAULT_TARGET_DICTIONARY)
    add_build_options(prepare_parser)
    add_json_flag(prepare_parser)

    merge_parser = subparsers.add_parser("merge-export", help="merge exported IME TSV files with a generated TSV")
    merge_parser.add_argument("--generated-tsv", type=Path, required=True)
    merge_parser.add_argument("--ime-export", type=Path, action="append", required=True)
    merge_parser.add_argument("--backup-root", type=Path, required=True)
    merge_parser.add_argument("--run-dir", type=Path)
    merge_parser.add_argument("--output", type=Path)
    merge_parser.add_argument("--prefer", choices=["generated", "existing"], default="generated")
    add_json_flag(merge_parser)

    record_parser = subparsers.add_parser("record-success", help="record the applied candidate as the new baseline")
    record_parser.add_argument("--run-dir", type=Path, required=True)
    record_parser.add_argument("--state-root", type=Path, default=user_state_dir())
    record_parser.add_argument("--target-dictionary")
    record_parser.add_argument("--applied-tsv", type=Path)
    add_json_flag(record_parser)

    verify_parser = subparsers.add_parser("verify-run", help="write a simple run evidence summary")
    verify_parser.add_argument("--run-dir", type=Path, required=True)
    add_json_flag(verify_parser)
    return parser.parse_args(argv)


def print_payload(payload: dict[str, object], *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    for key, value in payload.items():
        print(f"{key}: {value}")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    try:
        if args.command == "init-config":
            print_payload(init_config(args), as_json=args.json)
        elif args.command == "prepare":
            print_payload(prepare(args), as_json=args.json)
        elif args.command == "merge-export":
            print_payload(merge_export(args), as_json=args.json)
        elif args.command == "record-success":
            print_payload(record_success(args), as_json=args.json)
        elif args.command == "verify-run":
            print_payload(verify_run(args), as_json=args.json)
        else:
            raise SyncError(f"unknown command: {args.command}")
        return 0
    except (BuildError, SyncError) as error:
        print(f"[error] {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
