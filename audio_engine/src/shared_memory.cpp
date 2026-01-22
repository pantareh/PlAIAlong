#include "shared_memory.hpp"
#include <cstring>
#include <stdexcept>

#ifdef _WIN32
#define NOMINMAX  // Prevent Windows.h from defining min/max macros
#include <windows.h>
#else
#include <sys/mman.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#endif

SharedMemory::SharedMemory() 
    : m_memory(nullptr)
    , m_size(0)
    , m_isOwner(false)
#ifdef _WIN32
    , m_fileMapping(nullptr)
#else
    , m_shmFd(-1)
#endif
{
}

SharedMemory::~SharedMemory() {
    close();
}

bool SharedMemory::init(const std::string& name, size_t size, bool create) {
    m_name = name;
    m_size = size;
    m_isOwner = create;

#ifdef _WIN32
    // Windows implementation
    if (create) {
        // Create file mapping
        m_fileMapping = CreateFileMappingA(
            INVALID_HANDLE_VALUE,
            nullptr,
            PAGE_READWRITE,
            0,
            static_cast<DWORD>(size),
            name.c_str()
        );
        
        if (m_fileMapping == nullptr) {
            return false;
        }
        
        // Map view of file
        m_memory = MapViewOfFile(
            m_fileMapping,
            FILE_MAP_ALL_ACCESS,
            0,
            0,
            size
        );
    } else {
        // Open existing file mapping
        m_fileMapping = OpenFileMappingA(
            FILE_MAP_ALL_ACCESS,
            FALSE,
            name.c_str()
        );
        
        if (m_fileMapping == nullptr) {
            return false;
        }
        
        // Map view of file
        m_memory = MapViewOfFile(
            m_fileMapping,
            FILE_MAP_ALL_ACCESS,
            0,
            0,
            size
        );
    }
    
    if (m_memory == nullptr) {
        if (m_fileMapping != nullptr) {
            CloseHandle(m_fileMapping);
            m_fileMapping = nullptr;
        }
        return false;
    }
    
    // Initialize memory if we created it
    if (create) {
        memset(m_memory, 0, size);
    }
    
    return true;
#else
    // Linux/Mac implementation
    int flags = create ? (O_CREAT | O_RDWR) : O_RDWR;
    mode_t mode = create ? 0666 : 0;
    
    m_shmFd = shm_open(name.c_str(), flags, mode);
    if (m_shmFd == -1) {
        return false;
    }
    
    if (create) {
        // Set size
        if (ftruncate(m_shmFd, size) == -1) {
            close(m_shmFd);
            m_shmFd = -1;
            return false;
        }
    }
    
    // Map shared memory
    m_memory = mmap(nullptr, size, PROT_READ | PROT_WRITE, MAP_SHARED, m_shmFd, 0);
    if (m_memory == MAP_FAILED) {
        close(m_shmFd);
        m_shmFd = -1;
        m_memory = nullptr;
        return false;
    }
    
    // Initialize memory if we created it
    if (create) {
        memset(m_memory, 0, size);
    }
    
    return true;
#endif
}

void SharedMemory::close() {
    if (m_memory != nullptr) {
#ifdef _WIN32
        UnmapViewOfFile(m_memory);
        if (m_fileMapping != nullptr) {
            CloseHandle(m_fileMapping);
            m_fileMapping = nullptr;
        }
#else
        munmap(m_memory, m_size);
        if (m_shmFd != -1) {
            close(m_shmFd);
            m_shmFd = -1;
        }
        if (m_isOwner) {
            shm_unlink(m_name.c_str());
        }
#endif
        m_memory = nullptr;
    }
}

SessionState* SharedMemory::getSessionState() const {
    if (m_memory == nullptr) {
        return nullptr;
    }
    return reinterpret_cast<SessionState*>(m_memory);
}

bool SharedMemory::writeGuitarBuffer(const float* buffer, int size) {
    SessionState* state = getSessionState();
    if (state == nullptr || size > MAX_AUDIO_BUFFER_SIZE) {
        return false;
    }
    
    memcpy(state->audio_inputs.guitar_channel, buffer, size * sizeof(float));
    state->audio_inputs.buffer_size = size;
    state->audio_inputs.guitar_ready = 1;
    
    return true;
}

bool SharedMemory::writeVoiceBuffer(const float* buffer, int size) {
    SessionState* state = getSessionState();
    if (state == nullptr || size > MAX_AUDIO_BUFFER_SIZE) {
        return false;
    }
    
    memcpy(state->audio_inputs.voice_channel, buffer, size * sizeof(float));
    state->audio_inputs.buffer_size = size;
    state->audio_inputs.voice_ready = 1;
    
    return true;
}
