#!/usr/bin/env python3
"""
Merge permissions.json into openapi-auto.json producing docs/served-openapi.json

Heuristics:
- operationId: try to extract from description like 'for usuarios.listar_usuarios'
- fallback: use first tag + sanitized summary
- list endpoints -> paginated schema Paginated<Schema>
- map permissions to operations by token overlap between permission description and operation text
"""
from pathlib import Path
import json
import re
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
OPENAPI_IN = ROOT / 'docs' / 'openapi-auto.json'
PERMS_IN = ROOT / 'docs' / 'permissions.json'
OUT = ROOT / 'docs' / 'served-openapi.json'

if not OPENAPI_IN.exists():
    raise SystemExit(f"OpenAPI not found: {OPENAPI_IN}")
if not PERMS_IN.exists():
    raise SystemExit(f"Permissions not found: {PERMS_IN}")

def load_json(p: Path):
    return json.loads(p.read_text(encoding='utf-8'))

openapi = load_json(OPENAPI_IN)
perms = load_json(PERMS_IN).get('permissions', [])

components = openapi.setdefault('components', {})
schemas = components.setdefault('schemas', {})

def ensure_paginated(schema_name, item_ref):
    pag_name = f'Paginated{schema_name}'
    if pag_name in schemas:
        return pag_name
    # Include pagination constraints if available from shared config
    try:
        from src.shared.pagination import DEFAULT_PAGE, DEFAULT_SIZE, MAX_PAGE_SIZE
        page_schema = {'type': 'integer', 'minimum': 1, 'default': DEFAULT_PAGE}
        size_schema = {'type': 'integer', 'minimum': 1, 'default': DEFAULT_SIZE, 'maximum': MAX_PAGE_SIZE}
    except Exception:
        page_schema = {'type': 'integer'}
        size_schema = {'type': 'integer'}

    schemas[pag_name] = {
        'type': 'object',
        'properties': {
            'totalElements': {'type': 'integer'},
            'items': {'type': 'array', 'items': {'$ref': item_ref}},
            'page': page_schema,
            'size': size_schema,
        }
    }
    return pag_name

def extract_operation_id_from_description(desc: str):
    if not desc:
        return None
    m = re.search(r'for\s+([A-Za-z0-9_.]+)', desc)
    if m:
        return m.group(1)
    return None

def sanitize_summary(tag, summary):
    s = summary or ''
    s = re.sub(r'[^A-Za-z0-9]+', '_', s).strip('_')
    return f'{tag}.{s}' if tag else s

# Build list of operations
ops = []  # tuples (path, method, operation)
for path, methods in openapi.get('paths', {}).items():
    for method, operation in methods.items():
        if method.lower() not in ('get','post','put','patch','delete','options','head'):
            continue
        ops.append((path, method.lower(), operation))

# Ensure operationId and responses[200].content
for path, method, op in ops:
    # ensure operationId
    op_id = op.get('operationId')
    if not op_id:
        op_id = extract_operation_id_from_description(op.get('description','') or '')
    if not op_id:
        tag = (op.get('tags') or [None])[0]
        op_id = sanitize_summary(tag, op.get('summary') or op.get('description') or f'{method}_{path}')
    op['operationId'] = op_id

    # Ensure 200 response has content schema
    responses = op.setdefault('responses', {})
    resp200 = responses.setdefault('200', {})
    content = resp200.get('content')
    if not content:
        # heuristics: list endpoints if 'listar' in description/summary or path ends with '/'
        text = ' '.join([str(op.get('summary') or ''), str(op.get('description') or ''), path]).lower()
        is_list = ('listar' in text) or ('list' in text) or path.rstrip('/').endswith('/usuarios') or path.rstrip('/').endswith('/academias') or path.endswith('/')
        if is_list:
            # determine item schema by tag or path
            tag = (op.get('tags') or [None])[0]
            # guess component name
            if tag:
                comp_name = tag.rstrip('s')
            else:
                # fallback: last path segment
                seg = path.strip('/').split('/')[-1]
                comp_name = seg.rstrip('s')
            comp_name = comp_name[0].upper() + comp_name[1:] if comp_name else 'Item'
            if comp_name in schemas:
                item_ref = f"#/components/schemas/{comp_name}"
            else:
                # default to Usuario if users in path
                if 'usuarios' in path:
                    item_ref = '#/components/schemas/Usuario'
                    comp_name = 'Usuario'
                elif 'academias' in path:
                    item_ref = '#/components/schemas/Academia'
                    comp_name = 'Academia'
                else:
                    # generic object
                    schemas.setdefault('Item', {'type':'object'})
                    item_ref = '#/components/schemas/Item'
            pag_name = ensure_paginated(comp_name, item_ref)
            resp200['content'] = {'application/json': {'schema': {'$ref': f'#/components/schemas/{pag_name}'}}}
        else:
            # detail endpoint: pick component by tag or last path segment
            tag = (op.get('tags') or [None])[0]
            if tag:
                comp_name = tag.rstrip('s')
            else:
                comp_name = path.strip('/').split('/')[-1]
            comp_name = comp_name[0].upper() + comp_name[1:] if comp_name else None
            if comp_name and comp_name in schemas:
                resp200['content'] = {'application/json': {'schema': {'$ref': f'#/components/schemas/{comp_name}'}}}
            else:
                # leave as-is (no-op)
                pass

# Prepare operation search strings for mapping
op_search = {}
for path, method, op in ops:
    key = (path, method)
    tokens = ' '.join([op.get('operationId',''), op.get('summary','') or '', op.get('description','') or '', ' '.join(op.get('tags') or []), path]).lower()
    op_search[key] = set(re.findall(r"[a-zA-Z0-9_]+", tokens))

def normalize_role(r: str) -> str:
    if not r:
        return r
    # keep underscores, just capitalize first letter to match 'Admin_plataforma'
    return r[0].upper() + r[1:]


def load_permissions_map():
    """Load explicit mapping file if present.

    Format (JSON): { "can_query_users": "usuarios.listar_usuarios", ... }
    The mapped value is an operationId present in the generated OpenAPI.
    """
    map_p = ROOT / 'scripts' / 'permissions_map.json'
    if not map_p.exists():
        return {}
    try:
        return json.loads(map_p.read_text(encoding='utf-8'))
    except Exception:
        print(f'Warning: failed to read permissions map {map_p} — ignoring')
        return {}

# load explicit map and apply it first
perm_map = load_permissions_map()
unmapped = []
processed_names = set()

for perm in perms:
    name = perm.get('name')
    mapped = None
    if name:
        processed_names.add(name)
    if name and name in perm_map:
        mapped = perm_map[name]
        # mapped can be a string (operationId), a list of operationIds, or an object with metadata
        metadata = None
        op_ids = []

        if isinstance(mapped, str):
            op_ids = [mapped]
        elif isinstance(mapped, list):
            op_ids = list(mapped)
        elif isinstance(mapped, dict):
            # metadata may include operationId as str or list
            metadata = mapped
            opv = mapped.get('operationId')
            if isinstance(opv, str):
                op_ids = [opv]
            elif isinstance(opv, list):
                op_ids = list(opv)
            else:
                # no explicit operationId in metadata: fall back to heuristic below
                op_ids = []
        else:
            print(f'Unsupported map entry for {name}: {mapped!r}')
            unmapped.append(name)
            continue

        if not op_ids:
            # nothing explicitly mapped; fallback to heuristic - leave for later
            # record unmapped for reporting
            unmapped.append(name)
            continue

        # For each operationId in op_ids, find the operation and attach x-permissions
        attached_any = False
        for target_op_id in op_ids:
            found = None
            for (path, method, operation) in ops:
                if operation.get('operationId') == target_op_id:
                    found = (path, method, operation)
                    break
            if not found:
                print(f'Permissions map points to unknown operationId: {target_op_id} (perm: {name})')
                continue

            path, method, operation = found
            xp = operation.setdefault('x-permissions', {})

            # if metadata present, copy fields, normalizing role names where needed
            if metadata:
                # copy allowed_roles normalizing casing
                if 'allowed_roles' in metadata:
                    xp['allowed_roles'] = sorted({normalize_role(r) for r in metadata.get('allowed_roles') or []})

                # enforced_filters and note copy as-is
                if 'enforced_filters' in metadata:
                    xp['enforced_filters'] = metadata['enforced_filters']
                if 'note' in metadata:
                    xp['note'] = metadata['note']

                # scope (single string)
                if 'scope' in metadata:
                    xp['scope'] = metadata['scope']
                    # if explicitly public scope, ensure the OpenAPI operation has no security requirements
                    if metadata.get('scope') == 'public':
                        operation['security'] = []

                # scope_by_role: normalize role keys
                if 'scope_by_role' in metadata:
                    sb = {}
                    for rk, rv in (metadata.get('scope_by_role') or {}).items():
                        sb[normalize_role(rk)] = rv
                    xp['scope_by_role'] = sb

                # allowed_target_roles: normalize keys and values (role lists)
                if 'allowed_target_roles' in metadata:
                    atr = {}
                    for rk, rv in (metadata.get('allowed_target_roles') or {}).items():
                        nk = normalize_role(rk)
                        # rv may be list of role names
                        if isinstance(rv, (list, tuple)):
                            atr[nk] = [normalize_role(x) for x in rv]
                        else:
                            atr[nk] = rv
                    xp['allowed_target_roles'] = atr

                # mutable_fields_by_role: normalize keys
                if 'mutable_fields_by_role' in metadata:
                    mfb = {}
                    for rk, rv in (metadata.get('mutable_fields_by_role') or {}).items():
                        mfb[normalize_role(rk)] = rv
                    xp['mutable_fields_by_role'] = mfb
            else:
                # fallback to detected_roles from permissions.json
                roles = [normalize_role(r) for r in (perm.get('detected_roles') or [])]
                xp['allowed_roles'] = sorted(set(roles))

            xp['source'] = 'permissions_map'
            xp['generated_at'] = datetime.now(timezone.utc).isoformat()
            attached_any = True

        if attached_any:
            continue
        else:
            unmapped.append(name)
            continue

    # fallback to token-overlap heuristic
    perm_desc = (perm.get('description') or '') .lower()
    perm_tokens = set(re.findall(r"[a-zA-Z0-9_]+", perm_desc))
    best = None
    best_score = 0
    for (path, method), tokens in op_search.items():
        score = len(perm_tokens & tokens)
        if score > best_score:
            best_score = score
            best = (path, method)
    if best and best_score>0:
        # attach x-permissions
        path, method = best
        operation = openapi['paths'][path][method]
        roles = [normalize_role(r) for r in (perm.get('detected_roles') or [])]
        xp = operation.setdefault('x-permissions', {})
        xp['allowed_roles'] = sorted(set(roles))
        xp['source'] = 'permissions.json'
        xp['generated_at'] = datetime.now(timezone.utc).isoformat()
    else:
        # no mapping found; collect for reporting
        unmapped.append(name or '(unnamed)')

if unmapped:
    report_p = OUT.parent / 'permissions-unmapped.json'
    report_p.write_text(json.dumps({'unmapped': unmapped}, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Warning: {len(unmapped)} permissions left unmapped. See {report_p}')

# Also process permissions declared in scripts/permissions_map.json but not present in docs/permissions.json
for name, mapped in perm_map.items():
    if name in processed_names:
        continue
    metadata = None
    op_ids = []

    if isinstance(mapped, str):
        op_ids = [mapped]
    elif isinstance(mapped, list):
        op_ids = list(mapped)
    elif isinstance(mapped, dict):
        metadata = mapped
        opv = mapped.get('operationId')
        if isinstance(opv, str):
            op_ids = [opv]
        elif isinstance(opv, list):
            op_ids = list(opv)
        else:
            op_ids = []
    else:
        print(f'Unsupported map entry for {name}: {mapped!r}')
        unmapped.append(name)
        continue

    if not op_ids:
        unmapped.append(name)
        continue

    attached_any = False
    for target_op_id in op_ids:
        found = None
        for (path, method, operation) in ops:
            if operation.get('operationId') == target_op_id:
                found = (path, method, operation)
                break
        if not found:
            print(f'Permissions map points to unknown operationId: {target_op_id} (perm: {name})')
            continue

        path, method, operation = found
        xp = operation.setdefault('x-permissions', {})

        if metadata:
            if 'allowed_roles' in metadata:
                xp['allowed_roles'] = sorted({normalize_role(r) for r in metadata.get('allowed_roles') or []})
            if 'enforced_filters' in metadata:
                xp['enforced_filters'] = metadata['enforced_filters']
            if 'note' in metadata:
                xp['note'] = metadata['note']
            if 'scope' in metadata:
                xp['scope'] = metadata['scope']
                # if explicitly public scope, ensure the OpenAPI operation has no security requirements
                if metadata.get('scope') == 'public':
                    operation['security'] = []
            if 'scope_by_role' in metadata:
                sb = {}
                for rk, rv in (metadata.get('scope_by_role') or {}).items():
                    sb[normalize_role(rk)] = rv
                xp['scope_by_role'] = sb
            if 'allowed_target_roles' in metadata:
                atr = {}
                for rk, rv in (metadata.get('allowed_target_roles') or {}).items():
                    nk = normalize_role(rk)
                    if isinstance(rv, (list, tuple)):
                        atr[nk] = [normalize_role(x) for x in rv]
                    else:
                        atr[nk] = rv
                xp['allowed_target_roles'] = atr
            if 'mutable_fields_by_role' in metadata:
                mfb = {}
                for rk, rv in (metadata.get('mutable_fields_by_role') or {}).items():
                    mfb[normalize_role(rk)] = rv
                xp['mutable_fields_by_role'] = mfb
        else:
            # fallback to empty allowed_roles if no metadata given
            xp['allowed_roles'] = []

        xp['source'] = 'permissions_map'
        xp['generated_at'] = datetime.now(timezone.utc).isoformat()
        attached_any = True

    if attached_any:
        # mark as processed
        processed_names.add(name)
        continue
    else:
        unmapped.append(name)
        continue

# write output
OUT.write_text(json.dumps(openapi, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'Wrote {OUT}')
