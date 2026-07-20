#!/usr/bin/env python3
import sys
import json
from app.services.parser.orchestrator import parse_resume

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python parse_sample.py <resume-file>')
        sys.exit(1)
    path = sys.argv[1]
    out = parse_resume(path)
    print(json.dumps(out, indent=2))
