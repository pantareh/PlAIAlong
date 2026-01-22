#include "audio_mixer.hpp"
#include <algorithm>
#include <cmath>
#include <cstring>
#include <limits>

AudioMixer::AudioMixer(int sample_rate, int buffer_size)
    : m_midiSynthesizer(nullptr)
    , m_syncEngine(nullptr)
    , m_sharedMemory(nullptr)
    , m_sampleRate(sample_rate)
    , m_bufferSize(buffer_size)
    , m_localLevel(0.7f)
    , m_cloudLevel(0.5f)
    , m_cloudStemEnabled(true)
    , m_cloudStemPosition(0)
    , m_cloudStemPlaying(false)
{
    m_localBuffer.resize(buffer_size);
    m_cloudBuffer.resize(buffer_size);
    m_mixBuffer.resize(buffer_size);
}

AudioMixer::~AudioMixer() {
}

bool AudioMixer::init(MidiSynthesizer* midi_synth, SyncEngine* sync_engine, SharedMemory* shared_mem) {
    m_midiSynthesizer = midi_synth;
    m_syncEngine = sync_engine;
    m_sharedMemory = shared_mem;
    
    if (m_midiSynthesizer == nullptr || m_syncEngine == nullptr || m_sharedMemory == nullptr) {
        return false;
    }
    
    return true;
}

void AudioMixer::processFrame(float* output, int frames) {
    // Clear output
    std::memset(output, 0, frames * sizeof(float));
    
    // Generate local MIDI audio
    if (m_midiSynthesizer) {
        m_midiSynthesizer->generateAudio(m_localBuffer.data(), frames);
    }
    
    // Check if we should play cloud stem
    if (m_syncEngine && m_cloudStemEnabled) {
        // Check if at loop boundary and cloud stem is ready
        if (m_syncEngine->detectLoopBoundary() && m_syncEngine->isCloudStemReady()) {
            // Start playing cloud stem
            m_cloudStemPosition = 0;
            m_cloudStemPlaying = true;
        }
        
        // Play cloud stem if active
        if (m_cloudStemPlaying) {
            auto* cloudStem = m_syncEngine->getCloudStemBuffer();
            if (cloudStem && cloudStem->data) {
                int samples_to_copy = std::min(frames, cloudStem->size - m_cloudStemPosition);
                
                if (samples_to_copy > 0) {
                    std::memcpy(m_cloudBuffer.data(), 
                               cloudStem->data + m_cloudStemPosition,
                               samples_to_copy * sizeof(float));
                    
                    // Zero out rest if needed
                    if (samples_to_copy < frames) {
                        std::memset(m_cloudBuffer.data() + samples_to_copy, 0, 
                                   (frames - samples_to_copy) * sizeof(float));
                    }
                    
                    m_cloudStemPosition += samples_to_copy;
                    
                    // Check if we've played the entire stem
                    if (m_cloudStemPosition >= cloudStem->size) {
                        m_cloudStemPlaying = false;
                        m_cloudStemPosition = 0;
                    }
                } else {
                    // Stem finished
                    std::memset(m_cloudBuffer.data(), 0, frames * sizeof(float));
                    m_cloudStemPlaying = false;
                    m_cloudStemPosition = 0;
                }
            } else {
                std::memset(m_cloudBuffer.data(), 0, frames * sizeof(float));
            }
        } else {
            std::memset(m_cloudBuffer.data(), 0, frames * sizeof(float));
        }
    } else {
        std::memset(m_cloudBuffer.data(), 0, frames * sizeof(float));
    }
    
    // Mix buffers
    mixBuffers(m_localBuffer.data(), m_cloudBuffer.data(), output, frames, 
               m_localLevel, m_cloudLevel);
}

void AudioMixer::mixBuffers(const float* local, const float* cloud, float* output, 
                            int frames, float local_gain, float cloud_gain) {
    for (int i = 0; i < frames; i++) {
        output[i] = (local[i] * local_gain) + (cloud[i] * cloud_gain);
        
        // Soft clipping to prevent overflow
        if (output[i] > 1.0f) {
            output[i] = 1.0f;
        } else if (output[i] < -1.0f) {
            output[i] = -1.0f;
        }
    }
}

void AudioMixer::applyCrossfade(float* buffer, int frames, bool fade_in) {
    int fade_samples = std::min(frames, m_sampleRate / 20);  // 50ms fade
    
    if (fade_in) {
        for (int i = 0; i < fade_samples; i++) {
            float gain = static_cast<float>(i) / fade_samples;
            buffer[i] *= gain;
        }
    } else {
        for (int i = 0; i < fade_samples; i++) {
            float gain = 1.0f - (static_cast<float>(i) / fade_samples);
            buffer[frames - 1 - i] *= gain;
        }
    }
}

void AudioMixer::setMixLevels(float local_level, float cloud_level) {
    m_localLevel = std::clamp(local_level, 0.0f, 1.0f);
    m_cloudLevel = std::clamp(cloud_level, 0.0f, 1.0f);
}

void AudioMixer::setCloudStemEnabled(bool enabled) {
    m_cloudStemEnabled = enabled;
    if (!enabled) {
        m_cloudStemPlaying = false;
        m_cloudStemPosition = 0;
    }
}
