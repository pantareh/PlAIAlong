# PlAIAlong Constitution

## Core Principles

### I. Local Timing and Sound

The player's device owns the musical clock and produces all sound locally.

- Beat timing, playback scheduling, and audio synthesis MUST run on the device.
- No audible event MAY wait on a network response; network delay can only change *what* is
  played at a future bar, never *when* it plays.
- If the cloud falls behind or disconnects, the device MUST keep playing coherently (repeat,
  sustain, or fade) rather than stall or drift.

Rationale: phone-to-cloud round trips are tens to hundreds of milliseconds, well above what a
player tolerates for accompaniment timing.

### II. Compose Ahead, One Bar at a Time, as MIDI

The cloud generates the accompaniment ahead of the playhead in one-bar MIDI chunks.

- The unit of generation and delivery is one bar of symbolic (MIDI) data, not rendered audio.
- The device MUST hold a buffer of at least one upcoming bar before it is needed.
- Changes by the player are reflected at the next bar boundary the pipeline can meet.

Rationale: MIDI chunks are small and fast to generate and transmit; bar-sized units keep the
band responsive while keeping the buffer short.

### III. Stateful Session per Jam

Each jam session is served by a dedicated, stateful model instance that keeps the jam's
musical context in memory for the session's lifetime.

- Generation MUST continue from retained context (e.g., cached model state) rather than
  re-sending the full history per request.
- Stateless per-request generation services MUST NOT be used for per-bar generation.

Rationale: stateless APIs re-process context and bill per request, which makes one-bar chunks
slow and expensive; a session-bound model is billed by time regardless of chunk size.

### IV. Measured Before Adopted

No generation model or hosting option is adopted without measured evidence.

- Every candidate MUST be benchmarked for per-bar generation latency (target: comfortably
  under one bar at the target tempo) and for cost per jam-hour.
- Results, setup, and date MUST be recorded in the feature's plan or research notes.
- Unverified figures MUST be labeled as estimates.

Rationale: latency and cost decide whether the product works at all; assumptions are not
enough.

## Technical Constraints

- The device-side client targets mobile phones; the MVP runs in a mobile web browser unless
  measured latency proves a native app is required (see Principle IV).
- The musician uses headphones so accompaniment does not bleed into the input microphone.

## Development Workflow

- Work follows Spec Kit's spec-driven flow: constitution → specify → plan → tasks → implement.
- The project owner approves each stage's artifacts before the next stage starts.
- Plans MUST include a Constitution Check confirming compliance with Principles I–IV, and any
  deviation MUST be justified in the plan's complexity tracking.

## Governance

This constitution supersedes other project practices. Amendments are made by editing this file
with the owner's approval, recording the change in the commit message.

- Versioning follows semantic versioning: MAJOR for removing or redefining a principle, MINOR
  for adding a principle or materially expanding guidance, PATCH for clarifications.
- Every plan and code review verifies compliance with the principles above.

**Version**: 1.0.0 | **Ratified**: 2026-09-29 | **Last Amended**: 2026-09-29
