# flashcard-factory

> **Any document, URL, or topic → Anki-compatible flashcard deck.** Spaced-repetition optimized, cloze deletions, difficulty tagged, exports to Anki, CSV, or JSON.

[![PyPI](https://img.shields.io/pypi/v/flashcard-factory?style=flat)](https://pypi.org/project/flashcard-factory/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Quickstart

```bash
pip install flashcard-factory

# From a topic
python -m flashcard_factory "Python decorators" --count 20

# From a URL
python -m flashcard_factory https://docs.python.org/decorators --count 30

# From a file — export to Anki
python -m flashcard_factory notes.txt --anki deck.txt --count 50

# Export to CSV
python -m flashcard_factory biology_notes.pdf --csv cards.csv
```

## Card types generated

| Type | Example |
|------|---------|
| Basic | Q: What does `@property` do? A: Creates a getter method |
| Cloze | `{{c1::@property}}` decorator creates a getter |
| Reverse | Answer → Question (for vocabulary) |
| Enumeration | List the 4 HTTP methods... |

## Anki import

The `--anki` flag generates a tab-separated file you can import directly into Anki:
File → Import → select the .txt file → done.

## License
MIT © [Alper Nabil Gabra Zakher](https://github.com/AlperNab)
