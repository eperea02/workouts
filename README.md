# My Workout Planner

A personal static site cataloging 93 workouts (strength, conditioning,
benchmark, and tabata sessions) with a drag-and-drop weekly planner and an
individual page per workout. Built with plain HTML/CSS/JS — no build tools
required — ready to publish as-is with GitHub Pages.

## Structure

- `index.html` — the whole page: weekly planner + workout library
- `workouts/*.html` — one generated, static detail page per workout
- `styles.css` — shared styling
- `script.js` — library rendering/search, planner drag-and-drop, modal,
  "Plan my week" auto-fill
- `assets/logic.js` — pure planner logic (date formatting, plan
  encode/decode, search/filter, auto-fill picking), unit tested with
  Node's built-in test runner
- `data/workouts.json` — the 93 workouts shown on the site, including a
  `bodyFocus` tag (`lower`/`upper`/`total`/`cardio`) per workout
- `data/workouts_raw_extracted.json` — intermediate OCR output the final
  dataset was built from (kept for provenance, not fetched by the page)
- `scripts/build_workouts_json.py` — one-off transform from the raw OCR
  data to `data/workouts.json` (also derives `bodyFocus` via a movement-
  keyword heuristic — imperfect, but good enough for planning purposes)
- `scripts/build_workout_pages.py` — one-off generator that turns
  `data/workouts.json` into `workouts/*.html`
- `icloudphotos/` — source screenshots (not published as site assets)

## Editing the workout data

`data/workouts.json` is generated from `data/workouts_raw_extracted.json`,
and `workouts/*.html` is generated from `data/workouts.json`. To add/edit
workouts, edit the raw file and re-run both generators in order:

```bash
python3 scripts/build_workouts_json.py
python3 scripts/build_workout_pages.py
```

The page generator removes any `workouts/*.html` file that no longer has a
matching workout, so stale pages don't pile up.

## "Plan my week"

The planner has a "Plan my week" button that auto-fills Monday with a
lower-body workout, Wednesday with upper body, Friday with a total-body
workout, and Tuesday/Thursday with two different cardio workouts —
weekends are left untouched. It picks randomly among matching workouts
each time, so clicking it again reshuffles the week. Body-focus tagging is
a heuristic (see above) — swap out any pick you disagree with by hand.

## Running the tests

```bash
python3 -m unittest discover -s tests -p "test_*.py" -v
node --test tests/logic.test.js
```

## Running locally

```bash
python3 -m http.server 8000
```

Then open `http://localhost:8000/`.

## Publishing

This site is designed to be served directly by GitHub Pages from the
repository root (no build step) — see the setup walkthrough for enabling
Pages in the repo settings.
