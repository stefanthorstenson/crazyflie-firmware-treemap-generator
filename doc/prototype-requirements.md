# Firmware treemap — prototype requirements

Reverse-engineered from `prototype.html`. Describes what a user sees and can
do with that page, precisely enough to rebuild an equivalent experience
without looking at it. This is a **single-build** prototype — no build A/B
diff or include-shadowing classification yet. See `design.md` for where this
fits in the larger goal.

## 1. Purpose

An interactive, drill-down treemap of one compiled firmware build's source
tree (`make cf2` in this instance), grouped by directory, where the size of
each tile reflects how much code it contains. Opens as a plain static page —
no server, no install step.

## 2. What's on the page

Top to bottom:

1. Title: "crazyflie-firmware — component treemap (prototype)".
2. A subtitle line explaining what the view shows: one build only
   (`make cf2`), tiles sized by line count, no hardware/simulator comparison
   yet.
3. A toolbar showing, on the left, a breadcrumb trail of where you've
   drilled into, and on the right, a summary of the current view (file count
   and line count).
4. The treemap chart itself, in a bordered panel.
5. A legend: one color swatch and label per top-level component.
6. A short note box ("What this shows:") explaining how to read and use the
   chart: one build's source tree, grouped by directory, tile area = line
   count, click a directory to drill in, click a breadcrumb to go back,
   files don't drill further, and colors currently represent components
   only (not yet hardware-only/simulator-only/shared status).
7. A tooltip that appears near the cursor when hovering a tile.

## 3. What the top level shows

At the top level, the chart shows the real components side by side —
`deck`, `drivers`, `hal`, `init`, `lib`, `modules`, `platform`, `utils` —
alongside `vendor` and `scripts`. There is no single dominating "src" box
containing all the components; that intermediate grouping is collapsed away
so the components are directly comparable at a glance.

## 4. Look and feel

- Follows the OS light/dark theme automatically, and can also be forced into
  light or dark mode.
- Each top-level component has its own distinct, consistent color, used for
  its swatch in the legend and for its tiles in the chart.
- Clean, readable typography: a regular sans-serif for titles/body text, and
  a monospace face for breadcrumbs, stats, and the tooltip.
- The page is centered with a comfortable reading width and doesn't stretch
  full-bleed on wide screens.

## 5. The treemap

- Each directory and file is a tile; a tile's area is proportional to the
  number of lines of code it (or, for a directory, everything under it)
  contains. Bigger subsystems are visually bigger.
- Directories are nested boxes: a directory's tile visually contains the
  tiles of its contents.
- Larger items are placed before smaller ones so the chart reads roughly
  biggest-to-smallest.
- Colors: every tile is colored by which top-level component it belongs to,
  even when you've drilled several levels deep — so no matter how far in you
  navigate, the color still tells you which component you're inside.
  Nested tiles within a component use shades/tints of that component's
  color rather than a flat single color, giving a sense of depth. A
  component with no assigned color falls back to a neutral gray.
- Top-level component tiles are outlined more strongly than nested tiles, so
  the major boundaries are easy to spot at a glance.
- Large enough top-level tiles show the component's name as a big,
  semi-transparent watermark in the background, so you can identify a
  region even when zoomed out and its nested contents are small. This
  watermark never spills outside its own tile's boundary.
- Individual files, when their tile is large enough to hold readable text,
  show the file name directly on the tile. Very small tiles skip the label
  entirely rather than showing overlapping, unreadable text.

## 6. Interactions

### Hovering

- Hovering any tile (file or directory) shows a tooltip near the cursor with:
  - The item's name.
  - Its path (relative to the top level).
  - For a file: how many lines it has.
  - For a directory: how many lines and how many files it contains in total.
- The tooltip disappears when the cursor leaves the tile.
- Hovering a directory tile dims it slightly to give hover feedback; file
  tiles don't dim (they're not drillable, so there's nothing to invite you
  further into).

### Clicking / drilling in

- Clicking anywhere inside a directory's area — including inside one of its
  nested children — drills into that directory and re-renders the chart to
  show just its contents. You don't have to click precisely on the parent's
  own border; clicking anywhere within the group works.
- If drilling into a directory lands you somewhere with only one
  subdirectory and nothing else, the view automatically continues drilling
  down through those single-child levels until it reaches a point with
  real choices — so you're never stuck clicking through a chain of
  directories that each only contain one thing.
- Files can't be drilled into — clicking one does nothing, and the cursor
  reflects that files aren't clickable while directories show a pointer
  cursor to indicate they are.

### Breadcrumbs

- Shows your current drill-down path as a "/"-separated trail, always
  starting from "crazyflie-firmware" at the root.
- The current (last) segment is visually highlighted and not clickable.
- Clicking any earlier segment jumps back up to that level.

## 7. Stats and legend

- The toolbar always shows a live "N files · N lines" summary for whatever
  subtree is currently in view.
- The tooltip shows the same kind of summary for whatever you're hovering,
  regardless of the current drill-down level.
- The legend lists every top-level component with its color and name. It's
  static — it doesn't change as you drill in, and clicking it doesn't do
  anything yet (no isolate/filter-by-category in this prototype, even
  though `design.md` describes that as a future goal).

## 8. Responsiveness

- Resizing the browser window reflows the chart to fit the new width (chart
  height adjusts proportionally, within sensible min/max bounds).
- The toolbar wraps on narrow widths; the chart itself always spans the
  full width of its panel.

## 9. Known limitations of this prototype

(Carried over from the note box on the page — a checklist of what the next
iteration is expected to add, per `design.md`.)

- No second build to compare against — no build-A/build-B comparison, no
  "shared & identical" vs. "shared & shadowed" distinction, no
  shadowed-header detail on hover.
- No legend-driven filtering — you can't click a legend entry to isolate or
  hide a component.
- No way to refresh the data from a new build without manually re-editing
  the page — there's no "load a new build" action.
- Colors currently tell you which *component* a tile belongs to, not
  whether it's hardware-only, simulator-only, or shared. Repurposing color
  for that distinction (per `design.md`) will mean finding another way to
  show component identity (e.g. via the watermark, breadcrumb, or tooltip
  path) since color will be needed for the new dimension.
