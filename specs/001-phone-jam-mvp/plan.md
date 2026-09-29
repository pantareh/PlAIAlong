# Implementation Plan: Phone Jam MVP

**Branch**: `claude/peaceful-cerf-3k6hac` | **Date**: 2026-09-29 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-phone-jam-mvp/spec.md`

## Summary

A musician opens a web page on an Android phone (Pixel 7, Chrome, wired headphones) and jams with
an AI band (drums, bass, pad). The phone owns the clock and synthesizes all sound locally; it
analyses the musician's playing (chords; tempo and key in "just playing" mode) and sends compact
symbolic context over a WebSocket. A Python service on a Modal L4 GPU holds one stateful Orpheus
session per jam and streams one bar of MIDI at a time, two bars ahead of the playhead. A
rule-based pattern engine covers warm-up and any late bar. The existing C++ audio engine is not
used in the MVP. See [research.md](./research.md).

## Technical Context

**Language/Version**: TypeScript 5 (phone client); Python 3.11 (cloud service)

**Primary Dependencies**:
- Client: Vite, Tone.js, Meyda, Essentia.js
- Server: FastAPI (WebSocket), Modal, PyTorch 2.x, vendored `x_transformer_2_3_1.py` and
  TMIDIX helpers from tegridy-tools, transformers (flan-t5-small for text prompts)

**Storage**: Phone `localStorage` for calibration and access token; no server-side persistence
(session state lives in GPU memory for the jam's lifetime)

**Testing**: Vitest (client units: scheduler, chord matcher, protocol); pytest (server units:
token↔note codec, bar termination, rule engine, protocol); benchmark scripts B1–B5
(research R7)

**Target Platform**: Android Chrome on Pixel 7 (client); Modal L4 GPU container (server)

**Project Type**: Web application (static web client + WebSocket GPU service)

**Performance Goals**: per-bar generation p95 < 1.0 s at 120 BPM; band hits within 20 ms of the
beat grid; first sound < 60 s from opening the link

**Constraints**: no audible event waits on the network; ≥ 1 bar buffered (target 2); survives
5 s network gaps; < $1 per jam-hour; owner-only access

**Scale/Scope**: 1 musician, 1 concurrent jam, sessions 10–60 min

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | How the design complies |
|-----------|--------|-------------------------|
| I. Local timing and sound | PASS | Phone runs the clock (Web Audio), lookahead scheduler and synths; network data only fills the bar queue. Empty queue → rule engine plays the bar. |
| II. Compose ahead, one bar, MIDI | PASS | Server sends one `bar` message per bar as note events; client requests bars up to 2 ahead of the playhead. |
| III. Stateful session per jam | PASS | One Modal container per jam keeps the Orpheus KV cache across bars; no per-request generation service. |
| IV. Measured before adopted | PASS (gated) | Orpheus, Modal and the web client are adopted provisionally; benchmarks B1–B5 in research R7 must pass before `/speckit-implement` builds past the spike tasks. |

**Post-design re-check (after Phase 1)**: PASS — the contracts carry bar indexes and note
timings in beats, never wall-clock play times, so the network cannot dictate *when* sound plays.

## Project Structure

### Documentation (this feature)

```text
specs/001-phone-jam-mvp/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── jam-websocket.md # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
web/                         # Phone client (static site)
├── src/
│   ├── audio/               # AudioContext setup, scheduler, synths (drums/bass/pad)
│   ├── analysis/            # mic capture, chord matcher (Meyda), tempo/key (Essentia.js worker)
│   ├── session/             # WebSocket client, bar queue, reconnect
│   ├── fallback/            # rule-based pattern engine (shared behaviour with server)
│   └── ui/                  # start screen (controls / words / just play), calibration, status
└── tests/

server/                      # Cloud GPU service (Python)
├── app.py                   # Modal app + FastAPI WebSocket endpoint
├── session.py               # JamSession: context, bar loop, lifecycle
├── generator/
│   ├── orpheus.py           # model load + persistent-KV per-bar decode with patch masking
│   ├── codec.py             # Orpheus tokens <-> note events (port of save_midi/load_midi)
│   └── rules.py             # rule-based pattern engine
├── prompt.py                # text → tempo/key/style (port of ml/src/utils.py InstructionParser)
├── vendor/                  # x_transformer_2_3_1.py, TMIDIX.py (tegridy-tools)
├── bench/                   # B1, B2, B5 benchmark scripts
└── tests/

audio_engine/, shared/       # C++ desktop engine — unchanged, not used by the MVP
ml/                          # Desktop prototype — source for ported logic, unchanged
```

**Structure Decision**: Two new top-level projects, `web/` and `server/`, next to the existing
desktop prototype. Porting rather than importing `ml/src` avoids its broken model loader, C++ IPC
and heavy Whisper import (research R2).

## Complexity Tracking

| Addition | Why Needed | Simpler Alternative Rejected Because |
|----------|------------|-------------------------------------|
| Rule-based engine on both client and server | Covers warm-up and late bars without breaking Principle I | Silence or looping one bar on a late bar is audible and fails SC-003 |
