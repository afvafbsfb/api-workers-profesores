#!/usr/bin/env python3
"""Annotate an OpenAPI JSON file with common query parameters missing from code-first generation.

Usage:
  python scripts/annotate_openapi_params.py docs/openapi-auto.json

This will create a backup of the original file (filename.bak) and overwrite the input file with
the annotated version. The script is idempotent: it will not duplicate parameters if they already exist.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import List, Dict, Any


def ensure_parameters(node: Dict[str, Any], params: List[Dict[str, Any]]) -> bool:
    """Ensure that node (a method object) has the parameters list including each param by name.
    Returns True if modified."""
    modified = False
    existing = node.get("parameters", [])
    existing_names = {(p.get("name"), p.get("in")) for p in existing}
    for p in params:
        key = (p.get("name"), p.get("in"))
        if key not in existing_names:
            existing.append(p)
            modified = True
    if modified:
        node["parameters"] = existing
    return modified


def main():
    if len(sys.argv) < 2:
        print("Usage: annotate_openapi_params.py <openapi-json-path>")
        sys.exit(2)

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"Error: file not found: {path}")
        sys.exit(1)

    data = json.loads(path.read_text(encoding="utf-8"))

    usuarios_params = [
        {
            "name": "academia_id",
            "in": "query",
            "required": False,
            "schema": {"type": "integer"},
            "description": "Filtrar por academia_id (nota: para roles de academia se fuerza este filtro)",
        },
        {
            "name": "rol",
            "in": "query",
            "required": False,
            "schema": {"type": "string"},
            "description": "Filtrar por nombre del rol (e.g. Admin_plataforma, Admin_academia, Profesor)",
        },
        {
            "name": "nombre",
            "in": "query",
            "required": False,
            "schema": {"type": "string"},
            "description": "Buscar por parte del nombre (ilike)",
        },
        {
            "name": "id",
            "in": "query",
            "required": False,
            "schema": {"type": "integer"},
            "description": "Filtrar por id del usuario (puede usarse como usuario_id)",
        },
    ]

    academias_params = [
        {
            "name": "id",
            "in": "query",
            "required": False,
            "schema": {"type": "integer"},
            "description": "Filtrar por id de academia (cuando el permiso lo permite)",
        }
    ]

    modified = False

    paths = data.setdefault("paths", {})

    # /usuarios/ may be present as '/usuarios/'
    for usuarios_path in ("/usuarios/", "/usuarios"):
        if usuarios_path in paths and "get" in paths[usuarios_path]:
            if ensure_parameters(paths[usuarios_path]["get"], usuarios_params):
                print(f"Annotated parameters for GET {usuarios_path}")
                modified = True

    # /academias may be present as '/academias' or '/academias/'
    for academias_path in ("/academias", "/academias/"):
        if academias_path in paths and "get" in paths[academias_path]:
            if ensure_parameters(paths[academias_path]["get"], academias_params):
                print(f"Annotated parameters for GET {academias_path}")
                modified = True

    if modified:
        bak = path.with_suffix(path.suffix + ".bak")
        bak.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Wrote annotated OpenAPI to {path} (backup at {bak})")
    else:
        print("No changes required (parameters already present)")


if __name__ == "__main__":
    main()
