#!/usr/bin/env python3
"""
Complete end-to-end reproduction of the published test vector.

Given only the raw captured Math.random() doubles and the published session
parameters, this script:
  1. recovers the LCG state S0 (2^21 brute force over the low bits),
  2. re-derives the pool, ArcFour keystream, private key and WIF,
  3. asserts the WIF matches the published value.

The reproduction depends only on S0 — the LCG state at the page's first captured
double — recovered directly from the doubles. It does NOT recover the browser's
original seed; that seed is (PRMJ_Now()/1000) ^ (context pointers) (file 01) and
is not needed here.

Run:  python3 08-reproduce.py
Expected output ends with:  MATCH: True
"""

import hashlib

MULT, ADD, MASK = 0x5DEECE66D, 0xB, (1 << 48) - 1
MINV = pow(MULT, -1, 1 << 48)
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
B58 = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'

# ---- Published inputs (see 03-verification.md) ----
mr = [
    0.6916910788095149, 0.9451758520596741, 0.9314258852618196, 0.18539301443526213,
    0.7420633179960179, 0.0984684624248714, 0.1649410890090468, 0.2957871441839697,
    0.7996298460946578, 0.04157191853491948, 0.5356337484073318, 0.2879753529580368,
    0.6092354028686456, 0.5631789131240399, 0.018629148666634343, 0.5418873942900593,
    0.11610486026563793, 0.7991190018065383, 0.7771333229256948, 0.8504294933786171,
    0.5096784694297047, 0.24064775755930456, 0.9404606355967202, 0.05044307973178974,
    0.41638140109094757, 0.6528167084639424, 0.7476857721874515, 0.04276368956336696,
    0.04409255086094466, 0.2713631345315918,
]
t0 = 1795157974750                 # Date.now() at the first Math.random call
sx, sy = 70, 27                    # window position
m_st, m_prod = 1795157974788, 157628   # single mousemove: seedTime, clientX*clientY
dj, intra = 21, 1                  # timer jitter, getByte seedTime offset
EXPECTED_WIF = '5JX94yZLbsATpd4bZFt5FAdvMkRNzVnkzfyCFTFY8522TDVzSVr'

def b58check(payload):
    h = hashlib.sha256(hashlib.sha256(payload).digest()).digest()
    n = int.from_bytes(payload + h[:4], 'big')
    s = ''
    while n:
        n, r = divmod(n, 58)
        s = B58[r] + s
    return s

# ---- 1. Recover the LCG state from the first four doubles ----
X = [round(d * (1 << 53)) for d in mr]
hi = [x >> 27 for x in X]
lo = [x & 0x7FFFFFF for x in X]

S2 = None
for beta in range(1 << 21):
    s2 = (lo[0] << 21) | beta
    s3 = (s2 * MULT + ADD) & MASK
    if (s3 >> 22) != hi[1]:
        continue
    s4 = (s3 * MULT + ADD) & MASK
    if (s4 >> 21) != lo[1]:
        continue
    S2 = s2
    break
assert S2 is not None, "state recovery failed"
S1 = ((S2 - ADD) * MINV) & MASK
S0 = ((S1 - ADD) * MINV) & MASK
print("recovered state S0 =", hex(S0))

# ---- 2. Re-derive the pool and WIF (forward) ----
state = S0
pool = [0] * 256
for i in range(128):
    state = (state * MULT + ADD) & MASK
    hh = state >> 22
    state = (state * MULT + ADD) & MASK
    ll = state >> 21
    t = ((hh << 27) | ll) >> 37
    pool[2 * i] = (t >> 8) & 255
    pool[2 * i + 1] = t & 255

seed_limit = 0
for i in range(12):
    state = (state * MULT + ADD) & MASK
    hh = state >> 22
    state = (state * MULT + ADD) & MASK
    ll = state >> 21
    if i == 11:
        seed_limit = 50 + (((hh << 27) | ll) >> 45)

pptr = 0
def seed_int(x):
    global pptr
    pool[pptr] ^= x & 255; pptr += 1
    pool[pptr] ^= (x >> 8) & 255; pptr += 1
    pool[pptr] ^= (x >> 16) & 255; pptr += 1
    pool[pptr] ^= (x >> 24) & 255; pptr += 1
    if pptr >= 256:
        pptr -= 256

seed_int(t0); seed_int(sx); seed_int(sy)      # page load: seedTime + screenX + screenY
seed_int(m_st); seed_int(m_prod)              # one mouse event: seedTime + clientX*clientY
F = t0 + seed_limit * 20 + dj                 # forceGenerate timestamp (seedLimit*20 + jitter)
seed_int(F); seed_int(F)                      # forceGenerate: two seedTime(F) calls
seed_int(F + intra)                           # getByte() first call: one seedTime ~1-2 ms later, then ArcFour

S = list(range(256))
j = 0
for i in range(256):
    j = (j + S[i] + pool[i]) & 255
    S[i], S[j] = S[j], S[i]
rc4 = []
ai = aj = 0
for _ in range(33):
    ai = (ai + 1) & 255
    aj = (aj + S[ai]) & 255
    S[ai], S[aj] = S[aj], S[ai]
    rc4.append(S[(S[ai] + S[aj]) & 255])

raw = int.from_bytes(bytes(rc4[1:33]), 'big')
key = (raw % (N - 1)) + 1
kb = key.to_bytes(32, 'big')   # fixed 32-byte width; leading zero bytes are KEPT (WIF needs them)
wif = b58check(b'\x80' + kb)

print("recomputed WIF =", wif)
print("MATCH:", wif == EXPECTED_WIF)
assert wif == EXPECTED_WIF, "WIF mismatch"
