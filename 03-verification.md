# 03 — Verification Methodology: Proving the Model End-to-End

## Goal

Prove that the documented chain reproduces a real wallet **exactly** — private key included.

## Controlled setup

- Firefox 20.0 (Linux x86_64) in a private virtual machine
- A local copy of bitaddress.org **v2.4** (self-contained HTML)
- The researcher's own **disposable test wallet, zero funds**

## Capture

A small instrumentation layer (first script in `<head>`) recorded:

1. The first 200 `Math.random()` doubles, with the timestamp of the first call (`t0`)
2. Every subsequent `seedTime()` / `seedInt()` call (value + position)
3. The generated address and WIF

The browser's own pre-page consumption (K) was **not** visible to the page; it is **not
needed** for the reproduction below, which starts from the recovered state S0 (no seed, no K).

## State recovery

From the first captured doubles `d_i`, with `X_i = round(d_i · 2^53)`:

```
hi_i = X_i >> 27            (26 bits of state S_{2i+1})
lo_i = X_i & 0x7FFFFFF      (27 bits of state S_{2i+2})
```

⚠️ The correct extraction of `lo` is `X & 0x7FFFFFF` — shifting first and masking afterwards
is a subtle, costly error.

The full state was recovered by brute-forcing the 21 unknown low bits of `S_2`
(`lo_0` fixes the top 27) and validating against `hi_1`, `lo_1` — 2^21 candidates, seconds of work.

## The PRNG state (S0) is recovered from the captured doubles — not from a timestamp

The end-to-end replay below needs only **S0**, the LCG state at the page's first captured
double, obtained directly from the 2^21 brute force above. It does **not** need the
browser's original seed.

> An earlier draft attempted to walk S0 backwards to a "browser-launch microsecond" seed.
> That step was removed after peer review: the true seed (file 01) is
> `(PRMJ_Now()/1000) ^ context-pointers`, and the walk-back "match" was a false positive of
> a loose test. The verified result below depends only on S0.

## End-to-end replay

With (S0, t0, screen position, the logged event sequence) the full chain was recomputed:

```
pool → XORs → ArcFour → 33 bytes → key = (raw mod (N−1)) + 1 → WIF
```

**Result: the recomputed WIF matched the page-generated WIF character for character.**

## Published test vector (proof of result)

For full reproducibility, the complete input/output of the verification session:

```
Browser            : Firefox 20.0 (X11; Linux x86_64)
Page               : bitaddress.org v2.4 (local file)
Page-load time t0  : 1795157974750 ms  (Date.now at first Math.random call)
Recovered state S0 : 0x75736c04abbb     (from the first four captured doubles)
Window position    : screenX = 70, screenY = 27
Timer jitter dj    : 21 ms
Mouse (1 event)    : seedTime = 1795157974788, product = 157628
Generation         : auto (forceGenerate), seedLimit = 140

Test address       : 13Wn4ESYdNCTM8Cm8y2YJ2non2NCVzjfeQ   (empty, disposable, researcher-owned)
Recomputed WIF     : 5JX94yZLbsATpd4bZFt5FAdvMkRNzVnkzfyCFTFY8522TDVzSVr
                     (matches the page output exactly — wallet has zero funds, do not use)
```

This vector allows any independent researcher to re-derive the same WIF from the
documented chain (files 01 and 02) and confirm the result.

> ⚠️ **WARNING:** This WIF is published publicly. The address `13Wn4ESYdNCTM8Cm8y2YJ2non2NCVzjfeQ`
> **MUST remain empty.** If you send funds to it, they will be swept instantly by anyone
> reading this repository. It is a controlled test vector, **not** a usable wallet.

## Raw captured PRNG values (first 30 doubles, in order)

For state recovery, the first four doubles are sufficient; the rest corroborate. These are
the exact `Math.random()` return values captured at the start of the page (before the pool
fill):

```
0.6916910788095149, 0.9451758520596741, 0.9314258852618196, 0.18539301443526213,
0.7420633179960179, 0.0984684624248714, 0.1649410890090468, 0.2957871441839697,
0.7996298460946578, 0.04157191853491948, 0.5356337484073318, 0.2879753529580368,
0.6092354028686456, 0.5631789131240399, 0.018629148666634343, 0.5418873942900593,
0.11610486026563793, 0.7991190018065383, 0.7771333229256948, 0.8504294933786171,
0.5096784694297047, 0.24064775755930456, 0.9404606355967202, 0.05044307973178974,
0.41638140109094757, 0.6528167084639424, 0.7476857721874515, 0.04276368956336696,
0.04409255086094466, 0.2713631345315918
```

A complete, runnable reproduction script is provided in [`08-reproduce.py`](08-reproduce.py).

## Reproducibility notes

- Float-exact pool fill (`floor(65536 * d)` in double precision)
- RC4 PRGA: capture `t = S[i]` **before** the swap
- XOR positions follow `pptr` (number of mouse events shifts everything)
- The pool is wiped by the first `getByte()` — captures after generation show zeros
