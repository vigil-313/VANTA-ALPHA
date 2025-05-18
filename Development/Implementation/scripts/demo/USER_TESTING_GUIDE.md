# VANTA Voice Pipeline User Testing Guide

This document provides instructions for early user testing of the VANTA Voice Pipeline. The current implementation includes Voice Activity Detection (VAD) and Speech-to-Text (STT) components.

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

4. **System Controls**:
   - Test manual activation (5) in Manual mode (3)
   - Toggle listening (6) and verify behavior
   - Try the TTS function (7)

## Providing Feedback

Please provide feedback on your testing experience:

1. **What worked well?**
2. **What issues did you encounter?**
3. **How was the accuracy of:
   - Wake word detection?
   - Voice activity detection?
   - Speech recognition?
4. **Any suggestions for improvements?**

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

## Next Steps

After user testing, we'll collect feedback and prioritize improvements to the VANTA Voice Pipeline.