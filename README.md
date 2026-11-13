# My Workout Planner

A personal static site cataloging 103 workouts (strength, conditioning,
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
- `data/workouts.json` — the 103 workouts shown on the site, including a
  `p90xDay` tag (`chest_back`/`plyometrics`/`shoulders_arms`/`legs_back`/
  `null`) per workout
- `data/workouts_raw_extracted.json` — intermediate OCR output the final
  dataset was built from (kept for provenance, not fetched by the page)
- `scripts/build_workouts_json.py` — one-off transform from the raw OCR
  data to `data/workouts.json` (also derives `p90xDay` via a movement-
  keyword heuristic — imperfect, but good enough for planning purposes)
- `scripts/build_workout_pages.py` — one-off generator that turns
  `data/workouts.json` into `workouts/*.html`
- `assets/icon-16.png`, `icon-32.png`, `icon-180.png` — site favicon and
  the `apple-touch-icon` used for iOS "Add to Home Screen" (a dumbbell
  mark in the site's ink/paper/accent palette); regenerate by editing
  and rerunning the Pillow script used to create them (not checked in —
  install Pillow in a venv, redraw, resave over these files)
- `scripts/fetch_monthly_workouts.py` — reads the Academy qrfy page, has Claude
  transcribe any new workout images, and appends them to
  `data/workouts_raw_extracted.json`; `data/qrfy_imported_images.json` records
  which images were already imported
- `.github/workflows/monthly-workouts.yml` — runs that script monthly and
  opens a pull request (see "Monthly auto-update")
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

## Browsing the library

The library has two independent filter rows &mdash; workout type
(Strength/Conditioning/Benchmark/Tabata) and P90X day type (Chest &amp;
Back/Plyometrics/Shoulders &amp; Arms/Legs &amp; Back), plus the search
box &mdash; and they combine (e.g. Strength + Shoulders &amp; Arms shows
only strength workouts tagged for that day). Every card shows its full
workout text and day-assignment buttons right on the page, no click
needed; the title link still opens that workout's own static page
(`workouts/<id>.html`) for a bookmarkable, shareable URL.

## "Plan my week"

The planner covers Monday&ndash;Friday and follows the P90X Phase 1
day-type rotation (Kenpo X dropped to fit the 5-day grid):

| Day       | Purpose            |
|-----------|--------------------|
| Monday    | Chest, Back & Abs  |
| Tuesday   | Plyometrics        |
| Wednesday | Shoulders & Arms   |
| Thursday  | Yoga X             |
| Friday    | Legs & Back        |

Each day's purpose is shown under the weekday name, and clicking an
empty day opens the picker pre-filtered to that day's type (with an
"All" chip to browse everything else). Tuesday's "Plyometrics" filter
and auto-fill pool also include everything tagged `legs_back`, since
true plyometric content is rare in the library (2 workouts) and
legs/back movements (squats, jumps, thrusters) overlap with it —
without that, Tuesday would repeat the same couple of workouts
constantly. A "Plan my week" button auto-fills Monday, Tuesday,
Wednesday, and Friday by picking randomly from workouts tagged with
that day's type — click it again to reshuffle. Thursday (Yoga X) is
always left blank since there's no yoga/mobility content in the
library; pick something by hand. Day-type tagging is a heuristic (see
above) — swap out any pick you disagree with by hand, or drag any
workout onto any day regardless of its tag.

## Monthly auto-update

A GitHub Actions workflow checks the Academy qrfy page at 14:00 UTC on the
1st of each month. If the page has workout images it hasn't imported yet, it
transcribes them with the Claude API, rebuilds the data and pages, runs the
tests, and opens a pull request titled "Add new Academy workouts". Nothing
is published until you merge that PR, so check each workout against its
source image (linked in the PR) first -- a misread number is easy to miss.
New entries are dated the day the workflow ran and tagged `strength`.

One-time setup (repository **Settings**):

1. **Secrets and variables > Actions > New repository secret**: name
   `ANTHROPIC_API_KEY`, value an Anthropic API key. A month's three images
   cost a few cents.
2. **Actions > General > Workflow permissions**: tick "Allow GitHub Actions
   to create and approve pull requests".

To run it on demand (or to test the setup), open the **Actions** tab, pick
"Monthly workout update", and click **Run workflow**. If there is nothing
new it finishes without opening a PR. Set an `ANTHROPIC_MODEL` environment
variable in the workflow to use a different Claude model. The qrfy link is
set by `PAGE_URI` in the script.

Scheduled workflows are paused by GitHub after 60 days without repository
activity; merging each month's PR keeps it alive.

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
