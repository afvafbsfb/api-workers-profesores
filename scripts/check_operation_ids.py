#!/usr/bin/env python3
"""Check that every operation in an OpenAPI spec has a non-empty operationId.

Usage:
  python scripts/check_operation_ids.py --spec docs/openapi-auto.json

Exit code: 0 = all good, 1 = missing operationId(s), 2 = file not found / parse error
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import List, Dict, Any


def load_spec(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        print(f"Spec file not found: {path}")
        raise SystemExit(2)
    with open(path, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except Exception as e:
            print(f"Failed to parse JSON spec: {e}")
            raise SystemExit(2)


def find_missing_operation_ids(spec: Dict[str, Any]) -> List[str]:
    missing: List[str] = []
    paths = spec.get('paths', {}) or {}
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        for method, op in methods.items():
            if method.lower() not in ('get', 'post', 'put', 'patch', 'delete', 'options', 'head'):
                continue
            if not isinstance(op, dict):
                continue
            opid = op.get('operationId')
            if not (isinstance(opid, str) and opid.strip()):
                missing.append(f"{method.upper()} {path}")
    return missing


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--spec', default='docs/openapi-auto.json', help='Path to OpenAPI JSON spec (default: docs/openapi-auto.json)')
    args = parser.parse_args(argv)

    spec_path = args.spec
    spec = load_spec(spec_path)
    missing = find_missing_operation_ids(spec)
    if missing:
        print('Operations missing operationId:')
        for m in missing:
            print(' -', m)
        return 1
    print('All operations have operationId')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
