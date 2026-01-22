#ifndef SESSION_STATE_H
#define SESSION_STATE_H

#include <stdint.h>

// Maximum number of samples in audio buffer
#define MAX_AUDIO_BUFFER_SIZE 2048
#define MAX_STEM_PATH_LENGTH 512

// Audio buffer structure for multi-channel input
struct AudioBuffers {
    float guitar_channel[MAX_AUDIO_BUFFER_SIZE];  // Channel 1: Guitar input
    float voice_channel[MAX_AUDIO_BUFFER_SIZE];   // Channel 2: Voice commands
    int buffer_size;                              // Actual size of buffers
    int sample_rate;                              // Sample rate (typically 44100 or 48000)
    uint64_t frame_counter;                       // Frame counter for sync tracking
    int guitar_ready;                             // Flag: guitar buffer ready for processing
    int voice_ready;                              // Flag: voice buffer ready for processing
};

// Session state structure shared between Python and C++
struct SessionState {
    // Musical context
    float current_key;                            // Key as float (0.0-11.0, where 0=C, 1=C#, etc.)
    float tempo;                                  // BPM
    int loop_length_bars;                         // Bars in loop (typically 8)
    double loop_timer;                            // Current position in loop (0.0 to loop_length)
    
    // Cloud stem management
    int cloud_stem_ready;                         // Boolean flag: stem available
    char cloud_stem_path[MAX_STEM_PATH_LENGTH];  // Path to audio file
    
    // Analysis data
    float harmonic_data[128];                     // Chord/harmonic analysis
    float rhythmic_data[64];                     // Beat/tempo analysis
    int harmonic_data_size;                       // Actual size of harmonic data
    int rhythmic_data_size;                       // Actual size of rhythmic data
    
    // Audio buffers
    AudioBuffers audio_inputs;                    // Multi-channel audio data
    
    // Control flags
    int fallback_active;                          // Boolean: fallback mode active
    int system_running;                           // Boolean: system is running
    
    // Synchronization
    uint64_t sync_timestamp;                      // Timestamp for sync operations
};

// Size of the shared memory region
#define SESSION_STATE_SIZE sizeof(SessionState)

#endif // SESSION_STATE_H
