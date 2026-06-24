# google-ime-dictionary-sync

Language:
[日本語](README.ja.md) | [English](README.en.md) | [简体中文](README.zh-CN.md)

`google-ime-dictionary-sync` は、Markdown の辞書シートから Google 日本語入力向け TSV を生成し、必要に応じて Codex Skill / Computer Use で取り込み手順を安全に補助するための CLI です。

## 目的

難読語、固有名詞、プロジェクト用語、作品名、人名などを、毎回手で Google 日本語入力へ登録する手間を減らすことが目的です。

用語を Markdown の表として管理し、CLI で Google 日本語入力が読み込める TSV に変換します。実際の辞書変更は自動で勝手に行わず、取り込み直前にユーザー確認を挟む設計です。

## 利用シーン

- 創作、研究、開発、サポート業務などで固有名詞の表記ゆれを減らしたい。
- 複数の用語をまとめて Google 日本語入力へ登録したい。
- 辞書データを Markdown / Git で管理し、変更履歴を残したい。
- Codex Skill に辞書シートの追記、検証、取り込み準備を手伝わせたい。
- Windows の Google 日本語入力 UI で TSV import を行うとき、Computer Use に監督付きで操作を補助させたい。

## 利用用途

- `--init-sheet` で辞書シートのひな形を作成。
- Markdown 表から Google 日本語入力 TSV を生成。
- `prepare` で前回 baseline と比較し、更新が必要か確認。
- Google IME export と生成 TSV の merge 補助。
- repo-local Codex Skill による辞書シート確認と、任意の Computer Use import 補助。

## メリット

- Markdown 表が入力元なので、人間がレビューしやすい。
- strict validation により、読み、status、重複、TSV を壊す文字を早めに検出できる。
- canonical TSV hash と build option hash により、変更なしのときは Google 日本語入力や Computer Use を開かずに済む。
- 実辞書の変更前に TSV path、SHA256、backup path、予定操作を確認するため、誤操作を減らせる。
- 外部 Python 依存なしで試せる。

## 対象者

- Google 日本語入力のユーザー辞書を安全にまとめて管理したい人。
- 難読固有名詞や専門用語を多く扱う作家、翻訳者、研究者、開発者、サポート担当者。
- Codex Skill / Computer Use を使って、ローカル UI 操作を監督付きで補助させたい人。
- private な辞書データを公開せず、生成ルールとサンプルだけを再利用したい人。

## クイックスタート

```bash
python scripts/build_dictionary.py --init-sheet my-terms.md
python scripts/build_dictionary.py --source my-terms.md --build-dir build --check
python scripts/google_ime_dictionary_sync.py prepare --source-md my-terms.md --backup-root ./tmp/google-ime-runs --json
```

実際に Google 日本語入力へ import する前に、生成 TSV と backup/export path を確認してください。Computer Use は本体機能ではなく任意の UI 補助であり、実辞書を変更する直前に明示確認が必要です。

詳しい説明:

- [日本語](README.ja.md)
- [English](README.en.md)
- [简体中文](README.zh-CN.md)
