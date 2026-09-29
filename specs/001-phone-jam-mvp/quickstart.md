# Quickstart & Validation: Phone Jam MVP

How to run the MVP and prove it meets the spec. See [plan.md](./plan.md) for structure and
[contracts/jam-websocket.md](./contracts/jam-websocket.md) for the protocol.

## Prerequisites

- Google Pixel 7 with Chrome, wired or USB-C headphones
- A Modal account with the CLI authenticated (`modal token new`)
- The Orpheus medium checkpoint (`.pth`) uploaded to a Modal volume
- An access token stored as a Modal secret (owner-only access)
- Node 20+ (client build), Python 3.11 (server)

## Run

1. Deploy the server: `modal deploy server/app.py` → note the app URL.
2. Build and host the client: `cd web && npm install && npm run build`, then serve `web/dist`
   over HTTPS (mic access requires a secure context), with the server URL configured.
3. On the Pixel 7, open the client URL, enter the access token once, allow the microphone.

## Validation scenarios

| # | Scenario | Steps | Expected | Covers |
|---|----------|-------|----------|--------|
| V1 | Start with controls | Pick 100 BPM, A minor, blues → Start | Count-in, band within 10 s (warm) | US1, SC-001 |
| V2 | Start with words | Type "slow funk in E" → Start | Controls fill in; band plays in E at a slow tempo | FR-002 |
| V3 | Just playing | Choose "Just play", strum a steady groove | Band joins within 4 bars in your tempo/key | FR-002, US1 |
| V4 | Keeps time | Jam 10 min; record headphone output via loopback | Hits within 20 ms of grid; no gaps | SC-002 |
| V5 | Follows chords | Play Am–F–C–G, one chord per bar, 8 times | Band harmony matches within 2 bars, ≥ 80% of changes | US2, SC-004 |
| V6 | Network gap | Toggle airplane mode for 5 s mid-jam | Band never stops or loses time; new material resumes | SC-003 |
| V7 | Long disconnect | Airplane mode for 40 s | Band ends the phrase and reports connection lost | FR-010 |
| V8 | Calibration | Run tap-along, reload page | Calibration reused without asking | US3 |
| V9 | Access | Open the link on another device without the token | Cannot start a jam | FR-011 |
| V10 | Cost | Check Modal usage after a 1-hour jam | < $1 | SC-006 |

## Benchmarks (run before building past the spike)

- B1/B2/B5: `modal run server/bench/bench_bar_latency.py` — prints per-bar p50/p95 and cold
  start; pass thresholds in [research.md](./research.md#r7-benchmarks-required-before-adoption-constitution-iv).
- B3/B4: `web` → `/lab` page on the Pixel 7 — latency loopback test and chord-detection test.
