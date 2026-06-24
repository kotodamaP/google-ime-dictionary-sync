# Contributing

Thank you for helping improve `google-ime-dictionary-sync`.

Before opening an issue or pull request:

- use synthetic sample dictionary data only;
- do not include private dictionary files, IME exports, screenshots, local paths, account data, customer names, or personal names;
- run `python -m unittest discover -s tests`;
- run `python scripts/build_dictionary.py --source examples/term-candidates.md --build-dir build --check`.

Keep the CLI deterministic and dependency-free unless a dependency is clearly justified.
