#!/usr/bin/env python3
"""Validate synchronization between permissions_map.json, permissions.py and OpenAPI spec.

Usage:
  python scripts/validate_permissions_sync.py --map scripts/permissions_map.json --spec docs/openapi-auto.json --code src/shared/application/permissions.py

Exit code: 0 = ok (no missing functions or operationIds), 1 = missing items found
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
from typing import Dict, List, Tuple, Any


def load_json(path: str) -> Dict[str, Any]:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def collect_operation_ids_from_spec(spec: Dict[str, Any]) -> List[str]:
    ids = []
    paths = spec.get('paths', {}) or {}
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        for method, op in methods.items():
            if not isinstance(op, dict):
                continue
            opid = op.get('operationId')
            if isinstance(opid, str) and opid:
                ids.append(opid)
    return ids


def collect_functions_from_code(code_path: str) -> Dict[str, ast.FunctionDef]:
    with open(code_path, 'r', encoding='utf-8') as f:
        src = f.read()
    tree = ast.parse(src)
    funcs: Dict[str, ast.FunctionDef] = {}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            funcs[node.name] = node
    return funcs


def function_source_contains(node: ast.FunctionDef, text: str) -> bool:
    # simple heuristic: check within function body source text
    try:
        import inspect
        src = ast.get_source_segment(open(node.lineno and node.body[0].lineno and __file__, 'r').read(), node)
    except Exception:
        # fallback: convert AST nodes to string
        try:
            src = ast.unparse(node)
        except Exception:
            src = ''
    return text in src


def heuristically_check_scope(function_node: ast.FunctionDef, json_entry: Dict[str, Any]) -> List[str]:
    issues = []
    # read function source via ast.unparse (not perfect but usable)
    try:
        src = ast.unparse(function_node)
    except Exception:
        src = ''

    # If JSON declares scope_by_role, expect role keywords in function
    if 'scope_by_role' in json_entry:
        role_keywords = ['admin_plataforma', 'admin_academia', 'profesor_academia']
        found = [r for r in role_keywords if r in src]
        if not found:
            issues.append('scope_by_role in JSON but function does not reference role keywords')

    # If JSON declares scope public but function checks for current_user presence, warn
    if json_entry.get('scope') == 'public':
        if re.search(r"if\s+not\s+current_user|not\s+current_user", src):
            issues.append('JSON scope=public but function appears to require authentication')

    return issues


def normalize_opids(field: Any) -> List[str]:
    if isinstance(field, str):
        return [field]
    if isinstance(field, list):
        return [str(x) for x in field]
    if isinstance(field, dict):
        # support {operationId: 'x'} or mapping
        if 'operationId' in field:
            return normalize_opids(field['operationId'])
    return []


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--map', required=True, help='Path to permissions_map.json')
    parser.add_argument('--spec', required=False, help='Path to openapi spec (json/yaml). If omitted tries docs/openapi-auto.json then docs/served-openapi.json')
    parser.add_argument('--code', required=True, help='Path to permissions.py')
    args = parser.parse_args(argv)

    map_path = args.map
    code_path = args.code
    spec_path = args.spec

    if not os.path.exists(map_path):
        print(f'Map file not found: {map_path}')
        return 2
    if not os.path.exists(code_path):
        print(f'Code file not found: {code_path}')
        return 2

    perm_map = load_json(map_path)

    # load spec
    spec = None
    tried = []
    if spec_path:
        tried.append(spec_path)
        if os.path.exists(spec_path):
            spec = load_json(spec_path)
    else:
        for candidate in ('docs/openapi-auto.json', 'docs/served-openapi.json'):
            tried.append(candidate)
            if os.path.exists(candidate):
                spec = load_json(candidate)
                spec_path = candidate
                break

    if spec is None:
        print('OpenAPI spec not found. Tried:', tried)
        return 2

    opids = set(collect_operation_ids_from_spec(spec))
    funcs = collect_functions_from_code(code_path)

    missing_functions = []
    missing_opids = []
    scope_issues = []

    for key, entry in perm_map.items():
        # expect a function with same name
        if key not in funcs:
            missing_functions.append(key)
        else:
            # heuristics: check scope consistency
            issues = heuristically_check_scope(funcs[key], entry)
            if issues:
                scope_issues.append({'permission': key, 'issues': issues})

        # check operationId(s)
        op_field = entry.get('operationId')
        op_list = normalize_opids(op_field)
        for op in op_list:
            if op and op not in opids:
                missing_opids.append({'permission': key, 'operationId': op})

    # Print report
    print('\n=== permissions_map.json vs permissions.py / OpenAPI spec report ===\n')
    print(f'Map file: {map_path}')
    print(f'Code file: {code_path}')
    print(f'Spec file: {spec_path}\n')

    if missing_functions:
        print('Permissions declared in JSON but missing corresponding function in code:')
        for m in missing_functions:
            print(' -', m)
    else:
        print('All permissions in JSON have corresponding functions in code.')

    print()

    if missing_opids:
        print('OperationIds referenced in JSON but missing in OpenAPI spec:')
        for m in missing_opids:
            print(' -', m['permission'], '->', m['operationId'])
    else:
        print('All operationIds referenced in JSON exist in the OpenAPI spec.')

    print()
    if scope_issues:
        print('Scope heuristic issues found (manual review recommended):')
        for s in scope_issues:
            print(' -', s['permission'], ':', '; '.join(s['issues']))
    else:
        print('No obvious scope mismatches detected by heuristic.')

    errors = bool(missing_functions or missing_opids)
    print('\nSummary: missing_functions=%d, missing_opids=%d, scope_issues=%d' % (len(missing_functions), len(missing_opids), len(scope_issues)))

    return 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
