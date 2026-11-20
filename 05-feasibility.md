# 05 — Feasibility Analysis: Why Blind Recovery Is Infeasible

## The two recovery models

### Model A — Firefox 20 (documented here)

```
seed = (PRMJ_Now()/1000) ^ (context pointers)     — see file 01
```

| Component | Uncertainty |
|---|---|
| Millisecond timestamp | coarse (~10^3 per second), bounded to minutes by session evidence |
| Context pointer(s) (ASLR) | per-launch pointer entropy (typically tens of bits on x86_64 — **not measured in this environment**) |
| Internal consumption K | not independently measured in this work; irrelevant once the state is captured |
| Page-load time | bounded by `seedLimit × 20` ≈ 1–6 s after load |
| Timer jitter | quantized by system timer resolution (2 ms in the test VM) |

The seed is **not a function of time alone**: it includes ASLR-randomized pointer values
that a timestamp, however precise, does not determine. In this experiment the artifacts
available were **not sufficient** to recover those pointer values; whether another
environment leaves them recoverable (memory dump, crash dump) is an open question. A
"µs × K" scan (an earlier, incorrect framing) does not apply.

### Model B — Chrome-era MWC (verified separately)

```
search space = 1.2 × 10^9 MWC states × time window
```

The state space is fixed (~7 minutes of GPU per time-second at ~2.9 M/s), so recovery is
**practical only with a tight time window** (seconds to minutes around a known generation
time). A full-era scan (years × 1.2 × 10^9 × per-second cost) remains centuries.

## The information-theoretic boundary

A Bitcoin address is `RIPEMD160(SHA256(pubkey))` — 160 bits. The private key is 256 bits.
The hash **destroys 96 bits of information irreversibly**: ~2^96 distinct private keys map
to every address, so the address can never be inverted to a unique key.

Two distinct situations must not be conflated:

- **Truly random key (2^256 space):** the address offers no shortcut — enumeration of the
  full key space is infeasible regardless of hardware.
- **Weak-PRNG key (small space, e.g. the documented LCG/MWC):** the address *is* the
  verification oracle — candidates drawn from the small space are simply enumerated and
  checked against it (this is exactly what the recovery model does). The address lets you
  **check** a candidate in O(1); it does not let you **skip** candidates.

The 96-bit loss therefore bounds the *weak-PRNG* problem, not the key space itself: the
search cost is the size of the PRNG seed space, and the address is the check, not a key
reconstruction. No known technique (GPU, ASIC, batch inversion, affine hops) reduces the
seed-space enumeration below its intrinsic size — batch inversion only lowers the constant
factor (~1.5–2×), not the exponent.

## When recovery IS feasible

| Condition | Result |
|---|---|
| Captured PRNG state / doubles (Firefox model) | state recovery + replay = exact WIF (minutes, CPU) |
| Known generation time ± seconds (Chrome model) | MWC state scan completes in hours |
| No captured state, no session evidence (tested setup) | Not achieved — the available artifacts were insufficient to recover the seed's pointer term |

## Measurement conditions (GPU)

The throughput figures are **measured on a single card**, not general benchmarks:

| Property | Value |
|---|---|
| GPU | NVIDIA RTX 4070 Super (sm_89) |
| Full derivation rate (Firefox pipeline) | 2.7–4.0 M keys/s |
| Full derivation rate (Chrome MWC pipeline) | ~2.9 M keys/s |
| Method | CUDA kernels: LCG/MWC fill → ArcFour → secp256k1 scalar mult (window-4/5) → SHA256+RIPEMD160 → target compare |

Rates are end-to-end (key derivation + address hashing + comparison), timed over
repeated full-space chunks, and are reported here as **conditional estimates** for that
specific card — not as universal figures.

## Scope note

The infeasibility estimates above are based on measurements from **one controlled
environment** (a single virtual machine, Firefox 20.0 on Linux x86_64, K not
independently measured, a ~10-minute launch window, the GPU listed above). They should be read as
*"infeasible under these conditions"* — not as a universal impossibility proof for
every environment, browser build, or future hardware. The information-theoretic
boundary (Section "The information-theoretic boundary") is the only claim that is
independent of such conditions, as it follows directly from the hash sizes.

## Conclusion

The weakness is real and fully characterized. In the tested environment its exploitation
window is the **captured PRNG state / documented session**; whether other environments
leave recoverable traces of the seed (a memory dump, a captured `Math.random()` stream, or
a crash dump) is an open question for further research. This is consistent with the
original Randstorm disclosure: recovery targeted wallets whose creation context was known,
not arbitrary historical addresses.
