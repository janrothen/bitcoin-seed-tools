# Bitcoin Seed Tools

![License](https://img.shields.io/badge/license-MIT-green)
![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux-lightgrey.svg)
![Python](https://img.shields.io/badge/python-3.13%2B-blue)
![Status](https://img.shields.io/badge/status-unaudited%20%E2%80%94%20use%20at%20your%20own%20risk-orange)

A small collection of command-line tools for working with BIP-39 seed phrases. Everything runs locally on your own machine — there is no deployment, no network access, and no service to configure. The BIP-39 English wordlist ships with the repository in [assets/](assets), so the tools work fully offline.

> **Security:** these tools are meant for throwaway or test seed phrases. Never type a seed phrase that holds funds into a machine that is online. See [Security](#security).

## Disclaimer

**This software is provided "as is", without warranty of any kind. Use it entirely at your own risk.**

These tools operate on the secrets that control Bitcoin wallets. An error — in this software, in your transcription, or in your backup procedure — can make funds **permanently unrecoverable**. There is no undo, no recovery mechanism, and no support desk. This code has not been independently audited.

- **No warranty.** The author makes no representation or guarantee that this software is correct, complete, secure, or fit for any particular purpose.
- **No liability.** To the maximum extent permitted by applicable law, the author shall not be liable for any loss of funds, loss of data, or any other direct, indirect, incidental or consequential damages arising from the use of, or the inability to use, this software — even if advised of the possibility of such damage.
- **Sole responsibility.** You alone are responsible for verifying that any output is correct before relying on it, for the security of the machine you run it on, and for your own backups.
- **Not financial advice.** Nothing in this repository is a recommendation about how to custody assets or manage risk.

Before trusting any output with a wallet that holds value: reproduce the result with an **independent implementation**, confirm the two agree, and rehearse the full backup-and-restore path with a worthless amount first.

The warranty and liability terms in [LICENSE](LICENSE) govern your use of this software. This section summarises them for visibility; it does not replace or extend them.

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

By submitting a contribution you agree that it is licensed under the same MIT terms as the rest of the project.

## License

MIT © Jan Rothen — see [LICENSE](LICENSE) for details.

The MIT terms include a disclaimer of warranty and a limitation of liability. See [Disclaimer](#disclaimer) for what that means in practice before using these tools with real funds.
