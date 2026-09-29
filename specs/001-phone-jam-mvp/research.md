# Research: Phone Jam MVP

**Date**: 2026-09-29 · **Feature**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md)

Several vendor sites (huggingface.co, modal.com, runpod.io, MDN, web.dev) were blocked from the
research environment. Items marked **[unverified]** are estimates or come from search snippets and
MUST be confirmed by the benchmarks in R7 before adoption (Constitution IV).

## R1. Generation model: Orpheus Music Transformer

- **Decision**: Use Orpheus (medium variant, ~480M params) as the primary generator, with a
  custom persistent-KV decode loop; keep a rule-based pattern engine as fallback and warm-up.
- **Rationale**:
  - Decoder-only x-transformers model, 8k context, RoPE; weights are a plain PyTorch
    `state_dict` needing the author's `x_transformer_2_3_1.py` (not HF `AutoModel`)
    ([app](https://raw.githubusercontent.com/asigalov61/tegridy-tools/main/Examples/Orpheus_Music_Transformer_Gradio_App_Example.py),
    [xt](https://raw.githubusercontent.com/asigalov61/tegridy-tools/main/tegridy-tools/X-Transformer/x_transformer_2_3_1.py)).
    License Apache-2.0 **[unverified]**.
  - Tokens: 0–255 delta-time (×16 ms), 256–16767 `128*patch+pitch+256` (patch 128 = drums),
    16768–18815 duration×velocity, 18816–18819 SOS/outro/EOS/PAD. ~3 tokens per note. No bar,
    tempo, key or chord tokens — time is absolute ms.
  - Token→MIDI: the app's `save_midi` loop (~40 lines) is portable to per-bar note events.
  - Instrument restriction is possible with token masking (`generate_masked` /
    `forbidden_token_ids` in xt).
  - KV caching exists within one `generate` call but is reset per call; a per-jam session needs
    a custom loop that keeps the cache across bars.
  - Estimated ~60–90 tokens per bar for drums+bass+pad; at ~10–15 ms/token on an L4 that is
    ~0.6–1.3 s per bar for the medium model **[unverified]** — plausible under the 2 s bar at
    120 BPM, tight for the large model.
- **Risks**:
  - No chord/key control tokens: conditioning is only by placing the musician's detected chords
    in the context as notes. It may follow loosely.
  - "Exactly one bar" is not native: the decode loop stops when summed delta-time reaches the
    bar length in ms.
- **Alternatives considered**:
  - Anticipatory Music Transformer ([paper](https://arxiv.org/abs/2306.08620)) — designed for
    accompaniment around control events; best conceptual fit; backup candidate.
  - MIDI-GPT ([repo](https://github.com/Metacreation-Lab/MIDI-GPT)) — per-track, per-bar
    infilling with instrument controls; speed unknown; backup candidate.
  - Hosted music APIs (per-request, audio) — rejected by Constitution III and cost.

## R2. Existing Python code (`ml/src`)

- **Decision**: Build a new `server/` package; port selected logic, do not import `ml/src` as-is.
- **Findings**:
  - `local_generator.py`: Orpheus loading does not work (HF path cannot load it; `.pth` path
    returns `None`, L289–433); token→MIDI is a TODO (L634–639); named-pipe IPC (L458–536) is
    irrelevant to a WebSocket service.
  - `input_listener.py`: chord estimator (L104–127), tempo tracker (L129–166) and activity
    gates (L51–63) are portable; key detection calls a non-existent librosa function (L80) and
    always fails; Whisper is imported at module load.
  - `utils.py`: `InstructionParser` (flan-t5-small, L10–175) is reusable for the "describe it
    in words" start mode.

## R3. Where musician analysis runs

- **Decision**: On the phone. The phone detects chords (per beat), and for "just playing" mode
  tempo and key; it sends compact chord/key/tempo messages to the server, not audio.
- **Rationale**: Tiny uplink, no audio leaves the device, and analysis latency does not include
  the network. The server only needs symbolic context for the model.
- **Alternatives considered**: Stream mic audio to the server and reuse the librosa code —
  rejected (bandwidth, extra latency, more server CPU).

## R4. Mobile web audio (Android first, Pixel 7 + Chrome)

- **Decision**: Mobile web client; Android Chrome first; wired/USB-C headphones required.
- **Rationale**:
  - Scheduled `start(t)` playback is sample-accurate; the residual error is constant output
    latency, removed by tap calibration. Native Android round-trip averaged 39 ms in 2021
    ([Android blog](https://android-developers.googleblog.com/2021/03/an-update-on-androids-audio-latency.html));
    Chrome Web Audio figures were not found — estimate 30–80 ms round-trip **[unverified]**.
  - Chrome honours `echoCancellation/noiseSuppression/autoGainControl: false` **[unverified on
    Pixel 7]**; AudioWorklet supported since Chrome 66 ([caniuse](https://caniuse.com/wf-audio-worklet)).
  - `outputLatency` in Chrome 102+ **[search]**; use it as the calibration starting value.
  - Screen Wake Lock keeps the screen on during a jam
    ([Chrome docs](https://developer.chrome.com/docs/capabilities/web-apis/wake-lock)).
  - Bluetooth adds ~100–300 ms **[unverified]** — out of scope.
- **iOS** (deferred): ignores mic-processing constraints, silent switch mutes Web Audio,
  sample-rate and mic-start bugs ([WebKit 179411](https://bugs.webkit.org/show_bug.cgi?id=179411),
  [264473](https://bugs.webkit.org/show_bug.cgi?id=264473),
  [258864](https://bugs.webkit.org/show_bug.cgi?id=258864)).
- **Alternatives considered**: Native app / Capacitor wrapper — kept as fallback if the Pixel 7
  latency spike fails.

## R5. Client audio and analysis libraries

- **Decision**:
  - Playback: Tone.js synths for bass and pad, a small set of drum one-shot samples
    (Tone.js ~75 KB gzipped **[search]**).
  - Scheduling: lookahead scheduler ("two clocks"): a Worker timer every ~25 ms schedules
    notes due within ~100 ms; bars arrive one or more bars earlier and sit in a queue.
  - Chords: Meyda chroma in an AudioWorklet + chord-template matching.
  - Tempo/key ("just playing"): Essentia.js (WASM, ~2 MB) in a Worker over a rolling 4–8 bar
    buffer ([ISMIR paper](https://transactions.ismir.net/articles/111)).
- **Alternatives considered**: smplr / soundfont-player (heavier sample downloads); porting the
  Python chord/tempo code to JS by hand (more work, less proven).

## R6. GPU hosting

- **Decision**: Modal, one L4 container per jam, WebSocket via FastAPI (`@asgi_app`),
  `max_containers=1`, scale to zero; warm-up request when the page opens.
- **Rationale**: L4 ~$0.80/h + CPU/memory ≈ **$0.85–0.90 per jam-hour**, $0 idle, per-second
  billing, WebSockets supported, 24 h function limit, cold start ~10–30 s **[unverified]**
  ([pricing](https://www.spheron.network/blog/modal-gpu-pricing-2026-per-second-billing/),
  [WebSockets](https://modal.com/blog/websocket-launch)). Meets SC-006 (< $1/jam-hour) on
  estimates.
- **Risk**: GPU containers can be preempted **[search]** — the client reconnects and the server
  rebuilds context from the last bars the client resends.
- **Alternatives considered**:
  - RunPod Pod L4 (~$0.39/h, no preemption, 1–3 min start) — fallback.
  - RunPod Serverless load-balancing endpoint (WebSockets, ~$0.94/h flex) — second fallback.
  - Cloud Run L4 — 60-minute WebSocket cap; rejected. Fly.io GPUs — discontinued.

## R7. Benchmarks required before adoption (Constitution IV)

| ID | Measure | Pass threshold |
|----|---------|----------------|
| B1 | Orpheus medium, per-bar generation time on Modal L4 (drums+bass+pad, persistent KV) | p95 < 1.0 s at 120 BPM |
| B2 | Cold start to first bar on Modal | < 30 s (hidden by warm-up) |
| B3 | Pixel 7 Chrome output latency and tap-calibrated alignment (loopback recording) | hits within 20 ms of grid (SC-002) |
| B4 | Pixel 7 mic with processing disabled: chord detection accuracy on a test progression | ≥ 80% (SC-004) |
| B5 | Cost of a measured 1-hour jam on Modal | < $1 (SC-006) |

If B1 fails: try the rule-based engine as primary with Orpheus for fills, then the backup models
in R1. If B3/B4 fail: evaluate a native/Capacitor Android build.
