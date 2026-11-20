# 01 — The Firefox 20.0 Math.random Model (Empirically Verified)

## 1. The generator

Firefox 20.0 (Linux x86_64, tested in a controlled VM) implements `Math.random()` as the classic
`java.util.Random` linear congruential generator:

```
MULTIPLIER = 0x5DEECE66D
ADDEND     = 0xB
MASK       = (1 << 48) - 1

state[n+1] = (state[n] * MULTIPLIER + ADDEND) & MASK
```

Each call produces a double from **two** state advances:

```
d = ((S1 >> 22) << 27 | (S2 >> 21)) / 2^53
```

where `S1` and `S2` are consecutive LCG states. The 53-bit mantissa is therefore
`(S1 >> 22) << 27 | (S2 >> 21)` — **not** a simple shift of a single state.

## 1a. Build under test and source-verified seeding

- **Build under test:** Firefox 20.0, user-agent
  `Mozilla/5.0 (X11; Linux x86_64; rv:20.0) Gecko/20100101 Firefox/20.0`.
- **Source checked:** the build's `js/src/jsmath.cpp` (retrieved from the Mozilla archive)
  seeds the RNG state **per JSContext** with:

      rngState = (PRMJ_Now() / 1000) ^ (context pointer values)

  where `PRMJ_Now()/1000` is the epoch time in **milliseconds** and the pointer term(s)
  are ASLR-randomized virtual addresses (e.g. the JSContext pointer) that differ on every
  process launch. See Section 2.

## 2. Seeding: milliseconds XOR context pointers — not a pure timestamp

The RNG state lives in the **JSContext** and is seeded once with:

```
rngState = (PRMJ_Now() / 1000) ^ (context pointer values)
```

- `PRMJ_Now()/1000` is the epoch time in **milliseconds** (coarse — roughly 10^3 values
  per second), **not** microseconds.
- The pointer term(s) are **ASLR-randomized virtual addresses** that are re-rolled on every
  process launch and are unpredictable from any timestamp.
- Because of the pointer term, the seed is **not** a function of the launch time alone, and
  it cannot be recovered by walking the LCG backwards to a timestamp.

> **Correction to an earlier draft.** A previous version of this document claimed the seed
> was the browser-launch microsecond (`PRMJ_Now()_µs ^ 0x5DEECE66D`), "recovered" by an
> LCG walk-back that appeared to land on a plausible timestamp after 1266/1485 steps. Peer
> review of the actual jsmath.cpp showed that claim was wrong: the walk-back was a false
> positive of a loose match test (the state was compared against any timestamp in a wide
> window), not the true seed. The corrected, source-verified model is the one above.

## 3. Internal consumption K (not independently measured)

Before the first page script executes, the browser itself consumes some number of
`Math.random()` outputs (UI, chrome, extensions). This work did **not** measure that number
independently: an earlier draft reported K = 633, but that figure was derived from the
discredited seed walk-back (Section 2) and has been removed.

The reproduction in file 08 does **not** use K at all — it starts from the recovered state
S0 (see file 03), so K is irrelevant to the verified result. K would matter only for
forward-modeling the state from a known seed, which is not possible here because the seed
contains the pointer term (Section 2).

## 4. Consequences

1. The wallet-generation time (observable on-chain) is **not** the seed.
2. The seed contains **ASLR-randomized context pointers** that are recorded in none of the
   examined system artifacts (see file 04 for which sources were checked) — so the seed
   cannot be reconstructed from a timestamp, however precise.
3. End-to-end recovery is therefore driven by a **captured PRNG state or captured doubles**
   (see files 02 and 03), not by a timestamp scan.
