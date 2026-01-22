#ifndef AUDIO_MIXER_HPP
#define AUDIO_MIXER_HPP

#include <vector>
#include <memory>
#include "midi_synthesizer.hpp"
#include "sync_engine.hpp"
#include "shared_memory.hpp"

class AudioMixer {
public:
    AudioMixer(int sample_rate, int buffer_size);
    ~AudioMixer();

    // Initialize
    bool init(MidiSynthesizer* midi_synth, SyncEngine* sync_engine, SharedMemory* shared_mem);
    
    // Process audio frame (called from audio callback)
    void processFrame(float* output, int frames);
    
    // Set mix levels
    void setMixLevels(float local_level, float cloud_level);
    
    // Enable/disable cloud stem
    void setCloudStemEnabled(bool enabled);

private:
    // Mix audio buffers
    void mixBuffers(const float* local, const float* cloud, float* output, int frames, float local_gain, float cloud_gain);
    
    // Apply crossfade
    void applyCrossfade(float* buffer, int frames, bool fade_in);

    MidiSynthesizer* m_midiSynthesizer;
    SyncEngine* m_syncEngine;
    SharedMemory* m_sharedMemory;
    
    int m_sampleRate;
    int m_bufferSize;
    
    // Mix levels
    float m_localLevel;
    float m_cloudLevel;
    bool m_cloudStemEnabled;
    
    // Buffers
    std::vector<float> m_localBuffer;
    std::vector<float> m_cloudBuffer;
    std::vector<float> m_mixBuffer;
    
    // Cloud stem playback
    int m_cloudStemPosition;
    bool m_cloudStemPlaying;
};

#endif // AUDIO_MIXER_HPP
