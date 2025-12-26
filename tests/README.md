# Tests

Comprehensive test suite for all connectors.

## Setup

1. **Install dependencies:**
   ```bash
   pip install -e .[all,dev]
   ```

2. **Set up environment variables:**

   Copy the `.env.example` file to `.env` in the project root:
   ```bash
   cp .env.example .env
   ```

   Then edit `.env` and add your actual API credentials:
   ```bash
   # Reddit
   REDDIT_CLIENT_ID=your_actual_client_id
   REDDIT_CLIENT_SECRET=your_actual_secret

   # Telegram
   TELEGRAM_API_ID=your_actual_api_id
   TELEGRAM_API_HASH=your_actual_hash
   TELEGRAM_PHONE=+1234567890

   # Twitter
   TWITTER_BEARER_TOKEN=your_actual_bearer_token
   ```

3. **Load environment variables:**

   On Windows (PowerShell):
   ```powershell
   Get-Content .env | ForEach-Object {
       if ($_ -match '^\s*([^#][^=]*?)\s*=\s*(.*)$') {
           [Environment]::SetEnvironmentVariable($matches[1], $matches[2], 'Process')
       }
   }
   ```

   On Linux/Mac:
   ```bash
   export $(cat .env | xargs)
   ```

   Or use `python-dotenv`:
   ```bash
   pip install python-dotenv
   ```
   Then in Python:
   ```python
   from dotenv import load_dotenv
   load_dotenv()
   ```

## Running Tests

### Run All Tests
```bash
pytest
```

### Run Specific Connector Tests
```bash
# Reddit only
pytest tests/reddit/

# YouTube only
pytest tests/youtube/

# Telegram only
pytest tests/telegram/

# Twitter only
pytest tests/twitter/
```

### Run Integration Tests
```bash
pytest tests/test_integration.py
```

### Run with Verbose Output
```bash
pytest -v
```

### Run with Coverage
```bash
pytest --cov=src/connectors --cov-report=term-missing
```

### Run Specific Test
```bash
pytest tests/reddit/test_reddit.py::TestRedditCollector::test_fetch_posts_hot
```

## Test Structure

```
tests/
├── conftest.py                 # Shared fixtures for all tests
├── test_integration.py         # Integration tests for all connectors
├── reddit/
│   └── test_reddit.py         # Reddit connector tests
├── youtube/
│   └── test_youtube.py        # YouTube connector tests
├── telegram/
│   └── test_telegram.py       # Telegram connector tests
└── twitter/
    └── test_twitter.py        # Twitter connector tests
```

## Test Types

### Unit Tests
- Test configuration validation
- Test data model validation
- Test input validation

### Integration Tests
- Test actual API calls (requires valid credentials)
- Test data fetching
- Test error handling
- **Note:** These tests will skip automatically if credentials are not set

## Skipped Tests

Tests will automatically skip if:
- Required credentials are not set in environment variables
- Credentials are placeholder values (start with "your_")

Example output:
```
SKIPPED [1] tests/conftest.py:14: Skipping test: REDDIT_CLIENT_ID not set in environment
```

## Notes

### Telegram Tests
Telegram tests may require interactive authentication on first run:
- You'll be prompted to enter a code sent to your Telegram app
- After first authentication, a session file is created
- Subsequent runs will use the cached session

### YouTube Tests
- YouTube connector doesn't require API credentials
- Uses public APIs and Whisper for transcription
- Tests may take longer due to video processing

### Rate Limits
Be aware of API rate limits:
- **Reddit:** 60 requests per minute (default)
- **Twitter:** 15 requests per 15-minute window
- **Telegram:** No strict rate limit for official API
- **YouTube:** No API key needed, uses public endpoints

## Troubleshooting

### Authentication Errors
If you see authentication errors, verify:
1. Environment variables are loaded correctly
2. Credentials are valid and not expired
3. API keys have correct permissions

### Import Errors
If you see import errors:
```bash
# Install in development mode
pip install -e .[all,dev]
```

### Session Errors (Telegram)
If Telegram session is corrupted:
```bash
# Delete session file and re-authenticate
rm *.session
```

## Contributing

When adding new tests:
1. Follow existing test patterns
2. Use fixtures from `conftest.py`
3. Add docstrings to test functions
4. Ensure tests can skip gracefully if credentials missing
5. Keep tests fast and focused
