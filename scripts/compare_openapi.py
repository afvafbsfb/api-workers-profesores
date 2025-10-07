#!/usr/bin/env python3
"""Compare OpenAPI files semantically.

Usage:
  # Compare working tree file vs committed HEAD version for each path
  python scripts/compare_openapi.py docs/openapi-auto.json docs/openapi-auto.yml

  # Compare two arbitrary files directly
  python scripts/compare_openapi.py --pair left.json right.json

Returns exit code 0 when semantically equal, 1 otherwise.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except Exception:
    yaml = None


def load_file_guess(path: Path):
    text = path.read_text(encoding="utf-8")
    # try json then yaml
    try:
        return json.loads(text)
    except Exception:
        if yaml:
            return yaml.safe_load(text)
        raise


def load_git_head(path: str):
    # Returns object loaded from git HEAD:path or None if not present
    try:
        r = subprocess.run(["git", "show", f"HEAD:{path}"], capture_output=True, text=True, check=True)
        txt = r.stdout
        try:
            return json.loads(txt)
        except Exception:
            if yaml:
                return yaml.safe_load(txt)
            return None
    except subprocess.CalledProcessError:
        return None


def normalize(obj: Any):
    # Recursively normalize dicts and lists to allow semantic comparison.
    if isinstance(obj, dict):
        return {k: normalize(obj[k]) for k in sorted(obj.keys())}
    if isinstance(obj, list):
        # If list of dicts and they look like tags -> sort by name
        if all(isinstance(i, dict) and "name" in i for i in obj):
            return sorted((normalize(i) for i in obj), key=lambda x: x.get("name"))
        # If list of parameters -> sort by (in,name)
        if all(isinstance(i, dict) and ("in" in i or "name" in i) for i in obj):
            return sorted((normalize(i) for i in obj), key=lambda x: (x.get("in"), x.get("name")))
        # Generic: normalize elements and sort by their JSON representation to be deterministic
        normed = [normalize(i) for i in obj]
        try:
            return sorted(normed, key=lambda x: json.dumps(x, sort_keys=True))
        except Exception:
            return normed
    return obj


def pretty(obj: Any):
    return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False)


def compare_objects(a: Any, b: Any):
    na = normalize(a)
    nb = normalize(b)
    return na == nb, na, nb


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="*", help="Paths to compare. If given one or more, each path is compared between working tree and HEAD. If --pair used, supply exactly two files to compare directly.")
    parser.add_argument("--pair", action="store_true", help="Compare two files directly: left right")
    args = parser.parse_args()

    diffs = []
    if args.pair:
        if len(args.paths) != 2:
            print("--pair requires exactly two file paths", file=sys.stderr)
            return 2
        left = Path(args.paths[0])
        right = Path(args.paths[1])
        if not left.exists():
            print(f"Left file not found: {left}", file=sys.stderr)
            return 2
        if not right.exists():
            print(f"Right file not found: {right}", file=sys.stderr)
            return 2
        a = load_file_guess(left)
        b = load_file_guess(right)
        equal, na, nb = compare_objects(a, b)
        if not equal:
            print(f"Files differ: {left} vs {right}\n")
            print("--- LEFT (normalized) ---")
            print(pretty(na))
            print("--- RIGHT (normalized) ---")
            print(pretty(nb))
            return 1
        print("Files are semantically equal")
        return 0

    # default mode: for each path compare working tree file vs git HEAD version
    if not args.paths:
        parser.print_help()
        return 2

    for p in args.paths:
        wd = Path(p)
        head_obj = load_git_head(p)
        if not wd.exists() and head_obj is None:
            print(f"Neither working file nor HEAD version exists for: {p}")
            continue
        if wd.exists():
            try:
                wd_obj = load_file_guess(wd)
            except Exception as e:
                print(f"Failed to parse working file {wd}: {e}")
                diffs.append(p)
                continue
        else:
            wd_obj = None

        if head_obj is None:
            print(f"No HEAD version for {p}, treating as new file.")
            diffs.append(p)
            continue

        equal, na, nb = compare_objects(head_obj, wd_obj)
        if not equal:
            print(f"Semantic differences detected in {p}:")
            print("--- HEAD (normalized) ---")
            print(pretty(na))
            print("--- WORKTREE (normalized) ---")
            print(pretty(nb))
            diffs.append(p)

    if diffs:
        print(f"Differences found in: {', '.join(diffs)}")
        return 1
    print("No semantic differences detected in supplied OpenAPI files.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
