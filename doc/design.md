# Firmware component treemap

Visualize the entire `crazyflie-firmware` tree by unit/component, and show which
parts are compiled into build A vs. build B — two arbitrary Kbuild targets (e.g.
two different platforms, or two configs of the same platform).

## Goal

For each source file (and the directory/component it belongs to), classify it as:

- **build A only** — compiled for target A, not for target B
- **build B only** — compiled for target B, not for target A
- **shared, identical** — compiled for both, resolving the same headers
- **shared, shadowed** — compiled for both, but at least one `#include` resolves to a
  different file depending on target (the include-path-shadowing mechanism, e.g.
  a header resolving to a different implementation on each side)

Render this as an interactive treemap/icicle over the firmware's existing directory
structure (`src/modules`, `src/hal`, `src/drivers`, `src/platform`, `src/deck`, …),
colored by the four categories above.

## 1. Data gathering

Ground truth comes from the build itself, not from hand-parsing Kbuild/Kconfig —
the Makefile conditionals (nested `ifneq`, `obj-$(CONFIG_PLATFORM_SIM)`, etc.) are
easy to misclassify statically, and shadowing doesn't appear in `obj-y` lines at all.
Specifically, it comes from Kbuild's own generated `.<obj>.o.cmd` files (written by
`fixdep` during a normal build): each one already records, per compiled object, its
exact source file (`source_<obj> := ...`) and the full list of resolved dependencies
— source + every header it pulled in (`deps_<obj> := ...`). No `-MMD`/`.d` files or
`bear`/`compiledb` needed; Kbuild already produces this for every build.

The tool doesn't drive the builds itself — it's a two-stage, user-in-the-loop
workflow, since "build both targets" can mean very different things (a plain
`<platform>_defconfig && make`, or the special `sim` target's own recipe) and the
person running it is in the best position to know how to build each side:

1. You build target A yourself, however that target is normally built.
2. Run the collector against A's Kbuild output directory (`build/` by default, or
   wherever `KBUILD_OUTPUT` pointed — note `make sim` lands under `build/sim/`,
   not the repo root, since the top-level Makefile's own out-of-tree
   reinvocation into `build/` happens before the `sim` target's recipe runs) →
   a snapshot JSON: source file → resolved dependency list.
3. You build target B yourself (cleaning/redirecting the output dir first, so
   Kbuild's incremental rebuild doesn't leave stale objects from A's config lying
   around).
4. Run the collector again against B's output → a second snapshot JSON.
5. Run the diff/tree-builder on the two snapshots:
   - file present in only one snapshot → build A only / build B only
   - file in both, dependency sets identical → shared, identical
   - file in both, dependency sets differ → shared, shadowed (headers matched
     between the two sides by filename; record the differing ones and their
     resolved path on each side — this is the interesting detail to surface on
     hover)
   - map each source file to a "component" by directory (top-level dirs under
     `src/`, plus `vendor`/`scripts` as siblings — same grouping validated in the
     single-build prototype)
   - emit one JSON file describing the tree: nested nodes (directory → file), each
     leaf tagged with its category and, for shadowed files, the differing header
     pairs.

Implemented as `01_collect_build.py` (build → snapshot) and `02_make_treemap_data.py`
(two snapshots → tree JSON) in the tool repo — see its README for the exact
commands. This only needed the include-path-shadowing mechanism from this
project's TODO to actually exist in the checkout being analyzed; the tooling
itself is agnostic to which two targets you point it at.

## 2. Visualization

A prototype of the base treemap mechanics (single build, colored by component,
no diff) already exists: `prototype.html`, fully specified in
`prototype-requirements.md`. That doc covers the parts that carry over
unchanged — D3 treemap layout and sizing, drill-down navigation with
breadcrumbs, hover tooltip, leaf/group labeling, watermarks, legend, resize
handling. This section only lists what still needs to change/be added on top
of that to reach the two-build-diff goal (see `prototype-requirements.md` §10
for the same list from the prototype's side):

- **Recolor by category**, not by component: rectangle color = build A only /
  build B only / shared identical / shared shadowed, instead of the
  prototype's per-directory palette. Component identity (which the color
  currently carries) will need to move elsewhere — e.g. the watermark/
  breadcrumb/tooltip path text — since color is being repurposed.
- **Tooltip**: extend with, for shadowed files, the specific headers that
  resolve differently between target A and target B (which headers, and
  their resolved path on each side).
- **Legend becomes interactive**: toggle to isolate a single category (e.g.
  "show only build B only files") — the prototype's legend is static/display
  -only.
- **Regeneratable JSON loading**: fetch the tree from an external JSON file
  (the output of step 1) instead of the prototype's hand-embedded inline
  `<script>` block, so re-running step 1 after firmware changes and
  reopening the same HTML page picks up the new data without editing the
  page. (`fetch()` of a local file is blocked by CORS in Chrome over
  `file://`; the page also offers a "Load JSON…" file picker and the README
  documents `python3 -m http.server` as the one-line fix.)

Implemented as `treemap.html` in the tool repo, evolved directly from
`prototype.html`. Also handles the single-build case (`requirements.md`:
"when given one build, treemap shall visualize the build") by branching on
`data.json`'s `meta.mode` (`"single"` vs `"diff"`, set by
`02_make_treemap_data.py` depending on whether a second snapshot was passed):
single-build view reuses the prototype's per-component palette and static
legend as-is (no category recoloring, no isolate-by-category, since there's
nothing to diff against), while diff mode keeps the behavior described
above. Both modes now flatten the `src/` wrapper at the top level (ported
from the prototype, previously only done there) so `deck`/`drivers`/…
appear directly as siblings instead of nested one level under a single
dominating `src` tile — this also fixes the diff view's top-level watermark,
which previously said "src" instead of naming the actual component.

## 3. Other things needed — resolved

- Directory grouping depth for "component": kept flat, one level under
  `src/` (`deck`, `drivers`, `hal`, `init`, `lib`, `modules`, `platform`,
  `utils`), with `vendor`/`scripts` as siblings — same grouping the
  prototype already validated as readable.
- File size metric: lines of code (matches the prototype).
- The classification logic lives in `02_make_treemap_data.py`, reading
  `01_collect_build.py`'s snapshots (see §1) — not `.d` files, since Kbuild's
  own `.cmd` files already carry this.
- No live/runtime data needed — this is a static, build-time snapshot,
  regenerated by rerunning the workflow in §1 whenever someone wants an
  updated view.
