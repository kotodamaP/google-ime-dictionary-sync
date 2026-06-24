# CLI Reference

## Build

Create a starter Markdown dictionary sheet:

```bash
python scripts/build_dictionary.py --init-sheet my-terms.md
```

Then validate or build it:

```bash
python scripts/build_dictionary.py --source my-terms.md --build-dir build
```

Important options:

- `--init-sheet <path>`: write a starter Markdown dictionary sheet and exit.
- `--force`: overwrite an existing `--init-sheet` target.
- `--check`: validate and render in memory without writing.
- `--pos 固有名詞`: set the Google Japanese Input part-of-speech label.
- `--emit-aliases`: experimental, emit the whole alias cell as one extra surface form.
- `--allow-long-vowel-mark`: allow `ー` in source readings.
- `--lenient`: warn and skip invalid rows where possible.
- `--json`: print a JSON summary.

## Prepare

```bash
python scripts/google_ime_dictionary_sync.py prepare \
  --source-md examples/term-candidates.md \
  --backup-root ./tmp/google-ime-runs \
  --json
```

`prepare` writes a run directory containing a candidate TSV, copied source Markdown, `sync-run.json`, and `approval-request.md`.

Status values:

- `no_previous_baseline`: no recorded canonical TSV baseline exists.
- `changed`: canonical TSV SHA256 or build option hash differs from baseline.
- `unchanged`: candidate identity matches baseline; no UI sync is needed.

## Record Success

Run only after a user-approved import or replacement has completed.

```bash
python scripts/google_ime_dictionary_sync.py record-success --run-dir <run-dir> --json
```

## Merge Export

```bash
python scripts/google_ime_dictionary_sync.py merge-export \
  --generated-tsv build/google-ime-dictionary.tsv \
  --ime-export exported.tsv \
  --backup-root ./tmp/google-ime-runs \
  --json
```

Export merge normalizes exported katakana readings to hiragana, drops blank reading/surface rows, and prefers generated rows by default.
