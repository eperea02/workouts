# Workout Planner Site — Design Spec

Date: 2026-08-28

## Purpose

The user has ~130 photos in `icloudphotos/` from an Instagram fitness page
("aquilafitness"), most of which are screenshots of daily WOD (Workout of the
Day) posts. The goal is a static, GitHub-Pages-ready site — modeled after the
existing `~/soccer-drills` repo — that:

1. Catalogs these workouts as a browsable library.
2. Lets the user drag-and-drop (or tap-to-assign) any workout from the
   library onto a day of a reusable Monday–Sunday weekly template, to plan
   their workout schedule, the same way `soccer-drills` lets you build a
   practice plan.

## Source data

All 126 non-video photos in `icloudphotos/` were OCR'd by parallel
subagents. Findings:

- 116 PNGs: screenshots of Instagram posts from `aquilafitness`. Almost all
  show a day banner (e.g. "MONDAY 11.10.25") followed by workout text
  (strength sets, a named benchmark like "Jackie", conditioning circuits, or
  tabata blocks).
- 10 JPEGs: action photos at the gym (no workout text) — **excluded** from
  the site per user decision.
- 3 PNGs were non-workout Instagram posts (party photo, generic caption
  post, sponsored ad) — excluded.
- Several PNGs were exact-duplicate screenshots (same post captured twice).
  Deduped by comparing normalized workout text.

Result: **93 unique workouts**, dated 2025-09-30 through 2026-07-06.
Category breakdown: 57 strength, 16 conditioning, 15 benchmark
(named workouts like Jackie, Cindy, The Chief, Nasty Girls), 5 tabata.

Extracted data lives at `data/workouts_raw_extracted.json` (intermediate
format from the OCR pass — see "Data transform" below for the final shape
consumed by the site).

## Non-goals

- Not a real calendar (no specific future dates) — the weekly planner is a
  reusable Mon–Sun template, matching the soccer-drills practice-plan model.
- Not tied to gym branding — this is the user's personal site, own visual
  identity.
- No backend/build step — plain static HTML/CSS/JS, deployable as-is to
  GitHub Pages from the repo root, consistent with `soccer-drills`.
- No detail sub-pages per workout (unlike soccer-drills' `drills/*.html`) —
  93 items is too many to hand-maintain as separate pages; full text expands
  inline on the card instead.

## Data shape

`data/workouts.json` — a JSON array, one object per workout:

```json
{
  "id": "2025-11-10-jackie",
  "date": "2025-11-10",
  "weekdayLabel": "MONDAY",
  "title": "Jackie",
  "category": "benchmark",
  "text": "5x5 Sumo Deadlift @2011\n\nJackie\nFor Time:\n1000m Row\n50 Thrusters 45/33\n30 Pull Ups"
}
```

- `title`: the named benchmark if the OCR pass found one; otherwise derived
  from the first non-empty line of `text` (e.g. "Box Squat 8-5-5-3-3").
- `category`: one of `strength`, `conditioning`, `benchmark`, `tabata`.
- `id`: `date` + slugified title/first-line, used as a stable key for
  planner persistence.
- `date`/`weekdayLabel` are display-only provenance ("originally posted
  Mon, Nov 10 2025") — they do not map to the weekly planner's generic
  Mon–Sun slots.

A build/transform step (one-time, run during implementation) converts
`data/workouts_raw_extracted.json` into this final `data/workouts.json`,
deriving `id` and fallback `title` for untitled entries. This does not need
to be a repeatable script — a one-off transform is fine since the source
photos are a fixed, closed set.

## Page structure (`index.html`, single page)

1. **Header** — site name (generic, not gym-branded), nav links to the two
   sections below.
2. **Hero** — one-line description.
3. **Weekly Planner** (`#planner`) — a 7-column grid, Monday–Sunday. Each
   day is a drop target holding zero or one workout.
   - **Desktop**: drag a library card and drop it onto a day slot.
   - **Mobile / click**: tapping an empty day slot opens a modal with the
     same search + category filter as the library, to pick a workout.
   - Dropping/picking a new workout on an already-filled day **replaces**
     the existing one (single-slot-per-day, confirmed by user).
   - Each filled day shows: category badge, title, a "remove" (×) control,
     and a "view details" toggle to expand the full text inline.
   - State persists to `localStorage` and is round-tripped through a URL
     query param (`?plan=...`) so a planned week is shareable/bookmarkable
     — same mechanism as `soccer-drills`' `?plan=` param.
4. **Workout Library** (`#library`) — the browsing/search surface.
   - Category filter chips: All / Strength / Conditioning / Benchmark /
     Tabata.
   - Text search box, matches against `title` and `text` (movement names).
   - Grid of cards, sorted most-recent-first by `date`. Each card shows:
     category badge + original date, title, a short snippet (first 1-2
     lines).
   - Click a card to expand it inline, revealing the full workout text and
     a day-picker (7 buttons, Mon–Sun) to assign it directly from the
     library without dragging.
   - Cards are also `draggable` for the desktop drag-to-planner flow.

## Visual identity

Structurally similar to `soccer-drills` (paper background, card grid, pill
badges, mono accent font for labels/timers) but its own palette — charcoal
ink on warm paper with an iron-red accent, evoking a gym logbook rather than
a soccer pitch. No use of Aquila Fitness branding or colors.

## Files

- `index.html` — full page markup + inline `<script>` (mirrors
  soccer-drills' single-file-script approach) or a separate `script.js` —
  implementation's call based on final size; prefer separate `script.js`
  since this page has meaningfully more logic (search/filter + planner +
  modal) than soccer-drills.
- `styles.css` — new palette, reuses soccer-drills' card/badge/pill
  patterns structurally.
- `data/workouts.json` — final 93-entry dataset consumed by the page.
- `data/workouts_raw_extracted.json` — intermediate OCR output, kept for
  provenance/debugging; not fetched by the page at runtime.
- `README.md` — updated to describe the site, data source, and how to
  regenerate/edit `data/workouts.json`.
- `icloudphotos/` — left as-is (source material), not published as site
  assets.

## Testing

No test framework needed for a static site. Verification is manual: serve
the directory locally (`python3 -m http.server`), confirm:
- Library renders all 93 cards, filter chips and search narrow results
  correctly.
- Dragging a card onto a planner day assigns it; dropping on an occupied
  day replaces it.
- Tapping a day slot opens the picker modal and assigns correctly.
- Card expand/collapse shows full text.
- Reloading the page preserves the planned week (localStorage) and loading
  a URL with `?plan=...` reproduces the same week.
