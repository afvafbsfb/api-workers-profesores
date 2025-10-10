#!/usr/bin/env python3
"""Validate presence of expected query parameters in an OpenAPI spec.

Usage: python scripts/validate_openapi_params.py [--spec PATH] [--fail-on-missing]

Checks (hardcoded for now):
 - GET /academias  -> query params: id, nombre, page, size
 - GET /usuarios   -> query params: academia_id, rol, nombre, id

The script looks for operations by operationId first, then by path+method.
Exits with non-zero if --fail-on-missing and any expected param is missing.
"""
from pathlib import Path
import json
import argparse
import sys


EXPECTED = [
    # (operationId, path_candidates, method, expected_query_param_names)
    ('academias.listar_academias', ['/academias', '/academias/'], 'get', ['id', 'nombre', 'page', 'size']),
    ('usuarios.listar_usuarios', ['/usuarios', '/usuarios/'], 'get', ['academia_id', 'rol', 'nombre', 'id']),
]


def load_spec(path: Path):
    if not path.exists():
        print(f'ERROR: spec not found: {path}')
        return None
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception as e:
        print(f'ERROR: failed to parse JSON spec {path}: {e}')
        return None


def find_operation(spec, opid=None, path_candidates=None, method='get'):
    paths = spec.get('paths', {}) if isinstance(spec, dict) else {}
    method = method.lower()

    # 1) search by operationId
    if opid:
        for p, methods in paths.items():
            if not isinstance(methods, dict):
                continue
            for m, op in methods.items():
                if m.lower() != method:
                    continue
                if isinstance(op, dict) and op.get('operationId') == opid:
                    return p, op

    # 2) search by path candidates exact match
    for cand in (path_candidates or []):
        for p, methods in paths.items():
            # Normalize trailing slash
            if p.rstrip('/') == cand.rstrip('/'):
                op = methods.get(method)
                if op:
                    return p, op

    # 3) fallback: look for path prefix match
    for cand in (path_candidates or []):
        for p, methods in paths.items():
            if p.startswith(cand.rstrip('/') + '/') or p == cand:
                op = methods.get(method)
                if op:
                    return p, op

    return None, None


def collect_query_param_names(op):
    names = set()
    if not op:
        return names
    params = op.get('parameters') or []
    for p in params:
        if not isinstance(p, dict):
            continue
        if p.get('in') == 'query' or (p.get('in') is None and p.get('name')):
            names.add(p.get('name'))
    return names


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--spec', default='docs/openapi-auto.json', help='Path to OpenAPI JSON spec')
    parser.add_argument('--fail-on-missing', action='store_true', help='Exit non-zero if expected params are missing')
    args = parser.parse_args()

    spec_path = Path(args.spec)
    spec = load_spec(spec_path)
    if spec is None:
        sys.exit(2)

    any_missing = False
    report = []

    for opid, path_cands, method, expected_params in EXPECTED:
        found_path, op = find_operation(spec, opid=opid, path_candidates=path_cands, method=method)
        if not op:
            report.append({'op': opid, 'found': False, 'detail': f'Operation not found for path candidates {path_cands} method {method}'})
            any_missing = True
            continue

        qnames = collect_query_param_names(op)
        missing = [p for p in expected_params if p not in qnames]
        if missing:
            report.append({'op': opid, 'found': True, 'path': found_path, 'method': method, 'missing_query_params': missing, 'available_query_params': sorted(list(qnames))})
            any_missing = True
        else:
            report.append({'op': opid, 'found': True, 'path': found_path, 'method': method, 'missing_query_params': [], 'available_query_params': sorted(list(qnames))})

    # Print report
    print(json.dumps({'spec': str(spec_path), 'results': report}, indent=2, ensure_ascii=False))

    if args.fail_on_missing and any_missing:
        print('One or more expected query params are missing; failing (exit 1)')
        sys.exit(1)
    elif any_missing:
        print('One or more expected query params are missing')
        sys.exit(0)
    else:
        print('All expected query params present')
        sys.exit(0)


if __name__ == '__main__':
    main()
