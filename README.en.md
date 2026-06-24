# google-ime-dictionary-sync

Language:
[日本語](README.ja.md) | [English](README.en.md) | [简体中文](README.zh-CN.md)

<!-- section:overview -->
## Overview

`google-ime-dictionary-sync` builds deterministic Google Japanese Input TSV files from a small Markdown term table. It also includes a preparation helper for comparing a generated TSV with the last recorded baseline, plus an optional Codex Skill for supervised UI assistance.

The CLI is the main product. Computer Use is optional assistance for the Google Japanese Input UI and must stop for explicit user confirmation before any real dictionary import or replacement.

Short pitch:
Create a Markdown dictionary sheet, turn it into a Google Japanese Input TSV, and optionally let the Codex Skill / Computer Use guide a local UI import under supervision. This is not an automatic background sync tool that changes a real dictionary on its own.

Optional Computer Use assistance:
After the CLI prepares a TSV file, the Codex Skill can help the user open Google Japanese Input settings and import the TSV through the UI. The Skill shows the planned action and requires explicit confirmation immediately before modifying the real user dictionary.

This project is not affiliated with, endorsed by, or sponsored by Google. Google Japanese Input and related names are trademarks of their respective owners.

<!-- section:features -->
## Features

- Markdown table to Google Japanese Input TSV.
- Strict default validation for status, readings, duplicate entries, and TSV-unsafe fields.
- Canonical TSV hashing with build option hashing for stable `prepare unchanged` checks.
- Export merge helper that normalizes exported katakana readings to hiragana.
- Optional repo-local Codex Skill in `.agents/skills/google-ime-dictionary-sync`.

<!-- section:requirements -->
## Requirements

- Python 3.10 or newer.
- Google Japanese Input installed by the user when importing TSVs into Google Japanese Input.
- Codex and Computer Use only if you choose the optional supervised UI workflow.

Supported environments:

| Environment | Support |
|---|---|
| Windows + Google Japanese Input | TSV generation, prepare flow, and Windows-first supervised UI guidance |
| macOS + Google Japanese Input | TSV generation and manual import docs unless explicitly tested |
| Linux + Mozc | TSV generation only; import guidance is experimental |
| Gboard Android/iOS | Unsupported |

<!-- section:installation -->
## Installation

Clone this repository and run the scripts with Python. No third-party Python dependencies are required.

```bash
python scripts/build_dictionary.py --help
python scripts/google_ime_dictionary_sync.py --help
```

Optional user-wide Codex Skill install:

```bash
mkdir -p "$HOME/.agents/skills"
cp -R ./.agents/skills/google-ime-dictionary-sync "$HOME/.agents/skills/"
```

Windows PowerShell:

```powershell
New-Item -ItemType Directory -Force "$HOME\.agents\skills"
Copy-Item -Recurse ".\.agents\skills\google-ime-dictionary-sync" "$HOME\.agents\skills\"
```

<!-- section:configuration -->
## Configuration

The build script has no required config file. The sync helper can write an optional local config:

```bash
python scripts/google_ime_dictionary_sync.py init-config \
  --backup-root ./tmp/google-ime-runs \
  --json
```

Backups and run directories should be user-chosen. Do not commit generated run directories, IME exports, local logs, or private dictionary files.

<!-- section:usage -->
## Usage

Create a dictionary sheet:

```bash
python scripts/build_dictionary.py --init-sheet my-terms.md
```

Build the sample TSV:

```bash
python scripts/build_dictionary.py \
  --source examples/term-candidates.md \
  --build-dir build \
  --check
```

Write a TSV:

```bash
python scripts/build_dictionary.py \
  --source examples/term-candidates.md \
  --build-dir build
```

Prepare a sync run:

```bash
python scripts/google_ime_dictionary_sync.py prepare \
  --source-md examples/term-candidates.md \
  --backup-root ./tmp/google-ime-runs \
  --json
```

If `prepare` returns `unchanged`, do not open Google Japanese Input and do not start Computer Use. The canonical TSV and build options match the recorded baseline.

Typical flow:

1. Write a Markdown term table.
2. Generate a Google Japanese Input TSV with the CLI.
3. Review the diff, backup path, and execution plan with the CLI.
4. If needed, use the Codex Skill / Computer Use to assist Google Japanese Input UI operation.
5. Confirm immediately before import.
6. Import into the dictionary only if the plan is correct.

### Dictionary Sheet And Skill

The dictionary sheet is a Markdown table that stores terms you want to register in Google Japanese Input. Start with `--init-sheet`, then review `正式表記`, `読み`, `memo`, and `status` as human-controlled data.

To ask Codex to help maintain the sheet, start from the repository root and use:

```text
Use $google-ime-dictionary-sync to help me add these terms to my dictionary sheet. Keep alias as metadata, validate 読み as hiragana, run --check, and do not open Google Japanese Input.
```

The Skill can help review the sheet, build the TSV, and inspect the `prepare` plan. It should proceed to the real Google Japanese Input import only when the user explicitly asks and confirms immediately before mutation.

### Try With Codex / Computer Use

After cloning this repository, start Codex from the repository root. Codex can discover the repo-local Skill at `.agents/skills/google-ime-dictionary-sync`.

First try a no-mutation check:

```text
Use $google-ime-dictionary-sync to check examples/term-candidates.md and prepare a sync run. Do not open Google Japanese Input and do not modify any real dictionary.
```

To try supervised UI assistance on Windows, first confirm that `prepare` returned `changed` or `no_previous_baseline`, then review the candidate TSV path, SHA256, and backup export path. Then ask:

```text
Use $google-ime-dictionary-sync to assist the Google Japanese Input import UI on Windows. Show the candidate TSV path, SHA256, target dictionary, backup export path, and planned action before import. Stop for my confirmation immediately before changing the real dictionary.
```

If `prepare` returns `unchanged`, do not open Google Japanese Input and do not use Computer Use.

Recommended prompt for this system's supervised import workflow:

```text
Use $google-ime-dictionary-sync to prepare and, only if needed, assist a supervised Google Japanese Input import on Windows. Use only the candidate TSV generated by the CLI. Show the candidate TSV path, SHA256, target dictionary, backup export path, and planned UI action. Do not upload files anywhere. Stop for my explicit confirmation immediately before changing the real dictionary.
```

See [CLI reference](docs/cli-reference.md), [input format](docs/input-format.en.md), and [privacy and safety](docs/privacy-and-safety.md).

<!-- section:troubleshooting -->
## Troubleshooting

- Invalid reading: use hiragana only by default. Add `--allow-long-vowel-mark` if you intentionally use `ー`.
- Duplicate entry: strict mode rejects duplicate `読み + 正式表記`; use `--lenient` only when you want first-entry-wins warnings.
- Import does not replace rows: Google Japanese Input selected-dictionary import can preserve existing rows. Use a dedicated dictionary and keep an export backup before any replacement workflow.

<!-- section:not-included -->
## What Is Not Included

- No real dictionaries, IME exports, backup evidence, screenshots, or logs.
- No automatic Google account, cloud, browser, or mobile keyboard integration.
- No Gboard Android/iOS support.
- No guarantee that macOS UI automation works; macOS import is documented as manual unless tested.

<!-- section:security-privacy -->
## Security / Privacy Notice

Do not put private URLs, local paths, account names, ticket IDs, customer names, or confidential source names in `出典` if you plan to share the file.

Do not paste private dictionary files, IME exports, screenshots, local paths, API keys, account data, customer names, or personal names into public issues.

Computer Use can operate UI. Keep it scoped to Google Japanese Input, stop on unexpected screen content, and require explicit confirmation immediately before changing a real dictionary.

<!-- section:license -->
## License

MIT. See [LICENSE](LICENSE).

<!-- section:attribution -->
## Attribution

Google Japanese Input and related names belong to their respective owners. This project is independent and unofficial.

<!-- section:disclaimer -->
## Disclaimer

This tool is provided as-is, without warranty. Review generated TSVs and keep backups before importing into any real dictionary.
