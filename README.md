# Bitcoin Seed Tools

![License](https://img.shields.io/badge/license-MIT-green)
![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux-lightgrey.svg)
![Python](https://img.shields.io/badge/python-3.13%2B-blue)

A small collection of command-line tools for working with BIP-39 seed phrases. Everything runs locally on your own machine — there is no deployment, no network access, and no service to configure. The BIP-39 English wordlist ships with the repository in [assets/](assets), so the tools work fully offline.

> **Security:** these tools are meant for throwaway or test seed phrases. Never type a seed phrase that holds funds into a machine that is online. See [Security](#security).

## Requirements

- Python 3.13+
- No runtime dependencies

## Structure

```
src/seed_tools/
    __main__.py          # entry point: python -m seed_tools
    cli.py               # argument parsing, subcommand dispatch
    config.py            # tomllib config loader
    wordlist.py          # BIP-39 wordlist: word ↔ index ↔ 11-bit binary
    tools/
        lookup.py        # `lookup` subcommand
tests/
assets/
    bip-0039-english.txt      # BIP-39 English wordlist (2048 words)
    bip-0039-english-printable.txt  # printable table: index, binary, word
config.toml              # non-secret settings (asset paths)
pyproject.toml
```

## Install & run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install .
export BITCOIN_SEED_TOOLS_HOME=$(pwd)
python -m seed_tools lookup abandon
```

Installing also puts a `seed-tools` command on your `PATH`:

```bash
seed-tools lookup 2047
```

`BITCOIN_SEED_TOOLS_HOME` tells the tools where `config.toml` and `assets/` live. It is only needed for a regular (non-editable) install — an editable dev install finds the project root on its own.

## Tools

### `lookup`

Resolve a BIP-39 word, an index (0–2047), or a word prefix. Output is `index`, `11-bit binary`, `word`:

```bash
seed-tools lookup abandon 42 zeb
```

```
   0  00000000000  abandon
  42  00000101010  aim
2044  11111111100  zebra
```

Unknown terms print `no match` and the command exits with status `1`.

### Adding a tool

Each tool is a module in [src/seed_tools/tools/](src/seed_tools/tools) exposing `register(subparsers)` and `run(args) -> int`. Add the module to `TOOLS` in [tools/__init__.py](src/seed_tools/tools/__init__.py) and it becomes a subcommand — no changes to `cli.py` needed.

## Configuration

`config.toml` holds non-secret settings only — the paths to the wordlist assets:

```toml
[wordlist]
file = "assets/bip-0039-english.txt"
printable_file = "assets/bip-0039-english-printable.txt"
```

There is no `.env`: these tools need no credentials and make no network calls.

## Development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

Linting and formatting run through `ruff` via pre-commit:

```bash
pre-commit install
```

## Security

- Never enter a seed phrase that controls real funds on an internet-connected machine. Use an offline machine, or use test phrases only.
- The tools never write a seed phrase to disk and never make network calls — but your shell does keep a history file. Clear it (or prefix commands with a space) after working with real words.
- Never commit anything containing a real seed phrase. Nothing scans for that automatically — treat every test vector you add as public.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `FileNotFoundError: config.toml` | Installed non-editable without setting `BITCOIN_SEED_TOOLS_HOME` — export it, pointing at the repository root |
| `FileNotFoundError` on a file in `assets/` | `config.toml` points at a path that does not exist, or the repository was copied without `assets/` |
| `ValueError: Wordlist must contain 2048 words` | The wordlist file was edited or truncated — restore it from git |
| `Not a BIP-39 word` | The word is not in the English wordlist; BIP-39 words are lowercase and unaccented |
| `no match` for a valid-looking number | Indices are 0-based and stop at 2047 |
| `command not found: seed-tools` | The virtualenv is not activated, or the package was installed elsewhere — run `source .venv/bin/activate` |
| `ModuleNotFoundError: No module named 'seed_tools'` | Running `python -m seed_tools` outside the venv, or the package was never installed — run `pip install -e .` |

## Contributing

Found a bug or have an idea? Open an issue or send a PR.
Run `pytest` before submitting and keep changes focused.

## License

MIT © Jan Rothen — see [LICENSE](LICENSE) for details.
