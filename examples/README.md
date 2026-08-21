# Examples

Sample input for every `< file` command in the [main README](../README.md), so
you can try each tool without a real seed phrase and without typing 24 words.

```bash
seed-tools tinyseed --reverse --file examples/plate-24.txt
```

## Plates

Rows of holes for `tinyseed --reverse`, which reads a punched plate back.

| File | What it is | What it does |
| --- | --- | --- |
| [plate-12.txt](plate-12.txt) | One side of a plate, 12 rows of `○`/`●`, exactly as they come off the metal | Prints the 12 words below, exit `0` |
| [plate-12-binary.txt](plate-12-binary.txt) | The same twelve words as `0`/`1` — what `tinyseed --style binary` prints, fed straight back in | Prints the same 12 words |
| [plate-12-typed.txt](plate-12-typed.txt) | The same twelve words written the way a keyboard can type them: `.`/`#`, grouped in threes | Prints the same 12 words — the notation is not part of the meaning |
| [plate-24.txt](plate-24.txt) | Both sides, written as twelve rows, a blank line, twelve more — how a 24-word plate is usually copied down | Prints all 24 words: read from a file, the blank line is the gap where the plate is turned over, not the end |
| [plate-24-misread.txt](plate-24-misread.txt) | `plate-24.txt` with a single hole moved in row 7 | `Invalid checksum`, exit `2`, nothing printed — the mistake this subcommand exists to catch |

All three notations for one side are here on purpose: `○`/`●` is what a plate
looks like, `0`/`1` is what `--style binary` prints, and `.`/`#` is what a
keyboard can type. They read back to the same twelve words, which is the point.

Either source works, and they read the same rows the same way:

```bash
seed-tools tinyseed --reverse --file examples/plate-24.txt
seed-tools tinyseed --reverse --stdin < examples/plate-24.txt
```

## Phrases

Words for the tools that read a phrase, all of them piped in with `--stdin`.

| File | For | What it does |
| --- | --- | --- |
| [backup.txt](backup.txt) | `tinyseed --stdin` | 24 words wrapped four to a line, as a backup is usually written. Prints the punch pattern for all 24 — a newline means nothing inside a phrase, so the wrapping does not split it |
| [first-23-words.txt](first-23-words.txt) | `checksum --stdin` | The same phrase without its last word. Lists the 8 words that complete it, one of which is `indoor` |
| [parts.txt](parts.txt) | `xor --stdin` | The three published Coldcard parts, one per line with a blank line between them. Combines to the phrase in `backup.txt` — piped, the blank lines are gaps and are skipped |

```bash
seed-tools tinyseed --stdin < examples/backup.txt
seed-tools checksum --stdin < examples/first-23-words.txt
seed-tools xor --stdin < examples/parts.txt
```

`xor` prints a `Part N:` prompt before every line it reads, so a file with gaps
in it shows a repeated prompt on stderr — that is the blank line being read and
skipped, not a part being read twice. The count it prints at the end (`Combined 3
parts of 24 words.`) is what to check.

The files go round in a circle, which is a useful thing to try end to end: XOR
the three parts, get the phrase in `backup.txt`, punch that phrase to a plate,
and read the plate back to get the same words again — which is what
`plate-24.txt` holds.

## The phrases themselves

They are the two published Coldcard Seed XOR worked examples, the same ones
[tests/vectors.py](../tests/vectors.py) uses:

- `plate-12.txt`, `plate-12-binary.txt`, `plate-12-typed.txt` — `cannon opinion leader nephew found yard metal galaxy crouch between real trade`
- `plate-24.txt`, `backup.txt`, `parts.txt` — `silent toe meat possible chair blossom wait occur this worth option bag nurse find fish scene bench asthma bike wage world quit primary indoor`

**These phrases are public.** They have been published, indexed and swept for
years; never send funds to them. They are here so a manual test needs no real
seed — and a real one has no business in a file inside a git repository.

The plate files hold nothing but rows. A plate row is 12 positions and anything
else is refused, so there is no comment syntax to explain them in place — that is
what this page is for. A test runs every file here and checks it against the
phrases above, so they cannot quietly rot.
