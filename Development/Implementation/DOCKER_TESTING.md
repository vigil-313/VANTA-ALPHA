# TASK-REF: ENV_004 - Test Framework Setup
# CONCEPT-REF: CON-TEST-011 - Docker Testing Environment
# CONCEPT-REF: CON-TEST-012 - Test Execution Scripts
# DOC-REF: DOC-DEV-TEST-1 - Testing Strategy

# Docker Testing Workflow

This document provides guidance for running tests in the Docker environment.

## Docker Environment Setup

Before running tests, ensure that the Docker environment is properly set up:

1. Start the Docker containers:
   ```bash
   ./scripts/dev_start.sh
   ```

2. Access the Docker shell:
   ```bash
   ./scripts/dev_shell.sh
   ```

## Test Execution in Docker

### Running Tests Using the Run Script

The `run_tests.sh` script provides a convenient way to run tests with various options:

```bash
# Inside Docker container
cd /app
./scripts/run_tests.sh all         # Run all tests
./scripts/run_tests.sh unit        # Run only unit tests
./scripts/run_tests.sh integration # Run only integration tests
./scripts/run_tests.sh performance # Run only performance tests
./scripts/run_tests.sh coverage    # Run tests with coverage report
```

### Running Tests Directly with Pytest

You can also run tests directly using pytest:

```bash
# Inside Docker container
cd /app
python -m pytest -v                 # Run all tests
python -m pytest tests/unit/ -v     # Run unit tests
python -m pytest tests/integration/ -v # Run integration tests
python -m pytest -m model -v        # Run tests with 'model' marker
python -m pytest --cov=./ --cov-report=html # Run with coverage report
```

## Test Dependencies in Docker

The Docker environment includes all necessary dependencies for running tests, including:

- pytest and pytest plugins (pytest-cov, pytest-mock)
- Audio processing libraries (librosa, soundfile, pyaudio)
- ML model dependencies (transformers, accelerate)
- Mock and test utilities

If additional dependencies are needed, they should be added to the `requirements.txt` file and the Docker image should be rebuilt:

```bash
# Outside Docker
cd Development/Implementation/docker
docker-compose build
```

## Test Data Management

Test data is stored in the following locations:

- Test audio samples: `/app/tests/fixtures/audio/`
- Test model artifacts: `/app/tests/fixtures/models/`
- Test outputs: `/app/logs/test_*.log`

These directories are mounted as volumes in the Docker container, ensuring that test data persists between container restarts.

## Continuous Integration

The GitHub Actions workflow in `.github/workflows/tests.yml` provides automated testing on code changes. It uses a similar Docker environment to ensure consistency between local development and CI environments.

## Troubleshooting

### Common Issues

1. **Missing Audio Devices**: Audio tests may fail if the Docker container can't access audio devices. Use the `@pytest.mark.skipif` decorator to conditionally skip these tests in environments without audio support.

2. **Model Download Failures**: Tests requiring models may fail if models aren't downloaded. Use the `skip_if_no_model` utility from the `model_utils.py` file to skip these tests when models aren't available.

3. **Resource Constraints**: Performance tests may fail due to resource constraints in the Docker environment. Consider using the `@pytest.mark.skipif` decorator to skip these tests in resource-constrained environments.

## Best Practices

1. **Run Tests Often**: Make it a habit to run tests after making changes, starting with the most relevant test type (unit, integration, or performance).

2. **Isolated Testing**: Use mock objects to isolate tests from external dependencies, especially in unit tests.

3. **Test Coverage**: Aim for high test coverage, especially for critical components like the Voice Pipeline and Memory Engine.

4. **Continuous Integration**: Push changes regularly to trigger CI testing, which provides an additional validation layer.

5. **Test in Docker**: Always test in the Docker environment to ensure consistency across development environments.

## Docker Testing Environment Validation Checklist

- [ ] Docker container starts successfully
- [ ] All required Python packages are installed
- [ ] System dependencies (audio libraries, etc.) are available
- [ ] Unit tests run successfully
- [ ] Integration tests run successfully
- [ ] Performance tests run successfully
- [ ] Test fixture directories are properly mounted
- [ ] Test logs are generated correctly
- [ ] Coverage reports are generated correctly