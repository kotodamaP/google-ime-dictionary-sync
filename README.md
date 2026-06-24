# google-ime-dictionary-sync

Language:
[日本語](README.ja.md) | [English](README.en.md) | [简体中文](README.zh-CN.md)

Deterministic Python CLI for creating a small Markdown dictionary sheet, turning it into a Google Japanese Input TSV, and preparing a safe import plan.

The optional repo-local Codex Skill can help review the dictionary sheet and guide a supervised Google Japanese Input UI import with Computer Use. The CLI is the core product; real dictionary changes require explicit user confirmation immediately before import.

Quick start:

```bash
python scripts/build_dictionary.py --init-sheet my-terms.md
python scripts/build_dictionary.py --source my-terms.md --build-dir build --check
python scripts/google_ime_dictionary_sync.py prepare --source-md my-terms.md --backup-root ./tmp/google-ime-runs --json
```

Choose a full README:

- [日本語](README.ja.md)
- [English](README.en.md)
- [简体中文](README.zh-CN.md)
