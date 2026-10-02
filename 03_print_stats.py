#!/usr/bin/env python3
"""Print statistics for a two-build comparison produced by 02_make_treemap_data.py.

    03_print_stats.py data.json

Reads only the tree JSON -- needs neither the firmware checkout nor the
snapshots. Prints two tables:

  - category totals (A only / B only / shared identical / shared shadowed),
    by files and by lines
  - lines per category for each component, using the same grouping as
    treemap.html (top-level directories under `src/`, plus the other
    top-level directories as siblings)
"""
import argparse
import json
import sys
from pathlib import Path

CATEGORIES = ("a_only", "b_only", "shared_identical", "shared_shadowed")


def leaves(node):
    if "children" not in node:
        yield node
        return
    for child in node["children"]:
        yield from leaves(child)


def components(tree):
    """Yield (component name, node), flattening the `src/` wrapper the same
    way treemap.html does."""
    for child in tree.get("children", []):
        if child["name"] == "src" and "children" in child:
            for sub in child["children"]:
                yield sub["name"], sub
        else:
            yield child["name"], child


def percent(part, total):
    return f"{100 * part / total:.1f}%" if total else "-"


def print_statistics(tree):
    meta = tree["meta"]
    labels = {
        "a_only": f"{meta['build_a']} only",
        "b_only": f"{meta['build_b']} only",
        "shared_identical": "shared, identical",
        "shared_shadowed": "shared, shadowed",
    }

    files = dict.fromkeys(CATEGORIES, 0)
    lines = dict.fromkeys(CATEGORIES, 0)
    by_component = {}
    for component, node in components(tree):
        comp_lines = by_component.setdefault(component, dict.fromkeys(CATEGORIES, 0))
        for leaf in leaves(node):
            files[leaf["category"]] += 1
            lines[leaf["category"]] += leaf["value"]
            comp_lines[leaf["category"]] += leaf["value"]

    total_files = sum(files.values())
    total_lines = sum(lines.values())

    # Both tables share the same columns: one per category, then the total.
    row_labels = ["files", "files %", "lines", "lines %"]
    label_width = max(len(name) for name in [*by_component, "component", *row_labels])
    col_widths = [max(len(labels[c]), 8) for c in CATEGORIES]
    header = "  ".join(f"{labels[c]:>{w}}" for c, w in zip(CATEGORIES, col_widths))

    def print_row(label, cells, total):
        row = "  ".join(f"{cell:>{w}}" for cell, w in zip(cells, col_widths))
        print(f"{label:<{label_width}}  {row}  {total:>8}".rstrip())

    print(f"{'':<{label_width}}  {header}  {'total':>8}")
    print_row("files", [files[c] for c in CATEGORIES], total_files)
    print_row("files %", [percent(files[c], total_files) for c in CATEGORIES], "")
    print_row("lines", [lines[c] for c in CATEGORIES], total_lines)
    print_row("lines %", [percent(lines[c], total_lines) for c in CATEGORIES], "")

    print()
    print("lines per component:")
    print(f"{'component':<{label_width}}  {header}  {'total':>8}")
    for component, comp_lines in sorted(by_component.items(),
                                        key=lambda item: -sum(item[1].values())):
        print_row(component, [comp_lines[c] for c in CATEGORIES], sum(comp_lines.values()))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("data", help="tree JSON written by 02_make_treemap_data.py (two-build mode)")
    args = ap.parse_args()

    tree = json.loads(Path(args.data).read_text())
    if tree.get("meta", {}).get("mode") != "diff":
        sys.exit(f"error: {args.data} is not a two-build comparison -- nothing to compare")

    print_statistics(tree)


if __name__ == "__main__":
    main()
