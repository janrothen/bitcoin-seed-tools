"""Published BIP-39 and Seed XOR test vectors.

=============================================================================
THESE PHRASES ARE PUBLIC. NEVER SEND FUNDS TO THEM.

Every phrase below is copied from a public specification document and has been
published, indexed and swept for years. Anyone can empty a wallet built from
them within seconds. They exist here only to prove this implementation agrees
with the reference implementations.

Do not add a phrase to this file unless it is already public. Do not generate a
"random" one for convenience — see the Security section of CLAUDE.md.
=============================================================================

Sources:
  BIP-39   https://github.com/trezor/python-mnemonic/blob/master/vectors.json
  Seed XOR https://github.com/Coldcard/firmware/blob/master/docs/seed-xor.md
"""

# (entropy hex, mnemonic) from the Trezor python-mnemonic English vectors.
BIP39_VECTORS = [
    (
        "00000000000000000000000000000000",
        "abandon abandon abandon abandon abandon abandon abandon abandon abandon"
        " abandon abandon about",
    ),
    (
        "7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f",
        "legal winner thank year wave sausage worth useful legal winner thank yellow",
    ),
    (
        "80808080808080808080808080808080",
        "letter advice cage absurd amount doctor acoustic avoid letter advice cage"
        " above",
    ),
    (
        "ffffffffffffffffffffffffffffffff",
        "zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo wrong",
    ),
    (
        "0000000000000000000000000000000000000000000000000000000000000000",
        "abandon abandon abandon abandon abandon abandon abandon abandon abandon"
        " abandon abandon abandon abandon abandon abandon abandon abandon abandon"
        " abandon abandon abandon abandon abandon art",
    ),
    (
        "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",
        "zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo"
        " zoo zoo zoo zoo zoo vote",
    ),
]

# The worked 24-word, 3-part example from the Coldcard Seed XOR documentation.
XOR_24_PARTS = [
    "romance wink lottery autumn shop bring dawn tongue range crater truth ability"
    " miss spice fitness easy legal release recall obey exchange recycle dragon room",
    "lion misery divide hurry latin fluid camp advance illegal lab pyramid unaware"
    " eager fringe sick camera series noodle toy crowd jeans select depth lounge",
    "vault nominee cradle silk own frown throw leg cactus recall talent worry gadget"
    " surface shy planet purpose coffee drip few seven term squeeze educate",
]
XOR_24_RESULT = (
    "silent toe meat possible chair blossom wait occur this worth option bag nurse"
    " find fish scene bench asthma bike wage world quit primary indoor"
)

# The worked 12-word, 3-part example from the same document.
XOR_12_PARTS = [
    "romance wink lottery autumn shop bring dawn tongue range crater truth ability",
    "boat unfair shell violin tree robust open ride visual forest vintage approve",
    "lion misery divide hurry latin fluid camp advance illegal lab pyramid unhappy",
]
XOR_12_RESULT = (
    "cannon opinion leader nephew found yard metal galaxy crouch between real trade"
)
