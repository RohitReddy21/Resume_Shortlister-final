"""Resume parser service package.
Provides orchestration for text extraction, OCR, NLP extraction, and JSON output.
"""

from .orchestrator import parse_resume

__all__ = ["parse_resume"]
