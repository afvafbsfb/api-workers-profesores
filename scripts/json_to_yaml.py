#!/usr/bin/env python3
"""Simple helper: read docs/openapi-auto.json and write a safe openapi.yml

Usage: python scripts/json_to_yaml.py
"""
import json
import sys
from pathlib import Path

try:
    import yaml
except Exception:
    print("PyYAML not installed. Install with: python -m pip install pyyaml", file=sys.stderr)
    sys.exit(2)


def main():
    src = Path('docs/openapi-auto.json')
    dst = Path('openapi.yml')
    if not src.exists():
        print(f"Source file not found: {src}", file=sys.stderr)
        return 2
    try:
        with src.open('r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Failed to load JSON from {src}: {e}", file=sys.stderr)
        return 2

    try:
        # Use safe_dump to avoid Python-specific tags, allow unicode and sort keys
        with dst.open('w', encoding='utf-8') as f:
            yaml.safe_dump(data, f, allow_unicode=True, sort_keys=True)
    except Exception as e:
        print(f"Failed to write YAML to {dst}: {e}", file=sys.stderr)
        return 2

    print(f"Wrote {dst} from {src}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
