# File-Based Microphone Input Bridge for Docker on macOS

## Overview
This design document outlines a file-based approach for enabling Docker containers to access the host's microphone on macOS. Similar to the TTS bridge implemented previously, this solution uses the filesystem as a communication channel between the host and container.

## Architecture

```
┌─────────────────────┐         ┌──────────────────────┐
│  macOS Host         │         │  Docker Container    │
│                     │         │                      │
│  ┌───────────────┐  │         │  ┌────────────────┐  │
│  │ Microphone    │  │         │  │ Audio Capture  │  │
│  │ Input Device  │  │         │  │ Application    │  │
│  └─────┬─────────┘  │         │  └────────┬───────┘  │
│        │            │         │           │          │
│  ┌─────▼─────────┐  │         │  ┌────────▼───────┐  │
│  │ mic_bridge.sh │  │         │  │ docker_mic     │  │
│  │ (monitor)     │  │         │  │ _client.py     │  │
│  └─────┬─────────┘  │  Files  │  └────────┬───────┘  │
│        │            │  ┌─────►│           │          │
│  ┌─────▼─────────┐  │  │      │  ┌────────▼───────┐  │
│  │ /tmp/vanta-   │◄─┼──┘      │  │ /host/vanta-   │  │
│  │ mic-bridge/   │  │         │  │ mic-bridge/    │  │
│  └───────────────┘  │         │  └────────────────┘  │
└─────────────────────┘         └──────────────────────┘
```

## Components

### 1. Host-side Bridge (`mic_bridge.sh`)

This script will:
- Create a shared directory (`/tmp/vanta-mic-bridge`)
- Monitor for control files (to start/stop recording)
- Capture audio from the system microphone using `ffmpeg` or a similar tool
- Write audio chunks to the shared directory as .wav files
- Support configuration of sampling rate, channels, and format

### 2. Container-side Client (`docker_mic_client.py`)

This Python client will:
- Monitor the shared directory for new audio files
- Read and process audio chunks
- Provide an API for audio capture applications
- Support configuration of audio parameters
- Handle start/stop commands by writing control files

### 3. System Integration (`MicBridgeAdapter` class)

This class will:
- Implement the `AudioCaptureAdapter` interface for the VANTA Voice Pipeline
- Manage the file-based bridge communication
- Provide audio data to the Voice Pipeline
- Handle configuration, statistics, and error reporting

## Communication Protocol

### Control Files
- `start_recording_{uuid}.ctrl`: Signal to start recording (with parameters)
- `stop_recording_{uuid}.ctrl`: Signal to stop recording
- `status.json`: Current status of the bridge (updated by the bridge script)

### Audio Files
- `chunk_{timestamp}_{uuid}.wav`: Audio chunks captured from the microphone
- Naming convention includes timestamps to ensure correct ordering

### Parameters
Parameters can be included in control files as JSON:
```
{
  "sample_rate": 16000,
  "channels": 1,
  "format": "wav",
  "chunk_duration": 0.5  // Duration of each chunk in seconds
}
```

## Implementation Details

### Real-time Audio Streaming
To support real-time audio processing:
1. The bridge will capture audio in small chunks (e.g., 0.5 seconds)
2. Each chunk will be written as a separate file
3. The client will read chunks sequentially
4. Old chunks will be automatically deleted after processing

### Error Handling
The system will handle various error conditions:
1. Microphone not available or permission denied
2. Bridge process termination
3. Disk space limitations
4. Container-host synchronization issues

### Performance Considerations
To ensure low latency:
1. Small chunk sizes for minimal buffering delay
2. Efficient file I/O and minimal processing
3. Background threads for file monitoring
4. Status reporting for latency tracking

## Directory Structure
```
/tmp/vanta-mic-bridge/              # Host directory
  control/                          # Control files
    start_recording_{uuid}.ctrl
    stop_recording_{uuid}.ctrl
    status.json
  audio/                            # Audio chunks
    chunk_{timestamp}_{uuid}.wav
  logs/                             # Log files
    mic_bridge.log
```

## Testing Approach
1. Test basic functionality (start/stop recording)
2. Test with different audio configurations
3. Test multiple start/stop cycles
4. Test error conditions (e.g., microphone unavailable)
5. Test integration with the Voice Pipeline
6. Measure and optimize latency

## Security Considerations
1. The bridge directory should have appropriate permissions
2. Audio data should be deleted once processed
3. Consider volume mounting with read-only access where appropriate

## Integration with Voice Pipeline
The `MicBridgeAdapter` will be integrated with the existing Voice Pipeline:
1. Implement the standard audio capture interface
2. Register the adapter in the factory
3. Support runtime switching between adapters
4. Add configuration options for Docker environments