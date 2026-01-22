#ifndef AUDIO_ENGINE_HPP
#define AUDIO_ENGINE_HPP

#include <string>
#include <functional>
#include <atomic>
#include <thread>
#include "shared_memory.hpp"

// Forward declarations
struct AudioConfig {
    int sample_rate;
    int buffer_size;
    int input_channels;
    int output_channels;
    int guitar_channel_index;
    int voice_channel_index;
    std::string device_name;
};

class AudioEngine {
public:
    AudioEngine();
    ~AudioEngine();

    // Initialize audio system
    bool init(const AudioConfig& config, SharedMemory* shared_mem);
    
    // Start audio processing
    bool start();
    
    // Stop audio processing
    void stop();
    
    // Check if running
    bool isRunning() const { return m_running.load(); }
    
    // Get current sample rate
    int getSampleRate() const { return m_config.sample_rate; }
    
    // Get buffer size
    int getBufferSize() const { return m_config.buffer_size; }

private:
    // Audio callback (called by audio system)
    void audioCallback(float** input, float** output, int frames);
    
    // Audio processing thread
    void audioThread();
    
    // Initialize ASIO (or fallback to PortAudio)
    bool initASIO();
    
    // Cleanup
    void cleanup();

    AudioConfig m_config;
    SharedMemory* m_sharedMemory;
    std::atomic<bool> m_running;
    std::thread m_audioThread;
    
    // Audio buffers
    float* m_inputBuffer;
    float* m_outputBuffer;
    int m_inputBufferSize;
    int m_outputBufferSize;
    
    // For simulation/testing (when ASIO not available)
    bool m_simulateMode;
};

#endif // AUDIO_ENGINE_HPP
