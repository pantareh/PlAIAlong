cmake_minimum_required(VERSION 3.15)
project(PlAIAlongAudioEngineTests)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Include directories
include_directories(${CMAKE_SOURCE_DIR}/../include)
include_directories(${CMAKE_SOURCE_DIR}/../../shared)

# Download and configure Google Test using FetchContent (CMake 3.11+)
include(FetchContent)
FetchContent_Declare(
    googletest
    GIT_REPOSITORY https://github.com/google/googletest.git
    GIT_TAG        v1.14.0
)

# For Windows: Prevent min/max macro issues
if(WIN32)
    set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
    add_definitions(-DNOMINMAX)  # Prevent Windows.h from defining min/max macros
endif()

# Make Google Test available
FetchContent_MakeAvailable(googletest)

# Test executable - include shared_memory source for linking
add_executable(test_shared_memory
    test_shared_memory.cpp
    ${CMAKE_SOURCE_DIR}/../src/shared_memory.cpp
)

# Link against Google Test
target_link_libraries(test_shared_memory
    PRIVATE
    GTest::gtest
    GTest::gtest_main
)

# Include directories for test
target_include_directories(test_shared_memory PRIVATE
    ${CMAKE_SOURCE_DIR}/../src
)

# Enable testing
enable_testing()
add_test(NAME SharedMemoryTests COMMAND test_shared_memory)
