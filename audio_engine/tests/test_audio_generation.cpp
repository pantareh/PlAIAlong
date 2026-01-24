#include <gtest/gtest.h>
#include <fstream>
#include <cmath>
#include <vector>
#include <cstring>
#include <cstdint>
#include <algorithm>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

// Helper function to write WAV file
bool writeWavFile(const std::string& filename, const std::vector<float>& samples, int sample_rate) {
    std::ofstream file(filename, std::ios::binary);
    if (!file.is_open()) {
        return false;
    }
    
    // WAV header structure
    struct WavHeader {
        char riff[4] = {'R', 'I', 'F', 'F'};
        uint32_t file_size;
        char wave[4] = {'W', 'A', 'V', 'E'};
        char fmt[4] = {'f', 'm', 't', ' '};
        uint32_t fmt_size = 16;  // PCM format chunk size
        uint16_t audio_format = 1;  // PCM
        uint16_t num_channels = 1;  // Mono
        uint32_t sample_rate;
        uint32_t byte_rate;
        uint16_t block_align = 2;  // 16-bit mono
        uint16_t bits_per_sample = 16;
        char data[4] = {'d', 'a', 't', 'a'};
        uint32_t data_size;
    };
    
    uint32_t num_samples = static_cast<uint32_t>(samples.size());
    uint32_t data_size = num_samples * 2;  // 16-bit = 2 bytes per sample
    uint32_t file_size = sizeof(WavHeader) - 8 + data_size;  // -8 for riff and file_size fields
    
    WavHeader header;
    header.file_size = file_size;
    header.sample_rate = sample_rate;
    header.byte_rate = sample_rate * 2;  // sample_rate * channels * bytes_per_sample
    header.data_size = data_size;
    
    // Write header
    file.write(reinterpret_cast<const char*>(&header), sizeof(WavHeader));
    
    // Convert float samples to 16-bit PCM and write
    for (float sample : samples) {
        // Clamp to [-1.0, 1.0]
        sample = std::max(-1.0f, std::min(1.0f, sample));
        // Convert to 16-bit integer
        int16_t pcm_sample = static_cast<int16_t>(sample * 32767.0f);
        file.write(reinterpret_cast<const char*>(&pcm_sample), sizeof(int16_t));
    }
    
    return file.good();
}

// Generate simple 8-bit style square wave (quantized to 8-bit levels)
std::vector<float> generate8BitSquareWave(int sample_rate, float frequency, float duration_seconds) {
    int num_samples = static_cast<int>(sample_rate * duration_seconds);
    std::vector<float> samples(num_samples);
    
    float period = sample_rate / frequency;
    
    for (int i = 0; i < num_samples; i++) {
        // Generate square wave
        float phase = std::fmod(static_cast<float>(i), period);
        float value = (phase < period / 2.0f) ? 1.0f : -1.0f;
        
        // Quantize to 8-bit levels (256 levels, but we'll use 128 for symmetry)
        // This gives that classic 8-bit sound
        value = std::round(value * 127.0f) / 127.0f;
        
        samples[i] = value * 0.5f;  // Scale down to avoid clipping
    }
    
    return samples;
}

// Generate simple sine wave
std::vector<float> generateSineWave(int sample_rate, float frequency, float duration_seconds) {
    int num_samples = static_cast<int>(sample_rate * duration_seconds);
    std::vector<float> samples(num_samples);
    
    for (int i = 0; i < num_samples; i++) {
        float t = static_cast<float>(i) / sample_rate;
        samples[i] = std::sin(2.0f * M_PI * frequency * t) * 0.5f;
    }
    
    return samples;
}

class AudioGenerationTest : public ::testing::Test {
protected:
    void SetUp() override {
        sample_rate = 44100;
        buffer_size = 512;
    }
    
    void TearDown() override {
        // Clean up any generated files if needed
    }
    
    int sample_rate;
    int buffer_size;
};

TEST_F(AudioGenerationTest, Generate8BitSquareWave) {
    // Generate 1 second of 8-bit square wave at 440 Hz (A4 note)
    float frequency = 440.0f;
    float duration = 1.0f;
    
    std::vector<float> audio = generate8BitSquareWave(sample_rate, frequency, duration);
    
    // Verify we got samples
    EXPECT_GT(audio.size(), 0);
    EXPECT_EQ(audio.size(), static_cast<size_t>(sample_rate * duration));
    
    // Verify samples are in valid range
    for (float sample : audio) {
        EXPECT_GE(sample, -1.0f);
        EXPECT_LE(sample, 1.0f);
    }
    
    // Write to WAV file
    std::string output_file = "test_8bit_square.wav";
    bool success = writeWavFile(output_file, audio, sample_rate);
    EXPECT_TRUE(success) << "Failed to write WAV file";
    
    // Verify file exists and has content
    std::ifstream check_file(output_file, std::ios::binary);
    EXPECT_TRUE(check_file.is_open()) << "Output file was not created";
    if (check_file.is_open()) {
        check_file.seekg(0, std::ios::end);
        size_t file_size = check_file.tellg();
        EXPECT_GT(file_size, 0) << "Output file is empty";
        check_file.close();
    }
}

TEST_F(AudioGenerationTest, GenerateSineWave) {
    // Generate 1 second of sine wave at 440 Hz
    float frequency = 440.0f;
    float duration = 1.0f;
    
    std::vector<float> audio = generateSineWave(sample_rate, frequency, duration);
    
    // Verify we got samples
    EXPECT_GT(audio.size(), 0);
    EXPECT_EQ(audio.size(), static_cast<size_t>(sample_rate * duration));
    
    // Write to WAV file
    std::string output_file = "test_sine.wav";
    bool success = writeWavFile(output_file, audio, sample_rate);
    EXPECT_TRUE(success) << "Failed to write WAV file";
    
    // Verify file exists
    std::ifstream check_file(output_file, std::ios::binary);
    EXPECT_TRUE(check_file.is_open()) << "Output file was not created";
}

TEST_F(AudioGenerationTest, AudioStreamingSimulation) {
    // Simulate audio streaming by processing in chunks
    float frequency = 440.0f;
    float duration = 2.0f;  // 2 seconds
    int total_samples = static_cast<int>(sample_rate * duration);
    
    std::vector<float> output_audio;
    output_audio.reserve(total_samples);
    
    // Simulate streaming: process audio in buffer-sized chunks
    int samples_generated = 0;
    while (samples_generated < total_samples) {
        int chunk_size = std::min(buffer_size, total_samples - samples_generated);
        
        // Generate chunk of audio
        std::vector<float> chunk = generate8BitSquareWave(
            sample_rate, 
            frequency, 
            static_cast<float>(chunk_size) / sample_rate
        );
        
        // Verify chunk is valid
        EXPECT_EQ(chunk.size(), static_cast<size_t>(chunk_size));
        
        // Append to output
        output_audio.insert(output_audio.end(), chunk.begin(), chunk.end());
        
        samples_generated += chunk_size;
    }
    
    // Verify total length
    EXPECT_EQ(output_audio.size(), static_cast<size_t>(total_samples));
    
    // Write streamed audio to file
    std::string output_file = "test_streamed_8bit.wav";
    bool success = writeWavFile(output_file, output_audio, sample_rate);
    EXPECT_TRUE(success) << "Failed to write streamed WAV file";
    
    // Verify file exists and has correct size
    std::ifstream check_file(output_file, std::ios::binary);
    EXPECT_TRUE(check_file.is_open()) << "Streamed output file was not created";
    if (check_file.is_open()) {
        check_file.seekg(0, std::ios::end);
        size_t file_size = check_file.tellg();
        // Should be at least header size + some data
        EXPECT_GT(file_size, 1000) << "Streamed output file seems too small";
        check_file.close();
    }
}

int main(int argc, char** argv) {
    ::testing::InitGoogleTest(&argc, argv);
    int result = RUN_ALL_TESTS();
    
    std::cout << "\nGenerated audio files:" << std::endl;
    std::cout << "  - test_8bit_square.wav (8-bit square wave)" << std::endl;
    std::cout << "  - test_sine.wav (sine wave)" << std::endl;
    std::cout << "  - test_streamed_8bit.wav (streamed 8-bit audio)" << std::endl;
    
    return result;
}
