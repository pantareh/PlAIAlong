#ifndef SHARED_MEMORY_HPP
#define SHARED_MEMORY_HPP

#include <string>
#include <cstddef>
#include "../shared/session_state.h"

class SharedMemory {
public:
    SharedMemory();
    ~SharedMemory();

    // Initialize shared memory (create or attach)
    bool init(const std::string& name, size_t size, bool create = false);
    
    // Close and cleanup
    void close();

    // Get pointer to session state
    SessionState* getSessionState() const;
    
    // Write audio buffer (guitar channel)
    bool writeGuitarBuffer(const float* buffer, int size);
    
    // Write audio buffer (voice channel)
    bool writeVoiceBuffer(const float* buffer, int size);
    
    // Check if shared memory is valid
    bool isValid() const { return m_memory != nullptr; }

private:
    void* m_memory;
    size_t m_size;
    std::string m_name;
    bool m_isOwner;
    
#ifdef _WIN32
    void* m_fileMapping;
#else
    int m_shmFd;
#endif
};

#endif // SHARED_MEMORY_HPP
