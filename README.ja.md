# google-ime-dictionary-sync

Language:
[日本語](README.ja.md) | [English](README.en.md) | [简体中文](README.zh-CN.md)

<!-- section:overview -->
## 概要

`google-ime-dictionary-sync` は、小さな Markdown 用語表から Google 日本語入力向け TSV を決定的に生成する CLI です。生成 TSV と前回 baseline を比較する `prepare` 補助、任意の Codex Skill による監督付き UI 補助も含みます。

本体は CLI です。Computer Use は Google 日本語入力 UI を扱う任意補助であり、実際の辞書 import や置換の直前に必ずユーザー確認で止めます。

任意の Computer Use 補助:
CLI で TSV を生成・検証したあと、Codex Skill が Google 日本語入力の設定画面を開き、ユーザー辞書へ TSV を取り込む操作を補助します。実際に辞書を変更する直前には、実行内容を表示し、ユーザーの明示確認を必須にします。

このプロジェクトは Google 公式ではなく、Google による承認・提供・支援を受けたものではありません。Google 日本語入力および関連名称は各権利者に帰属します。

<!-- section:features -->
## 機能

- Markdown 表から Google 日本語入力 TSV を生成。
- `status`、`読み`、重複、TSV を壊す文字を strict default で検証。
- canonical TSV hash と build option hash による安定した `prepare unchanged` 判定。
- Google IME export のカタカナ読みをひらがなへ正規化する merge 補助。
- `.agents/skills/google-ime-dictionary-sync` に repo-local Codex Skill を同梱。

<!-- section:requirements -->
## 要件

- Python 3.10 以上。
- TSV を Google 日本語入力へ import する場合は、ユーザー側で Google 日本語入力を用意。
- Codex と Computer Use は、任意の監督付き UI 手順を使う場合だけ必要。

対応範囲:

| 環境 | 対応 |
|---|---|
| Windows + Google 日本語入力 | TSV 生成、prepare、Windows-first の監督付き UI ガイド |
| macOS + Google 日本語入力 | TSV 生成と手動 import 手順。明示的に検証するまでは自動補助対象外 |
| Linux + Mozc | TSV 生成のみ。import 手順は experimental |
| Gboard Android/iOS | 非対応 |

<!-- section:installation -->
## インストール

このリポジトリを clone して Python で実行します。外部 Python 依存はありません。

```bash
python scripts/build_dictionary.py --help
python scripts/google_ime_dictionary_sync.py --help
```

任意の Codex Skill ユーザー単位インストール:

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
## 設定

TSV 生成に設定ファイルは不要です。同期補助 CLI は任意のローカル config を作れます。

```bash
python scripts/google_ime_dictionary_sync.py init-config \
  --backup-root ./tmp/google-ime-runs \
  --json
```

backup と run directory はユーザーが選びます。生成 run directory、IME export、local log、private dictionary file は commit しないでください。

<!-- section:usage -->
## 使い方

サンプル TSV を検証:

```bash
python scripts/build_dictionary.py \
  --source examples/term-candidates.md \
  --build-dir build \
  --check
```

TSV を出力:

```bash
python scripts/build_dictionary.py \
  --source examples/term-candidates.md \
  --build-dir build
```

同期準備:

```bash
python scripts/google_ime_dictionary_sync.py prepare \
  --source-md examples/term-candidates.md \
  --backup-root ./tmp/google-ime-runs \
  --json
```

`prepare` が `unchanged` の場合、Google 日本語入力を開かず、Computer Use も起動しません。canonical TSV と build options が baseline と一致しています。

基本の流れ:

1. Markdown 用語表を書く
2. CLI で Google 日本語入力用 TSV を生成
3. CLI で差分・バックアップ先・実行計画を確認
4. 必要なら Codex Skill / Computer Use で Google 日本語入力 UI の操作を補助
5. import 直前にユーザーが確認
6. 問題なければ辞書へ取り込み

### Codex / Computer Use で試す

このリポジトリを clone したあと、repo root で Codex を起動すると、repo-local Skill `.agents/skills/google-ime-dictionary-sync` を利用できます。

まずは実辞書を変更しない確認だけを試してください。

```text
Use $google-ime-dictionary-sync to check examples/term-candidates.md and prepare a sync run. Do not open Google Japanese Input and do not modify any real dictionary.
```

Windows で実際の UI 補助を試す場合は、`prepare` の結果が `changed` または `no_previous_baseline` であること、candidate TSV path、SHA256、backup export path を確認してから、次のように依頼します。

```text
Use $google-ime-dictionary-sync to assist the Google Japanese Input import UI on Windows. Show the candidate TSV path, SHA256, target dictionary, backup export path, and planned action before import. Stop for my confirmation immediately before changing the real dictionary.
```

`prepare` が `unchanged` の場合は、Google 日本語入力を開かず、Computer Use も使いません。

詳しくは [CLI reference](docs/cli-reference.md)、[input format](docs/input-format.ja.md)、[privacy and safety](docs/privacy-and-safety.md) を見てください。

<!-- section:troubleshooting -->
## トラブルシュート

- 読みが不正: デフォルトではひらがなのみです。意図して `ー` を使う場合だけ `--allow-long-vowel-mark` を付けます。
- 重複: strict mode は duplicate `読み + 正式表記` を拒否します。先勝ち warning にしたい場合だけ `--lenient` を使います。
- import で置換されない: Google 日本語入力の選択辞書 import は既存行を保持する場合があります。専用辞書を使い、置換前に export backup を取ってください。

<!-- section:not-included -->
## 含まないもの

- 実辞書、IME export、backup evidence、screenshot、log は含みません。
- Google account、cloud、browser、mobile keyboard integration の自動化は含みません。
- Gboard Android/iOS は非対応です。
- macOS UI automation は保証しません。明示的に検証するまでは手動 import のみです。

<!-- section:security-privacy -->
## セキュリティ / プライバシー

共有予定のファイルでは、`出典` に private URL、local path、account name、ticket ID、customer name、confidential source name を入れないでください。

public issue には、private dictionary file、IME export、screenshot、local path、API key、account data、customer name、personal name を貼らないでください。

Computer Use は UI を操作できます。Google 日本語入力だけに対象を絞り、予期しない画面内容では停止し、実辞書を変更する直前に明示確認してください。

<!-- section:license -->
## ライセンス

MIT。詳細は [LICENSE](LICENSE) を参照してください。

<!-- section:attribution -->
## 帰属

Google 日本語入力および関連名称は各権利者に帰属します。このプロジェクトは独立した非公式ツールです。

<!-- section:disclaimer -->
## 免責

このツールは現状有姿で提供され、保証はありません。実辞書へ import する前に TSV を確認し、backup を保持してください。
