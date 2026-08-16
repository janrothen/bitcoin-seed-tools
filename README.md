# Bitcoin Seed Tools

![License](https://img.shields.io/badge/license-MIT-green)
![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux-lightgrey.svg)
![Python](https://img.shields.io/badge/python-3.13%2B-blue)
![Status](https://img.shields.io/badge/status-unaudited%20%E2%80%94%20use%20at%20your%20own%20risk-orange)
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=bitcoin-seed-tools&metric=alert_status)](https://sonarcloud.io/project/overview?id=bitcoin-seed-tools)
[![Bugs](https://sonarcloud.io/api/project_badges/measure?project=bitcoin-seed-tools&metric=bugs)](https://sonarcloud.io/project/overview?id=bitcoin-seed-tools)
[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=bitcoin-seed-tools&metric=coverage)](https://sonarcloud.io/project/overview?id=bitcoin-seed-tools)
[![Security Rating](https://sonarcloud.io/api/project_badges/measure?project=bitcoin-seed-tools&metric=security_rating)](https://sonarcloud.io/project/overview?id=bitcoin-seed-tools)

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
    mnemonic.py          # BIP-39 phrases: entropy ↔ words, checksum, XOR
    tinyseed.py          # TinySeed plates: word ↔ 12-bit punch pattern
    phrase_input.py      # reading a phrase from a terminal without echoing it
    tools/
        checksum.py      # `checksum` subcommand
        lookup.py        # `lookup` subcommand
        tinyseed.py      # `tinyseed` subcommand
        xor.py           # `xor` subcommand
tests/
assets/
    bip-0039-english.txt      # BIP-39 English wordlist (2048 words)
    bip-0039-english-printable.txt  # printable table: index, binary, word
    bip-0039-english-tinyseed.txt   # TinySeed table: number, word, binary, circles
    bip-0039-tinyseed_io.pdf        # the printable reference card from tinyseed.io
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

Unknown terms print `no match`; like `grep`, the command exits with status `1` only when no term matched at all. Terms are matched lowercase, the way BIP-39 words are written.

### `checksum`

Complete a seed phrase: give it every word but the last, and it lists the final words that make the BIP-39 checksum come out right. Use it when you generated your own entropy — dice, coin flips, a deck of cards — and have 11 or 23 words with no way to compute the last one by hand.

```bash
seed-tools checksum
```

The tool prompts once, without echoing, and prints the candidates:

```
Seed phrase without its last word:
23 words read; 8 valid final words.
Each completes a different wallet. The last word carries 3 bits of entropy besides the checksum, so pick a number at random (3 coin flips) rather than taking the first.
  0  buddy
  1  cash
  …
  7  vote
```

**There is always more than one, and the choice is yours to make properly.** Only the trailing bits of the last word are the checksum — the ones before them are the final bits of your entropy. So a 23-word phrase has 8 valid endings and an 11-word one has 128, and every candidate is a valid phrase for a *completely different wallet*.

| Words given | Candidates | Entropy bits in the last word |
| --- | --- | --- |
| 11 | 128 | 7 |
| 14 | 64 | 6 |
| 17 | 32 | 5 |
| 20 | 16 | 4 |
| 23 | 8 | 3 |

That is why the candidates are numbered **from 0**, unlike the word positions the other tools print: the number is the value to draw, and the draw is exactly as many bits as the last word is worth. Flip a coin 3 times for a 23-word phrase, 7 times for an 11-word one, and take the number that comes up. Always taking the first candidate — or the one that reads nicest — throws those bits away and hands them to anyone who guesses the habit.

The same list answers the other question people ask it: *which last word did I have?* If a backup lost its final word, these are the only words it could have been, and each one needs trying against the wallet you expect. The tool cannot narrow it further — nothing in the phrase records which one you used.

Like the other phrase tools, the words are never taken from the command line, and `--stdin` reads the whole of stdin as one phrase, so a backup may wrap however it happens to be written:

```bash
seed-tools checksum --stdin < first-23-words.txt
```

The count on stderr is worth reading. A file that lost or gained a word can still land on an accepted length, and the candidates look exactly as convincing either way — the count is what gives it away. Prompts and errors go to stderr and the candidates to stdout.

> Verify before the wallet holds anything. Feed the completed phrase back through `seed-tools tinyseed` (or any wallet) and confirm it is accepted — that is a second, independent check on the word you picked.

### `tinyseed`

Turn a seed phrase into the punch pattern for a [TinySeed](https://tinyseed.io) plate — a titanium card that stores a backup as drilled holes instead of letters, so it survives fire and water. The plate is punched front and back, 12 words to a side: a 12-word phrase fills the front, a 24-word one carries on over the back. Reading all 24 rows off the printed card by hand is slow and easy to get wrong, and a hole cannot be un-punched. It goes both ways: `--reverse` [reads a punched plate back](#reading-a-plate-back) so you can check what you actually engraved.

TinySeed numbers the wordlist **1–2048** and punches that number in **12 bits**, most significant bit first. That is deliberately *not* the 11-bit index `lookup` prints: it is that index **plus one**, and only `zoo` (2048) sets the leading bit.

```bash
seed-tools tinyseed
```

The tool prompts once, without echoing, and prints one row per word — `○` to leave alone, `●` to punch:

```
Seed phrase:
 1  silent    ○●●○○●○○○●○○
 2  toe       ○●●●○○○●●●○●
 3  meat      ○●○○○●○●○○○●
 …
24  indoor    ○○●●●○○●●○○●
```

Add `--style binary` to print `1`/`0` instead. Use it if your terminal renders the circles at double width — `●` and `○` are East Asian *Ambiguous* characters, so a terminal configured for CJK will draw them wider than one column:

```
 1  silent    011001000100
```

The phrase is verified before anything is printed: the word count and the BIP-39 checksum must both be right, so a mistyped or transposed word is caught before it reaches the plate. Bad input exits with status `2` and prints nothing.

Like `xor`, the phrase is never taken as a command-line argument — that would leave it in your shell history. Pass `--stdin` to pipe it in instead — the flag reads a pipe or a file, and is refused at a terminal, where typing would echo. Prompts go to stderr and the rows to stdout.

All of stdin is the phrase, so it may wrap however your backup file happens to be written — two lines of 12, four lines of 6, one word per line. A newline carries no meaning inside a phrase, and reading only the first line would silently punch half a plate:

```bash
seed-tools tinyseed --stdin < backup.txt
```

Note this differs from `xor --stdin`, where a newline separates one part from the next.

The full translation table ships as [assets/bip-0039-english-tinyseed.txt](assets/bip-0039-english-tinyseed.txt) (number, word, binary, circles), alongside the official printable card in [assets/bip-0039-tinyseed_io.pdf](assets/bip-0039-tinyseed_io.pdf). A test regenerates the table from the wordlist and compares it against the shipped file, so the two cannot drift apart.

#### Reading a plate back

**Punching the plate is only half the job.** A hole in the wrong row is invisible until the day you need the backup, and by then the plate is all you have. So read it back: look at the finished plate, type in what you actually see, and let the tool tell you what it says.

```bash
seed-tools tinyseed --reverse
```

It asks for one row at a time — `○` where the metal is untouched, `●` where you punched it:

```
Row 1: ○●●○○●○○○●○○
Row 2: ○●●●○○○●●●○●
…
Row 12: ○○●●●○○●●○○●
Row 13 (blank to finish):
 1  silent
 2  toe
 …
12  indoor

silent toe meat …
```

A blank line ends the list. A side of the plate holds 12 rows, so a 24-word phrase runs across both — keep going past row 12 and finish with a blank line there instead.

Stopping at exactly 12 rows is the one ambiguous case, so it takes a second blank line to confirm:

```
Row 13 (blank to finish):
— 12 rows read, which is one full side of the plate. A 24-word phrase fills
both: turn the plate over and carry on, or press Enter again to finish here.
Row 13 (blank to finish):
```

That is there because row 12 is where you turn the plate over, and an Enter pressed in that pause would otherwise end the read at twelve words — which pass the checksum roughly once in sixteen and would then be printed as though they were the whole phrase.

Since `●` and `○` are not on a keyboard, a row may be written any of these ways, and they may be mixed within a row:

| Position | Accepted marks |
| --- | --- |
| Untouched | `○` `0` `.` `o` `O` |
| Punched | `●` `1` `#` `x` `X` |

So `.##..#...#..` and `011001000100` and `○●●○○●○○○●○○` are the same row. Spaces are ignored, so you may group the holes to keep your place: `○●● ○○● ○○○ ●○○`. Anything else is refused — a row must be exactly 12 positions, never nearly 12.

**The check that matters is the checksum.** The words are only printed if the whole plate decodes to a valid BIP-39 phrase, so a misread row or a mispunched hole almost always fails outright, and nothing is printed. That leaves the rare case where a wrong plate still checksums: compare the printed phrase against your backup, which is what the last line is for.

Unlike every other prompt in this project, **this one echoes what you type** — a transcription you cannot see is not one you can proofread, and the decoded words are printed anyway. `--style` is not accepted here: the marks are recognised however you write them.

```bash
seed-tools tinyseed --reverse --stdin < plate.txt
```

Piped like this the file's own end is what stops the read, so a blank line in it is only the gap between the front and the back of the plate and is skipped — write 24 rows as twelve, a gap, and twelve more if that is how you copied them down. (Typed at the prompt there is no end-of-file to wait for, so there a blank line still ends the list.)

> Verify before the wallet holds anything. Read the plate you just punched, not the phrase you meant to punch — the point is to catch the difference.

### `xor`

Combine two or more seed phrases into one by XOR-ing their entropy and computing a fresh checksum. Use it when you don't want to trust a single hardware wallet's random number generator: XOR the wallet's phrase with one you generated independently (dice, coin flips, a second device). As long as **any one** part is genuinely random and independent of the others, the combined seed is uniformly random — a biased or backdoored RNG in one device cannot skew the result.

This implements [Seed XOR](https://github.com/Coldcard/firmware/blob/master/docs/seed-xor.md), the open standard used by Coldcard, so the result can be reconstructed on any wallet that supports it — not just here.

```bash
seed-tools xor
```

The tool prompts for each part without echoing it, and a blank line ends the list:

```
Part 1:
Part 2:
Part 3 (blank to finish):
 1  silent
 2  toe
 3  meat
 …
24  indoor

silent toe meat possible chair blossom wait occur this worth option bag nurse find fish scene bench asthma bike wage world quit primary indoor
```

The numbered list is for transcribing onto a backup one word at a time; the final line repeats the same phrase in full for entering it into a wallet in one go.

Every part's own checksum is verified the moment it is entered, so a mistyped or transposed word is caught before it can silently produce a different — and unrecoverable — wallet. A bad part stops the command right there, naming the part that failed, rather than letting you type the remaining ones first:

```
Part 1:
Part 2:
ERROR seed_tools.cli: Part 2: Invalid checksum — check the words and their order
```

Add `--entropy` to also print the combined entropy as hex, which is useful for cross-checking against another implementation.

```bash
seed-tools xor --stdin < parts.txt
```

Piped like this the file's own end is what stops the read, so a blank line in it is only the gap between two parts and is skipped — write the parts out spaced apart if that is how you keep them. (Typed at the prompt there is no end-of-file to wait for, so there a blank line still ends the list.) Before the result, the tool reports on stderr what it actually combined:

```
Combined 3 parts of 24 words.
```

Check that line. A part that was stored wrapped across two lines reads as two shorter parts rather than one, and the phrase that comes out of that carries a perfectly valid checksum — the counts are what give it away.

All parts must have the same word count. The command refuses to emit a result when the parts cancel each other out, and exits with status `2` on any bad input. Prompts and errors go to stderr and the result to stdout, so redirecting stdout captures the phrase and nothing else. Ctrl-C or Ctrl-D at a prompt aborts without printing a result.

> **Seed XOR is used in two opposite ways, and they have opposite backup rules. Decide which one you are doing before you destroy anything.**
>
> **Generating a seed you don't have to trust one source for.** Combine the parts, back up the *combined* phrase, and destroy the parts. They are scratch work: once the result is backed up and verified, nothing depends on them ever again, and every copy left lying around is one more thing that has to stay secret. This is the scheme you want if the point was to avoid trusting a single hardware wallet's RNG. Verify the backup *before* you destroy the parts — restore from it, confirm the wallet fingerprint, and only then get rid of them, because afterwards that backup is the only copy in existence.
>
> **Splitting a seed you already have.** Keep the parts in separate places and never write the combined phrase down at all. Here every part is required forever — lose one and the wallet is gone. **This is not a threshold scheme**: there is no 2-of-3, it is all-of-n. Never store a part alongside the combined phrase, which would reduce the whole thing to plaintext.
>
> Both rest on the same assumption: provided one part is genuinely random and independent of the others, no subset of the rest reveals anything about the result. That guarantee is only as good as the independence — parts derived from each other, or from the same weak source, do not give it.

### Adding a tool

Each tool is a module in [src/seed_tools/tools/](src/seed_tools/tools) exposing `register(subparsers)` and `run(args) -> int`. Add the module to `TOOLS` in [tools/__init__.py](src/seed_tools/tools/__init__.py) and it becomes a subcommand — no changes to `cli.py` needed.

## Configuration

`config.toml` holds non-secret settings only — the paths to the wordlist assets:

```toml
[wordlist]
file = "assets/bip-0039-english.txt"
printable_file = "assets/bip-0039-english-printable.txt"

[tinyseed]
file = "assets/bip-0039-english-tinyseed.txt"
reference_file = "assets/bip-0039-tinyseed_io.pdf"
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
- Never commit anything containing a real seed phrase. Nothing scans for that automatically — treat every test vector you add as public. The phrases in [tests/vectors.py](tests/vectors.py) are published specification vectors and are already compromised.
- `xor`, `tinyseed` and `checksum` never echo a phrase you type and never write it anywhere. The one exception is `tinyseed --reverse`, which echoes the rows of holes on purpose so you can proofread them — it is still a secret on your screen, so read a plate back somewhere nobody is looking. Either way, **Python cannot reliably wipe a phrase from process memory** — strings are immutable and may be copied by the interpreter or paged to swap. Treat the machine as contaminated afterwards: use an offline system and power it off when you are done.
- Seed XOR has two uses with opposite backup rules — see [`xor`](#xor) before you throw anything away. If you are *splitting* a seed, every part is required forever, none of them may sit beside the combined phrase, and it is all-of-n rather than a threshold scheme. If you combined parts only to *generate* a seed that you then back up in full, the parts are scratch work and destroying them is the right move — but verify the backup first, because it becomes the only copy.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `FileNotFoundError: config.toml` | Installed non-editable without setting `BITCOIN_SEED_TOOLS_HOME` — export it, pointing at the repository root |
| `FileNotFoundError` on a file in `assets/` | `config.toml` points at a path that does not exist, or the repository was copied without `assets/` |
| `ValueError: Wordlist must contain 2048 words` | The wordlist file was edited or truncated — restore it from git |
| `Word N is not a BIP-39 word` | Word `N` of that phrase is not in the English wordlist; BIP-39 words are lowercase and unaccented. The word itself is deliberately not repeated back — errors reach a log, and a word typed at a seed prompt does not belong in one |
| `Wordlist contains duplicate words` / `Wordlist is not in sorted order` | The wordlist file was edited or replaced — restore it from git. Both corruptions keep the file at 2048 lines and would otherwise silently produce phrases no other wallet reproduces |
| `no match` for a valid-looking number | Indices are 0-based and stop at 2047 |
| `Part N: Invalid checksum` | A word in part `N` is wrong or out of order — the last word encodes a checksum over all the others, so re-read that part carefully |
| `Aborted — no result was produced` | Ctrl-C or Ctrl-D was pressed at a prompt; nothing was combined or printed |
| `Seed phrase must be 12, 15, 18, 21 or 24 words` | A word was dropped or duplicated while typing the part |
| `Seed phrase must be 11, 14, 17, 20 or 23 words` | `checksum` completes a phrase, so it wants every word *but* the last — pass 23 words to get the 24th, not 24 |
| `checksum` lists more than one word | Correct, and not a bug: the last word carries entropy as well as the checksum. Pick one at random — see [`checksum`](#checksum) |
| `All parts must have the same word count` | Mixing a 12-word and a 24-word part — `xor` needs them the same length |
| `Need at least 2 parts to XOR` | The list was ended with a blank line too early; enter at least two phrases |
| `Parts cancel out` | Two parts are identical, or one equals the XOR of the others — the extra parts add no entropy, so use independent ones |
| `stdin is not a terminal` | A phrase tool was piped or run from a script — pass `--stdin`. `xor` reads one phrase per line; `tinyseed` and `checksum` read the whole of stdin as one phrase, and `tinyseed --reverse` one plate row per line |
| `stdin is a terminal` | `--stdin` reads a pipe or a file, and typing at a terminal would echo the phrase into scrollback — drop the flag to be prompted with input hidden |
| `tinyseed` circles look doubled or misaligned | The terminal renders `●`/`○` at double width (they are East Asian *Ambiguous*) — use `--style binary` |
| A `tinyseed` number is one higher than `lookup` says | Correct: TinySeed numbers the wordlist 1–2048, `lookup` uses the BIP-39 index 0–2047 |
| `Row N: Expected 12 positions, got 11` | A hole was missed or double-counted while reading row `N` — every row is exactly 12 positions, so count them again, in groups of three if it helps |
| `Row N: Not a punch mark at position P` | Something that is not a hole or a blank was typed at position `P` of row `N` — use `○`/`●`, `0`/`1`, or `.`/`#` |
| `Row N: Row has no holes` | Row `N` was entered as twelve blanks, which is no word at all — either the row was skipped, or the plate is misaligned by one |
| `Row N: Pattern is past the end of the wordlist` | Position 1 of row `N` was read as punched, and only `zoo` has that hole — most likely the row was shifted by one, so check where it starts |
| `Invalid checksum` from `--reverse` | The plate does not say what you meant it to: one row is misread, or a hole really is in the wrong place. Re-read each row against [assets/bip-0039-english-tinyseed.txt](assets/bip-0039-english-tinyseed.txt) before trusting the plate |
| `command not found: seed-tools` | The virtualenv is not activated, or the package was installed elsewhere — run `source .venv/bin/activate` |
| `ModuleNotFoundError: No module named 'seed_tools'` | Running `python -m seed_tools` outside the venv, or the package was never installed — run `pip install -e .` |

## Contributing

Found a bug or have an idea? Open an issue or send a PR.
Run `pytest` before submitting and keep changes focused.

By submitting a contribution you agree that it is licensed under the same MIT terms as the rest of the project.

## License

MIT © Jan Rothen — see [LICENSE](LICENSE) for details.

The MIT terms include a disclaimer of warranty and a limitation of liability. See [Disclaimer](#disclaimer) for what that means in practice before using these tools with real funds.
