# Data Model: Phone Jam MVP

## JamSettings

How the jam starts (FR-002).

| Field | Type | Rules |
|-------|------|-------|
| mode | `controls` \| `words` \| `playing` | required |
| tempo_bpm | number | 60–200; required before the band starts (set, parsed, or detected) |
| key | string, e.g. `A minor` | 24 major/minor keys |
| style | string, e.g. `blues`, `rock`, `funk` | from a fixed MVP list |
| text | string | only for `words`; parsed server-side into tempo/key/style |
| time_signature | `4/4` | fixed in the MVP |

## JamSession

One jam by one musician (server memory + client state).

| Field | Type | Notes |
|-------|------|-------|
| session_id | string | assigned by server on `ready` |
| settings | JamSettings | fixed once playing (tempo does not follow the musician in MVP) |
| state | enum | see transitions below |
| bars_played | Bar[] | client keeps the last 8 for reconnect |
| detected_chords | ChordEvent[] | from the client, per beat |
| model_context | opaque | server only: token history + KV cache |

State transitions:

```text
connecting → warming → ready → (listening, for mode=playing) → counting_in → playing
playing → stopping → ended            (Stop pressed: finish current bar)
playing → reconnecting → playing      (network gap; rule engine fills bars)
reconnecting → ended                  (> 30 s disconnected, FR-010)
```

## Bar

One bar of band material (FR-006).

| Field | Type | Rules |
|-------|------|-------|
| index | integer | 0 = first bar after count-in; strictly increasing |
| source | `model` \| `rules` | for diagnostics |
| notes | NoteEvent[] | may be empty for a rest bar |

## NoteEvent

| Field | Type | Rules |
|-------|------|-------|
| track | `drums` \| `bass` \| `pad` | |
| pitch | integer 0–127 | drums use General MIDI drum map |
| start_beat | number | 0 ≤ start_beat < 4, relative to the bar start |
| duration_beats | number | > 0; may extend past the bar end for pad |
| velocity | integer 1–127 | |

Timing is in beats, never milliseconds or wall-clock time, so the client alone decides when
sound plays (Constitution I). The server converts Orpheus millisecond timing using the fixed
session tempo.

## ChordEvent

| Field | Type | Rules |
|-------|------|-------|
| bar | integer | bar index the chord was heard in |
| beat | integer 0–3 | |
| chord | string, e.g. `Am`, `G7`, `N` (no chord) | |
| confidence | number 0–1 | client sends only ≥ 0.5 |

## DeviceCalibration (client only, localStorage)

| Field | Type | Notes |
|-------|------|-------|
| output_offset_ms | number | from `outputLatency` + tap bias |
| input_offset_ms | number | for aligning mic analysis to the beat grid |
| measured_at | ISO date | |
| device_label | string | user agent summary |
