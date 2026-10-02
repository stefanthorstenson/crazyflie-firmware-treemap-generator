#!/usr/bin/env python3
"""Turn one or two 01_collect_build.py snapshots into the tree JSON treemap.html reads.

Two builds -- diff mode, classifies every source file that was compiled into
either build:

    02_make_treemap_data.py ~/code/bitcraze/crazyflie-firmware cf2.json sim.json \
        --name-a cf2 --name-b sim -o data.json

  a_only            - compiled for build A, not for build B
  b_only            - compiled for build B, not for build A
  shared_identical  - compiled for both, resolving the same headers
  shared_shadowed   - compiled for both, but at least one header resolves to
                       a different file depending on the build (matched by
                       filename between the two dependency sets)

One build -- single mode (omit snapshot_b), just visualizes that build's
source tree by component, no classification:

    02_make_treemap_data.py ~/code/bitcraze/crazyflie-firmware cf2.json \
        --name-a cf2 -o data.json

Never runs `make` or otherwise touches the firmware repo's build state --
it only reads already-checked-out source files (for line counts) and the
snapshot JSON file(s).
"""
import argparse
import json
import sys
from pathlib import Path

TOP_LEVEL_IGNORE = set()  # nothing excluded by default; every compiled file is shown


def count_lines(path):
    try:
        with open(path, "rb") as f:
            return sum(1 for _ in f)
    except OSError:
        return 0


def classify(path, deps_a, deps_b):
    if deps_a is None:
        return "b_only", None
    if deps_b is None:
        return "a_only", None
    if set(deps_a) == set(deps_b):
        return "shared_identical", None

    by_basename_a = {}
    for d in deps_a:
        by_basename_a.setdefault(Path(d).name, set()).add(d)
    by_basename_b = {}
    for d in deps_b:
        by_basename_b.setdefault(Path(d).name, set()).add(d)

    shadowed = []
    for name, paths_a in by_basename_a.items():
        paths_b = by_basename_b.get(name)
        if paths_b is not None and paths_b != paths_a:
            shadowed.append({
                "name": name,
                "a": sorted(paths_a),
                "b": sorted(paths_b),
            })
    shadowed.sort(key=lambda h: h["name"])
    return "shared_shadowed", shadowed


def insert(root, repo_relpath, leaf):
    parts = Path(repo_relpath).parts
    node = root
    for part in parts[:-1]:
        node = node.setdefault("children", {}).setdefault(
            part, {"name": part, "children": {}}
        )
    node.setdefault("children", {})[parts[-1]] = leaf


def freeze(node):
    """Convert the {name->node} children dicts used while building into the
    sorted list shape the page expects."""
    if "children" in node:
        children = [freeze(c) for c in node["children"].values()]
        children.sort(key=lambda c: c["name"])
        return {"name": node["name"], "children": children}
    return node


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("firmware_repo", help="path to the crazyflie-firmware checkout (for line counts)")
    ap.add_argument("snapshot_a", help="01_collect_build.py output for build A")
    ap.add_argument("snapshot_b", nargs="?", default=None,
                     help="01_collect_build.py output for build B; omit for a single-build "
                          "view of build A only (no classification)")
    ap.add_argument("--name-a", required=True, help="label for build A, e.g. cf2")
    ap.add_argument("--name-b", help="label for build B, e.g. sim (required if snapshot_b is given)")
    ap.add_argument("-o", "--output", required=True, help="tree JSON to write")
    args = ap.parse_args()

    single = args.snapshot_b is None
    if not single and not args.name_b:
        ap.error("--name-b is required when snapshot_b is given")

    repo = Path(args.firmware_repo).resolve()
    snap_a = json.loads(Path(args.snapshot_a).read_text())
    snap_b = {} if single else json.loads(Path(args.snapshot_b).read_text())

    all_files = sorted(set(snap_a) | set(snap_b))
    if not all_files:
        sys.exit("error: snapshot is empty" if single else "error: both snapshots are empty")

    root = {"name": repo.name, "children": {}}
    missing_on_disk = 0
    counts = {"a_only": 0, "b_only": 0, "shared_identical": 0, "shared_shadowed": 0}

    for relpath in all_files:
        abs_path = repo / relpath
        if not abs_path.exists():
            missing_on_disk += 1
            lines = 0
        else:
            lines = max(1, count_lines(abs_path))

        leaf = {"name": Path(relpath).name, "value": lines}
        if not single:
            deps_a = snap_a.get(relpath)
            deps_b = snap_b.get(relpath)
            category, shadowed_headers = classify(relpath, deps_a, deps_b)
            counts[category] += 1
            leaf["category"] = category
            if shadowed_headers:
                leaf["shadowed_headers"] = shadowed_headers
        insert(root, relpath, leaf)

    tree = freeze(root)
    tree["meta"] = {"mode": "single", "build": args.name_a} if single else \
        {"mode": "diff", "build_a": args.name_a, "build_b": args.name_b}

    Path(args.output).write_text(json.dumps(tree, indent=1) + "\n")

    print(f"wrote {len(all_files)} file(s) to {args.output}")
    if single:
        print(f"  {args.name_a}: {len(all_files)} file(s)")
    else:
        print(f"  {args.name_a} only:        {counts['a_only']}")
        print(f"  {args.name_b} only:        {counts['b_only']}")
        print(f"  shared, identical:  {counts['shared_identical']}")
        print(f"  shared, shadowed:   {counts['shared_shadowed']}")
    if missing_on_disk:
        print(f"warning: {missing_on_disk} file(s) referenced in the snapshot(s) no longer "
              f"exist in {repo} -- counted as 0 lines", file=sys.stderr)


if __name__ == "__main__":
    main()
