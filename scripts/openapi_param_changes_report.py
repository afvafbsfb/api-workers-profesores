#!/usr/bin/env python3
"""Generate a human-readable report of parameter changes between two OpenAPI JSON files.

Usage: python scripts/openapi_param_changes_report.py old.json new.json [output.txt]
"""
import json
import sys
from pathlib import Path
from typing import Dict, Any, List


def load(p: Path) -> Dict[str, Any]:
    return json.loads(p.read_text(encoding='utf-8'))


def params_map(method_obj: Dict[str, Any]) -> Dict[tuple, Dict[str, Any]]:
    pm = {}
    for p in method_obj.get('parameters', []):
        key = (p.get('in'), p.get('name'))
        pm[key] = p
    return pm


def summarize(old: Dict[str, Any], new: Dict[str, Any]) -> List[str]:
    lines: List[str] = []
    old_paths = old.get('paths', {})
    new_paths = new.get('paths', {})
    all_paths = sorted(set(old_paths.keys()) | set(new_paths.keys()))
    for path in all_paths:
        o_methods = old_paths.get(path, {})
        n_methods = new_paths.get(path, {})
        methods = sorted(set(o_methods.keys()) | set(n_methods.keys()))
        for m in methods:
            o = o_methods.get(m)
            n = n_methods.get(m)
            if o is None and n is not None:
                lines.append(f"Added method {m.upper()} {path}")
                continue
            if o is not None and n is None:
                lines.append(f"Removed method {m.upper()} {path}")
                continue
            # both present: compare parameters
            o_params = params_map(o)
            n_params = params_map(n)
            added = [n_params[k] for k in sorted(set(n_params) - set(o_params))]
            removed = [o_params[k] for k in sorted(set(o_params) - set(n_params))]
            if added or removed:
                lines.append(f"Changes in {m.upper()} {path}:")
                for p in added:
                    lines.append(f"  + param {p.get('name')} (in={p.get('in')}) - {p.get('description', '')}")
                for p in removed:
                    lines.append(f"  - param {p.get('name')} (in={p.get('in')}) - {p.get('description', '')}")
    if not lines:
        lines.append('No parameter changes detected')
    return lines


def main():
    if len(sys.argv) < 3:
        print('Usage: openapi_param_changes_report.py old.json new.json [out.txt]')
        return 2
    oldp = Path(sys.argv[1])
    newp = Path(sys.argv[2])
    out = Path(sys.argv[3]) if len(sys.argv) > 3 else None
    old = load(oldp)
    new = load(newp)
    lines = summarize(old, new)
    text = '\n'.join(lines) + '\n'
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding='utf-8')
        print(f'Wrote report to {out}')
    else:
        print(text)


if __name__ == '__main__':
    raise SystemExit(main())
