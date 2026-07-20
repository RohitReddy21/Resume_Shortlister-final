Resume parser service

Quick start (developer):

1. Create a virtualenv and install parser requirements (optional heavyweight packages separated):

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-parser.txt
```

2. Run the sample parser against a file:

```bash
python backend\scripts\parse_sample.py /path/to/resume.pdf
```

Notes:
- OCR (PaddleOCR) and spaCy transformer models are optional and may require large downloads.
- This is an initial implementation focusing on modularity: `extractor`, `ocr`, `nlp`, and `orchestrator`.
- For production, run parsing in a background worker and avoid sending raw PII to external LLMs without consent.
