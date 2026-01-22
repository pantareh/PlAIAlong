#ifndef IPC_PROTOCOL_H
#define IPC_PROTOCOL_H

#include <stdint.h>

// IPC message types for MIDI communication
#define IPC_MSG_MIDI_DATA 1
#define IPC_MSG_MIDI_EVENT 2
#define IPC_MSG_COMMAND 3

// MIDI message structure
struct MidiMessage {
    uint8_t status;        // MIDI status byte
    uint8_t data1;         // First data byte
    uint8_t data2;         // Second data byte
    uint32_t timestamp;    // Timestamp in samples
};

// IPC message header
struct IpcMessageHeader {
    uint32_t message_type;     // Message type (IPC_MSG_*)
    uint32_t message_size;     // Size of message payload
    uint64_t timestamp;        // Message timestamp
};

// Named pipe names (Windows)
#define MIDI_PIPE_NAME "\\\\.\\pipe\\plaialong_midi"
#define COMMAND_PIPE_NAME "\\\\.\\pipe\\plaialong_commands"

// Shared memory name
#define SHARED_MEMORY_NAME "plaialong_shared_memory"

#endif // IPC_PROTOCOL_H
