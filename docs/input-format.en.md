# Input Format

The source file is a Markdown table with exactly these columns. Columns may be reordered, but all columns must be present.

| Column | Meaning |
|---|---|
| `正式表記` | Surface form to emit to Google Japanese Input. Required. |
| `alias` | Single metadata string in v1. Not emitted by default. |
| `読み` | Hiragana reading. Required. |
| `memo` | TSV comment. |
| `scope候補` | Metadata for review workflows. |
| `出典` | Metadata only. Do not put private URLs, local paths, account names, ticket IDs, customer names, or confidential source names here when sharing. |
| `status` | `candidate` or `reviewed` entries are included. |

Strict mode is the default. It rejects unknown statuses, empty required columns, invalid readings, duplicate `読み + 正式表記`, and fields containing tabs or newlines.

Disabled statuses are ignored: `draft`, `rejected`, `hold`, `private`, `archived`.

`alias` is not emitted by default. `--emit-aliases` is experimental and treats the whole alias cell as one additional surface form.

`読み` accepts hiragana, small kana, and `ゔ`. Use `--allow-long-vowel-mark` to allow `ー`. Source readings reject kanji, katakana, Latin letters, spaces, tabs, and newlines.

Output is canonicalized by NFC normalization, trimming surrounding whitespace, and stable sorting by `読み`, then `正式表記`.
