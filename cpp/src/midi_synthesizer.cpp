#include "midi_synthesizer.hpp"
#include <iostream>
#include <cmath>
#include <algorithm>
#include <cstring>
#include <thread>
#include <chrono>
#include <limits>

#ifdef _WIN32
#include <windows.h>
#else
#include <fcntl.h>
#include <unistd.h>
#include <sys/stat.h>
#endif

MidiSynthesizer::MidiSynthesizer(int sample_rate)
    : m_sampleRate(sample_rate)
    , m_voices(16)  // 16 voice polyphony
    , m_currentEventIndex(0)
    , m_playbackPosition(0)
    , m_running(false)
    , m_pipeName("plaialong_midi")
{
    // Initialize voices
    for (auto& voice : m_voices) {
        voice.active = false;
        voice.frequency = 0.0f;
        voice.phase = 0.0f;
        voice.phaseInc = 0.0f;
        voice.amplitude = 0.0f;
        voice.note = -1;
    }
}

MidiSynthesizer::~MidiSynthesizer() {
    stop();
}

bool MidiSynthesizer::init() {
    return true;
}

void MidiSynthesizer::start() {
    if (m_running.load()) {
        return;
    }
    
    m_running = true;
    m_ipcThread = std::thread(&MidiSynthesizer::ipcThreadFunc, this);
}

void MidiSynthesizer::stop() {
    if (!m_running.load()) {
        return;
    }
    
    m_running = false;
    if (m_ipcThread.joinable()) {
        m_ipcThread.join();
    }
}

void MidiSynthesizer::processMidiEvent(const MidiEvent& event) {
    uint8_t status = event.status & 0xF0;
    uint8_t channel = event.status & 0x0F;
    
    if (status == 0x90) {  // Note On
        if (event.data2 > 0) {
            handleNoteOn(event.data1, event.data2);
        } else {
            handleNoteOff(event.data1);
        }
    } else if (status == 0x80) {  // Note Off
        handleNoteOff(event.data1);
    }
}

void MidiSynthesizer::handleNoteOn(uint8_t note, uint8_t velocity) {
    std::lock_guard<std::mutex> lock(m_voiceMutex);
    
    // Find free voice
    for (auto& voice : m_voices) {
        if (!voice.active) {
            voice.note = note;
            voice.frequency = 440.0f * std::pow(2.0f, (note - 69) / 12.0f);
            voice.phase = 0.0f;
            voice.phaseInc = voice.frequency / m_sampleRate;
            voice.amplitude = velocity / 127.0f * 0.5f;
            voice.active = true;
            return;
        }
    }
    
    // If no free voice, steal oldest
    m_voices[0].note = note;
    m_voices[0].frequency = 440.0f * std::pow(2.0f, (note - 69) / 12.0f);
    m_voices[0].phase = 0.0f;
    m_voices[0].phaseInc = m_voices[0].frequency / m_sampleRate;
    m_voices[0].amplitude = velocity / 127.0f * 0.5f;
    m_voices[0].active = true;
}

void MidiSynthesizer::handleNoteOff(uint8_t note) {
    std::lock_guard<std::mutex> lock(m_voiceMutex);
    
    for (auto& voice : m_voices) {
        if (voice.active && voice.note == note) {
            voice.active = false;
            voice.amplitude = 0.0f;
        }
    }
}

float MidiSynthesizer::generateSample(Voice& voice) {
    if (!voice.active || voice.amplitude <= 0.0f) {
        return 0.0f;
    }
    
    // Simple sine wave
    float sample = std::sin(voice.phase * 2.0f * 3.14159f) * voice.amplitude;
    
    // Update phase
    voice.phase += voice.phaseInc;
    if (voice.phase >= 1.0f) {
        voice.phase -= 1.0f;
    }
    
    return sample;
}

void MidiSynthesizer::generateAudio(float* output, int frames) {
    // Clear output
    std::memset(output, 0, frames * sizeof(float));
    
    std::lock_guard<std::mutex> lock(m_voiceMutex);
    
    // Generate audio for each frame
    for (int i = 0; i < frames; i++) {
        float sample = 0.0f;
        
        // Sum all active voices
        for (auto& voice : m_voices) {
            sample += generateSample(voice);
        }
        
        output[i] = sample;
        
        // Process MIDI events at current position
        while (m_currentEventIndex < m_midiEvents.size()) {
            const auto& event = m_midiEvents[m_currentEventIndex];
            if (event.timestamp <= m_playbackPosition) {
                processMidiEvent(event);
                m_currentEventIndex++;
            } else {
                break;
            }
        }
        
        m_playbackPosition++;
    }
}

bool MidiSynthesizer::loadMidiFile(const std::vector<uint8_t>& midi_data) {
    // For MVP, parse simple MIDI format
    // In production, would use a proper MIDI library
    
    m_midiEvents.clear();
    m_currentEventIndex = 0;
    m_playbackPosition = 0;
    
    // Simple MIDI parsing (basic implementation)
    // This is a placeholder - full MIDI parsing would be more complex
    size_t pos = 0;
    uint32_t current_time = 0;
    
    while (pos < midi_data.size() - 2) {
        // Read status byte
        uint8_t status = midi_data[pos++];
        
        if ((status & 0x80) == 0) {
            // Running status - use previous status
            pos--;
            continue;
        }
        
        if (status == 0xFF) {
            // Meta event - skip
            pos++;
            uint8_t length = midi_data[pos++];
            pos += length;
            continue;
        }
        
        uint8_t cmd = status & 0xF0;
        
        if (cmd == 0x90 || cmd == 0x80) {  // Note On/Off
            if (pos + 1 >= midi_data.size()) break;
            
            MidiEvent event;
            event.status = status;
            event.data1 = midi_data[pos++];
            event.data2 = midi_data[pos++];
            event.timestamp = current_time;
            
            m_midiEvents.push_back(event);
            current_time += 480;  // Simple timing
        } else {
            // Skip other events
            pos += 2;
        }
    }
    
    std::cout << "Loaded " << m_midiEvents.size() << " MIDI events" << std::endl;
    return true;
}

void MidiSynthesizer::ipcThreadFunc() {
    while (m_running.load()) {
        if (readMidiFromPipe()) {
            // MIDI data received and loaded
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
    }
}

bool MidiSynthesizer::readMidiFromPipe() {
#ifdef _WIN32
    // Windows named pipe
    std::string pipeName = "\\\\.\\pipe\\" + m_pipeName;
    
    HANDLE pipe = CreateFileA(
        pipeName.c_str(),
        GENERIC_READ,
        0,
        nullptr,
        OPEN_EXISTING,
        0,
        nullptr
    );
    
    if (pipe == INVALID_HANDLE_VALUE) {
        return false;
    }
    
    // Read message header
    uint32_t messageType, messageSize;
    uint64_t timestamp;
    
    DWORD bytesRead;
    if (!ReadFile(pipe, &messageType, sizeof(messageType), &bytesRead, nullptr) ||
        bytesRead != sizeof(messageType)) {
        CloseHandle(pipe);
        return false;
    }
    
    if (!ReadFile(pipe, &messageSize, sizeof(messageSize), &bytesRead, nullptr) ||
        bytesRead != sizeof(messageSize)) {
        CloseHandle(pipe);
        return false;
    }
    
    if (!ReadFile(pipe, &timestamp, sizeof(timestamp), &bytesRead, nullptr) ||
        bytesRead != sizeof(timestamp)) {
        CloseHandle(pipe);
        return false;
    }
    
    // Read MIDI data
    std::vector<uint8_t> midiData(messageSize);
    if (!ReadFile(pipe, midiData.data(), messageSize, &bytesRead, nullptr) ||
        bytesRead != messageSize) {
        CloseHandle(pipe);
        return false;
    }
    
    CloseHandle(pipe);
    
    // Load MIDI
    loadMidiFile(midiData);
    return true;
#else
    // Unix named pipe
    std::string pipePath = "/tmp/" + m_pipeName;
    
    FILE* pipe = fopen(pipePath.c_str(), "rb");
    if (!pipe) {
        return false;
    }
    
    // Read message header
    uint32_t messageType, messageSize;
    uint64_t timestamp;
    
    if (fread(&messageType, sizeof(messageType), 1, pipe) != 1 ||
        fread(&messageSize, sizeof(messageSize), 1, pipe) != 1 ||
        fread(&timestamp, sizeof(timestamp), 1, pipe) != 1) {
        fclose(pipe);
        return false;
    }
    
    // Read MIDI data
    std::vector<uint8_t> midiData(messageSize);
    if (fread(midiData.data(), 1, messageSize, pipe) != messageSize) {
        fclose(pipe);
        return false;
    }
    
    fclose(pipe);
    
    // Load MIDI
    loadMidiFile(midiData);
    return true;
#endif
}
