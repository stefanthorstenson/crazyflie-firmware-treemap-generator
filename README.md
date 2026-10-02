# crazyflie-firmware treemap

An interactive treemap of the `crazyflie-firmware` source tree. Point it at
one build to see that build's source tree by component, or at two builds —
any two Kbuild targets/configs — to compare them and see, for every source
file:

- **A only** — compiled into build A, not build B
- **B only** — compiled into build B, not build A
- **shared, identical** — compiled into both, resolving the same headers
- **shared, shadowed** — compiled into both, but at least one `#include`
  resolves to a different file depending on the build (e.g. the
  include-path-shadowing mechanism used to build the Simmyflie simulator
  against the same source tree as the hardware firmware)

Ground truth comes from the build itself — Kbuild's own generated
`.<obj>.o.cmd` files (written by `fixdep` during a normal build) already
record, per compiled object, its exact source file and every header it
resolved. Nothing here parses Makefiles/Kconfig.

## Workflow

The tool never runs `make` itself. You build each side yourself, however you
like, and snapshot the result right after each build finishes.

### One build

```
cd /path/to/crazyflie-firmware
make cf2_defconfig && make
python3 /path/to/collect_build.py . -o /tmp/cf2.json

python3 /path/to/make_treemap_data.py /path/to/crazyflie-firmware /tmp/cf2.json \
  --name-a cf2 -o /path/to/data.json
```

Shows that build's source tree grouped by component (`deck`, `drivers`,
`hal`, …) — no A-only/B-only/shared classification, since there's nothing to
compare against.

### Two builds

```
cd /path/to/crazyflie-firmware

make cf2_defconfig && make
python3 /path/to/collect_build.py . -o /tmp/cf2.json

rm -rf build && make cf2_defconfig && make sim
python3 /path/to/collect_build.py . --kbuild-output build/sim -o /tmp/sim.json

python3 /path/to/make_treemap_data.py /path/to/crazyflie-firmware /tmp/cf2.json /tmp/sim.json \
  --name-a cf2 --name-b sim -o /path/to/data.json
```

Notes:

- `collect_build.py`'s `--kbuild-output` is the build's output directory
  relative to the firmware repo — defaults to `build` (Kbuild's own
  default). The `sim` target needs an existing `.config` (run a
  `*_defconfig` first) and writes under `build/sim/`, not at the repo root
  — the top-level Makefile already reinvokes itself into `build/` before
  the `sim` target's own recipe (which sets `KBUILD_OUTPUT=$(CURDIR)/sim`)
  runs, so pass `--kbuild-output build/sim` after `make sim`.
- Snapshot build A, *then* rebuild for B — don't just point
  `collect_build.py` at a stale output directory from a different config,
  since Kbuild only rebuilds what changed and a leftover `.cmd` file from an
  earlier config would be misattributed to the wrong build. Cleaning the
  output dir between builds (as in the example above) avoids this;
  `collect_build.py` also warns if a `.cmd` file's recorded source no
  longer exists, which is the usual symptom.
- Works for any pair of builds, not just cf2 vs sim — two hardware
  platforms, two configs of the same platform, etc.

## Viewing

Open `treemap.html` next to `data.json` (or `?data=path/to/other.json`). If
it loads blank, your browser blocked the local `fetch()` (common for
`file://` in Chrome, not in Firefox) — either use the in-page "Load JSON…"
picker, or serve the folder locally:

```
python3 -m http.server -d /path/to/folder
```

and open it over `http://localhost:8000/treemap.html`.

### Try it without building anything

`example/` has two ready-made `data.json`-shaped files, generated from a real
`cf2` build (and `cf2bl`, the bootloader, for the comparison one) — no build
step needed to see the tool working:

In the repo root folder:

```
python3 -m http.server
```

- `http://localhost:8000/treemap.html?data=example/example-single-build.json`
  — one build (`cf2`)
- `http://localhost:8000/treemap.html?data=example/example-comparison.json`
  — two builds compared (`cf2` vs. `cf2bl`)

## Statistics

`print_stats.py` prints a text summary of a two-build comparison, read from
the same tree JSON the page loads — no firmware checkout or snapshots
needed:

```
python3 print_stats.py example/example-comparison.json
```

- **Category totals** — files and lines of code in each of the four
  categories, with percentages.
- **Lines per component** — lines of code per category for each component
  (same grouping as the treemap), largest component first.

Exits with an error for a single-build file, since there's nothing to
compare.

## Known limitations

- Header-shadow detection matches build A's and build B's dependency lists
  **by filename**, not a full `#include` resolution audit — good enough
  as long as headers aren't renamed across the shadow boundary, but not a
  formal proof.
- Tile area is lines of code; directory/component grouping is a single
  fixed depth (top-level directories under `src/`, plus `vendor` and
  `scripts`).
- A group tile's color is whichever category is most common among its
  leaves — drill in for the exact per-file breakdown.
