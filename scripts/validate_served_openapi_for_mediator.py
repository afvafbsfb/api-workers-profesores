#!/usr/bin/env python3
"""Validate served-openapi.json for mediator consumption.
Checks:
 - x-permissions presence for configured ops
 - allowed_roles normalized to Admin_* casing
 - allowed_target_roles and mutable_fields_by_role keys normalized
 - scope or scope_by_role present where expected
Generates a JSON report and prints a human summary.
Usage: python scripts/validate_served_openapi_for_mediator.py [--spec PATH] [--fix]
If --fix is provided, the script will normalize nested role keys in-place in the provided spec file.
"""
from pathlib import Path
import json
import re
import sys
import argparse

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SPEC = ROOT / 'docs' / 'served-openapi.json'
REPORT = ROOT / 'docs' / 'permissions-validation-report.json'

# CLI args
parser = argparse.ArgumentParser(description='Validate served-openapi.json for mediator consumption')
parser.add_argument('--spec', default=str(DEFAULT_SPEC), help='Path to served-openapi.json')
parser.add_argument('--fix', action='store_true', help='Apply normalization fixes in-place')
args = parser.parse_args()

SPEC = Path(args.spec)

if not SPEC.exists():
    raise SystemExit(f'served-openapi.json not found: {SPEC}')

spec = json.loads(SPEC.read_text(encoding='utf-8'))
paths = spec.get('paths', {})

# operations to validate (path, method, human name)
critical_ops = [
    ('/usuarios/', 'get', 'usuarios.listar_usuarios'),
    ('/usuarios/', 'post', 'usuarios.crear_usuario'),
    ('/usuarios/{usuario_id}', 'patch', 'usuarios.actualizar_usuario'),
    ('/usuarios/{usuario_id}', 'delete', 'usuarios.eliminar_usuario'),
    ('/academias', 'get', 'academias.listar_academias'),
    ('/academias', 'post', 'academias.crear_academia'),
    ('/academias/{academia_id}', 'patch', 'academias.modificar_academia'),
    ('/academias/{academia_id}', 'delete', 'academias.eliminar_academia'),
]

issues = []
changes = []

def normalize_role_name(r: str) -> str:
    if not r:
        return r
    return r[0].upper() + r[1:]

for path, method, opid in critical_ops:
    op = paths.get(path, {}).get(method)
    if not op:
        issues.append({'op': opid, 'problem': 'operation_missing', 'detail': f'{method.upper()} {path} not found in spec'})
        continue
    xp = op.get('x-permissions')
    if not xp:
        issues.append({'op': opid, 'problem': 'x-permissions_missing', 'detail': f'x-permissions not present for {method.upper()} {path}'})
        continue
    # allowed_roles
    allowed = xp.get('allowed_roles')
    if not allowed:
        issues.append({'op': opid, 'problem': 'allowed_roles_missing', 'detail': f'allowed_roles missing for {opid}'})
    else:
        bad = [r for r in allowed if not re.match(r'^[A-Z][A-Za-z0-9_]+$', r)]
        if bad:
            issues.append({'op': opid, 'problem': 'allowed_roles_not_normalized', 'detail': f'roles not normalized: {bad}', 'value': allowed})
    # allowed_target_roles normalization
    atr = xp.get('allowed_target_roles')
    if atr and isinstance(atr, dict):
        bad_keys = [k for k in atr.keys() if not re.match(r'^[A-Z][A-Za-z0-9_]+$', k)]
        bad_vals = []
        for k, vals in atr.items():
            for v in vals:
                if not re.match(r'^[A-Z][A-Za-z0-9_]+$', v):
                    bad_vals.append((k, v))
        if bad_keys or bad_vals:
            issues.append({'op': opid, 'problem': 'allowed_target_roles_not_normalized', 'detail': {'bad_keys': bad_keys, 'bad_vals': bad_vals}})
    # mutable_fields_by_role normalization
    mfr = xp.get('mutable_fields_by_role')
    if mfr and isinstance(mfr, dict):
        bad_keys = [k for k in mfr.keys() if not re.match(r'^[A-Z][A-Za-z0-9_]+$', k)]
        if bad_keys:
            issues.append({'op': opid, 'problem': 'mutable_fields_by_role_keys_not_normalized', 'detail': {'bad_keys': bad_keys}})
    # scope or scope_by_role check
    if 'scope' not in xp and 'scope_by_role' not in xp:
        # for list and create operations we expect scope if not global
        if path.startswith('/usuarios') or path.startswith('/academias'):
            issues.append({'op': opid, 'problem': 'scope_missing', 'detail': 'Neither scope nor scope_by_role present'})

# report
report = {'issues': issues, 'fixed': False, 'fixes': []}

# Offer to fix normalization if requested
if args.fix:
    modified = False
    for path, methods in paths.items():
        for method, op in methods.items():
            xp = op.get('x-permissions')
            if not xp:
                continue
            # normalize allowed_roles list
            if 'allowed_roles' in xp:
                new_allowed = [normalize_role_name(r) for r in xp.get('allowed_roles') or []]
                if new_allowed != xp.get('allowed_roles'):
                    changes.append({'path': path, 'method': method, 'field': 'allowed_roles', 'before': xp.get('allowed_roles'), 'after': new_allowed})
                    xp['allowed_roles'] = new_allowed
                    modified = True
            # normalize allowed_target_roles keys and values
            if 'allowed_target_roles' in xp and isinstance(xp['allowed_target_roles'], dict):
                old = dict(xp['allowed_target_roles'])
                new = {}
                for k, vals in old.items():
                    nk = normalize_role_name(k)
                    nvals = [normalize_role_name(v) for v in vals]
                    new[nk] = nvals
                    if nk != k or nvals != vals:
                        changes.append({'path': path, 'method': method, 'field': 'allowed_target_roles', 'before': {k: vals}, 'after': {nk: nvals}})
                xp['allowed_target_roles'] = new
                modified = True
            # normalize mutable_fields_by_role keys
            if 'mutable_fields_by_role' in xp and isinstance(xp['mutable_fields_by_role'], dict):
                old = dict(xp['mutable_fields_by_role'])
                new = {}
                for k, vals in old.items():
                    nk = normalize_role_name(k)
                    new[nk] = vals
                    if nk != k:
                        changes.append({'path': path, 'method': method, 'field': 'mutable_fields_by_role', 'before': {k: vals}, 'after': {nk: vals}})
                xp['mutable_fields_by_role'] = new
                modified = True
    if modified:
        SPEC.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding='utf-8')
        report['fixed'] = True
        report['fixes'] = changes

REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')

# print summary
print('Validation report written to', REPORT)
if not issues:
    print('No issues found — served-openapi.json looks ready for mediator.')
else:
    print(len(issues), 'issue(s) found:')
    for it in issues:
        print('-', it['op'], it['problem'])
    if args.fix:
        if report['fixed']:
            print('Applied fixes:')
            for c in changes:
                print('-', c['path'], c['method'], c['field'])
        else:
            print('No automatic fixes applied.')
    # Fail if any issues detected so CI step is blocking
    sys.exit(1)
