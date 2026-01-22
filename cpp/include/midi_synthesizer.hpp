#ifndef MIDI_SYNTHESIZER_HPP
#define MIDI_SYNTHESIZER_HPP

#include <vector>
#include <string>
#include <atomic>
#include <thread>
#include <mutex>
#include <memory>

// Forward declarations
struct MidiEvent {
    uint8_t status;
    uint8_t data1;
    uint8_t data2;
    uint32_t timestamp;
};

class MidiSynthesizer {
public:
    MidiSynthesizer(int sample_rate);
    ~MidiSynthesizer();

    // Initialize synthesizer
    bool init();
    
    // Process MIDI event
    void processMidiEvent(const MidiEvent& event);
    
    // Generate audio from MIDI
    void generateAudio(float* output, int frames);
    
    // Load MIDI file
    bool loadMidiFile(const std::vector<uint8_t>& midi_data);
    
    // Start/stop
    void start();
    void stop();
    
    // Check if running
    bool isRunning() const { return m_running.load(); }

private:
    // Simple wavetable synthesizer
    struct Voice {
        float frequency;
        float phase;
        float phaseInc;
        float amplitude;
        bool active;
        int note;
    };
    
    // Generate sample for a voice
    float generateSample(Voice& voice);
    
    // Process MIDI message
    void handleNoteOn(uint8_t note, uint8_t velocity);
    void handleNoteOff(uint8_t note);
    
    int m_sampleRate;
    std::vector<Voice> m_voices;
    std::mutex m_voiceMutex;
    
    // MIDI playback
    std::vector<MidiEvent> m_midiEvents;
    size_t m_currentEventIndex;
    uint32_t m_playbackPosition;
    std::atomic<bool> m_running;
    
    // IPC
    std::thread m_ipcThread;
    void ipcThreadFunc();
    bool readMidiFromPipe();
    std::string m_pipeName;
};

#endif // MIDI_SYNTHESIZER_HPP
