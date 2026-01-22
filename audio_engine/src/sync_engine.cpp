#include "sync_engine.hpp"
#include <iostream>
#include <cmath>
#include <algorithm>
#include <cstring>
#include <fstream>
#include <limits>
#include <vector>

// Simple audio file reading (WAV format)
#ifdef _WIN32
#define NOMINMAX  // Prevent Windows.h from defining min/max macros
#include <windows.h>
#else
#include <unistd.h>
#endif

SyncEngine::SyncEngine(int sample_rate, int buffer_size)
    : m_sharedMemory(nullptr)
    , m_sampleRate(sample_rate)
    , m_bufferSize(buffer_size)
    , m_loopTimer(0.0)
    , m_loopLengthBars(8)
    , m_tempo(120.0)
    , m_atBoundary(false)
    , m_lastLoopTimer(0.0)
    , m_cloudStemReady(false)
{
}

SyncEngine::~SyncEngine() {
    if (m_cloudStem) {
        delete[] m_cloudStem->data;
        m_cloudStem.reset();
    }
}

bool SyncEngine::init(SharedMemory* shared_mem) {
    m_sharedMemory = shared_mem;
    if (m_sharedMemory == nullptr || !m_sharedMemory->isValid()) {
        return false;
    }
    return true;
}

void SyncEngine::updateLoopTimer(double tempo, int loop_length_bars, double delta_time) {
    m_tempo = tempo;
    m_loopLengthBars = loop_length_bars;
    
    // Calculate loop duration in seconds
    double beats_per_bar = 4.0;
    double loop_duration = (60.0 / tempo) * beats_per_bar * loop_length_bars;
    
    // Update timer
    m_lastLoopTimer = m_loopTimer;
    m_loopTimer += delta_time;
    
    // Wrap around at loop boundary
    if (m_loopTimer >= loop_duration) {
        m_loopTimer = 0.0;
        m_atBoundary = true;
    } else {
        m_atBoundary = false;
    }
}

bool SyncEngine::detectLoopBoundary() const {
    return m_atBoundary || (m_loopTimer < 0.1 && m_lastLoopTimer > 0.5);
}

bool SyncEngine::loadCloudStem(const std::string& path) {
    if (path.empty() || path == m_cloudStemPath) {
        return false;
    }
    
    std::vector<float> audio;
    int file_sample_rate;
    
    if (!loadAudioFile(path, audio, file_sample_rate)) {
        std::cerr << "Failed to load cloud stem: " << path << std::endl;
        return false;
    }
    
    // Resample if needed (simple linear interpolation for MVP)
    if (file_sample_rate != m_sampleRate) {
        std::vector<float> resampled;
        double ratio = static_cast<double>(m_sampleRate) / file_sample_rate;
        resampled.resize(static_cast<size_t>(audio.size() * ratio));
        
        for (size_t i = 0; i < resampled.size(); i++) {
            double src_index = i / ratio;
            size_t idx0 = static_cast<size_t>(src_index);
            size_t idx1 = std::min(idx0 + 1, static_cast<size_t>(audio.size() - 1));
            double frac = src_index - idx0;
            resampled[i] = audio[idx0] * (1.0 - frac) + audio[idx1] * frac;
        }
        
        audio = resampled;
    }
    
    // Create audio buffer
    if (m_cloudStem) {
        delete[] m_cloudStem->data;
    }
    
    m_cloudStem = std::make_unique<AudioBuffer>();
    m_cloudStem->size = static_cast<int>(audio.size());
    m_cloudStem->sample_rate = m_sampleRate;
    m_cloudStem->data = new float[audio.size()];
    std::memcpy(m_cloudStem->data, audio.data(), audio.size() * sizeof(float));
    
    m_cloudStemPath = path;
    m_cloudStemReady = true;
    
    std::cout << "Loaded cloud stem: " << path << " (" << m_cloudStem->size << " samples)" << std::endl;
    return true;
}

bool SyncEngine::alignWithDTW(const AudioBuffer& /*local*/, const AudioBuffer& /*cloud*/, AudioBuffer& aligned) {
    if (!m_cloudStem || !m_cloudStemReady) {
        return false;
    }
    
    // For MVP, use simple alignment (no DTW)
    // In production, would use full DTW algorithm
    
    // Simple approach: use cloud stem as-is (assuming it's already aligned)
    aligned.data = m_cloudStem->data;
    aligned.size = m_cloudStem->size;
    aligned.sample_rate = m_cloudStem->sample_rate;
    
    return true;
}

float SyncEngine::computeDTWDistance(const float* seq1, int len1, const float* seq2, int len2) {
    // Simple DTW implementation (O(n*m) complexity)
    // For MVP, this is a placeholder
    
    if (len1 == 0 || len2 == 0) {
        return 1.0f;//std::numeric_limits<float>::max();
    }
    
    // Create cost matrix
    std::vector<std::vector<float>> cost(len1 + 1, std::vector<float>(len2 + 1, 1.0f)); // std::numeric_limits<float>::max()
    cost[0][0] = 0.0f;
    
    // Fill cost matrix
    for (int i = 1; i <= len1; i++) {
        for (int j = 1; j <= len2; j++) {
            float dist = std::abs(seq1[i-1] - seq2[j-1]);
            cost[i][j] = dist + std::min({
                cost[i-1][j],      // Insertion
                cost[i][j-1],      // Deletion
                cost[i-1][j-1]     // Match
            });
        }
    }
    
    return cost[len1][len2];
}

bool SyncEngine::loadAudioFile(const std::string& path, std::vector<float>& audio, int& sample_rate) {
    // Simple WAV file reader (basic implementation)
    std::ifstream file(path, std::ios::binary);
    if (!file.is_open()) {
        return false;
    }
    
    // Read WAV header
    char header[44];
    file.read(header, 44);
    
    // Check RIFF header
    if (std::memcmp(header, "RIFF", 4) != 0) {
        return false;
    }
    
    // Check WAVE format
    if (std::memcmp(header + 8, "WAVE", 4) != 0) {
        return false;
    }
    
    // Read sample rate (little endian)
    sample_rate = *reinterpret_cast<int*>(header + 24);
    
    // Read data size
    int data_size = *reinterpret_cast<int*>(header + 40);
    
    // Read audio data (assuming 16-bit PCM)
    std::vector<int16_t> samples(data_size / 2);
    file.read(reinterpret_cast<char*>(samples.data()), data_size);
    
    // Convert to float
    audio.resize(samples.size());
    for (size_t i = 0; i < samples.size(); i++) {
        audio[i] = samples[i] / 32768.0f;
    }
    
    return true;
}

void SyncEngine::resetLoop() {
    m_loopTimer = 0.0;
    m_lastLoopTimer = 0.0;
    m_atBoundary = false;
}
