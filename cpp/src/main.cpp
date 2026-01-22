#include "audio_engine.hpp"
#include "midi_synthesizer.hpp"
#include "sync_engine.hpp"
#include "audio_mixer.hpp"
#include "shared_memory.hpp"
#include "../shared/session_state.h"
#include <iostream>
#include <chrono>
#include <thread>
#include <cstring>
#ifdef _WIN32
#include <windows.h>
#else
#include <signal.h>
#include <unistd.h>
#endif

// Global pointers for cleanup
static AudioEngine* g_audioEngine = nullptr;
static MidiSynthesizer* g_midiSynthesizer = nullptr;
static SyncEngine* g_syncEngine = nullptr;
static AudioMixer* g_audioMixer = nullptr;
static SharedMemory* g_sharedMemory = nullptr;

static bool g_running = true;

#ifdef _WIN32
BOOL WINAPI signalHandler(DWORD dwCtrlType) {
    if (dwCtrlType == CTRL_C_EVENT || dwCtrlType == CTRL_BREAK_EVENT) {
        std::cout << "\nShutting down..." << std::endl;
        g_running = false;
        return TRUE;
    }
    return FALSE;
}
#else
void signalHandler(int signal) {
    std::cout << "\nShutting down..." << std::endl;
    g_running = false;
}
#endif

int main(int argc, char* argv[]) {
    std::cout << "PlAIAlong Audio Engine Starting..." << std::endl;
    
    // Setup signal handlers
#ifdef _WIN32
    SetConsoleCtrlHandler(signalHandler, TRUE);
#else
    signal(SIGINT, signalHandler);
    signal(SIGTERM, signalHandler);
#endif
    
    // Configuration
    const int sample_rate = 44100;
    const int buffer_size = 512;
    const std::string shared_mem_name = "plaialong_shared_memory";
    
    // Initialize shared memory
    g_sharedMemory = new SharedMemory();
    if (!g_sharedMemory->init(shared_mem_name, SESSION_STATE_SIZE, false)) {
        std::cerr << "Failed to initialize shared memory" << std::endl;
        return 1;
    }
    
    // Initialize components
    g_midiSynthesizer = new MidiSynthesizer(sample_rate);
    if (!g_midiSynthesizer->init()) {
        std::cerr << "Failed to initialize MIDI synthesizer" << std::endl;
        return 1;
    }
    
    g_syncEngine = new SyncEngine(sample_rate, buffer_size);
    if (!g_syncEngine->init(g_sharedMemory)) {
        std::cerr << "Failed to initialize sync engine" << std::endl;
        return 1;
    }
    
    g_audioMixer = new AudioMixer(sample_rate, buffer_size);
    if (!g_audioMixer->init(g_midiSynthesizer, g_syncEngine, g_sharedMemory)) {
        std::cerr << "Failed to initialize audio mixer" << std::endl;
        return 1;
    }
    
    // Configure audio engine
    AudioConfig audioConfig;
    audioConfig.sample_rate = sample_rate;
    audioConfig.buffer_size = buffer_size;
    audioConfig.input_channels = 2;  // Guitar + Voice
    audioConfig.output_channels = 2;
    audioConfig.guitar_channel_index = 0;
    audioConfig.voice_channel_index = 1;
    audioConfig.device_name = "";
    
    g_audioEngine = new AudioEngine();
    if (!g_audioEngine->init(audioConfig, g_sharedMemory)) {
        std::cerr << "Failed to initialize audio engine" << std::endl;
        return 1;
    }
    
    // Start components
    g_midiSynthesizer->start();
    if (!g_audioEngine->start()) {
        std::cerr << "Failed to start audio engine" << std::endl;
        return 1;
    }
    
    std::cout << "Audio engine running. Press Ctrl+C to stop." << std::endl;
    
    // Main loop
    auto last_time = std::chrono::high_resolution_clock::now();
    
    while (g_running) {
        // Update sync engine
        auto current_time = std::chrono::high_resolution_clock::now();
        auto delta = std::chrono::duration<double>(current_time - last_time).count();
        last_time = current_time;
        
        // Read tempo and loop length from shared memory
        SessionState* state = g_sharedMemory->getSessionState();
        if (state) {
            double tempo = state->tempo > 0 ? state->tempo : 120.0;
            int loop_length = state->loop_length_bars > 0 ? state->loop_length_bars : 8;
            
            g_syncEngine->updateLoopTimer(tempo, loop_length, delta);
            
            // Check for cloud stem
            if (state->cloud_stem_ready && strlen(state->cloud_stem_path) > 0) {
                std::string stem_path(state->cloud_stem_path);
                g_syncEngine->loadCloudStem(stem_path);
                // Clear ready flag
                state->cloud_stem_ready = 0;
            }
        }
        
        // Sleep
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
    }
    
    // Cleanup
    std::cout << "Shutting down components..." << std::endl;
    
    if (g_audioEngine) {
        g_audioEngine->stop();
        delete g_audioEngine;
    }
    
    if (g_midiSynthesizer) {
        g_midiSynthesizer->stop();
        delete g_midiSynthesizer;
    }
    
    if (g_syncEngine) {
        delete g_syncEngine;
    }
    
    if (g_audioMixer) {
        delete g_audioMixer;
    }
    
    if (g_sharedMemory) {
        g_sharedMemory->close();
        delete g_sharedMemory;
    }
    
    std::cout << "Shutdown complete." << std::endl;
    return 0;
}
