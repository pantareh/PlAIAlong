# Feature Specification: Phone Jam MVP

**Feature Branch**: `claude/peaceful-cerf-3k6hac`

**Created**: 2026-09-29

**Status**: Draft

**Input**: User description: "Create an MVP for a phone: a musician opens PlAIAlong on their phone,
plays their instrument, and an AI band plays along in time. The phone keeps the beat and makes the
sound; the cloud composes ahead one bar at a time. Web-based (no app install) unless proven
insufficient."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Jam with a band that keeps time (Priority: P1)

A musician opens a link on their phone, puts on headphones, sets up the jam with controls or a short description (see FR-002),
and presses Start. After a short count-in, an AI band starts playing and keeps playing in steady
time, bar after bar, with new material composed as the jam goes on, until the musician presses
Stop. The musician plays along over it.

**Why this priority**: This is the core promise — a band that plays with you, on your phone,
in time. Without it nothing else matters.

**Independent Test**: Open the link on a phone, start a jam at a set tempo and key, and play
along for 5 minutes; the band plays continuously, in time, without gaps, and does not simply
loop the same bar.

**Acceptance Scenarios**:

1. **Given** the musician has opened the link and connected headphones, **When** they press
   Start, **Then** they hear a count-in followed by the band within 10 seconds.
2. **Given** a jam is running, **When** 5 minutes pass, **Then** the band has stayed on the beat
   throughout with no audible gaps, stutters, or drift.
3. **Given** the musician chose to start by just playing, **When** they play a steady groove
   for up to 4 bars, **Then** the band joins at the next bar in the detected tempo and key.
4. **Given** a jam is running, **When** the musician presses Stop, **Then** the band ends at the
   end of the current bar and the session is released.

---

### User Story 2 - The band follows my chords (Priority: P2)

While jamming, the musician plays chords on their instrument into the phone's microphone. The
band listens and adapts: when the musician changes chords, the band's harmony changes to match
within the next bar or two.

**Why this priority**: Following the player is what makes it "playing along" rather than a
backing track, but P1 must work first.

**Independent Test**: Start a jam, then strum a clear chord progression (e.g., four chords, one
per bar); the band's harmony matches the played chords after a delay of at most two bars.

**Acceptance Scenarios**:

1. **Given** a jam is running in one key, **When** the musician switches to a different chord
   and holds it for two bars, **Then** the band's harmony matches that chord by the second bar.
2. **Given** a jam is running, **When** the musician stops playing, **Then** the band keeps
   playing its current groove rather than stopping or glitching.

---

### User Story 3 - Calibrate once so the band sits right on my beat (Priority: P3)

Before the first jam, the musician does a short tap-along: they tap the screen in time with a
click for a few seconds. The app uses this to line the band up with what the musician hears,
and remembers it for that phone.

**Why this priority**: Phones differ in audio delay; without calibration the band may feel
slightly early or late. P1 can ship with a default, so this is a refinement.

**Independent Test**: On a phone, run calibration, then start a jam; the musician reports the
band feels on the beat, and a recording of the headphone output shows band hits aligned with
the beat grid.

**Acceptance Scenarios**:

1. **Given** a first-time user, **When** they open the app, **Then** they are offered
   calibration before their first jam and can skip it.
2. **Given** calibration was completed, **When** the musician returns later on the same phone,
   **Then** the saved calibration is reused without asking again.

---

### Edge Cases

- The network slows or drops for a few seconds mid-jam: the band keeps playing (repeating or
  sustaining its last material) and resumes new material when the connection returns.
- The network is lost for more than 30 seconds: the band finishes the current phrase, stops
  cleanly, and tells the musician the connection was lost.
- The phone screen locks or the musician switches apps: the jam pauses or stops cleanly and can
  be restarted; it never plays garbled audio.
- Headphones are not connected: the musician is warned that the band will leak into the
  microphone and that chord-following may misbehave.
- Microphone permission is denied: the jam still works as in User Story 1, and chord-following
  is reported as unavailable.
- When starting by just playing, the tempo or key cannot be detected within 8 bars: the
  musician is asked to set them with controls instead.
- No cloud capacity is available: the musician is told the band is busy and to try again,
  rather than hearing silence.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Musicians MUST be able to start a jam from a phone's web browser by opening a link,
  with no app installation.
- **FR-002**: Musicians MUST be able to start a jam in any of three ways:
  - **Controls**: pick tempo, key, and style.
  - **Words**: describe it (e.g., "slow blues in A"), which sets tempo, key, and style.
  - **Just playing**: start playing unaccompanied; the band detects tempo and key from the
    musician's opening bars and joins at the next bar.
  Controls and words may be combined (words fill in the controls, which the musician can adjust).
- **FR-003**: The band MUST consist of drums, bass, and a pad (sustained chords).
- **FR-004**: The band MUST play continuously in steady time from the end of the count-in until
  the musician stops the jam.
- **FR-005**: The band's timing MUST NOT depend on network responses; network delays may only
  affect which material plays at an upcoming bar, never when it plays.
- **FR-006**: The system MUST compose new band material during the jam, ahead of playback, in
  one-bar steps, continuing from what has been played so far in that jam.
- **FR-007**: The band MUST keep playing coherent material if new material does not arrive in
  time, and resume new material when it does.
- **FR-008**: The system MUST listen to the musician's instrument through the phone microphone
  and adapt the band's harmony to the chords being played (User Story 2).
- **FR-009**: The system MUST offer a tap-along calibration and store the result on the device
  (User Story 3).
- **FR-010**: The system MUST end a jam and release its cloud resources when the musician stops,
  closes the page, or is disconnected for more than 30 seconds.
- **FR-011**: Access to jams MUST be limited to the project owner (a single private access);
  anyone else opening the link MUST NOT be able to start a jam.
- **FR-012**: The system MUST warn the musician when headphones do not appear to be connected.

### Key Entities

- **Jam Session**: One continuous jam by one musician; has a start setting (tempo, key, style),
  a running history of bars played, the chords detected from the musician, and a start/end time.
- **Bar**: One bar of band material for all band instruments, identified by its position in the
  session; composed ahead of time and scheduled for playback at its bar position.
- **Device Calibration**: The per-phone timing offset measured by the tap-along, stored on the
  device.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A first-time musician goes from opening the link to hearing the band in under
  60 seconds (excluding optional calibration).
- **SC-002**: In a 10-minute jam, band hits stay within 20 ms of the session's beat grid, with
  no audible gaps, on the target test phones.
- **SC-003**: With network interruptions of up to 5 seconds, the band never stops or loses time.
- **SC-004**: When the musician changes chords, the band matches the new chord within two bars
  in at least 80% of changes.
- **SC-005**: In a test with at least 5 musicians, at least 4 describe the band as "in time"
  after calibration.
- **SC-006**: The running cost of one jam-hour stays under $1.

## Assumptions

- The musician uses wired or low-delay headphones; speaker playback is out of scope for the MVP.
- The musician has a stable mobile or Wi-Fi connection during a jam.
- One musician per jam session; multi-player jams are out of scope.
- Recording, saving, or sharing jams is out of scope for the MVP.
- Voice commands (present in the existing desktop prototype) are out of scope for the MVP;
  control is by on-screen buttons.
- The MVP targets Android first (one recent Android phone, Chrome, wired or USB-C headphones);
  iPhone support follows the MVP, as iOS browsers add known microphone and audio restrictions.
- Tempo following (the band speeding up or slowing down with the musician) is out of scope for
  the MVP; the tempo is fixed once the jam starts (set, described, or detected).
- The per-jam cost target (SC-006) is based on estimates from published GPU pricing and must be
  confirmed by measurement during planning.
