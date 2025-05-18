# VANTA Voice Pipeline User Testing Guide

This document provides instructions for early user testing of the VANTA Voice Pipeline. The current implementation includes Voice Activity Detection (VAD), Speech-to-Text (STT), and Text-to-Speech (TTS) components.

## System Requirements

- Python 3.9+ with pip
- Audio input device (microphone)
- Audio output device (speakers)
- Required Python packages (installed automatically by the demo script):
  - torch
  - torchaudio
  - onnxruntime
  - pyaudio
  - numpy

## Setup Instructions

1. Clone the repository (if you haven't already):
   ```bash
   git clone <repository-url>
   cd VANTA-ALPHA/Development/Implementation
   ```

2. Run the setup script to install dependencies:
   ```bash
   ./scripts/dev/dev_setup.sh
   ```

3. Download required models:
   ```bash
   ./scripts/model_management/setup_all_models.sh
   ```

## Running the Demo

1. Start the demo:
   ```bash
   ./scripts/demo/run_voice_demo.sh
   ```

   You can optionally specify a custom configuration file:
   ```bash
   ./scripts/demo/run_voice_demo.sh /path/to/custom_config.yaml
   ```

   For comprehensive logging (recommended for testing):
   ```bash
   ./scripts/demo/run_voice_demo_with_logs.sh
   ```

2. The demo provides a simple command-line interface to interact with the VANTA Voice Pipeline.

## Demo Commands

- **[1]**: Change mode to Wake Word (activate when "hey vanta" is detected)
- **[2]**: Change mode to Continuous (always on)
- **[3]**: Change mode to Manual (activate only when manually triggered)
- **[4]**: Change mode to Off (disable voice activation)
- **[5]**: Manual activation (in Manual mode)
- **[6]**: Toggle listening on/off
- **[7]**: Say something (text-to-speech)
- **[8]**: Choose TTS engine (API, local, or system)
- **[9]**: Change TTS voice
- **[0]**: Play TTS test sequence to demonstrate capabilities
- **[q]**: Quit the demo

## Test Scenarios

During testing, please try the following scenarios:

1. **Wake Word Detection**:
   - Set mode to Wake Word (1)
   - Say "hey vanta" and observe if the system activates
   - Try variations of the wake word to test robustness

2. **Voice Activity Detection**:
   - Set mode to Continuous (2)
   - Speak and observe if the system detects your speech
   - Test with different levels of background noise

3. **Speech Recognition**:
   - After activation, speak a simple phrase
   - Check if the transcription is accurate
   - Try with different speaking speeds and accents

4. **Text-to-Speech**:
   - Use command (7) to enter text and hear it spoken
   - Try different TTS engines using command (8):
     - API (OpenAI) - Highest quality but requires an API key
     - Local (Piper) - Offline capability but lower quality
     - System (macOS) - Good for development and testing
   - Try changing voices with command (9)
   - Run the TTS test sequence (0) to hear various speech capabilities
   - Note differences in quality, speed, and naturalness between engines

5. **System Controls**:
   - Test manual activation (5) in Manual mode (3)
   - Toggle listening (6) and verify behavior

## Providing Feedback

Please provide feedback on your testing experience:

1. **What worked well?**
2. **What issues did you encounter?**
3. **How was the accuracy and quality of:
   - Wake word detection?
   - Voice activity detection?
   - Speech recognition?
   - Text-to-speech output?
4. **Which TTS engine performed best for your needs?**
5. **How natural did the speech sound across different engines?**
6. **Were there any specific types of text or phrases that weren't pronounced correctly?**
7. **Any suggestions for improvements?**

## Logs

Logs are saved to the `logs/` directory. These can be helpful for debugging issues.

Use the `run_voice_demo_with_logs.sh` script to capture comprehensive logs during testing, which will include:
- System environment information
- Module availability
- Audio device enumeration
- All console output
- Performance metrics

This information is valuable for troubleshooting problems you might encounter.

## Troubleshooting

- **No audio input/output**: Check your system audio settings and ensure the correct devices are selected
- **Module not found errors**: Run `./scripts/dev/dev_setup.sh` to install dependencies
- **Model download errors**: Run `./scripts/model_management/setup_all_models.sh` with appropriate permissions
- **Permission denied**: Make sure scripts are executable (`chmod +x script_name.sh`)
- **OpenAI API errors**: Ensure you have a valid API key set in the environment or entered when prompted
- **TTS engine switching issues**: If switching between engines causes errors, restart the demo
- **Piper model not found**: Run `./scripts/model_management/setup_tts_models.sh` to download Piper voice models

## Next Steps

After user testing, we'll collect feedback and prioritize improvements to the VANTA Voice Pipeline.