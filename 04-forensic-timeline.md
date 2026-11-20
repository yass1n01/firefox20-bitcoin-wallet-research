# 04 — Forensic Reconstruction of a Real Generation Session

A complete case study: reconstructing the morning a set of test wallets was generated,
using only OS boot logs, file timestamps, and the researcher's own notes.

## The evidence

| Source | Evidence |
|---|---|
| `last -x` (wtmp) | Four VM boot sessions that morning |
| Desktop file mtime | `bitaddress.org.html` copied at 11:05:18 local |
| Research note file | `TIMESTAMP_OBSERVED_MS=1794903718521` (11:21:58 local) |
| Note file mtime | saved 11:23:59 local |
| Blockchain record | first activity 11:37:38 local |
| Note content | `INITIAL_WALLET_ON_PAGE_LOAD=YES` (auto-generated, no mouse) |

## Reconstructed timeline (local time)

```
10:49   Boot #1 — VM setup (11 min)
11:02   Boot #2 — bitaddress.org.html copied to Desktop (11:05:18)
11:11   Boot #3 — THE GENERATION SESSION (31 min)
         11:12       login
         11:12–11:21 Firefox launched, page loaded
                     wallet #1 auto-generated 1–6 s after page load (no mouse)
         11:21:58    observation timestamp recorded
         11:23:59    note file saved
11:37:38 first on-chain activity (funding)
11:44   Boot #4 — short session, then long shutdown
```

## Measured vs. inferred

To be precise about evidential strength, the timeline above mixes two kinds of information:

| Item | Status | Source |
|---|---|---|
| Boot / shutdown times (10:49, 11:02, 11:11, 11:44) | **Measured** | `last -x` (wtmp) |
| `bitaddress.org.html` copied 11:05:18 | **Measured** | file mtime |
| Observation timestamp 11:21:58 | **Measured** | researcher's own note (`TIMESTAMP_OBSERVED_MS`) |
| Note file saved 11:23:59 | **Measured** | file mtime |
| First on-chain activity 11:37:38 | **Measured** | blockchain record |
| Firefox launched 11:12–11:21 (9.5-min window) | **Inferred** | between login (measured) and observation (measured) |
| Wallet generated 1–6 s after page load | **Inferred** | bitaddress auto-generation semantics |

Only the seed's **pointer term** (ASLR-randomized context addresses — file 01) is
unobserved; the 9.5-minute launch window is itself an inference bounded by two measured
anchors, but even a microsecond-exact launch time would not recover the seed.

## The decisive missing piece

Everything about the session is now known **except** the seed's unpredictable term. The
seed is `(PRMJ_Now()/1000) ^ (context pointers)` (file 01): the millisecond timestamp is
coarse, and the context-pointer term is ASLR-randomized per launch and recorded in **none**
of the examined artifacts.

```
9.5 minutes ≈ 570,000 possible launch milliseconds
              … but this is irrelevant: the ASLR pointer term is not a function of time
```

**In the artifacts examined** (wtmp — minute precision; the Firefox profile directory,
which had been recreated later; bash history — untimestamped), **no record of the seed's
pointer term was found** — and none is expected, since ASLR re-randomizes it per launch.
A memory dump or a capture of the page's own `Math.random()` outputs would bypass this, but
no such artifact existed in this session. Other environments or forensic sources (audit
logs, crash dumps, filesystem journaling) may behave differently — this conclusion is
scoped to the tested setup.

## Conclusion

This case study demonstrates both sides of the coin:

1. How much can be reconstructed from ordinary system artifacts, and
2. Why the single unrecoverable value — the ASLR-randomized pointer term in the seed — is
   the hard boundary of recovery.

The wallet in this session belongs to the researcher and is used here solely as a controlled
case study. Its identifier is intentionally not published.
