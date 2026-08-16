# Bitcoin Seed Tools

Command-line tools for working with BIP-39 seed phrases. They run locally on a
workstation — no deployment, no service, no network access, no credentials.

## Target environment
- macOS / Linux workstation
- Python: 3.13+
- No runtime dependencies (stdlib only)

## Structure
```
src/seed_tools/
    __main__.py          # entry point: python -m seed_tools
    cli.py               # argparse setup, subcommand dispatch, error handling
    config.py            # tomllib config loader
    wordlist.py          # Wordlist: word ↔ index ↔ 11-bit binary
    mnemonic.py          # BIP-39 phrases: entropy ↔ words, checksum, XOR
    tools/
        __init__.py      # TOOLS registry — add new tool modules here
        lookup.py        # `lookup` subcommand
        xor.py           # `xor` subcommand
tests/
assets/
    bip-0039-english.txt      # BIP-39 English wordlist (2048 words)
    bip-0039-english-printable.txt # printable table: index, binary, word
config.toml              # non-secret settings (asset paths)
pyproject.toml
```

## Dev/test
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Run
```bash
python -m seed_tools lookup abandon
# or, after install:
seed-tools lookup 2047
```

## Adding a tool
A tool is a module in `src/seed_tools/tools/` exposing:
- `register(subparsers) -> None` — adds its subparser and calls
  `parser.set_defaults(run=run)`
- `run(args) -> int` — the exit code

Register it in `TOOLS` in `tools/__init__.py`. `cli.py` stays untouched.

## Conventions
- Exit codes: `0` success, `1` the tool ran but found nothing, `2` bad input
  (`ValueError` raised by a tool is caught in `cli.main` and logged).
- Assets are resolved through `config.toml` and `config.asset()`, never by
  hardcoded path. `BITCOIN_SEED_TOOLS_HOME` overrides the project root for
  non-editable installs.
- `wordlist.wordlist()` is cached — load it through that, not `Wordlist.from_file`.
- BIP-39 encoding lives in `mnemonic.py` and stays I/O-free: it returns values or
  raises `ValueError`, never prints or prompts. Tools own the interaction.

## Security
- Never write a seed phrase to disk, log it, or send it anywhere. The tools make
  no network calls; keep it that way.
- Never commit test vectors that look like real seed phrases.
