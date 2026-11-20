# 06 — Lessons Learned: Pitfalls in Reproducing 2013-era Browser RNG Chains

Technical pitfalls discovered during this research, in the order they caused damage:

## 1. The seed is the browser launch, not the wallet time

The single most expensive wrong assumption. The thread-local RNG is seeded once at browser
launch (microsecond clock) and shared across the whole browsing session. Any model that
seeds from the wallet's on-chain time searches an empty space.

## 2. `lo` extraction: mask, don't shift

For `X = (hi << 27) | lo`: the correct recovery is `lo = X & 0x7FFFFFF`.
Deriving `lo` by shifting `X` first and masking afterwards produces garbage and silently
wastes hours of debugging.

## 3. Floor and bit-shift are equivalent (correcting an earlier claim)

`Math.floor(65536 * (X / 2^53))` equals `X >> 37` identically: `X` is a 53-bit integer,
`2^53` and `2^16` are powers of two, so the product `X / 2^37` is exactly representable
and no rounding occurs. An early draft of this research claimed the two could differ on
rounding boundaries — that was **wrong**, and the error was corrected after peer review.

## 4. RC4: capture `t` before the swap

In the PRGA, `t = S[i]` must be read **before** swapping `S[i]` and `S[j]`. Reading after
changes the keystream entirely. (The commonly seen `S[(S[i]+S[j]) & 255]` post-swap form is
correct because addition commutes — but any `t`-based variant must respect the order.)

## 5. XOR positions follow pptr

The entropy XORs land at positions determined by how many prior events occurred
(page load → screen → each mouse event → auto-generate chain). Assuming fixed positions
(e.g., always 12–23) breaks whenever the mouse-move count differs.

## 6. The pool is wiped by the first getByte()

bitaddress v2.4 zeroes the pool immediately after initializing ArcFour. Captures taken
after wallet generation show a zeroed pool re-XORed by later events — correct behavior,
but a confusing artifact if expected to be the key material.

## 7. Timer granularity quantizes the jitter

System timers advance in discrete steps (2 ms in the test VM, ~15.6 ms on older Windows).
Jitter parameters are therefore quantized — a useful reduction, easily missed.

## 8. The `mod (N−1) + 1` step

The 256-bit raw value from the RNG is **not** the private key; the key is
`(raw mod (N−1)) + 1`. Skipping this step produces keys that are simply wrong.

## 9. One missing microsecond ended this particular game

The most important lesson: in the tested setup, the session's launch microsecond was
recorded nowhere we looked (boot logs, file mtimes, notes). Those forensic sources
reconstructed everything else — and the search space remained beyond practical GPU time
without that single value. Whether other environments leave such a trace is an open
question, not a settled fact.
