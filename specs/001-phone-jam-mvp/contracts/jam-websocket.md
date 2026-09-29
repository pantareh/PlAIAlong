# Contract: Jam WebSocket

One WebSocket per jam between the phone client and the GPU service. JSON text frames, each with a
`type` field. Entities are defined in [data-model.md](../data-model.md).

**Endpoint**: `wss://<modal-app-host>/jam` · **Warm-up**: `GET https://<modal-app-host>/warm`
(no body; starts a container; returns `204` when the model is loaded)

## Client → Server

| type | Fields | When |
|------|--------|------|
| `hello` | `token`, `settings: JamSettings`, `resume?: { session_id, last_bars: Bar[] }` | First frame. Server closes with code 4401 if `token` is wrong (FR-011). |
| `detected` | `tempo_bpm`, `key` | `mode=playing` only, once tempo/key are detected. |
| `chords` | `events: ChordEvent[]` | Every beat or batched per bar. |
| `need` | `up_to_bar` | Client asks for bars through this index (playhead + 2). |
| `stop` | — | Musician pressed Stop. |

## Server → Client

| type | Fields | When |
|------|--------|------|
| `status` | `state` (`warming` \| `ready` \| `busy`), `detail?` | Any time. `busy` = no GPU capacity. |
| `ready` | `session_id`, `settings: JamSettings` (resolved tempo/key/style) | Model loaded and settings resolved (e.g. parsed from `words`). |
| `bar` | `bar: Bar` | One per requested bar, in index order. |
| `error` | `code`, `message` | Recoverable errors; fatal ones close the socket. |

## Rules

1. The server MUST never send wall-clock times; note timing is in beats within a bar.
2. The server MUST generate bars in index order and include each bar's `index`; the client
   discards bars whose index is at or behind the playhead.
3. If a `bar` for the next index has not arrived one lookahead window (~100 ms) before it is
   due, the client plays a `rules` bar locally; a later-arriving model bar for that index is
   discarded.
4. Chords heard in bar *n* condition bars *n+2* onward (one bar of generation lag + one bar of
   buffer).
5. On disconnect, the client reconnects with `resume` including its last 8 bars; the server
   rebuilds model context from them. After 30 s without a connection the client ends the jam.
6. On `stop`, the server sends no further bars and releases the session; the container scales
   to zero after its idle window.

## Close codes

| Code | Meaning |
|------|---------|
| 1000 | Normal end (stop) |
| 4401 | Bad or missing access token |
| 4409 | Another jam is already running (single-session MVP) |
| 4500 | Server error; client may retry with `resume` |
