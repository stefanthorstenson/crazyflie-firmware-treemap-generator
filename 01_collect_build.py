#!/usr/bin/env python3
"""Snapshot a Kbuild output directory into JSON: compiled source file -> its
fully resolved dependencies (itself + every header it pulled in), as recorded
by Kbuild's own `.o.cmd` files (written by `fixdep` during a normal build).

Run this once per build, right after you finish compiling it yourself:

    cd ~/code/bitcraze/crazyflie-firmware
    make cf2_defconfig && make
    01_collect_build.py . -o cf2.json

    rm -rf build && make cf2_defconfig && make sim
    01_collect_build.py . --kbuild-output build/sim -o sim.json

Feed the two resulting snapshots to 02_make_treemap_data.py.

Note: `make sim`'s own KBUILD_OUTPUT=$(CURDIR)/sim resolves *under* `build/`
(build/sim), not at the repo root -- the top-level Makefile already
reinvokes itself into build/ before the `sim` target's recipe runs, so
$(CURDIR) inside that recipe is already build/, not the repo root.
"""
import argparse
import json
import re
import sys
from pathlib import Path

SOURCE_RE = re.compile(r"^source_(\S+) := (.+)$", re.MULTILINE)
DEPS_RE = re.compile(r"^deps_(\S+) := (.*?)\n\n", re.MULTILINE | re.DOTALL)


def parse_cmd_file(path):
    text = path.read_text(errors="replace")
    source_m = SOURCE_RE.search(text)
    deps_m = DEPS_RE.search(text)
    if not source_m or not deps_m:
        return None
    source = source_m.group(2).strip()
    deps = []
    for line in deps_m.group(2).splitlines():
        line = line.strip().rstrip("\\").strip()
        if not line or line.startswith("$(wildcard"):
            # $(wildcard include/config/*.h) entries are Kbuild's own
            # config-change tripwires, not real files that got #included.
            continue
        deps.append(line)
    return source, deps


def resolve(repo, out_dir, raw_path):
    p = Path(raw_path)
    if p.is_absolute():
        return p
    for base in (repo, out_dir):
        candidate = base / p
        if candidate.exists():
            return candidate.resolve()
    # Neither exists (yet) -- return the repo-relative guess; caller checks
    # existence and reports it as missing/stale.
    return repo / p


def to_repo_relative(repo, path):
    try:
        return str(path.relative_to(repo))
    except ValueError:
        return str(path)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("firmware_repo", help="path to the crazyflie-firmware checkout")
    ap.add_argument("--kbuild-output", default="build",
                     help="KBUILD_OUTPUT dir the build you just ran wrote into, "
                          "relative to firmware_repo (default: build; use "
                          "'build/sim' after `make sim` -- that target's own "
                          "KBUILD_OUTPUT=$(CURDIR)/sim resolves under build/, "
                          "since the top-level Makefile's own out-of-tree "
                          "reinvocation into build/ happens first)")
    ap.add_argument("-o", "--output", required=True, help="snapshot JSON to write")
    args = ap.parse_args()

    repo = Path(args.firmware_repo).resolve()
    out_dir = (repo / args.kbuild_output).resolve()
    if not out_dir.is_dir():
        sys.exit(f"error: output dir not found: {out_dir}")

    snapshot = {}
    missing = []
    cmd_files = list(out_dir.rglob(".*.cmd"))
    for cmd_path in cmd_files:
        parsed = parse_cmd_file(cmd_path)
        if parsed is None:
            continue
        source, deps = parsed
        source_abs = resolve(repo, out_dir, source)
        if not source_abs.exists():
            missing.append(source)
            continue
        source_rel = to_repo_relative(repo, source_abs)

        dep_rels = set()
        for dep in deps:
            dep_abs = resolve(repo, out_dir, dep)
            if not dep_abs.exists():
                continue
            dep_rels.add(to_repo_relative(repo, dep_abs))
        dep_rels.add(source_rel)

        snapshot[source_rel] = sorted(dep_rels)

    if not cmd_files:
        sys.exit(f"error: no .o.cmd files found under {out_dir} -- did the build actually run?")

    if missing:
        print(f"warning: {len(missing)} source file(s) recorded in .cmd files no longer "
              f"exist on disk (stale output dir from a different config?) -- skipped:",
              file=sys.stderr)
        for m in missing[:10]:
            print(f"  {m}", file=sys.stderr)
        if len(missing) > 10:
            print(f"  ... and {len(missing) - 10} more", file=sys.stderr)

    Path(args.output).write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n")
    print(f"wrote {len(snapshot)} compiled source file(s) to {args.output}")


if __name__ == "__main__":
    main()
