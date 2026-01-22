#include "audio_engine.hpp"
#include <iostream>
#include <cstring>
#include <cmath>

// For now, we'll implement a basic version that can work with PortAudio
// or be extended with direct ASIO SDK later
#ifdef USE_PORTAUDIO
#include "portaudio.h"
#else
// Simulated audio for testing without ASIO
#define SIMULATE_AUDIO
#endif

AudioEngine::AudioEngine()
    : m_sharedMemory(nullptr)
    , m_running(false)
    , m_inputBuffer(nullptr)
    , m_outputBuffer(nullptr)
    , m_inputBufferSize(0)
    , m_outputBufferSize(0)
    , m_simulateMode(false)
{
}

AudioEngine::~AudioEngine() {
    stop();
    cleanup();
}

bool AudioEngine::init(const AudioConfig& config, SharedMemory* shared_mem) {
    m_config = config;
    m_sharedMemory = shared_mem;
    
    if (m_sharedMemory == nullptr || !m_sharedMemory->isValid()) {
        std::cerr << "AudioEngine: Invalid shared memory" << std::endl;
        return false;
    }
    
    // Allocate buffers
    m_inputBufferSize = config.buffer_size * config.input_channels;
    m_outputBufferSize = config.buffer_size * config.output_channels;
    
    m_inputBuffer = new float[m_inputBufferSize];
    m_outputBuffer = new float[m_outputBufferSize];
    
    memset(m_inputBuffer, 0, m_inputBufferSize * sizeof(float));
    memset(m_outputBuffer, 0, m_outputBufferSize * sizeof(float));
    
#ifdef USE_PORTAUDIO
    // Initialize PortAudio
    PaError err = Pa_Initialize();
    if (err != paNoError) {
        std::cerr << "PortAudio initialization failed: " << Pa_GetErrorText(err) << std::endl;
        return false;
    }
    m_simulateMode = false;
#else
    // For MVP, use simulation mode if ASIO/PortAudio not available
    m_simulateMode = true;
    std::cout << "AudioEngine: Running in simulation mode (no ASIO)" << std::endl;
#endif
    
    return true;
}

bool AudioEngine::start() {
    if (m_running.load()) {
        return true;
    }
    
    m_running = true;
    
#ifdef USE_PORTAUDIO
    // Start PortAudio stream
    // Implementation would go here
    // For now, fall through to simulation
#endif
    
    if (m_simulateMode) {
        // Start simulation thread
        m_audioThread = std::thread(&AudioEngine::audioThread, this);
    }
    
    return true;
}

void AudioEngine::stop() {
    if (!m_running.load()) {
        return;
    }
    
    m_running = false;
    
    if (m_audioThread.joinable()) {
        m_audioThread.join();
    }
    
#ifdef USE_PORTAUDIO
    // Stop PortAudio stream
    // Implementation would go here
#endif
}

void AudioEngine::audioCallback(float** input, float** output, int frames) {
    if (!m_running.load() || m_sharedMemory == nullptr) {
        return;
    }
    
    // Extract guitar and voice channels
    float* guitar_channel = nullptr;
    float* voice_channel = nullptr;
    
    if (input != nullptr && m_config.input_channels > 0) {
        if (m_config.guitar_channel_index < m_config.input_channels) {
            guitar_channel = input[m_config.guitar_channel_index];
        }
        if (m_config.voice_channel_index < m_config.input_channels) {
            voice_channel = input[m_config.voice_channel_index];
        }
    }
    
    // Write to shared memory
    if (guitar_channel != nullptr) {
        m_sharedMemory->writeGuitarBuffer(guitar_channel, frames);
    }
    
    if (voice_channel != nullptr) {
        m_sharedMemory->writeVoiceBuffer(voice_channel, frames);
    }
    
    // Read output from mixer (would be set by mixer)
    // For now, output silence
    if (output != nullptr && m_config.output_channels > 0) {
        for (int ch = 0; ch < m_config.output_channels; ch++) {
            memset(output[ch], 0, frames * sizeof(float));
        }
    }
}

void AudioEngine::audioThread() {
    // Simulation mode: generate test audio and process it
    const int frames = m_config.buffer_size;
    const float sample_rate = static_cast<float>(m_config.sample_rate);
    float phase = 0.0f;
    float phase_inc = 440.0f / sample_rate;  // A4 note
    
    float** input_channels = new float*[m_config.input_channels];
    float** output_channels = new float*[m_config.output_channels];
    
    for (int i = 0; i < m_config.input_channels; i++) {
        input_channels[i] = new float[frames];
    }
    for (int i = 0; i < m_config.output_channels; i++) {
        output_channels[i] = new float[frames];
    }
    
    while (m_running.load()) {
        // Generate test input (sine wave for guitar, silence for voice)
        for (int i = 0; i < frames; i++) {
            if (m_config.guitar_channel_index < m_config.input_channels) {
                input_channels[m_config.guitar_channel_index][i] = 
                    std::sin(phase * 2.0f * 3.14159f) * 0.5f;
            }
            if (m_config.voice_channel_index < m_config.input_channels) {
                input_channels[m_config.voice_channel_index][i] = 0.0f;
            }
            phase += phase_inc;
            if (phase >= 1.0f) phase -= 1.0f;
        }
        
        // Process audio
        audioCallback(input_channels, output_channels, frames);
        
        // Sleep for buffer duration
        std::this_thread::sleep_for(
            std::chrono::microseconds(
                static_cast<int>(frames * 1000000.0f / sample_rate)
            )
        );
    }
    
    // Cleanup
    for (int i = 0; i < m_config.input_channels; i++) {
        delete[] input_channels[i];
    }
    for (int i = 0; i < m_config.output_channels; i++) {
        delete[] output_channels[i];
    }
    delete[] input_channels;
    delete[] output_channels;
}

bool AudioEngine::initASIO() {
    // Placeholder for ASIO initialization
    // Would use ASIO SDK here
    return false;
}

void AudioEngine::cleanup() {
    if (m_inputBuffer) {
        delete[] m_inputBuffer;
        m_inputBuffer = nullptr;
    }
    
    if (m_outputBuffer) {
        delete[] m_outputBuffer;
        m_outputBuffer = nullptr;
    }
    
#ifdef USE_PORTAUDIO
    Pa_Terminate();
#endif
}
