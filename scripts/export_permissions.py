#!/usr/bin/env python3
"""
Export permissions metadata from src/shared/application/permissions.py into docs/permissions.yaml
This script does static analysis (AST) and does NOT import the application code.

Usage: python scripts/export_permissions.py
"""
from pathlib import Path
import ast
import textwrap
import re
import glob

from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
PERMISSIONS_PATH = ROOT / 'src' / 'shared' / 'application' / 'permissions.py'
OUT_DIR = ROOT / 'docs'
OUT_PATH = OUT_DIR / 'permissions.yaml'

if not PERMISSIONS_PATH.exists():
    raise SystemExit(f"permissions.py not found at {PERMISSIONS_PATH}")

src = PERMISSIONS_PATH.read_text(encoding='utf-8')
module = ast.parse(src)

# Helper: collect string constants in a node
class StringCollector(ast.NodeVisitor):
    def __init__(self):
        self.strings = []
    def visit_Constant(self, node):
        if isinstance(node.value, str):
            self.strings.append(node.value)
    # Python <3.8 fallback for ast.Str
    def visit_Str(self, node):
        self.strings.append(node.s)


def collect_known_roles(root: Path):
    """Scan a few repository files (seeds, init scripts, models) to collect candidate role names.
    Returns a set of role name strings as they appear in DB/seed (e.g. 'Admin_plataforma').
    """
    candidates = set()
    # prefer explicit whitelist if present
    whitelist = root / 'scripts' / 'roles_whitelist.txt'
    if whitelist.exists():
        try:
            for line in whitelist.read_text(encoding='utf-8').splitlines():
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                candidates.add(line)
        except Exception:
            pass
        # return normalized set
        extra = set()
        for c in candidates:
            extra.add(c)
            extra.add(c.lower())
        return extra
    # Files to scan: create_database.sql, init_db_pruebas_test.py, and any models.py under src/**/infrastructure
    files = []
    files.append(root / 'docs' / 'create_database.sql')
    files.append(root / 'init_db_pruebas_test.py')
    files.extend(Path(p) for p in glob.glob(str(root / 'src' / '**' / 'infrastructure' / 'models.py'), recursive=True))

    str_re = re.compile(r"'([^']{3,100})'|\"([^\"]{3,100})\"")
    role_pattern = re.compile(r'^[A-Za-z]+(_[A-Za-z]+)*$')
    for f in files:
        try:
            text = Path(f).read_text(encoding='utf-8')
        except Exception:
            continue
        for m in str_re.finditer(text):
            val = m.group(1) or m.group(2)
            if not val:
                continue
            val = val.strip()
            # narrow to words like Admin_plataforma, Profesor_academia, etc.
            if role_pattern.match(val) and len(val) > 4:
                candidates.add(val)
    # normalize some casing variants to add lowercase forms
    extra = set()
    for c in candidates:
        extra.add(c)
        extra.add(c.lower())
    return {x for x in extra}


def extract_permissions_info(module_ast, known_roles:set):
    funcs = []
    for node in module_ast.body:
        if isinstance(node, ast.FunctionDef) and node.name.startswith('can_'):
            info = {'name': node.name}
            doc = ast.get_docstring(node) or ''
            info['description'] = doc.strip()
            # params
            params = [a.arg for a in node.args.args]
            info['params'] = params
            # collect string constants inside function body
            sc = StringCollector()
            sc.visit(node)
            strings = sc.strings
            # heuristics: candidate roles are strings that look like role names
            role_pattern = re.compile(r'^[A-Za-z_]+$')
            raw_roles = {s for s in strings if role_pattern.match(s) and len(s) > 3}
            # intersect with known_roles (case-insensitive)
            detected = set()
            for r in raw_roles:
                if r in known_roles or r.lower() in known_roles:
                    detected.add(r)
            # if intersection is empty, fall back to a pruned raw_roles (remove obvious field names)
            if not detected:
                # filter out common field names and generic error keys
                blacklist = {'nombre', 'fecha_baja', 'email', 'password', 'estado', 'rol_id', 'rol_nombre', 'nombre', 'academia_id'}
                detected = {r for r in raw_roles if r not in blacklist}
            info['detected_roles'] = sorted(detected)
            funcs.append(info)
    return funcs

known_roles = collect_known_roles(ROOT)
perms = extract_permissions_info(module, known_roles)

# Ensure output dir
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Simple YAML emitter (no external deps)
lines = []
lines.append('# Auto-generated from src/shared/application/permissions.py')
lines.append('# Regenerate with: python scripts/export_permissions.py')
lines.append('permissions:')
for p in perms:
    lines.append(f"  - name: {p['name']}")
    # description as block scalar
    if p['description']:
        desc = textwrap.indent(p['description'].rstrip(), '      ')
        lines.append('    description: |')
        for dline in p['description'].splitlines():
            lines.append('      ' + dline)
    else:
        lines.append('    description: ""')
    # params
    if p['params']:
        lines.append('    params:')
        for prm in p['params']:
            lines.append(f"      - {prm}")
    else:
        lines.append('    params: []')
    # roles
    if p['detected_roles']:
        lines.append('    detected_roles:')
        for r in p['detected_roles']:
            lines.append(f"      - {r}")
    else:
        lines.append('    detected_roles: []')

OUT_PATH.write_text('\n'.join(lines) + '\n', encoding='utf-8')
print(f'Wrote {OUT_PATH}')
# Also write a JSON representation for easy consumption by other tools
OUT_JSON_PATH = OUT_DIR / 'permissions.json'
json_payload = {'permissions': perms}
OUT_JSON_PATH.write_text(json.dumps(json_payload, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'Wrote {OUT_JSON_PATH}')
