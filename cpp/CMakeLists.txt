cmake_minimum_required(VERSION 3.15)
project(PlAIAlongAudioEngine)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Include directories
include_directories(${CMAKE_SOURCE_DIR}/include)
include_directories(${CMAKE_SOURCE_DIR}/../shared)

# Source files
set(SOURCES
    src/main.cpp
    src/audio_engine.cpp
    src/sync_engine.cpp
    src/audio_mixer.cpp
    src/shared_memory.cpp
    src/midi_synthesizer.cpp
)

# Header files
set(HEADERS
    include/audio_engine.hpp
    include/sync_engine.hpp
    include/audio_mixer.hpp
    include/shared_memory.hpp
    include/midi_synthesizer.hpp
)

# Create executable
add_executable(plaialong_audio ${SOURCES} ${HEADERS})

# Find packages (add as needed)
# find_package(PkgConfig REQUIRED)
# pkg_check_modules(ASIO REQUIRED asio)

# Link libraries
# target_link_libraries(plaialong_audio ${ASIO_LIBRARIES})

# Compiler-specific options
if(MSVC)
    target_compile_options(plaialong_audio PRIVATE /W4)
else()
    target_compile_options(plaialong_audio PRIVATE -Wall -Wextra -pedantic)
endif()

# Output directory
set_target_properties(plaialong_audio PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin
)
