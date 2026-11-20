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

## 1a. Tested build and version caveat

- **Build under test:** Firefox 20.0, user-agent
  `Mozilla/5.0 (X11; Linux x86_64; rv:20.0) Gecko/20100101 Firefox/20.0`.
- **Known version history (Mozilla):** before ~2009 the RNG was seeded per-context with
  `(PRMJ_Now()/1000) ^ context-pointers`; in 2009 it moved to thread-local storage; in
  Firefox 21 it moved again to compartment scope. The model below matches the **2009+
  thread-local** era.
- **Caveat:** the seeding formula is inferred **empirically** (see Section 3) and is
  consistent with the thread-local source, but it was **not** re-verified against the
  exact jsmath.cpp of this build. Readers should pin the exact build before treating the
  formula as source-confirmed.

## 2. Seeding: at browser launch, not page load

The decisive empirical finding:

```
rngState = (PRMJ_Now()_µs ^ 0x5DEECE66D) & MASK
```

- `PRMJ_Now()` returns microseconds since the Unix epoch.
- The RNG is **thread-local** (shared by all pages/scripts on the main thread).
- It is seeded **once, when the browser thread starts** — hours before any wallet page loads.

### Measured evidence (two independent sessions)

| Session | Browser-start seed recovered | Distance to page load |
|---|---|---|
| A | walk-back of **1485** LCG steps (742.5 doubles consumed) | 6.8 hours |
| B | walk-back of **1266** LCG steps (633 doubles consumed) | 12.8 hours |

The seed was recovered by inverting the LCG (the multiplier has an inverse mod 2^48) and
walking the state backwards until it matched a plausible launch microsecond.

## 3. Internal consumption K

Before the first page script executes, the browser itself consumes a roughly constant number
of doubles (UI, chrome, extensions): **K ≈ 600–750** in the tested profile. This consumption
is the reason the page's first `Math.random()` call does **not** start from the seed directly.

## 4. Consequences

1. The wallet-generation time (observable on-chain) is **not** the seed.
2. The seed is the browser-launch microsecond — a value we found recorded in none of the examined system artifacts (see file 04 for which sources were checked).
3. Any recovery attempt must scan a two-dimensional space: launch microsecond × K.
