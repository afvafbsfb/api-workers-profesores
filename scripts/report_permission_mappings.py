#!/usr/bin/env python3
"""Generate a report of permission -> operationId mappings using the explicit map
and the same heuristic used by merge_permissions_into_openapi.py
"""
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]
PERMS_IN = ROOT / 'docs' / 'permissions.json'
MAP_IN = ROOT / 'scripts' / 'permissions_map.json'
OPENAPI_IN = ROOT / 'docs' / 'served-openapi.json'
OUT = ROOT / 'docs' / 'permissions-mapping-report.json'

if not PERMS_IN.exists():
    raise SystemExit('permissions.json not found')
if not OPENAPI_IN.exists():
    raise SystemExit('served-openapi.json not found (run merge script first)')

perms = json.loads(PERMS_IN.read_text(encoding='utf-8')).get('permissions', [])
perm_map = {}
if MAP_IN.exists():
    try:
        perm_map = json.loads(MAP_IN.read_text(encoding='utf-8'))
    except Exception:
        perm_map = {}

openapi = json.loads(OPENAPI_IN.read_text(encoding='utf-8'))

# build op lookup by operationId
op_by_id = {}
for path, methods in openapi.get('paths', {}).items():
    for method, op in methods.items():
        op_id = op.get('operationId')
        if op_id:
            op_by_id[op_id] = {'path': path, 'method': method, 'operation': op}

# prepare tokenized op search
op_search = {}
for op_id, meta in op_by_id.items():
    op = meta['operation']
    tokens = ' '.join([op_id, op.get('summary','') or '', op.get('description','') or '', ' '.join(op.get('tags') or []), meta['path']]).lower()
    op_search[op_id] = set(re.findall(r"[a-zA-Z0-9_]+", tokens))

report = {'mappings': []}

for perm in perms:
    name = perm.get('name')
    desc = perm.get('description') or ''
    detected_roles = perm.get('detected_roles') or []
    entry = {'permission': name, 'detected_roles': detected_roles}

    if name and name in perm_map:
        mapped_to = perm_map[name]
        entry['mapping_source'] = 'explicit_map'
        entry['mapped_to'] = mapped_to
        entry['mapped_target_exists'] = mapped_to in op_by_id
        report['mappings'].append(entry)
        continue

    # heuristic: token overlap
    perm_tokens = set(re.findall(r"[a-zA-Z0-9_]+", desc.lower()))
    best = None
    best_score = 0
    for op_id, tokens in op_search.items():
        score = len(perm_tokens & tokens)
        if score > best_score:
            best_score = score
            best = op_id
    if best and best_score>0:
        entry['mapping_source'] = 'heuristic'
        entry['mapped_to'] = best
        entry['score'] = best_score
    else:
        entry['mapping_source'] = 'unmapped'
    report['mappings'].append(entry)

OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'Wrote {OUT}')
