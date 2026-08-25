"""Test-local setup for the YouTube connector test suite.

`faster_whisper`'s real dependencies (ctranslate2, onnxruntime) are heavy
native binaries and are not needed here -- every test that touches Whisper
mocks the transcription call directly. We inject a lightweight fake module
so `from faster_whisper import WhisperModel` (in connectors.youtube.client)
succeeds at import time without installing the real package or hitting the
network to download any model weights.
"""

import sys
import types
from unittest.mock import MagicMock

if "faster_whisper" not in sys.modules:
    fake_module = types.ModuleType("faster_whisper")
    fake_module.WhisperModel = MagicMock(name="WhisperModel")
    sys.modules["faster_whisper"] = fake_module
