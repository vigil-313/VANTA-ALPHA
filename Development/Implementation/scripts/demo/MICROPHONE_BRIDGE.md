# Microphone Bridge for Docker on macOS

This documentation outlines the implementation of the file-based microphone bridge that enables Docker containers to access the host's microphone on macOS.

## Overview

The microphone bridge solves the problem of accessing macOS audio input devices from within Docker containers. Since Docker containers cannot directly access hardware devices on macOS, we use a file-based approach where:

1. A host-side bridge script captures audio from the macOS microphone
2. Audio is written to a shared directory as WAV chunks
3. A container-side client reads these audio chunks

## Implementation

### Components

1. **Host-Side Bridge (`mic_bridge_final.sh`)**
   - Runs on the macOS host
   - Captures audio using ffmpeg in chunk mode
   - Manages recording state and client requests
   - Provides status information

2. **Container-Side Client (`docker_mic_client.py`)**
   - Runs inside the Docker container
   - Communicates with the bridge via control files
   - Reads audio chunks and processes them
   - Provides a Python API for applications

3. **Shared Directory Structure**
   - `/tmp/vanta-mic-bridge/` on host, mounted as `/host/vanta-mic-bridge/` in container
   - `control/` - Contains control files and status information
   - `audio/` - Contains audio chunks
   - `logs/` - Contains bridge logs

### Communication Protocol

The bridge and client communicate using files:

1. **Starting Recording:**
   - Client creates: `/host/vanta-mic-bridge/control/start_recording_{uuid}.ctrl`
   - File content: `{"sample_rate": 16000, "channels": 1, "chunk_duration": 0.5}`
   - Bridge starts recording and removes the control file

2. **Stopping Recording:**
   - Client creates: `/host/vanta-mic-bridge/control/stop_recording_{uuid}.ctrl`
   - Bridge stops recording and removes the control file

3. **Status Information:**
   - Bridge maintains: `/host/vanta-mic-bridge/control/status.json`
   - Contains current recording state, configuration, and any errors

4. **Audio Data:**
   - Bridge creates: `/host/vanta-mic-bridge/audio/chunk_{nnn}_{uuid}.wav`
   - Sequentially numbered chunk files with client's UUID

## Technical Details

### Audio Capture Method

- Uses ffmpeg with the avfoundation input device
- Captures in 0.5-second chunks by default (configurable)
- Converts to 16kHz mono WAV format (configurable)
- Explicit naming scheme that the client can recognize

### Error Handling

- Bridge monitors the recording process and restarts if needed
- Client can detect recording failures and retry
- Explicit permission checks ensure microphone access
- Status file provides detailed error information

### Performance Considerations

- Chunk files are kept small for low-latency processing
- Old chunks are automatically cleaned up (after 60 seconds)
- Minimal CPU usage when idle

## Usage

### Setting Up Bridge

1. Run the bridge script on the macOS host:
   ```bash
   ./mic_bridge_final.sh
   ```

2. Ensure the Docker container mounts the bridge directory:
   ```bash
   docker run -v /tmp/vanta-mic-bridge:/host/vanta-mic-bridge [other-options] image-name
   ```

### Using the Client

In Python code within the container:

```python
from docker_mic_client import MicrophoneClient

# Create client
mic = MicrophoneClient()

# Start recording
mic.start_recording()

# Read audio data
audio_data, sample_rate, channels = mic.read_audio(duration=5.0)

# Stop recording
mic.stop_recording()

# Process audio data...
```

Or as a standalone script:

```bash
python docker_mic_client.py --duration 5.0 --output recording.wav
```

## Troubleshooting

1. **Microphone Access Issues**
   - Ensure Terminal has microphone permission in macOS System Settings
   - Run the test script to verify microphone access: `./test_mic_bridge_minimal.sh`

2. **Docker Integration Issues**
   - Verify volume mounting: `docker exec container ls -la /host/vanta-mic-bridge`
   - Check bridge status: `cat /tmp/vanta-mic-bridge/control/status.json`

3. **Audio Quality Issues**
   - Check microphone volume in macOS settings
   - Inspect audio levels in bridge logs
   - Try adjusting sample rate or channels in client configuration

## Implementation Details

The bridge uses a simple but reliable approach:

- Each audio chunk is created using a separate ffmpeg process for better reliability
- Explicit chunk naming and file permissions ensure Docker container access
- Status monitoring ensures the bridge recovers from errors
- Regular file cleanup prevents disk space issues

## Future Improvements

1. Add volume level normalization option
2. Support multiple simultaneous clients with different configurations
3. Add audio format conversion options
4. Implement a more efficient shared memory approach for lower latency

## Testing

Use the following scripts to test the microphone bridge:

1. `test_mic_bridge_minimal.sh` - Tests the basic bridge functionality
2. `test_docker_mic_client.sh` - Tests the Docker client with the bridge