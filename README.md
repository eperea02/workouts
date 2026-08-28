# My Workout Planner

A personal static site cataloging 93 workouts (strength, conditioning,
benchmark, and tabata sessions) with a drag-and-drop weekly planner. Built
with plain HTML/CSS/JS — no build tools required — ready to publish as-is
with GitHub Pages.

## Structure

- `index.html` — the whole page: weekly planner + workout library
- `styles.css` — shared styling
- `script.js` — library rendering/search, planner drag-and-drop, modal
- `assets/logic.js` — pure planner logic (date formatting, plan
  encode/decode, search/filter), unit tested with Node's built-in test
  runner
- `data/workouts.json` — the 93 workouts shown on the site
- `data/workouts_raw_extracted.json` — intermediate OCR output the final
  dataset was built from (kept for provenance, not fetched by the page)
- `scripts/build_workouts_json.py` — one-off transform from the raw OCR
  data to `data/workouts.json`
- `icloudphotos/` — source screenshots (not published as site assets)

## Editing the workout data

`data/workouts.json` is generated from `data/workouts_raw_extracted.json`.
To add/edit workouts, edit the raw file and re-run:

```bash
python3 scripts/build_workouts_json.py
```

## Running the tests

```bash
python3 -m unittest tests.test_build_workouts_json -v
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
