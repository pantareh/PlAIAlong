"""
Utility functions for PlAIAlong ML Layer.
"""
import torch
from transformers import pipeline
import re
import json
from typing import Dict, Any

class InstructionParser:
    """Uses a local LLM to parse musical instructions into structured data."""
    
    def __init__(self, model_id: str = "google/flan-t5-small"):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        # For Intel Arc, we use CPU for now as IPEX requires specific setup, 
        # but T5-small is very fast on your Core Ultra CPU.
        self.pipe = pipeline(
            "text2text-generation", 
            model=model_id, 
            device=-1 if self.device == "cpu" else 0
        )
        
        self.keys = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

    def parse(self, instruction: str) -> Dict[str, Any]:
        """
        Extract key, mood, and tempo from natural language using LLM.
        """
        # Request JSON format for structured output
        prompt = (
            f"Extract musical parameters from: '{instruction}'\n"
            "Return JSON format: {{\"key\": \"C\", \"mood\": \"happy\", \"tempo\": 120}}"
        )
        
        # Use max_new_tokens to avoid warnings
        result = self.pipe(prompt, max_new_tokens=100, num_return_sequences=1)[0]['generated_text']
        
        # Try to parse as JSON first
        parsed = self._try_parse_json(result, instruction)
        if parsed:
            parsed['instruction'] = instruction
            parsed['raw_llm_output'] = result
            return parsed
        
        # Fallback to regex-based extraction if JSON parsing fails
        return {
            'key': self._extract_key(result, instruction),
            'mood': self._extract_mood(result, instruction),
            'tempo': self._extract_tempo(result, instruction),
            'instruction': instruction,
            'raw_llm_output': result
        }
    
    def _try_parse_json(self, text: str, original: str) -> Dict[str, Any] | None:
        """Try to extract and parse JSON from LLM output."""
        # Look for JSON object in the text
        json_match = re.search(r'\{[^}]+\}', text)
        if json_match:
            try:
                json_str = json_match.group(0)
                data = json.loads(json_str)
                
                # Validate and convert to expected format
                result = {}
                
                # Extract key (convert note name to index)
                key_value = data.get('key', '')
                if isinstance(key_value, str):
                    # Remove "major" or "minor" and clean up
                    key_str = key_value.upper().replace('MAJOR', '').replace('MINOR', '').strip()
                    # Extract just the note name (e.g., "A" from "A minor" or "A#")
                    key_match = re.match(r'([A-G][#b]?)', key_str)
                    if key_match:
                        key_str = key_match.group(1)
                    
                    if key_str in self.keys:
                        result['key'] = self.keys.index(key_str)
                    else:
                        result['key'] = self._extract_key(text, original)
                else:
                    result['key'] = self._extract_key(text, original)
                
                # Extract mood - trust the LLM's extraction, just normalize case
                mood = data.get('mood', '').strip().lower()
                if mood:
                    result['mood'] = mood
                else:
                    result['mood'] = self._extract_mood(text, original)
                
                # Extract tempo
                tempo = data.get('tempo')
                if isinstance(tempo, int) and 40 <= tempo <= 200:
                    result['tempo'] = tempo
                elif isinstance(tempo, str) and tempo.isdigit():
                    result['tempo'] = int(tempo)
                else:
                    result['tempo'] = self._extract_tempo(text, original)
                
                return result
            except (json.JSONDecodeError, KeyError, ValueError):
                pass
        
        return None

    def _extract_key(self, llm_text: str, original: str) -> int:
        # Check KEY: line first (if LLM used structured format)
        match = re.search(r"KEY:\s*([A-Ga-g][#b]?)", llm_text, re.IGNORECASE)
        if match:
            key_str = match.group(1).upper()
            if key_str in self.keys:
                return self.keys.index(key_str)
        
        # Fallback: search both LLM text and original instruction for keys
        combined = (llm_text + " " + original).upper()
        
        # First, check for patterns like "A minor", "C major", etc. (most specific)
        key_match = re.search(r'\b([A-G][#b]?)\s+(minor|major)', combined, re.IGNORECASE)
        if key_match:
            key_str = key_match.group(1).upper()
            if key_str in self.keys:
                return self.keys.index(key_str)
        
        # Then search for keys with word boundaries to avoid partial matches
        # Search for longer names first to avoid "A" matching "A#"
        sorted_keys = sorted([(k, i) for i, k in enumerate(self.keys)], key=lambda x: len(x[0]), reverse=True)
        for k, i in sorted_keys:
            # Use word boundary to match whole words only (avoids matching "A" inside "MAJOR")
            pattern = r'\b' + re.escape(k) + r'\b'
            if re.search(pattern, combined):
                return i
        
        return 0  # Default to C

    def _extract_mood(self, llm_text: str, original: str) -> str:
        # Check MOOD: line first (if LLM used structured format)
        match = re.search(r"MOOD:\s*([^\n,]+)", llm_text, re.IGNORECASE)
        if match:
            return match.group(1).strip().lower()
        
        # Fallback: extract any descriptive adjective from the original instruction
        # This is a minimal heuristic - the LLM should handle most cases via JSON
        # Look for common emotional/mood descriptors in the instruction
        words = original.lower().split()
        # Common mood descriptors (non-exhaustive, just for fallback)
        mood_keywords = ['happy', 'sad', 'energetic', 'calm', 'dark', 'bright', 
                        'peaceful', 'intense', 'melancholic', 'joyful', 'somber',
                        'playful', 'serious', 'relaxing', 'aggressive', 'gentle']
        
        for word in words:
            if word in mood_keywords:
                return word
        
        return 'neutral'  # Default if nothing found

    def _extract_tempo(self, llm_text: str, original: str) -> int:
        # Check TEMPO: line first
        match = re.search(r"TEMPO:\s*(\d+)", llm_text)
        if match:
            return int(match.group(1))
        
        # Fallback: look for keywords in original text
        combined = (llm_text + " " + original).lower()
        if any(w in combined for w in ['fast', 'upbeat', 'energetic']):
            return 140
        if any(w in combined for w in ['slow', 'sad', 'calm']):
            return 80
        
        # Last resort: find any number
        nums = re.findall(r"\d+", llm_text)
        if nums:
            return int(nums[0])
        return 120

# Singleton instance for easy access
_parser = None

def parse_text_instruction(instruction: str) -> dict:
    """Global utility function that uses the LLM parser."""
    global _parser
    if _parser is None:
        print("Initializing LLM Instruction Parser (this may take a moment on first run)...")
        _parser = InstructionParser()
    return _parser.parse(instruction)


def parse_midi_file(midi_path: str) -> str:
    """
    Parse a MIDI file and return a tab-separated table format.
    
    Args:
        midi_path: Path to the MIDI file
        
    Returns:
        Tab-separated table string describing the MIDI file contents
    """
    import mido
    
    try:
        mid = mido.MidiFile(midi_path)
        
        lines = []
        lines.append(f"MIDI File: {midi_path}")
        lines.append(f"Ticks per beat: {mid.ticks_per_beat}\tNumber of tracks: {len(mid.tracks)}\tType: {mid.type}")
        lines.append("")
        
        # Note names for readability
        note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        
        # Table header
        header = "Time(s)\tTrack\tType\tNote\tMIDI\tVelocity\tChannel\tDuration(s)\tInfo"
        lines.append(header)
        lines.append("-" * len(header))
        
        for track_idx, track in enumerate(mid.tracks):
            tempo = 500000  # Default tempo (120 BPM)
            current_time = 0.0  # Time in seconds
            time_signature = (4, 4)  # Default time signature
            
            notes_on = {}  # Track notes currently playing: {note: start_time}
            
            for msg in track:
                # Update time based on delta time
                current_time += mido.tick2second(msg.time, mid.ticks_per_beat, tempo)
                
                track_name = track.name or f"Track{track_idx}"
                
                if msg.type == 'set_tempo':
                    tempo = msg.tempo
                    bpm = mido.tempo2bpm(tempo)
                    lines.append(f"{current_time:.3f}\t{track_name}\tTempo\t-\t-\t-\t-\t-\t{bpm:.1f} BPM")
                
                elif msg.type == 'time_signature':
                    time_signature = (msg.numerator, msg.denominator)
                    lines.append(f"{current_time:.3f}\t{track_name}\tTimeSig\t-\t-\t-\t-\t-\t{time_signature[0]}/{time_signature[1]}")
                
                elif msg.type == 'key_signature':
                    lines.append(f"{current_time:.3f}\t{track_name}\tKeySig\t-\t-\t-\t-\t-\t{msg.key}")
                
                elif msg.type == 'note_on':
                    if msg.velocity > 0:
                        note_name = note_names[msg.note % 12]
                        octave = msg.note // 12 - 1
                        note_str = f"{note_name}{octave}"
                        notes_on[msg.note] = current_time
                        lines.append(f"{current_time:.3f}\t{track_name}\tNoteOn\t{note_str}\t{msg.note}\t{msg.velocity}\t{msg.channel}\t-\t-")
                    else:
                        # Note off (velocity 0)
                        if msg.note in notes_on:
                            duration = current_time - notes_on[msg.note]
                            note_name = note_names[msg.note % 12]
                            octave = msg.note // 12 - 1
                            note_str = f"{note_name}{octave}"
                            lines.append(f"{current_time:.3f}\t{track_name}\tNoteOff\t{note_str}\t{msg.note}\t0\t{msg.channel}\t{duration:.3f}\t-")
                            del notes_on[msg.note]
                
                elif msg.type == 'note_off':
                    if msg.note in notes_on:
                        duration = current_time - notes_on[msg.note]
                        note_name = note_names[msg.note % 12]
                        octave = msg.note // 12 - 1
                        note_str = f"{note_name}{octave}"
                        lines.append(f"{current_time:.3f}\t{track_name}\tNoteOff\t{note_str}\t{msg.note}\t0\t{msg.channel}\t{duration:.3f}\t-")
                        del notes_on[msg.note]
                
                elif msg.type == 'program_change':
                    lines.append(f"{current_time:.3f}\t{track_name}\tProgChg\t-\t-\t-\t{msg.channel}\t-\tProgram {msg.program}")
                
                elif msg.type == 'control_change':
                    lines.append(f"{current_time:.3f}\t{track_name}\tCtrlChg\t-\t-\t{msg.value}\t{msg.channel}\t-\tCC{msg.control}")
        
        lines.append("")
        lines.append("-" * len(header))
        
        # Summary
        total_notes = sum(len([m for m in track if m.type in ['note_on', 'note_off']]) for track in mid.tracks)
        duration = sum(sum(mido.tick2second(msg.time, mid.ticks_per_beat, 500000) for msg in track) for track in mid.tracks)
        
        lines.append(f"Summary\tTotal note events: {total_notes}\tEstimated duration: {duration:.2f}s")
        
        return "\n".join(lines)
    
    except Exception as e:
        return f"Error parsing MIDI file: {e}"


def parse_midi_to_tabs(midi_path: str, instrument_type: str = "auto") -> str:
    """
    Parse a MIDI file and return tablature format (6 lines).
    
    Args:
        midi_path: Path to the MIDI file
        instrument_type: "guitar", "drums", "keyboard", or "auto" (detect from MIDI)
        
    Returns:
        Tablature string (6 lines) representing the MIDI file
    """
    import mido
    
    try:
        mid = mido.MidiFile(midi_path)
        
        # Collect all note events and metadata
        tempo = 500000  # Default tempo (120 BPM)
        time_signature = (4, 4)  # Default time signature
        current_time = 0.0
        note_events = []  # List of (time, note, velocity, duration, channel)
        
        for track in mid.tracks:
            notes_on = {}
            for msg in track:
                current_time += mido.tick2second(msg.time, mid.ticks_per_beat, tempo)
                
                if msg.type == 'set_tempo':
                    tempo = msg.tempo
                
                elif msg.type == 'time_signature':
                    time_signature = (msg.numerator, msg.denominator)
                
                elif msg.type == 'note_on' and msg.velocity > 0:
                    notes_on[msg.note] = current_time
                
                elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                    if msg.note in notes_on:
                        duration = current_time - notes_on[msg.note]
                        note_events.append((notes_on[msg.note], msg.note, msg.velocity if msg.type == 'note_on' else 0, duration, msg.channel))
                        del notes_on[msg.note]
        
        # Auto-detect instrument type
        if instrument_type == "auto":
            # Check if channel 9 (drums) is used
            if any(evt[4] == 9 for evt in note_events):
                instrument_type = "drums"
            # Check note range for guitar (typically E2-E6)
            elif any(40 <= evt[1] <= 88 for evt in note_events):
                instrument_type = "guitar"
            else:
                instrument_type = "keyboard"
        
        # Sort events by time
        note_events.sort(key=lambda x: x[0])
        
        # Calculate bar line positions
        bpm = mido.tempo2bpm(tempo)
        beats_per_measure = time_signature[0]
        seconds_per_measure = (60.0 / bpm) * beats_per_measure
        # 16th note quantization: 4 sixteenths per beat
        slots_per_measure = beats_per_measure * 4
        
        if instrument_type == "guitar":
            return _format_guitar_tabs(note_events, slots_per_measure)
        elif instrument_type == "drums":
            return _format_drum_tabs(note_events, slots_per_measure)
        elif instrument_type == "keyboard":
            return _format_keyboard_tabs(note_events, slots_per_measure)
        else:
            return f"Unknown instrument type: {instrument_type}"
    
    except Exception as e:
        return f"Error parsing MIDI file: {e}"


def _format_guitar_tabs(note_events, slots_per_measure=16):
    """Format MIDI notes as guitar tablature (6 strings) with bar lines."""
    # Guitar string tunings (MIDI notes): E2=40, A2=45, D3=50, G3=55, B3=59, E4=64
    strings = [
        ("E", 64),  # High E
        ("B", 59),
        ("G", 55),
        ("D", 50),
        ("A", 45),
        ("E", 40),  # Low E
    ]
    
    # Group notes by time (quantize to 16th notes)
    time_slots = {}
    for time, note, velocity, duration, channel in note_events:
        slot = int(time / 0.125)  # 16th note quantization
        if slot not in time_slots:
            time_slots[slot] = []
        time_slots[slot].append(note)
    
    max_slot = max(time_slots.keys()) if time_slots else 0
    
    # Build 6 string lines with bar lines
    # Insert bar lines every slots_per_measure
    total_slots = max_slot + 1
    num_measures = (total_slots + slots_per_measure - 1) // slots_per_measure
    
    # Create tab lines with bar line positions
    tab_lines = []
    for _ in range(6):
        line = []
        for measure in range(num_measures):
            start_slot = measure * slots_per_measure
            end_slot = min(start_slot + slots_per_measure, total_slots)
            # Add bar line at start of measure (except first)
            if measure > 0:
                line.append("|")
            # Add slots for this measure
            for slot in range(start_slot, end_slot):
                line.append("-")
        tab_lines.append(line)
    
    # Map notes to tab positions (accounting for bar lines)
    for slot, notes in time_slots.items():
        # Calculate position in tab (accounting for bar lines)
        measure = slot // slots_per_measure
        position_in_line = slot + measure  # Add one position for each bar line before this measure
        
        for note in notes:
            # Find best string for this note (lowest fret)
            best_string = None
            best_fret = None
            min_fret = 999
            
            for string_idx, (string_name, open_note) in enumerate(strings):
                if note >= open_note:
                    fret = note - open_note
                    if fret <= 24 and fret < min_fret:
                        min_fret = fret
                        best_string = string_idx
                        best_fret = fret
            
            # If note is below all strings, try to find the best string anyway
            if best_string is None:
                best_string = 5  # Default to low E
                lowest_open = strings[5][1]  # E2 = 40
                best_fret = note - lowest_open
                
                for string_idx, (string_name, open_note) in enumerate(strings):
                    fret = note - open_note
                    if (fret >= 0 and fret <= 24) or (best_fret < 0 and fret > best_fret):
                        best_string = string_idx
                        best_fret = fret
            
            if best_string is not None and position_in_line < len(tab_lines[best_string]):
                if best_fret is not None:
                    if best_fret < 0:
                        note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
                        note_name = note_names[note % 12]
                        tab_lines[best_string][position_in_line] = note_name.lower()
                    else:
                        if tab_lines[best_string][position_in_line] == "-":
                            tab_lines[best_string][position_in_line] = str(best_fret)
                        else:
                            tab_lines[best_string][position_in_line] += str(best_fret)
                else:
                    tab_lines[best_string][position_in_line] = "x"
    
    # Format output
    lines = []
    lines.append("Guitar Tablature:")
    for i, (string_name, _) in enumerate(strings):
        line = f"{string_name} |" + "".join(tab_lines[i])
        lines.append(line)
    
    return "\n".join(lines)


def _format_drum_tabs(note_events, slots_per_measure=16):
    """Format MIDI notes as drum tablature (6 lines for common drums) with bar lines."""
    # Common drum MIDI notes mapped to lines
    drum_to_line = {
        36: 0,  # Kick
        38: 1,  # Snare
        42: 2,  # Hi-Hat Closed
        46: 2,  # Open Hi-Hat
        44: 2,  # Pedal Hi-Hat
        49: 3,  # Crash
        51: 4,  # Ride
        48: 5,  # Tom 1
        47: 5,  # Tom 2
        45: 5,  # Tom 3
    }
    
    drum_symbols = {
        36: "K", 38: "S", 42: "H", 46: "O", 44: "P",
        49: "C", 51: "R", 48: "T", 47: "M", 45: "L"
    }
    
    # Group by time slots
    time_slots = {}
    for time, note, velocity, duration, channel in note_events:
        slot = int(time / 0.125)  # 16th note quantization
        if slot not in time_slots:
            time_slots[slot] = []
        time_slots[slot].append(note)
    
    max_slot = max(time_slots.keys()) if time_slots else 0
    total_slots = max_slot + 1
    num_measures = (total_slots + slots_per_measure - 1) // slots_per_measure
    
    # Build drum lines with bar lines
    drum_lines = []
    for _ in range(6):
        line = []
        for measure in range(num_measures):
            start_slot = measure * slots_per_measure
            end_slot = min(start_slot + slots_per_measure, total_slots)
            if measure > 0:
                line.append("|")
            for slot in range(start_slot, end_slot):
                line.append("-")
        drum_lines.append(line)
    
    line_names = ["Kick", "Snare", "Hi-Hat", "Crash", "Ride", "Toms"]
    
    for slot, notes in time_slots.items():
        measure = slot // slots_per_measure
        position_in_line = slot + measure
        
        for note in notes:
            if note in drum_to_line:
                line_idx = drum_to_line[note]
                symbol = drum_symbols.get(note, "x")
                if position_in_line < len(drum_lines[line_idx]):
                    if drum_lines[line_idx][position_in_line] == "-":
                        drum_lines[line_idx][position_in_line] = symbol
                    else:
                        drum_lines[line_idx][position_in_line] += symbol
    
    # Format output
    lines = ["Drum Tablature:"]
    for i, name in enumerate(line_names):
        line = f"{name:8} |" + "".join(drum_lines[i])
        lines.append(line)
    
    return "\n".join(lines)


def _format_keyboard_tabs(note_events, slots_per_measure=16):
    """Format MIDI notes as keyboard/piano tablature (6 lines for different octaves) with bar lines."""
    # Note names
    note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    
    # Group by time slots and octave
    time_slots = {}
    for time, note, velocity, duration, channel in note_events:
        slot = int(time / 0.125)  # 16th note quantization
        octave = (note // 12) - 1
        note_name = note_names[note % 12]
        
        if 0 <= octave < 6:  # C0 to C5
            if slot not in time_slots:
                time_slots[slot] = {}
            if octave not in time_slots[slot]:
                time_slots[slot][octave] = []
            time_slots[slot][octave].append(note_name)
    
    max_slot = max(time_slots.keys()) if time_slots else 0
    total_slots = max_slot + 1
    num_measures = (total_slots + slots_per_measure - 1) // slots_per_measure
    
    # Build 6 octave lines with bar lines (C5 down to C0)
    keyboard_lines = []
    for _ in range(6):
        line = []
        for measure in range(num_measures):
            start_slot = measure * slots_per_measure
            end_slot = min(start_slot + slots_per_measure, total_slots)
            if measure > 0:
                line.append("|")
            for slot in range(start_slot, end_slot):
                line.append("-")
        keyboard_lines.append(line)
    
    for slot, octaves in time_slots.items():
        measure = slot // slots_per_measure
        position_in_line = slot + measure
        
        for octave, notes in octaves.items():
            if 0 <= octave < 6 and position_in_line < len(keyboard_lines[octave]):
                keyboard_lines[octave][position_in_line] = "".join(notes)
    
    # Format output
    lines = ["Keyboard Tablature:"]
    for octave in range(5, -1, -1):  # C5 down to C0
        line = f"C{octave} |" + "".join(keyboard_lines[octave])
        lines.append(line)
    
    return "\n".join(lines)
