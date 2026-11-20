# 02 — The bitaddress.org v2.4 Wallet Derivation Chain

The complete chain from browser PRNG outputs to the displayed Bitcoin address.
All steps verified against the actual v2.4 source (`securerandom.js` / `jsbn` / `eckey` sections).

## Step 1 — Pool fill (256 bytes)

```
for 128 iterations:
    t = Math.floor(65536 * Math.random())
    pool[2i]   = t >> 8
    pool[2i+1] = t & 255
```

Note: because `d = X / 2^53` is exact (X is a 53-bit integer) and `65536 = 2^16`, the product
`65536 * d = X / 2^37` is exactly representable, so `Math.floor(65536 * d)` is **identical** to
the integer shift `X >> 37`. (An earlier draft incorrectly claimed a rounding difference; the
two operations are equivalent in this model.)

## Step 2 — Initial entropy XORs (pptr = 0 → 12)

```
seedTime():        pool[0..3]  ^= Date.now() at page load    (t0)
seedInt(screenX):  pool[4..7]  ^= window position X
seedInt(screenY):  pool[8..11] ^= window position Y
```

## Step 3 — Mouse entropy (optional, pptr continues)

```
each mousemove event:
    seedTime():           pool[pptr..pptr+3] ^= Date.now()
    seedInt(clientX*clientY): pool[pptr+4..pptr+7] ^= pageX * pageY
```

The XOR **positions depend on how many events occurred** (pptr advances 8 per event after init).

## Step 4 — seedLimit (from the same weak Math.random)

```
12 calls to Crypto.util.randomBytes (one Math.random each):
    seedLimit = 50 + Math.floor(d_12 * 256)
```

The seedLimit byte comes from **the same weak Math.random PRNG** via a simple per-byte
loop — verified empirically: the 12 calls correspond exactly to Math.random outputs
#128–#139 of the page (not to a separate buffered generator).

Note on scope: this is **not** the CryptoJS MWC (`WordArray.random`, illbloom.org /
CVE-2026-71851) — bitaddress v2.4's bundled `Crypto.util.randomBytes` consumes
Math.random directly. The two weaknesses share the same *class* (weak PRNGs feeding
wallet generation) but are technically distinct paths.

## Step 5 — forceGenerate (auto-generation without mouse)

After `seedLimit × 20` ms, if the mouse entropy quota was not met, the auto-generate timer
fires and XORs the timestamp twice:

```
F = t0 + seedLimit*20 + jitter        (jitter ≈ system timer granularity)

seedTime(F):  pool[12..15] ^= F      (no-mouse layout)
seedTime(F):  pool[16..19] ^= F
```

## Step 6 — First getByte: one more seedTime, then ArcFour + pool wipe

The first `getByte()` re-seeds once (its own `Date.now()`, ~1–2 ms later), then builds the
ArcFour state and wipes the pool:

```
getByte() first call:
    seedTime(F3):   pool[20..23] ^= F3   (F3 = F + 1..2 ms)
    state = ArcFour(pool)                → RC4 KSA over the 256-byte pool
    pool[i] = 0 for all i                → THE POOL IS WIPED after use
    33 bytes from RC4 PRGA
```

So the total after the mouse is **three** seedTime XORs (F, F, F3) — two from forceGenerate
and one from getByte — matching the reproduction in file 08.

(Post-generation captures therefore show a zeroed pool re-XORed by later mouse events — a
confusing but correct observation.)

## Step 7 — BigInteger and the private key

```
x = 33 bytes from the RC4 stream
x[0] = 0                         (masked)
raw = big-endian(x[1..32])       (256-bit integer)
key = (raw mod (N - 1)) + 1      (N = secp256k1 order)
```

⚠️ The `mod (N−1) + 1` step is easy to miss — the raw value is not the key.

## Step 8 — WIF encoding

```
WIF = base58check(0x80 || key)     (uncompressed — prefix '5')
```

The leading `5` of every WIF is the **format version byte (0x80)**, not randomness.
