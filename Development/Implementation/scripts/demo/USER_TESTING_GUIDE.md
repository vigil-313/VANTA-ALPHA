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
   
   To quickly test with different TTS engines, use our specialized script:
   ```bash
   # Run with OpenAI TTS engine
   ./scripts/demo/tts_engine_switch.sh --engine api --key YOUR_API_KEY --voice echo --logs
   
   # Run with local Piper TTS engine
   ./scripts/demo/tts_engine_switch.sh --engine local --logs
   
   # Run with system TTS (macOS)
   ./scripts/demo/tts_engine_switch.sh --engine system --voice "Daniel" --logs
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
- **[p]**: Run performance comparison between TTS engines
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

4. **Text-to-Speech (TTS)**:
   - Use command (7) to enter text and hear it spoken
   - Try different TTS engines using command (8):
     - **API (OpenAI)** - Highest quality but requires an API key and internet connection
       - Pros: Most natural sounding, excellent prosody, good emotional expression
       - Cons: Requires API key, internet connection, higher latency, API costs
     - **Local (Piper)** - Offline capability, runs directly on your device
       - Pros: Works offline, consistent latency, no API cost
       - Cons: Lower voice quality, less natural prosody, higher resource usage
     - **System (macOS)** - Uses built-in system voices
       - Pros: No setup required, reliable, low resource usage
       - Cons: Less natural sounding, limited prosody control
   - Try changing voices with command (9)
     - For API voices, try the different character voices (alloy, echo, fable, etc.)
     - For system voices, explore the variety of available voices on your system
   - Run the TTS test sequence (0) to hear various speech capabilities
     - The test showcases various speech patterns: questions, statements, emphasis
     - Tests technical term pronunciation, prosody variations, and emotional expression
     - After the test, you can compare the same sequence with different engines
   - Compare TTS Engines by testing:
     - **Voice Quality**: Overall clarity and naturalness of speech
     - **Prosody**: Natural intonation, pauses, and emphasis
     - **Emotional Expression**: Whether the voice conveys emotion effectively
     - **Technical Term Handling**: Pronunciation of technical terms like API, JSON, etc.
     - **Latency**: How quickly the speech is generated after entering text
     - **Stability**: Whether the system maintains performance over time

5. **TTS Performance Comparison**:
   - Use command (p) to run the performance comparison
   - The comparison will test all available TTS engines with a set of standard phrases
   - Watch and listen to each engine's performance on different types of content
   - Note the objective measurements (latency) and subjective quality differences
   - This feature helps you quantify the tradeoffs between quality and speed

6. **System Controls**:
   - Test manual activation (5) in Manual mode (3)
   - Toggle listening (6) and verify behavior

## Providing Feedback

Please provide feedback on your testing experience:

1. **What worked well in the overall demo?**
2. **What issues did you encounter during testing?**
3. **How was the accuracy and quality of:
   - Wake word detection?
   - Voice activity detection?
   - Speech recognition?
   - Text-to-speech output?

### TTS-Specific Feedback

Please rate each TTS engine on a scale of 1-5 (5 being best) for:

1. **Voice Quality and Naturalness**
   - API (OpenAI): ____
   - Local (Piper): ____
   - System (macOS): ____
   - Comments: 

2. **Prosody (Natural intonation, pauses, emphasis)**
   - API (OpenAI): ____
   - Local (Piper): ____
   - System (macOS): ____
   - Comments:

3. **Technical Term Pronunciation**
   - API (OpenAI): ____
   - Local (Piper): ____
   - System (macOS): ____
   - Comments:

4. **Emotional Expression**
   - API (OpenAI): ____
   - Local (Piper): ____
   - System (macOS): ____
   - Comments:

5. **Latency/Response Time**
   - API (OpenAI): ____
   - Local (Piper): ____
   - System (macOS): ____
   - Comments:

6. **Overall Performance**
   - API (OpenAI): ____
   - Local (Piper): ____
   - System (macOS): ____
   - Comments:

7. **Which TTS engine would you prefer for daily use and why?**

8. **Were there any specific types of text or phrases that weren't pronounced correctly?**

9. **What improvements would you suggest for the TTS functionality?**

10. **Any additional feedback on the voice pipeline demo or user experience?**

## Logs

Logs are saved to the `logs/` directory. These can be helpful for debugging issues.

Use the `run_voice_demo_with_logs.sh` script to capture comprehensive logs during testing, which will include:
- System environment information
- Module availability
- Audio device enumeration
- All console output
- Performance metrics

This information is valuable for troubleshooting problems you might encounter.

## TTS Capabilities & Configuration

The VANTA Voice Pipeline includes a sophisticated Text-to-Speech system with the following capabilities:

### TTS Engine Architecture

VANTA's TTS system is designed with a multi-tier architecture to balance quality, latency, and resource usage:

1. **API-based TTS** (highest quality):
   - Using OpenAI's TTS API
   - Requires internet connection and API key
   - Multiple voice options (alloy, echo, fable, onyx, nova, shimmer)
   - Excellent prosody and natural speech patterns
   - Configure with command (8) option [a]

2. **Local TTS** (offline capability):
   - Using Piper TTS models that run directly on your device
   - Works without internet connection
   - Lower voice quality but consistent performance
   - Useful for deployment in offline environments
   - Configure with command (8) option [l]

3. **System TTS** (development friendly):
   - Using macOS built-in text-to-speech capabilities
   - No setup required, multiple voices available
   - Good for development and testing
   - Configure with command (8) option [s]

### Prosody and Speech Enhancement

VANTA's TTS system includes prosody formatting capabilities:

- **Intonation Control**: Questions, statements, and commands use appropriate patterns
- **Emphasis Handling**: Words marked with *asterisks* receive emphasis when supported
- **Abbreviation Expansion**: Common abbreviations like "Dr." expand to "Doctor"
- **Punctuation Enhancement**: Proper pauses for commas, periods, etc.
- **Technical Term Handling**: Special handling for technical terms and acronyms

### Performance Considerations

Different TTS engines have different performance characteristics:

- **API (OpenAI)**:
  - Highest quality but highest latency (200-1000ms)
  - Requires internet connection
  - API usage costs apply
  - Least resource intensive locally

- **Local (Piper)**:
  - Medium quality with consistent latency (100-300ms)
  - Works offline
  - No API costs
  - More resource intensive (CPU/RAM)

- **System (macOS)**:
  - Lower quality but very low latency (50-100ms)
  - Works offline
  - No API costs
  - Minimal resource usage

### Configuration Options

You can modify TTS behavior through:

- **Command (8)**: Choose the TTS engine
- **Command (9)**: Select voices for the current engine
- **Command (0)**: Run the test sequence to compare capabilities
- **Command (7)**: Enter custom text for synthesis

## Troubleshooting

- **No audio input/output**: Check your system audio settings and ensure the correct devices are selected
- **Module not found errors**: Run `./scripts/dev/dev_setup.sh` to install dependencies
- **Model download errors**: Run `./scripts/model_management/setup_all_models.sh` with appropriate permissions
- **Permission denied**: Make sure scripts are executable (`chmod +x script_name.sh`)
- **OpenAI API errors**: Ensure you have a valid API key set in the environment or entered when prompted
  - Set `OPENAI_API_KEY` environment variable to avoid entering your key each time
  - Example: `export OPENAI_API_KEY=sk-your-key-here`
- **TTS engine switching issues**: If switching between engines causes errors, restart the demo
- **Piper model not found**: Run `./scripts/model_management/setup_tts_models.sh` to download Piper voice models
- **Voice selection errors**: If voice selection fails, try restarting the demo application

## Next Steps

After user testing, we'll collect feedback and prioritize improvements to the VANTA Voice Pipeline.