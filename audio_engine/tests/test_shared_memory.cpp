#include <gtest/gtest.h>
#include "shared_memory.hpp"
#include "../../shared/session_state.h"

class SharedMemoryTest : public ::testing::Test {
protected:
    void SetUp() override {
        sharedMem = new SharedMemory();
    }
    
    void TearDown() override {
        if (sharedMem) {
            sharedMem->close();
            delete sharedMem;
        }
    }
    
    SharedMemory* sharedMem;
};

TEST_F(SharedMemoryTest, InitCreate) {
    bool result = sharedMem->init("test_shared_mem", SESSION_STATE_SIZE, true);
    EXPECT_TRUE(result);
    EXPECT_TRUE(sharedMem->isValid());
}

TEST_F(SharedMemoryTest, GetSessionState) {
    sharedMem->init("test_shared_mem", SESSION_STATE_SIZE, true);
    SessionState* state = sharedMem->getSessionState();
    EXPECT_NE(state, nullptr);
}

TEST_F(SharedMemoryTest, WriteGuitarBuffer) {
    sharedMem->init("test_shared_mem", SESSION_STATE_SIZE, true);
    float buffer[512];
    for (int i = 0; i < 512; i++) {
        buffer[i] = 0.1f;
    }
    bool result = sharedMem->writeGuitarBuffer(buffer, 512);
    EXPECT_TRUE(result);
}

int main(int argc, char** argv) {
    ::testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}
