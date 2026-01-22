#ifndef SYNC_ENGINE_HPP
#define SYNC_ENGINE_HPP

#include <string>
#include <vector>
#include <atomic>
#include <memory>
#include "shared_memory.hpp"

// Forward declarations
struct AudioBuffer {
    float* data;
    int size;
    int sample_rate;
};

class SyncEngine {
public:
    SyncEngine(int sample_rate, int buffer_size);
    ~SyncEngine();

    // Initialize
    bool init(SharedMemory* shared_mem);
    
    // Update loop timer (called from audio thread)
    void updateLoopTimer(double tempo, int loop_length_bars, double delta_time);
    
    // Check if at loop boundary
    bool detectLoopBoundary() const;
    
    // Load cloud stem
    bool loadCloudStem(const std::string& path);
    
    // Align cloud stem with local audio using DTW
    bool alignWithDTW(const AudioBuffer& local, const AudioBuffer& cloud, AudioBuffer& aligned);
    
    // Get current cloud stem buffer
    AudioBuffer* getCloudStemBuffer() { return m_cloudStem.get(); }
    
    // Check if cloud stem is ready
    bool isCloudStemReady() const { return m_cloudStemReady.load(); }
    
    // Reset for new loop
    void resetLoop();

private:
    // Simple DTW implementation
    float computeDTWDistance(const float* seq1, int len1, const float* seq2, int len2);
    
    // Load audio file
    bool loadAudioFile(const std::string& path, std::vector<float>& audio, int& sample_rate);
    
    SharedMemory* m_sharedMemory;
    int m_sampleRate;
    int m_bufferSize;
    
    // Loop state
    double m_loopTimer;
    int m_loopLengthBars;
    double m_tempo;
    bool m_atBoundary;
    double m_lastLoopTimer;
    
    // Cloud stem
    std::unique_ptr<AudioBuffer> m_cloudStem;
    std::atomic<bool> m_cloudStemReady;
    std::string m_cloudStemPath;
    
    // DTW alignment
    std::vector<float> m_alignmentBuffer;
};

#endif // SYNC_ENGINE_HPP
