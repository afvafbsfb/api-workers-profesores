#!/usr/bin/env python3
"""Validate critical endpoints heuristically against an OpenAPI JSON/YAML spec.

Usage: python scripts/validate_critical_endpoints.py --spec docs/served-openapi.json

This script marks endpoints as "critical" using these rules:
- All POST/PUT/PATCH/DELETE are critical.
- GET is critical when:
  - path contains a path parameter (e.g. /usuarios/{id}), OR
  - operationId or path matches sensitive keywords (usuario|academia|credentials|role|me|profile|recuperar), OR
  - tag is in a configured set (Usuarios, Academias, login, oauth), OR
  - response schema references sensitive models (Usuario, Academia), OR
  - the operation has an explicit x-permissions entry (we consider it critical)

For each critical endpoint we check that:
- operationId exists
- x-permissions exists (warning/error if missing)
- security is present (warning if missing)

The script prints a human-readable report and exits with code 1 if there are any errors
(missing operationId or missing x-permissions on a critical endpoint). It returns 0 otherwise.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Dict, List, Tuple, Any

CRITICAL_TAGS = {"Usuarios", "Academias", "login", "oauth", "Admin"}
SENSITIVE_KEYWORDS = re.compile(
    r"usuario|usuarios|academia|academias|credentials|role|roles|me|profile|recuperar|obtener|sensitive|private",
    re.IGNORECASE,
)


def load_spec(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    try:
        return json.loads(content)
    except Exception:
        # try YAML if json fails
        try:
            import yaml

            return yaml.safe_load(content)
        except Exception as e:
            raise RuntimeError(f"Failed to parse spec as JSON or YAML: {e}")


def response_refs_to_sensitive(responses: Dict[str, Any]) -> bool:
    # look for $ref to Usuario or Academia
    if not isinstance(responses, dict):
        return False
    for status, resp in responses.items():
        if not isinstance(resp, dict):
            continue
        content = resp.get("content") or {}
        for media, media_obj in (content.items() if isinstance(content, dict) else []):
            schema = media_obj.get("schema") if isinstance(media_obj, dict) else None
            if isinstance(schema, dict):
                ref = schema.get("$ref")
                if isinstance(ref, str) and ("/Usuario" in ref or "Usuario" in ref or "Academia" in ref):
                    return True
    return False


def is_get_critical(path: str, op: Dict[str, Any]) -> bool:
    # path param
    if re.search(r"\{[^/}]+\}", path):
        return True
    # operationId / path keywords
    opid = op.get("operationId", "")
    if SENSITIVE_KEYWORDS.search(opid or ""):
        return True
    if SENSITIVE_KEYWORDS.search(path):
        return True
    # tags
    tags = op.get("tags") or []
    if any(t in CRITICAL_TAGS for t in tags):
        return True
    # response schema
    if response_refs_to_sensitive(op.get("responses", {})):
        return True
    # x-permissions explicit
    if "x-permissions" in op:
        return True
    return False


def collect_endpoints(spec: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    critical = []
    non_critical = []
    paths = spec.get("paths", {}) or {}
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        for method_raw, op in methods.items():
            method = method_raw.lower()
            entry = {
                "path": path,
                "method": method,
                "operationId": op.get("operationId"),
                "tags": op.get("tags", []),
                "has_x_permissions": "x-permissions" in op,
                # consider security present if the key exists (even as an empty list)
                "has_security": ("security" in op),
                "op": op,
            }
            if method in ("post", "put", "patch", "delete"):
                critical.append(entry)
            elif method == "get":
                if is_get_critical(path, op):
                    critical.append(entry)
                else:
                    non_critical.append(entry)
            else:
                # other methods treat as non-critical by default
                non_critical.append(entry)
    return critical, non_critical


def validate_critical(critical: List[Dict[str, Any]]) -> Tuple[List[str], List[str], List[Dict[str, Any]]]:
    errors = []
    warnings = []
    details = []
    for e in critical:
        issues = []
        if not e.get("operationId"):
            issues.append("missing operationId")
            errors.append(f"{e['method'].upper()} {e['path']} - missing operationId")
        if not e.get("has_x_permissions"):
            issues.append("missing x-permissions")
            errors.append(f"{e['method'].upper()} {e['path']} - missing x-permissions")
        if not e.get("has_security"):
            # skip warning if x-permissions explicitly marks scope as public
            op = e.get('op') or {}
            xp = op.get('x-permissions') or {}
            if xp.get('scope') == 'public':
                # explicitly public endpoint; no security required
                pass
            else:
                warnings.append(f"{e['method'].upper()} {e['path']} - missing security")
        details.append({**e, "issues": issues})
    return errors, warnings, details


def print_report(errors: List[str], warnings: List[str], details: List[Dict[str, Any]], non_critical: List[Dict[str, Any]]):
    print("\n=== Critical endpoints report ===\n")
    print(f"Total critical endpoints checked: {len(details)}")
    print(f"Errors: {len(errors)}; Warnings: {len(warnings)}; Non-critical endpoints: {len(non_critical)}\n")

    if errors:
        print("Errors (must fix):")
        for err in errors:
            print("  -", err)
        print()

    if warnings:
        print("Warnings (recommend fix):")
        for w in warnings:
            print("  -", w)
        print()

    print("Critical endpoints details:")
    for d in details:
        opid = d.get("operationId") or "<none>"
        print(f" - {d['method'].upper():4} {d['path']:30} opId={opid} x-perm={d['has_x_permissions']} security={d['has_security']} issues={d['issues']}")

    print("\nEndpoints OUTSIDE automatic validation (for human review):")
    for d in non_critical:
        opid = d.get("operationId") or "<none>"
        print(f" - {d['method'].upper():4} {d['path']:30} opId={opid} tags={d.get('tags')} x-perm={d['has_x_permissions']}")


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", required=True, help="Path to OpenAPI JSON/YAML file")
    args = parser.parse_args(argv)

    spec_path = args.spec
    if not os.path.exists(spec_path):
        print(f"Spec file not found: {spec_path}")
        return 2
    spec = load_spec(spec_path)

    critical, non_critical = collect_endpoints(spec)
    errors, warnings, details = validate_critical(critical)
    print_report(errors, warnings, details, non_critical)

    # exit 1 if there are errors (missing operationId or x-permissions on critical endpoints)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
