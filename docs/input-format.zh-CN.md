# 输入格式

源文件是一个 Markdown 表，必须包含下列列。列顺序可以不同，但所有列都必须存在。

| 列 | 含义 |
|---|---|
| `正式表記` | 输出到 Google Japanese Input 的表面形式。必填。 |
| `alias` | v1 中是单一 metadata 字符串。默认不输出。 |
| `読み` | 平假名读音。必填。 |
| `memo` | TSV comment。 |
| `scope候補` | review workflow metadata。 |
| `出典` | 仅 metadata。共享文件时不要写入 private URL、local path、account name、ticket ID、customer name 或 confidential source name。 |
| `status` | `candidate` 或 `reviewed` 的行会被输出。 |

默认是 strict mode。它会拒绝 unknown status、必填列为空、无效读音、重复的 `読み + 正式表記`，以及包含 tab/newline 的字段。

禁用状态会被忽略: `draft`, `rejected`, `hold`, `private`, `archived`。

`alias` 默认不会输出。`--emit-aliases` 是 experimental，会将整个 alias cell 当作一个额外表面形式。

`読み` 接受平假名、小假名和 `ゔ`。如果需要允许 `ー`，请使用 `--allow-long-vowel-mark`。source reading 会拒绝汉字、片假名、Latin letters、space、tab 和 newline。

输出会通过 NFC normalization、首尾 whitespace trim、按 `読み` 和 `正式表記` stable sort 进行 canonical 化。
