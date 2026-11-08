"""wallet_sweep - read-only crypto artifact search for ViperCrest.

Searches a target drive or folder for cryptocurrency artifacts (wallet files,
keystores, seed phrases, keys) and writes a situated case record: every find is
VERIFIED by mathematics where mathematics can verify it, held as a CANDIDATE
where it cannot, and recorded as searched-and-absent where nothing was found.
Nothing is opened, decrypted, moved, or cracked. Secrets are never written to
the record - a seed hit is reported by first word, word count, and the hash of
the file it was found in.

Stdlib only. Air-gapped by construction: this module makes no network calls.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac as _hmac
import json
import os
import re
import sys
import time
import unicodedata
import zipfile
from pathlib import Path

# ---------------------------------------------------------------------------
# BIP39 English wordlist (canonical, 2048 words).
# Source: bitcoin/bips BIP0039 english.txt (via trezor/python-mnemonic mirror).
# SHA-256 of the source file: 2f5eed53a4727b4bf8880d8f3f199efc90e58503646d9ff8eff3a2ed3b24dbda
# ---------------------------------------------------------------------------
_BIP39_WORDS = """
abandon ability able about above absent absorb abstract absurd abuse access accident
account accuse achieve acid acoustic acquire across act action actor actress actual
adapt add addict address adjust admit adult advance advice aerobic affair afford
afraid again age agent agree ahead aim air airport aisle alarm album
alcohol alert alien all alley allow almost alone alpha already also alter
always amateur amazing among amount amused analyst anchor ancient anger angle angry
animal ankle announce annual another answer antenna antique anxiety any apart apology
appear apple approve april arch arctic area arena argue arm armed armor
army around arrange arrest arrive arrow art artefact artist artwork ask aspect
assault asset assist assume asthma athlete atom attack attend attitude attract auction
audit august aunt author auto autumn average avocado avoid awake aware away
awesome awful awkward axis baby bachelor bacon badge bag balance balcony ball
bamboo banana banner bar barely bargain barrel base basic basket battle beach
bean beauty because become beef before begin behave behind believe below belt
bench benefit best betray better between beyond bicycle bid bike bind biology
bird birth bitter black blade blame blanket blast bleak bless blind blood
blossom blouse blue blur blush board boat body boil bomb bone bonus
book boost border boring borrow boss bottom bounce box boy bracket brain
brand brass brave bread breeze brick bridge brief bright bring brisk broccoli
broken bronze broom brother brown brush bubble buddy budget buffalo build bulb
bulk bullet bundle bunker burden burger burst bus business busy butter buyer
buzz cabbage cabin cable cactus cage cake call calm camera camp can
canal cancel candy cannon canoe canvas canyon capable capital captain car carbon
card cargo carpet carry cart case cash casino castle casual cat catalog
catch category cattle caught cause caution cave ceiling celery cement census century
cereal certain chair chalk champion change chaos chapter charge chase chat cheap
check cheese chef cherry chest chicken chief child chimney choice choose chronic
chuckle chunk churn cigar cinnamon circle citizen city civil claim clap clarify
claw clay clean clerk clever click client cliff climb clinic clip clock
clog close cloth cloud clown club clump cluster clutch coach coast coconut
code coffee coil coin collect color column combine come comfort comic common
company concert conduct confirm congress connect consider control convince cook cool copper
copy coral core corn correct cost cotton couch country couple course cousin
cover coyote crack cradle craft cram crane crash crater crawl crazy cream
credit creek crew cricket crime crisp critic crop cross crouch crowd crucial
cruel cruise crumble crunch crush cry crystal cube culture cup cupboard curious
current curtain curve cushion custom cute cycle dad damage damp dance danger
daring dash daughter dawn day deal debate debris decade december decide decline
decorate decrease deer defense define defy degree delay deliver demand demise denial
dentist deny depart depend deposit depth deputy derive describe desert design desk
despair destroy detail detect develop device devote diagram dial diamond diary dice
diesel diet differ digital dignity dilemma dinner dinosaur direct dirt disagree discover
disease dish dismiss disorder display distance divert divide divorce dizzy doctor document
dog doll dolphin domain donate donkey donor door dose double dove draft
dragon drama drastic draw dream dress drift drill drink drip drive drop
drum dry duck dumb dune during dust dutch duty dwarf dynamic eager
eagle early earn earth easily east easy echo ecology economy edge edit
educate effort egg eight either elbow elder electric elegant element elephant elevator
elite else embark embody embrace emerge emotion employ empower empty enable enact
end endless endorse enemy energy enforce engage engine enhance enjoy enlist enough
enrich enroll ensure enter entire entry envelope episode equal equip era erase
erode erosion error erupt escape essay essence estate eternal ethics evidence evil
evoke evolve exact example excess exchange excite exclude excuse execute exercise exhaust
exhibit exile exist exit exotic expand expect expire explain expose express extend
extra eye eyebrow fabric face faculty fade faint faith fall false fame
family famous fan fancy fantasy farm fashion fat fatal father fatigue fault
favorite feature february federal fee feed feel female fence festival fetch fever
few fiber fiction field figure file film filter final find fine finger
finish fire firm first fiscal fish fit fitness fix flag flame flash
flat flavor flee flight flip float flock floor flower fluid flush fly
foam focus fog foil fold follow food foot force forest forget fork
fortune forum forward fossil foster found fox fragile frame frequent fresh friend
fringe frog front frost frown frozen fruit fuel fun funny furnace fury
future gadget gain galaxy gallery game gap garage garbage garden garlic garment
gas gasp gate gather gauge gaze general genius genre gentle genuine gesture
ghost giant gift giggle ginger giraffe girl give glad glance glare glass
glide glimpse globe gloom glory glove glow glue goat goddess gold good
goose gorilla gospel gossip govern gown grab grace grain grant grape grass
gravity great green grid grief grit grocery group grow grunt guard guess
guide guilt guitar gun gym habit hair half hammer hamster hand happy
harbor hard harsh harvest hat have hawk hazard head health heart heavy
hedgehog height hello helmet help hen hero hidden high hill hint hip
hire history hobby hockey hold hole holiday hollow home honey hood hope
horn horror horse hospital host hotel hour hover hub huge human humble
humor hundred hungry hunt hurdle hurry hurt husband hybrid ice icon idea
identify idle ignore ill illegal illness image imitate immense immune impact impose
improve impulse inch include income increase index indicate indoor industry infant inflict
inform inhale inherit initial inject injury inmate inner innocent input inquiry insane
insect inside inspire install intact interest into invest invite involve iron island
isolate issue item ivory jacket jaguar jar jazz jealous jeans jelly jewel
job join joke journey joy judge juice jump jungle junior junk just
kangaroo keen keep ketchup key kick kid kidney kind kingdom kiss kit
kitchen kite kitten kiwi knee knife knock know lab label labor ladder
lady lake lamp language laptop large later latin laugh laundry lava law
lawn lawsuit layer lazy leader leaf learn leave lecture left leg legal
legend leisure lemon lend length lens leopard lesson letter level liar liberty
library license life lift light like limb limit link lion liquid list
little live lizard load loan lobster local lock logic lonely long loop
lottery loud lounge love loyal lucky luggage lumber lunar lunch luxury lyrics
machine mad magic magnet maid mail main major make mammal man manage
mandate mango mansion manual maple marble march margin marine market marriage mask
mass master match material math matrix matter maximum maze meadow mean measure
meat mechanic medal media melody melt member memory mention menu mercy merge
merit merry mesh message metal method middle midnight milk million mimic mind
minimum minor minute miracle mirror misery miss mistake mix mixed mixture mobile
model modify mom moment monitor monkey monster month moon moral more morning
mosquito mother motion motor mountain mouse move movie much muffin mule multiply
muscle museum mushroom music must mutual myself mystery myth naive name napkin
narrow nasty nation nature near neck need negative neglect neither nephew nerve
nest net network neutral never news next nice night noble noise nominee
noodle normal north nose notable note nothing notice novel now nuclear number
nurse nut oak obey object oblige obscure observe obtain obvious occur ocean
october odor off offer office often oil okay old olive olympic omit
once one onion online only open opera opinion oppose option orange orbit
orchard order ordinary organ orient original orphan ostrich other outdoor outer output
outside oval oven over own owner oxygen oyster ozone pact paddle page
pair palace palm panda panel panic panther paper parade parent park parrot
party pass patch path patient patrol pattern pause pave payment peace peanut
pear peasant pelican pen penalty pencil people pepper perfect permit person pet
phone photo phrase physical piano picnic picture piece pig pigeon pill pilot
pink pioneer pipe pistol pitch pizza place planet plastic plate play please
pledge pluck plug plunge poem poet point polar pole police pond pony
pool popular portion position possible post potato pottery poverty powder power practice
praise predict prefer prepare present pretty prevent price pride primary print priority
prison private prize problem process produce profit program project promote proof property
prosper protect proud provide public pudding pull pulp pulse pumpkin punch pupil
puppy purchase purity purpose purse push put puzzle pyramid quality quantum quarter
question quick quit quiz quote rabbit raccoon race rack radar radio rail
rain raise rally ramp ranch random range rapid rare rate rather raven
raw razor ready real reason rebel rebuild recall receive recipe record recycle
reduce reflect reform refuse region regret regular reject relax release relief rely
remain remember remind remove render renew rent reopen repair repeat replace report
require rescue resemble resist resource response result retire retreat return reunion reveal
review reward rhythm rib ribbon rice rich ride ridge rifle right rigid
ring riot ripple risk ritual rival river road roast robot robust rocket
romance roof rookie room rose rotate rough round route royal rubber rude
rug rule run runway rural sad saddle sadness safe sail salad salmon
salon salt salute same sample sand satisfy satoshi sauce sausage save say
scale scan scare scatter scene scheme school science scissors scorpion scout scrap
screen script scrub sea search season seat second secret section security seed
seek segment select sell seminar senior sense sentence series service session settle
setup seven shadow shaft shallow share shed shell sheriff shield shift shine
ship shiver shock shoe shoot shop short shoulder shove shrimp shrug shuffle
shy sibling sick side siege sight sign silent silk silly silver similar
simple since sing siren sister situate six size skate sketch ski skill
skin skirt skull slab slam sleep slender slice slide slight slim slogan
slot slow slush small smart smile smoke smooth snack snake snap sniff
snow soap soccer social sock soda soft solar soldier solid solution solve
someone song soon sorry sort soul sound soup source south space spare
spatial spawn speak special speed spell spend sphere spice spider spike spin
spirit split spoil sponsor spoon sport spot spray spread spring spy square
squeeze squirrel stable stadium staff stage stairs stamp stand start state stay
steak steel stem step stereo stick still sting stock stomach stone stool
story stove strategy street strike strong struggle student stuff stumble style subject
submit subway success such sudden suffer sugar suggest suit summer sun sunny
sunset super supply supreme sure surface surge surprise surround survey suspect sustain
swallow swamp swap swarm swear sweet swift swim swing switch sword symbol
symptom syrup system table tackle tag tail talent talk tank tape target
task taste tattoo taxi teach team tell ten tenant tennis tent term
test text thank that theme then theory there they thing this thought
three thrive throw thumb thunder ticket tide tiger tilt timber time tiny
tip tired tissue title toast tobacco today toddler toe together toilet token
tomato tomorrow tone tongue tonight tool tooth top topic topple torch tornado
tortoise toss total tourist toward tower town toy track trade traffic tragic
train transfer trap trash travel tray treat tree trend trial tribe trick
trigger trim trip trophy trouble truck true truly trumpet trust truth try
tube tuition tumble tuna tunnel turkey turn turtle twelve twenty twice twin
twist two type typical ugly umbrella unable unaware uncle uncover under undo
unfair unfold unhappy uniform unique unit universe unknown unlock until unusual unveil
update upgrade uphold upon upper upset urban urge usage use used useful
useless usual utility vacant vacuum vague valid valley valve van vanish vapor
various vast vault vehicle velvet vendor venture venue verb verify version very
vessel veteran viable vibrant vicious victory video view village vintage violin virtual
virus visa visit visual vital vivid vocal voice void volcano volume vote
voyage wage wagon wait walk wall walnut want warfare warm warrior wash
wasp waste water wave way wealth weapon wear weasel weather web wedding
weekend weird welcome west wet whale what wheat wheel when where whip
whisper wide width wife wild will win window wine wing wink winner
winter wire wisdom wise wish witness wolf woman wonder wood wool word
work world worry worth wrap wreck wrestle wrist write wrong yard year
yellow you young youth zebra zero zone zoo
""".split()
_WORD_INDEX = {w: i for i, w in enumerate(_BIP39_WORDS)}
assert len(_BIP39_WORDS) == 2048, "BIP39 wordlist must contain exactly 2048 words"

# ---------------------------------------------------------------------------
# Base58 / Base58Check
# ---------------------------------------------------------------------------
_B58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
_B58_INDEX = {c: i for i, c in enumerate(_B58_ALPHABET)}


def _b58decode(text: str) -> bytes:
    num = 0
    for ch in text:
        if ch not in _B58_INDEX:
            raise ValueError(f"invalid base58 character: {ch!r}")
        num = num * 58 + _B58_INDEX[ch]
    raw = num.to_bytes((num.bit_length() + 7) // 8, "big") if num else b""
    pad = len(text) - len(text.lstrip("1"))
    return b"\x00" * pad + raw


def _b58encode(raw: bytes) -> str:
    num = int.from_bytes(raw, "big") if raw else 0
    out = ""
    while num:
        num, rem = divmod(num, 58)
        out = _B58_ALPHABET[rem] + out
    pad = len(raw) - len(raw.lstrip(b"\x00"))
    return "1" * pad + (out or "")


def _sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def _b58check_valid(text: str) -> bool:
    try:
        raw = _b58decode(text)
    except ValueError:
        return False
    if len(raw) < 5:
        return False
    payload, checksum = raw[:-4], raw[-4:]
    return _sha256(_sha256(payload))[:4] == checksum


def _b58check_encode(payload: bytes) -> str:
    return _b58encode(payload + _sha256(_sha256(payload))[:4])


# ---------------------------------------------------------------------------
# RIPEMD-160 (pure Python - hashlib's ripemd160 is not portable across
# OpenSSL 3 builds, and this tool must behave identically on any machine)
# ---------------------------------------------------------------------------
_RMD_R1 = [
    0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15,
    7, 4, 13, 1, 10, 6, 15, 3, 12, 0, 9, 5, 2, 14, 11, 8,
    3, 10, 14, 4, 9, 15, 8, 1, 2, 7, 0, 6, 13, 11, 5, 12,
    1, 9, 11, 10, 0, 8, 12, 4, 13, 3, 7, 15, 14, 5, 6, 2,
    4, 0, 5, 9, 7, 12, 2, 10, 14, 1, 3, 8, 11, 6, 15, 13,
]
_RMD_R2 = [
    5, 14, 7, 0, 9, 2, 11, 4, 13, 6, 15, 8, 1, 10, 3, 12,
    6, 11, 3, 7, 0, 13, 5, 10, 14, 15, 8, 12, 4, 9, 1, 2,
    15, 5, 1, 3, 7, 14, 6, 9, 11, 8, 12, 2, 10, 0, 4, 13,
    8, 6, 4, 1, 3, 11, 15, 0, 5, 12, 2, 13, 9, 7, 10, 14,
    12, 15, 10, 4, 1, 5, 8, 7, 6, 2, 13, 14, 0, 3, 9, 11,
]
_RMD_S1 = [
    11, 14, 15, 12, 5, 8, 7, 9, 11, 13, 14, 15, 6, 7, 9, 8,
    7, 6, 8, 13, 11, 9, 7, 15, 7, 12, 15, 9, 11, 7, 13, 12,
    11, 13, 6, 7, 14, 9, 13, 15, 14, 8, 13, 6, 5, 12, 7, 5,
    11, 12, 14, 15, 14, 15, 9, 8, 9, 14, 5, 6, 8, 6, 5, 12,
    9, 15, 5, 11, 6, 8, 13, 12, 5, 12, 13, 14, 11, 8, 5, 6,
]
_RMD_S2 = [
    8, 9, 9, 11, 13, 15, 15, 5, 7, 7, 8, 11, 14, 14, 12, 6,
    9, 13, 15, 7, 12, 8, 9, 11, 7, 7, 12, 7, 6, 15, 13, 11,
    9, 7, 15, 11, 8, 6, 6, 14, 12, 13, 5, 14, 13, 13, 7, 5,
    15, 5, 8, 11, 14, 14, 6, 14, 6, 9, 12, 9, 12, 5, 15, 8,
    8, 5, 12, 9, 12, 5, 14, 6, 8, 13, 6, 5, 15, 13, 11, 11,
]
_RMD_K1 = [0x00000000, 0x5A827999, 0x6ED9EBA1, 0x8F1BBCDC, 0xA953FD4E]
_RMD_K2 = [0x50A28BE6, 0x5C4DD124, 0x6D703EF3, 0x7A6D76E9, 0x00000000]


def _rol32(x: int, n: int) -> int:
    return ((x << n) | (x >> (32 - n))) & 0xFFFFFFFF


def _rmd_f(j: int, x: int, y: int, z: int) -> int:
    if j < 16:
        return x ^ y ^ z
    if j < 32:
        return (x & y) | (~x & z)
    if j < 48:
        return (x | ~y) ^ z
    if j < 64:
        return (x & z) | (y & ~z)
    return x ^ (y | ~z)


def _ripemd160(data: bytes) -> bytes:
    msg = bytearray(data)
    bit_len = (len(msg) * 8) & 0xFFFFFFFFFFFFFFFF
    msg.append(0x80)
    while len(msg) % 64 != 56:
        msg.append(0x00)
    msg += bit_len.to_bytes(8, "little")

    h0, h1, h2, h3, h4 = 0x67452301, 0xEFCDAB89, 0x98BADCFE, 0x10325476, 0xC3D2E1F0
    for block_off in range(0, len(msg), 64):
        block = msg[block_off:block_off + 64]
        x = [int.from_bytes(block[i * 4:(i + 1) * 4], "little") for i in range(16)]
        a1, b1, c1, d1, e1 = h0, h1, h2, h3, h4
        a2, b2, c2, d2, e2 = h0, h1, h2, h3, h4
        for j in range(80):
            t = (_rol32((a1 + _rmd_f(j, b1, c1, d1) + x[_RMD_R1[j]] + _RMD_K1[j // 16]) & 0xFFFFFFFF,
                        _RMD_S1[j]) + e1) & 0xFFFFFFFF
            a1, e1, d1, c1, b1 = e1, d1, _rol32(c1, 10), b1, t
            t = (_rol32((a2 + _rmd_f(79 - j, b2, c2, d2) + x[_RMD_R2[j]] + _RMD_K2[j // 16]) & 0xFFFFFFFF,
                        _RMD_S2[j]) + e2) & 0xFFFFFFFF
            a2, e2, d2, c2, b2 = e2, d2, _rol32(c2, 10), b2, t
        t = (h1 + c1 + d2) & 0xFFFFFFFF
        h1 = (h2 + d1 + e2) & 0xFFFFFFFF
        h2 = (h3 + e1 + a2) & 0xFFFFFFFF
        h3 = (h4 + a1 + b2) & 0xFFFFFFFF
        h4 = (h0 + b1 + c2) & 0xFFFFFFFF
        h0 = t
    return b"".join(h.to_bytes(4, "little") for h in (h0, h1, h2, h3, h4))


def _hash160(data: bytes) -> bytes:
    return _ripemd160(_sha256(data))


# ---------------------------------------------------------------------------
# secp256k1 (pure Python - derivation only, a handful of point multiplies)
# ---------------------------------------------------------------------------
_SECP_P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
_SECP_N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
_SECP_G = (
    0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798,
    0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8,
)


def _point_add(p1, p2):
    if p1 is None:
        return p2
    if p2 is None:
        return p1
    x1, y1 = p1
    x2, y2 = p2
    if x1 == x2 and (y1 + y2) % _SECP_P == 0:
        return None
    if p1 == p2:
        slope = (3 * x1 * x1) * pow(2 * y1, -1, _SECP_P) % _SECP_P
    else:
        slope = (y2 - y1) * pow(x2 - x1, -1, _SECP_P) % _SECP_P
    x3 = (slope * slope - x1 - x2) % _SECP_P
    y3 = (slope * (x1 - x3) - y1) % _SECP_P
    return (x3, y3)


def _point_mul(k: int, point=_SECP_G):
    result = None
    addend = point
    while k:
        if k & 1:
            result = _point_add(result, addend)
        addend = _point_add(addend, addend)
        k >>= 1
    return result


def _pubkey_compressed(priv: bytes) -> bytes:
    x, y = _point_mul(int.from_bytes(priv, "big"))
    return (b"\x03" if y & 1 else b"\x02") + x.to_bytes(32, "big")


# ---------------------------------------------------------------------------
# Bech32 (BIP173) - encoding for native SegWit addresses + checksum verify
# ---------------------------------------------------------------------------
_BECH32_CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"


def _bech32_polymod(values) -> int:
    chk = 1
    gen = [0x3B6A57B2, 0x26508E6D, 0x1EA119FA, 0x3D4233DD, 0x2A1462B3]
    for v in values:
        top = chk >> 25
        chk = ((chk & 0x1FFFFFF) << 5) ^ v
        for i in range(5):
            if (top >> i) & 1:
                chk ^= gen[i]
    return chk


def _bech32_hrp_expand(hrp: str):
    return [ord(c) >> 5 for c in hrp] + [0] + [ord(c) & 31 for c in hrp]


def _convertbits(data, frombits: int, tobits: int, pad: bool = True):
    acc = 0
    bits = 0
    ret = []
    maxv = (1 << tobits) - 1
    for value in data:
        acc = (acc << frombits) | value
        bits += frombits
        while bits >= tobits:
            bits -= tobits
            ret.append((acc >> bits) & maxv)
    if pad:
        if bits:
            ret.append((acc << (tobits - bits)) & maxv)
    elif bits >= frombits or ((acc << (tobits - bits)) & maxv):
        return None
    return ret


def _bech32_encode(hrp: str, witver: int, witprog: bytes) -> str:
    values = [witver] + _convertbits(witprog, 8, 5)
    const = 1  # bech32 (not bech32m) for witness v0
    polymod = _bech32_polymod(_bech32_hrp_expand(hrp) + values + [0] * 6) ^ const
    checksum = [(polymod >> 5 * (5 - i)) & 31 for i in range(6)]
    return hrp + "1" + "".join(_BECH32_CHARSET[d] for d in values + checksum)


def _bech32_checksum_valid(addr: str) -> bool:
    addr = addr.lower()
    pos = addr.rfind("1")
    if pos < 1 or len(addr) - pos - 1 < 6:
        return False
    hrp = addr[:pos]
    try:
        data = [_BECH32_CHARSET.index(c) for c in addr[pos + 1:]]
    except ValueError:
        return False
    return _bech32_polymod(_bech32_hrp_expand(hrp) + data) == 1


# ---------------------------------------------------------------------------
# BIP39 mnemonic validation + BIP32 derivation
# ---------------------------------------------------------------------------
def mnemonic_checksum_valid(words) -> bool:
    """True iff the word sequence carries a valid BIP39 checksum."""
    if len(words) not in (12, 15, 18, 21, 24):
        return False
    try:
        indices = [_WORD_INDEX[w] for w in words]
    except KeyError:
        return False
    bits = "".join(f"{i:011b}" for i in indices)
    ent_bits = len(bits) * 32 // 33
    ent = int(bits[:ent_bits], 2).to_bytes(ent_bits // 8, "big")
    cs_len = len(bits) - ent_bits
    expected = f"{_sha256(ent)[0]:08b}"[:cs_len]
    return bits[ent_bits:] == expected


def _mnemonic_seed(words, passphrase: str = "") -> bytes:
    password = unicodedata.normalize("NFKD", " ".join(words)).encode("utf-8")
    salt = unicodedata.normalize("NFKD", "mnemonic" + passphrase).encode("utf-8")
    return hashlib.pbkdf2_hmac("sha512", password, salt, 2048, dklen=64)


_HARDENED = 0x80000000


def _ckd_priv(key: bytes, chain: bytes, index: int):
    if index >= _HARDENED:
        data = b"\x00" + key + index.to_bytes(4, "big")
    else:
        data = _pubkey_compressed(key) + index.to_bytes(4, "big")
    digest = _hmac.new(chain, data, hashlib.sha512).digest()
    child = (int.from_bytes(digest[:32], "big") + int.from_bytes(key, "big")) % _SECP_N
    return child.to_bytes(32, "big"), digest[32:]


def _derive_key(seed: bytes, path) -> bytes:
    digest = _hmac.new(b"Bitcoin seed", seed, hashlib.sha512).digest()
    key, chain = digest[:32], digest[32:]
    for index in path:
        key, chain = _ckd_priv(key, chain, index)
    return key


def _p2pkh_address(priv: bytes) -> str:
    return _b58check_encode(b"\x00" + _hash160(_pubkey_compressed(priv)))


def _p2wpkh_address(priv: bytes) -> str:
    return _bech32_encode("bc", 0, _hash160(_pubkey_compressed(priv)))


def derive_first_addresses(words, count: int = 3) -> dict:
    """First `count` receive addresses on the standard BIP44 and BIP84 paths."""
    seed = _mnemonic_seed(words)
    out = {"bip44_p2pkh": [], "bip84_p2wpkh": []}
    for i in range(count):
        k44 = _derive_key(seed, [44 + _HARDENED, _HARDENED, _HARDENED, 0, i])
        out["bip44_p2pkh"].append(_p2pkh_address(k44))
        k84 = _derive_key(seed, [84 + _HARDENED, _HARDENED, _HARDENED, 0, i])
        out["bip84_p2wpkh"].append(_p2wpkh_address(k84))
    return out


# ---------------------------------------------------------------------------
# Candidate validation (form-level mathematics; never touches a network)
# ---------------------------------------------------------------------------
def validate_wif(text: str) -> bool:
    """WIF private key: valid Base58Check, 0x80 prefix, 32-byte key (+optional 0x01)."""
    if not _b58check_valid(text):
        return False
    payload = _b58decode(text)[:-4]
    return payload[0] == 0x80 and len(payload) in (33, 34)


def validate_xkey(text: str) -> bool:
    """Extended key: valid Base58Check wrapping a 78-byte payload."""
    if not _b58check_valid(text):
        return False
    return len(_b58decode(text)) - 4 == 78


def validate_legacy_address(text: str) -> bool:
    if not _b58check_valid(text):
        return False
    payload = _b58decode(text)[:-4]
    return len(payload) == 21 and payload[0] in (0x00, 0x05)


def _mask(secret: str) -> str:
    if len(secret) <= 10:
        return secret[:2] + "..."
    return secret[:4] + "..." + secret[-4:]


# ---------------------------------------------------------------------------
# Search patterns
# ---------------------------------------------------------------------------
_WIF_RE = re.compile(r"\b[5KL][1-9A-HJ-NP-Za-km-z]{50,51}\b")
_HEXKEY_RE = re.compile(r"\b[0-9a-fA-F]{64}\b")
_XKEY_RE = re.compile(r"\b(?:xpub|xprv|ypub|yprv|zpub|zprv)[1-9A-HJ-NP-Za-km-z]{100,110}\b")
_ETH_ADDR_RE = re.compile(r"\b0x[0-9a-fA-F]{40}\b")
_BTC_LEGACY_RE = re.compile(r"\b[13][1-9A-HJ-NP-Za-km-z]{25,34}\b")
_BTC_BECH32_RE = re.compile(r"\bbc1[qpzry9x8gf2tvdw0s3jn54khce6mua7l]{38,58}\b")
_WORD_TOKEN_RE = re.compile(r"[a-z]+")

_METAMASK_ID = "nkbihfbeogaeaoehlefnkodbefgpgknn"
_HASH_CAP = 512 * 1024 * 1024
_CONTENT_CAP = 8 * 1024 * 1024
_CONTENT_EXTS = {
    ".txt", ".md", ".json", ".csv", ".log", ".eml", ".mbox", ".ini",
    ".cfg", ".xml", ".html", ".htm", ".rtf", ".doc",
}

_ARTIFACT_DIRECTIVES = {
    "bitcoin_core_wallet": "Encrypted wallet database. Inspect with the wallet's own software; password recovery is outside this tool's scope.",
    "ethereum_keystore": "Encrypted keystore. Requires the keystore password; recovery is outside this tool's scope.",
    "blockchain_backup": "Encrypted wallet backup. Requires the wallet password; recovery is outside this tool's scope.",
    "password_vault": "Password vault - a common place for stored seed phrases and keys. Open with the vault password and search inside it.",
    "metamask_vault_file": "Browser extension vault data (encrypted). Requires the extension password; recovery is outside this tool's scope.",
    "wallet_file": "Wallet data file. Identify its software and inspect it with that software.",
}


def _artifact_kind(path: Path):
    name = path.name.lower()
    if name == "wallet.dat":
        return "bitcoin_core_wallet"
    if name == "wallet.aes.json":
        return "blockchain_backup"
    if name.startswith("utc--"):
        return "ethereum_keystore"
    if path.suffix.lower() == ".kdbx":
        return "password_vault"
    if path.suffix.lower() == ".wallet":
        return "wallet_file"
    if _METAMASK_ID in str(path) and path.suffix.lower() in (".log", ".ldb", ".sst"):
        return "metamask_vault_file"
    return None


def _file_sha256(path: Path):
    try:
        if path.stat().st_size > _HASH_CAP:
            return None
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return None


def _extract_text(path: Path) -> str:
    if path.suffix.lower() == ".docx":
        try:
            with zipfile.ZipFile(path) as archive:
                xml = archive.read("word/document.xml").decode("utf-8", errors="ignore")
            return re.sub(r"<[^>]+>", " ", xml)
        except (OSError, KeyError, zipfile.BadZipFile):
            return ""
    try:
        return path.read_bytes().decode("utf-8", errors="ignore")
    except OSError:
        return ""


def _bip39_clusters(text: str):
    """Maximal runs of >= 12 consecutive BIP39-list words in the token stream."""
    tokens = _WORD_TOKEN_RE.findall(text.lower())
    clusters = []
    run = []
    for tok in tokens:
        if tok in _WORD_INDEX:
            run.append(tok)
        else:
            if len(run) >= 12:
                clusters.append(run)
            run = []
    if len(run) >= 12:
        clusters.append(run)
    return clusters


_STANDARD_LENGTHS = (24, 21, 18, 15, 12)
_WORDLIST_RUN_THRESHOLD = 36


def _seed_findings(run):
    """Classify one maximal run of BIP39-list words.

    Yields (kind, words, offset) where kind is one of:
      verified            - a standard-length window whose checksum validates
      candidate_checksum  - standard-length run, checksum fails
      candidate_nonstandard - run of a non-standard length, no valid window
      candidate_wordlist  - run too long to be a phrase (a stored wordlist)
    A real phrase is often embedded in prose whose neighbouring words are also
    on the list ("... about - keep safe"), extending the maximal run past the
    phrase itself; hence windows inside the run are tested, not just the run.
    """
    if len(run) > _WORDLIST_RUN_THRESHOLD:
        yield ("candidate_wordlist", run, 0)
        return
    found = []
    seen = set()
    for length in _STANDARD_LENGTHS:
        if length > len(run):
            continue
        for start in range(0, len(run) - length + 1):
            window = tuple(run[start:start + length])
            if window in seen:
                continue
            seen.add(window)
            if mnemonic_checksum_valid(list(window)):
                found.append((window, start))
    if found:
        for window, start in found:
            yield ("verified", list(window), start)
        return
    if len(run) in _STANDARD_LENGTHS:
        yield ("candidate_checksum", run, 0)
    else:
        yield ("candidate_nonstandard", run, 0)


# ---------------------------------------------------------------------------
# The sweep
# ---------------------------------------------------------------------------
def run_sweep(target: Path, address_count: int = 3) -> dict:
    started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    artifacts, verified, candidates, f7 = [], [], [], []
    files_walked = 0
    content_read = 0
    skipped = 0

    def _onerror(_err):
        nonlocal skipped
        skipped += 1

    for dirpath, _dirnames, filenames in os.walk(target, onerror=_onerror):
        for name in filenames:
            path = Path(dirpath) / name
            files_walked += 1

            kind = _artifact_kind(path)
            if kind:
                try:
                    size = path.stat().st_size
                except OSError:
                    size = -1
                artifacts.append({
                    "kind": kind,
                    "path": str(path),
                    "size_bytes": size,
                    "sha256": _file_sha256(path),
                })
                f7.append({
                    "item": f"{kind} at {path}",
                    "directive": _ARTIFACT_DIRECTIVES[kind],
                })

            suffix = path.suffix.lower()
            if suffix not in _CONTENT_EXTS and suffix != ".docx" and suffix != "":
                continue
            try:
                if path.stat().st_size > _CONTENT_CAP:
                    skipped += 1
                    continue
            except OSError:
                skipped += 1
                continue
            text = _extract_text(path)
            if not text:
                continue
            content_read += 1
            source_sha = _file_sha256(path)

            for cluster in _bip39_clusters(text):
                for finding, words_found, offset in _seed_findings(cluster):
                    base = {
                        "type": "bip39_seed_phrase",
                        "source": str(path),
                        "source_sha256": source_sha,
                        "first_word": words_found[0],
                        "word_count": len(words_found),
                    }
                    if finding == "verified":
                        entry = dict(base)
                        entry["checksum"] = "valid"
                        if len(cluster) != len(words_found):
                            entry["found_inside_longer_run"] = {
                                "run_length": len(cluster), "offset": offset}
                        entry["derived_addresses"] = derive_first_addresses(words_found, address_count)
                        entry["derivation_note"] = "BIP44/BIP84 receive addresses, empty passphrase. A BIP39 passphrase, if one was set, yields a different wallet."
                        verified.append(entry)
                    elif finding == "candidate_checksum":
                        entry = dict(base)
                        entry["checksum"] = "invalid"
                        entry["reason"] = "Word sequence is on the BIP39 list but its checksum fails."
                        candidates.append(entry)
                        f7.append({
                            "item": f"seed-phrase candidate ({len(words_found)} words, first word '{words_found[0]}') in {path}",
                            "directive": "Checksum fails as written. Check the source for word order, spelling, or missing/extra words; a corrected sequence can be re-validated.",
                        })
                    elif finding == "candidate_wordlist":
                        entry = dict(base)
                        entry["reason"] = f"Run of {len(words_found)} consecutive list words - consistent with a stored BIP39 wordlist, not a phrase."
                        candidates.append(entry)
                        f7.append({
                            "item": f"wordlist-length run ({len(words_found)} words) in {path}",
                            "directive": "Too long to be a seed phrase; likely a copied wordlist. No window inside it was treated as a phrase.",
                        })
                    else:
                        entry = dict(base)
                        entry["reason"] = f"Non-standard phrase length ({len(words_found)} words)."
                        candidates.append(entry)
                        f7.append({
                            "item": f"word cluster ({len(words_found)} words, first word '{words_found[0]}') in {path}",
                            "directive": "Length is not a standard BIP39 size (12/15/18/21/24). May be a partial phrase or prose coincidence; inspect the source in context.",
                        })

            for match in _WIF_RE.findall(text):
                if validate_wif(match):
                    verified.append({"type": "wif_private_key", "source": str(path),
                                     "source_sha256": source_sha, "masked": _mask(match),
                                     "format": "valid Base58Check (0x80 prefix)"})
                    f7.append({
                        "item": f"WIF private key material in {path}",
                        "directive": "Live key material in a plaintext file. Handle offline; move any funds to a fresh wallet under your control.",
                    })
                else:
                    candidates.append({"type": "wif_like_string", "source": str(path),
                                       "source_sha256": source_sha, "masked": _mask(match),
                                       "reason": "WIF-shaped but fails Base58Check or payload form."})

            for match in _XKEY_RE.findall(text):
                if validate_xkey(match):
                    verified.append({"type": "extended_key", "source": str(path),
                                     "source_sha256": source_sha, "masked": _mask(match),
                                     "key_class": "private (xprv-class)" if "prv" in match[:4] else "public (xpub-class)",
                                     "format": "valid Base58Check, 78-byte payload"})
                    if "prv" in match[:4]:
                        f7.append({
                            "item": f"extended PRIVATE key material in {path}",
                            "directive": "Master key material in a plaintext file. Handle offline; treat every address under it as exposed.",
                        })
                else:
                    candidates.append({"type": "extended_key_like", "source": str(path),
                                       "source_sha256": source_sha, "masked": _mask(match),
                                       "reason": "Extended-key-shaped but fails Base58Check."})

            for match in _HEXKEY_RE.findall(text):
                candidates.append({"type": "hex_64_string", "source": str(path),
                                   "source_sha256": source_sha, "masked": _mask(match),
                                   "reason": "64-hex form matches raw private keys and also SHA-256 hashes; form alone cannot distinguish them."})
                f7.append({
                    "item": f"64-hex string in {path}",
                    "directive": "Cannot be validated from form. Inspect the surrounding context in the source file; if it is a key, its public address can be derived to confirm.",
                })

            seen_addr = set()
            for regex, kind, validator in (
                (_BTC_LEGACY_RE, "bitcoin_address_legacy", validate_legacy_address),
                (_BTC_BECH32_RE, "bitcoin_address_bech32", _bech32_checksum_valid),
            ):
                for match in regex.findall(text):
                    if match in seen_addr:
                        continue
                    seen_addr.add(match)
                    if validator(match):
                        verified.append({"type": kind, "source": str(path),
                                         "source_sha256": source_sha, "address": match,
                                         "format": "valid checksum"})
                    else:
                        candidates.append({"type": kind, "source": str(path),
                                           "source_sha256": source_sha, "address": match,
                                           "reason": "Address-shaped but checksum fails."})
            for match in _ETH_ADDR_RE.findall(text):
                if match not in seen_addr:
                    seen_addr.add(match)
                    candidates.append({"type": "ethereum_address", "source": str(path),
                                       "source_sha256": source_sha, "address": match,
                                       "reason": "Ethereum addresses carry no checksum in lowercase form; a signpost only."})

    finished = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    record = {
        "tool": "wallet_sweep",
        "version": 1,
        "target": str(target),
        "started_utc": started,
        "finished_utc": finished,
        "searched": {
            "files_walked": files_walked,
            "content_files_read": content_read,
            "skipped": skipped,
            "note": "Absence in this record means searched and not found under these patterns - never proof that nothing exists.",
        },
        "artifacts": artifacts,
        "verified": verified,
        "candidates": candidates,
        "f7_register": f7,
    }
    record["summary"] = {
        "artifacts": len(artifacts),
        "verified": len(verified),
        "candidates": len(candidates),
        "f7_open": len(f7),
    }
    return record


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="viper sweep",
        description="Read-only search of a drive or folder for crypto wallet artifacts. Writes a situated case record; secrets are never printed or stored in the record.",
    )
    parser.add_argument("target", help="Drive or folder to search (explicit path, searched read-only).")
    parser.add_argument("--out", default="sweep_record.json", help="Where to write the JSON case record (default: sweep_record.json).")
    parser.add_argument("--addresses", type=int, default=3, help="Receive addresses to derive per validated seed (default: 3).")
    args = parser.parse_args(argv)

    target = Path(args.target)
    if not target.is_dir():
        print(f"[SWEEP] Target is not a readable directory: {target}", file=sys.stderr)
        return 2

    record = run_sweep(target, address_count=max(1, args.addresses))
    out = Path(args.out)
    out.write_text(json.dumps(record, indent=2), encoding="utf-8")

    s = record["summary"]
    print(f"[SWEEP] Target: {target}")
    print(f"[SWEEP] Files walked: {record['searched']['files_walked']}  Content files read: {record['searched']['content_files_read']}  Skipped: {record['searched']['skipped']}")
    print(f"[SWEEP] Artifacts situated: {s['artifacts']}  Verified: {s['verified']}  Candidates: {s['candidates']}  F7 open items: {s['f7_open']}")
    print(f"[SWEEP] Record written: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
