# 07 — Proof-of-Work Code Snippets

These snippets reproduce the **documented model and its verification**. They are
analysis tools that operate on the researcher's own captured data — **not** recovery
tools for third-party wallets. The full GPU scanner is intentionally not published.

## 1. The Firefox 20.0 Math.random core (verified)

```python
MULT, ADD, MASK = 0x5DEECE66D, 0xB, (1 << 48) - 1

def next_double(state):
    state = (state * MULT + ADD) & MASK   # step 1
    hi = state >> 22
    state = (state * MULT + ADD) & MASK   # step 2
    lo = state >> 21
    return state, ((hi << 27) | lo) / (1 << 53)
```

## 2. State recovery from captured doubles (the verification core)

```python
X  = [round(d * (1 << 53)) for d in captured_doubles]
hi = [x >> 27 for x in X]
lo = [x & 0x7FFFFFF for x in X]          # NOTE: mask first — shifting first is a trap

# brute the 21 unknown low bits of S2; lo[0] fixes the top 27
for beta in range(1 << 21):
    S2 = (lo[0] << 21) | beta
    S3 = (S2 * MULT + ADD) & MASK
    if (S3 >> 22) != hi[1]:
        continue
    S4 = (S3 * MULT + ADD) & MASK
    if (S4 >> 21) != lo[1]:
        continue
    break   # S2 found — the full state follows
```

## 3. LCG inversion (seed walk-back)

```python
MINV = pow(MULT, -1, 1 << 48)            # the multiplier is invertible mod 2^48

def step_back(state):
    return ((state - ADD) * MINV) & MASK
```

Walking the recovered state backwards until `state ^ MULT` matched a plausible
browser-launch microsecond yielded the exact seed after 1266 / 1485 steps in two
independent sessions (details in file 01).

## 4. Pool fill (floor == shift — both are equivalent)

```python
# JavaScript: t = Math.floor(65536 * Math.random())
# X is a 53-bit integer, so X / 2^53 is exact and 65536 * (X / 2^53) == X / 2^37.
# Therefore these two forms are IDENTICAL:
t = int(65536.0 * (X / 9007199254740992.0))   # form A
t = X >> 37                                   # form B — same value
```

## 5. The private key from the 33 RC4 bytes

```python
N   = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
raw = int.from_bytes(rc4_bytes[1:33], 'big')   # x[0] is masked to zero
key = (raw % (N - 1)) + 1                       # the raw value is NOT the key
```

## 6. RC4 PRGA (with the classic pitfall)

```python
def rc4_next(S, i, j):
    i = (i + 1) & 255
    j = (j + S[i]) & 255
    t = S[i]                 # capture BEFORE the swap
    S[i], S[j] = S[j], S[i]
    return S[(t + S[i]) & 255]
```

---

Combined with the published test vector (file 03), these snippets let any
independent researcher re-derive the exact WIF and confirm the model.
