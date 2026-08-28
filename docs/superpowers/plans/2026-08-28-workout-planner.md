# Workout Planner Site Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a static, GitHub-Pages-ready site that catalogs 93 extracted workouts as a searchable library and lets the user drag-and-drop (or tap-to-assign) any workout onto a reusable Monday–Sunday weekly planner.

**Architecture:** Plain HTML/CSS/JS, no build step, modeled structurally on `~/soccer-drills` (card grid, pill badges, drag-and-drop practice-plan pattern) but with its own visual identity. A one-off Python script transforms the raw OCR data into the final `data/workouts.json` consumed by the page at runtime via `fetch`. Pure, side-effect-free planner logic (date formatting, plan encode/decode, search/filter) lives in a small vanilla-JS module that works unmodified in both the browser (`<script>` tag, globals) and Node (`node --test`), so it can be unit tested without a bundler. DOM wiring (rendering, drag-and-drop, modal) lives in `script.js` and is verified manually in a browser.

**Tech Stack:** HTML5, CSS3, vanilla JS (ES5-style, no modules/bundler — matches soccer-drills), Python 3 stdlib (one-off data transform + `unittest`), Node.js built-in test runner (`node --test`) for the pure JS logic.

**Spec:** `docs/superpowers/specs/2026-08-28-workout-planner-design.md`

## Global Constraints

- No build step — the site must be servable as static files directly from the repo root (GitHub Pages compatible).
- No external JS dependencies/frameworks — vanilla JS only, consistent with `soccer-drills`.
- The weekly planner is a reusable Monday–Sunday template (not tied to real calendar dates) — one workout per day; assigning a new workout to an occupied day replaces the old one.
- Planner state persists to `localStorage` AND round-trips through a `?plan=` URL query param (shareable link), same mechanism as `soccer-drills`.
- Category values are exactly one of: `strength`, `conditioning`, `benchmark`, `tabata`.
- `data/workouts_raw_extracted.json` (already committed) is the source of truth for OCR'd content — do not re-extract or hand-edit workout text; only the transform step touches it.
- No gym branding (no "Aquila Fitness" name/colors) — this is the user's own personal site.
- No per-workout HTML detail pages — full text expands inline on the card.

---

## Task 1: Data transform — raw OCR JSON → final `data/workouts.json`

**Files:**
- Create: `scripts/build_workouts_json.py`
- Create: `tests/test_build_workouts_json.py`
- Generate (by running the script): `data/workouts.json`

**Interfaces:**
- Consumes: `data/workouts_raw_extracted.json` (array of `{file, date, weekday_label, title, raw_text, category, is_workout}` — `title`/`date`/`weekday_label` may be `null`; only entries are already filtered to `is_workout: true` records, i.e. all 93 array entries in this file are usable as-is, no need to re-filter).
- Produces: `data/workouts.json`, an array of objects: `{id: string, date: string, weekdayLabel: string, title: string, category: string, text: string}`, sorted ascending by `date`. `build_workouts_json.build(raw_path, out_path)` is the importable function later tasks/tests rely on.

- [ ] **Step 1: Write the failing test**

Create `tests/test_build_workouts_json.py`:

```python
import json
import os
import re
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

import build_workouts_json as bwj

RAW_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'workouts_raw_extracted.json')
WEEKDAY_RE = re.compile(r'^(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b')
ALLOWED_CATEGORIES = {'strength', 'conditioning', 'benchmark', 'tabata'}


class BuildWorkoutsJsonTest(unittest.TestCase):
    def setUp(self):
        with open(RAW_PATH) as f:
            self.raw_count = len(json.load(f))
        self.tmp = tempfile.NamedTemporaryFile(suffix='.json', delete=False)
        self.tmp.close()
        self.out_path = self.tmp.name

    def tearDown(self):
        os.unlink(self.out_path)

    def test_builds_one_entry_per_raw_record(self):
        result = bwj.build(RAW_PATH, self.out_path)
        self.assertEqual(len(result), self.raw_count)

    def test_output_file_matches_returned_data(self):
        result = bwj.build(RAW_PATH, self.out_path)
        with open(self.out_path) as f:
            on_disk = json.load(f)
        self.assertEqual(on_disk, result)

    def test_every_entry_has_required_fields(self):
        result = bwj.build(RAW_PATH, self.out_path)
        for w in result:
            for key in ('id', 'date', 'weekdayLabel', 'title', 'category', 'text'):
                self.assertIn(key, w)
            self.assertTrue(w['id'])
            self.assertTrue(w['date'])
            self.assertTrue(w['title'])
            self.assertTrue(w['text'])
            self.assertIn(w['category'], ALLOWED_CATEGORIES)

    def test_ids_are_unique(self):
        result = bwj.build(RAW_PATH, self.out_path)
        ids = [w['id'] for w in result]
        self.assertEqual(len(ids), len(set(ids)))

    def test_sorted_ascending_by_date(self):
        result = bwj.build(RAW_PATH, self.out_path)
        dates = [w['date'] for w in result]
        self.assertEqual(dates, sorted(dates))

    def test_text_does_not_start_with_weekday_banner_line(self):
        result = bwj.build(RAW_PATH, self.out_path)
        for w in result:
            first_line = w['text'].split('\n', 1)[0].strip().lower()
            self.assertFalse(WEEKDAY_RE.match(first_line), msg=w['id'])

    def test_derives_title_from_first_line_when_missing(self):
        # IMG_6009.PNG in the raw data has title=null; its raw_text's first
        # non-empty line is "5 Rounds:" — confirm that fallback happens by
        # spot-checking a known untitled record still gets a non-generic title.
        with open(RAW_PATH) as f:
            raw = json.load(f)
        untitled = [r for r in raw if r['title'] is None]
        self.assertGreater(len(untitled), 0)
        result = bwj.build(RAW_PATH, self.out_path)
        by_date_category = {(w['date'], w['category']): w for w in result}
        sample = untitled[0]
        match = by_date_category.get((sample['date'], sample['category']))
        self.assertIsNotNone(match)
        self.assertNotEqual(match['title'], 'Workout')


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/workouts && python3 -m unittest tests.test_build_workouts_json -v`
Expected: FAIL/ERROR — `ModuleNotFoundError: No module named 'build_workouts_json'` (the script doesn't exist yet).

- [ ] **Step 3: Write the implementation**

Create `scripts/build_workouts_json.py`:

```python
"""One-off transform: data/workouts_raw_extracted.json -> data/workouts.json.

The raw file is a fixed, closed set of 93 OCR'd workout screenshots — this
script does not need to be re-run except to regenerate data/workouts.json
after manually editing the raw file.
"""
import json
import re

WEEKDAY_RE = re.compile(
    r'^(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
    re.IGNORECASE,
)


def slugify(text):
    text = text.lower()
    text = text.replace('&amp;', 'and').replace('&', 'and')
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-') or 'workout'


def strip_banner(raw_text):
    lines = raw_text.split('\n')
    while lines and (WEEKDAY_RE.match(lines[0].strip()) or lines[0].strip() == ''):
        lines.pop(0)
    return '\n'.join(lines).strip('\n')


def derive_title(text):
    for line in text.split('\n'):
        line = line.strip()
        if line:
            return line
    return 'Workout'


def build(raw_path, out_path):
    with open(raw_path) as f:
        raw_records = json.load(f)

    seen_ids = set()
    out = []
    for record in raw_records:
        text = strip_banner(record['raw_text'])
        title = record['title'] or derive_title(text)

        base_id = '{0}-{1}'.format(record['date'], slugify(title))
        workout_id = base_id
        suffix = 2
        while workout_id in seen_ids:
            workout_id = '{0}-{1}'.format(base_id, suffix)
            suffix += 1
        seen_ids.add(workout_id)

        out.append({
            'id': workout_id,
            'date': record['date'],
            'weekdayLabel': record['weekday_label'],
            'title': title,
            'category': record['category'],
            'text': text,
        })

    out.sort(key=lambda w: w['date'])

    with open(out_path, 'w') as f:
        json.dump(out, f, indent=2)
        f.write('\n')

    return out


if __name__ == '__main__':
    build('data/workouts_raw_extracted.json', 'data/workouts.json')
    print('Wrote data/workouts.json')
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ~/workouts && python3 -m unittest tests.test_build_workouts_json -v`
Expected: `OK` — all 7 tests pass.

- [ ] **Step 5: Generate the real output file**

Run: `cd ~/workouts && python3 scripts/build_workouts_json.py`
Expected output: `Wrote data/workouts.json`

Then spot-check: `python3 -c "import json; d=json.load(open('data/workouts.json')); print(len(d)); print(d[0])"` — should print `93` and the earliest-dated workout (2025-09-30).

- [ ] **Step 6: Commit**

```bash
cd ~/workouts
git add scripts/build_workouts_json.py tests/test_build_workouts_json.py data/workouts.json
git commit -m "Add data transform script producing data/workouts.json"
```

---

## Task 2: Pure planner logic module (`assets/logic.js`) + Node tests

**Files:**
- Create: `assets/logic.js`
- Test: `tests/logic.test.js`

**Interfaces:**
- Produces (globals in the browser via `<script src="assets/logic.js">`, and `module.exports` in Node): `DAYS` (array of 7 day-code strings `['MON','TUE','WED','THU','FRI','SAT','SUN']`), `DAY_LABELS` (object mapping day code → full name), `formatDateLabel(dateStr)` → `"Nov 10, 2025"`-style string, `emptyPlan()` → `{MON: null, TUE: null, ..., SUN: null}`, `encodePlan(plan)` → JSON string, `decodePlan(str)` → plan object or `null` if invalid, `filterWorkouts(workouts, {category, query})` → filtered array.
- Consumes: nothing (pure functions, no DOM, no fetch).
- Later tasks (`script.js`) call all of the above by their global names.

- [ ] **Step 1: Write the failing test**

Create `tests/logic.test.js`:

```js
const test = require('node:test');
const assert = require('node:assert');
const {
  DAYS,
  DAY_LABELS,
  formatDateLabel,
  emptyPlan,
  encodePlan,
  decodePlan,
  filterWorkouts,
} = require('../assets/logic.js');

test('DAYS has the 7 day codes in week order', () => {
  assert.deepStrictEqual(DAYS, ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']);
});

test('DAY_LABELS has a full name for every day code', () => {
  DAYS.forEach((d) => {
    assert.strictEqual(typeof DAY_LABELS[d], 'string');
    assert.ok(DAY_LABELS[d].length > 0);
  });
});

test('formatDateLabel formats an ISO date without timezone drift', () => {
  assert.strictEqual(formatDateLabel('2025-11-10'), 'Nov 10, 2025');
  assert.strictEqual(formatDateLabel('2026-01-02'), 'Jan 2, 2026');
  assert.strictEqual(formatDateLabel('2025-12-31'), 'Dec 31, 2025');
});

test('emptyPlan has all 7 days set to null', () => {
  const plan = emptyPlan();
  assert.strictEqual(Object.keys(plan).length, 7);
  DAYS.forEach((d) => assert.strictEqual(plan[d], null));
});

test('encodePlan/decodePlan round-trip a partially filled plan', () => {
  const plan = emptyPlan();
  plan.MON = '2025-11-10-jackie';
  plan.FRI = '2025-12-05-strength';
  const encoded = encodePlan(plan);
  assert.strictEqual(typeof encoded, 'string');
  const decoded = decodePlan(encoded);
  assert.deepStrictEqual(decoded, plan);
});

test('encodePlan/decodePlan round-trip an empty plan', () => {
  const plan = emptyPlan();
  assert.deepStrictEqual(decodePlan(encodePlan(plan)), plan);
});

test('decodePlan returns null for malformed input', () => {
  assert.strictEqual(decodePlan('not json'), null);
  assert.strictEqual(decodePlan('{}'), null);
  assert.strictEqual(decodePlan('[1,2,3]'), null);
  assert.strictEqual(decodePlan('[]'), null);
});

const SAMPLE_WORKOUTS = [
  { id: '1', title: 'Jackie', category: 'benchmark', text: 'row thrusters pull ups' },
  { id: '2', title: 'Box Squat', category: 'strength', text: 'box squat 5x5' },
  { id: '3', title: 'Tabata Circuit', category: 'tabata', text: 'ski cals push ups' },
];

test('filterWorkouts with no options returns everything', () => {
  const result = filterWorkouts(SAMPLE_WORKOUTS, {});
  assert.strictEqual(result.length, 3);
});

test('filterWorkouts filters by category', () => {
  const result = filterWorkouts(SAMPLE_WORKOUTS, { category: 'strength' });
  assert.deepStrictEqual(result.map((w) => w.id), ['2']);
});

test('filterWorkouts filters by search query across title and text, case-insensitively', () => {
  const result = filterWorkouts(SAMPLE_WORKOUTS, { query: 'THRUSTER' });
  assert.deepStrictEqual(result.map((w) => w.id), ['1']);
});

test('filterWorkouts combines category and query filters', () => {
  const result = filterWorkouts(SAMPLE_WORKOUTS, { category: 'benchmark', query: 'squat' });
  assert.strictEqual(result.length, 0);
});

test('filterWorkouts category "all" matches every category', () => {
  const result = filterWorkouts(SAMPLE_WORKOUTS, { category: 'all' });
  assert.strictEqual(result.length, 3);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/workouts && node --test tests/logic.test.js`
Expected: FAIL — `Cannot find module '../assets/logic.js'`

- [ ] **Step 3: Write the implementation**

Create `assets/logic.js`:

```js
// Pure planner logic — no DOM access. Loaded as a plain <script> tag in the
// browser (exposes globals) and required directly from Node tests.

var DAYS = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN'];

var DAY_LABELS = {
  MON: 'Monday',
  TUE: 'Tuesday',
  WED: 'Wednesday',
  THU: 'Thursday',
  FRI: 'Friday',
  SAT: 'Saturday',
  SUN: 'Sunday',
};

var MONTH_NAMES = [
  'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
];

function formatDateLabel(dateStr) {
  var parts = dateStr.split('-');
  var year = parts[0];
  var month = parseInt(parts[1], 10);
  var day = parseInt(parts[2], 10);
  return MONTH_NAMES[month - 1] + ' ' + day + ', ' + year;
}

function emptyPlan() {
  var plan = {};
  DAYS.forEach(function (d) {
    plan[d] = null;
  });
  return plan;
}

function encodePlan(plan) {
  return JSON.stringify(DAYS.map(function (d) {
    return plan[d] || '';
  }));
}

function decodePlan(str) {
  var arr;
  try {
    arr = JSON.parse(str);
  } catch (e) {
    return null;
  }
  if (!Array.isArray(arr) || arr.length !== DAYS.length) return null;
  var plan = emptyPlan();
  DAYS.forEach(function (d, i) {
    plan[d] = arr[i] || null;
  });
  return plan;
}

function filterWorkouts(workouts, opts) {
  opts = opts || {};
  var category = opts.category || 'all';
  var query = (opts.query || '').trim().toLowerCase();
  return workouts.filter(function (w) {
    if (category !== 'all' && w.category !== category) return false;
    if (!query) return true;
    return (
      w.title.toLowerCase().indexOf(query) !== -1 ||
      w.text.toLowerCase().indexOf(query) !== -1
    );
  });
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    DAYS: DAYS,
    DAY_LABELS: DAY_LABELS,
    formatDateLabel: formatDateLabel,
    emptyPlan: emptyPlan,
    encodePlan: encodePlan,
    decodePlan: decodePlan,
    filterWorkouts: filterWorkouts,
  };
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ~/workouts && node --test tests/logic.test.js`
Expected: all tests pass (look for `# pass 13`, `# fail 0` in the summary).

- [ ] **Step 5: Commit**

```bash
cd ~/workouts
git add assets/logic.js tests/logic.test.js
git commit -m "Add pure planner logic module with Node unit tests"
```

---

## Task 3: Visual identity — `styles.css`

**Files:**
- Create: `styles.css`

**Interfaces:**
- Produces: all CSS class names that Tasks 4–7 rely on: `.wrap`, `.site-header`, `.brand`, `.site-nav`, `.hero`, `.eyebrow`, `.section-title`, `.filter-bar`, `.filter-chip` (+ `.is-active`), `.search-input`, `.library-grid`, `.workout-card` (+ `.is-expanded`), `.badge` (+ `.badge-strength`, `.badge-conditioning`, `.badge-benchmark`, `.badge-tabata`), `.card-snippet`, `.card-full-text`, `.assign-row`, `.day-pick-btn`, `.planner-controls`, `.plan-btn` (+ `.plan-btn-danger`), `.planner-grid`, `.day-column`, `.day-column-header`, `.day-slot` (+ `.is-drag-over`, `.is-filled`), `.day-slot-empty`, `.day-slot-card`, `.day-remove-btn`, `.empty-state`, `.modal-overlay`, `.modal`, `.modal-header`, `.modal-close`, `.modal-body`, `.picker-list`, `.picker-item`, `.site-footer`.
- Consumes: nothing.

- [ ] **Step 1: Create the file**

Create `styles.css`:

```css
/* ---------------------------------------------
   My Workout Planner — shared styles
--------------------------------------------- */

:root {
  --paper: #F1ECE1;
  --paper-alt: #FAF7EF;
  --ink: #211D1A;
  --ink-soft: #6B6259;
  --line: #DCD2BF;
  --accent: #B4402C;
  --accent-deep: #8C2F1F;
  --steel: #3C5A70;
  --gold: #A6791F;
  --violet: #5C4A80;
  --shadow: rgba(33, 29, 26, 0.10);
  --radius: 14px;
  --max-width: 1040px;
}

* {
  box-sizing: border-box;
}

html {
  scroll-behavior: smooth;
}

body {
  margin: 0;
  background: var(--paper);
  color: var(--ink);
  font-family: "Libre Franklin", system-ui, sans-serif;
  line-height: 1.55;
  -webkit-font-smoothing: antialiased;
}

a {
  color: var(--accent-deep);
  text-decoration: none;
}

a:hover {
  text-decoration: underline;
}

.wrap {
  max-width: var(--max-width);
  margin: 0 auto;
  padding: 0 20px;
}

h1, h2, h3 {
  font-family: "Oswald", system-ui, sans-serif;
  text-transform: uppercase;
}

/* Header */
header.site-header {
  background: var(--ink);
  color: var(--paper-alt);
  padding: 20px 0;
}

header.site-header .wrap {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 10px;
}

header.site-header a.brand {
  color: var(--paper-alt);
  font-family: "Oswald", system-ui, sans-serif;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.02em;
  font-size: 1.15rem;
  display: flex;
  align-items: center;
  gap: 8px;
}

header.site-header a.brand:hover {
  text-decoration: none;
  opacity: 0.9;
}

nav.site-nav a {
  color: var(--paper-alt);
  opacity: 0.85;
  margin-left: 18px;
  font-family: "IBM Plex Mono", monospace;
  font-size: 0.82rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

nav.site-nav a:hover {
  opacity: 1;
  text-decoration: none;
}

/* Hero */
.hero {
  padding: 46px 0 34px;
  text-align: center;
}

.eyebrow {
  font-family: "IBM Plex Mono", monospace;
  font-size: 11.5px;
  letter-spacing: 0.11em;
  text-transform: uppercase;
  color: var(--accent-deep);
  margin: 0 0 12px;
}

.hero h1 {
  font-weight: 700;
  letter-spacing: 0.01em;
  font-size: clamp(30px, 6vw, 44px);
  line-height: 1.05;
  margin: 0 0 12px;
  color: var(--ink);
}

.hero p {
  color: var(--ink-soft);
  font-size: 1.05rem;
  max-width: 560px;
  margin: 0 auto;
}

/* Section titles */
.section-title {
  font-size: 1.2rem;
  font-weight: 600;
  letter-spacing: 0.02em;
  color: var(--ink);
  margin: 44px 0 16px;
  padding-bottom: 10px;
  border-bottom: 3px solid var(--accent);
}

.section-hint {
  color: var(--ink-soft);
  font-size: 0.92rem;
  margin: 0 0 16px;
}

/* Filter bar */
.filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  margin-bottom: 18px;
}

.filter-chip {
  font-family: "IBM Plex Mono", monospace;
  font-size: 0.78rem;
  font-weight: 600;
  letter-spacing: 0.02em;
  background: var(--paper-alt);
  color: var(--ink);
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 7px 16px;
  cursor: pointer;
  text-transform: uppercase;
}

.filter-chip:hover {
  border-color: var(--accent);
}

.filter-chip.is-active {
  background: var(--ink);
  color: var(--paper-alt);
  border-color: var(--ink);
}

.search-input {
  flex: 1 1 220px;
  min-width: 180px;
  font-family: "Libre Franklin", system-ui, sans-serif;
  font-size: 0.92rem;
  padding: 8px 14px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: var(--paper-alt);
  color: var(--ink);
}

.search-input:focus {
  outline: none;
  border-color: var(--accent);
}

/* Library grid */
.library-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 16px;
  margin-bottom: 10px;
}

.workout-card {
  background: var(--paper-alt);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 18px 20px;
  box-shadow: 0 1px 3px var(--shadow);
  display: flex;
  flex-direction: column;
  gap: 8px;
  cursor: pointer;
  transition: transform 0.12s ease, box-shadow 0.12s ease;
}

.workout-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 18px var(--shadow);
}

.workout-card[draggable="true"] {
  cursor: grab;
}

.workout-card.is-dragging {
  opacity: 0.4;
}

.badge {
  align-self: flex-start;
  font-family: "IBM Plex Mono", monospace;
  background: var(--paper);
  border: 1px solid var(--line);
  font-size: 0.7rem;
  font-weight: 600;
  padding: 3px 10px;
  border-radius: 999px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.badge-strength { color: var(--steel); }
.badge-conditioning { color: var(--accent-deep); }
.badge-benchmark { color: var(--gold); }
.badge-tabata { color: var(--violet); }

.badge-date {
  color: var(--ink-soft);
  margin-left: 6px;
}

.workout-card h3 {
  margin: 2px 0 0;
  font-size: 1.05rem;
  font-weight: 600;
  text-transform: none;
  letter-spacing: normal;
  color: var(--ink);
}

.card-snippet {
  margin: 0;
  color: var(--ink-soft);
  font-size: 0.88rem;
  white-space: pre-line;
}

.card-full-text {
  display: none;
  margin: 4px 0 0;
  color: var(--ink);
  font-size: 0.88rem;
  white-space: pre-line;
  background: var(--paper);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 12px 14px;
}

.workout-card.is-expanded .card-snippet {
  display: none;
}

.workout-card.is-expanded .card-full-text {
  display: block;
}

.assign-row {
  display: none;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 4px;
}

.workout-card.is-expanded .assign-row {
  display: flex;
}

.day-pick-btn {
  font-family: "IBM Plex Mono", monospace;
  font-size: 0.7rem;
  font-weight: 600;
  background: var(--paper);
  color: var(--ink);
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 5px 10px;
  cursor: pointer;
}

.day-pick-btn:hover {
  border-color: var(--accent);
}

.empty-state {
  color: var(--ink-soft);
  font-size: 0.92rem;
  border: 1px dashed var(--line);
  border-radius: 10px;
  padding: 20px;
  text-align: center;
  margin: 0 0 10px;
}

/* Planner */
.planner-controls {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 16px;
}

.plan-btn {
  font-family: "IBM Plex Mono", monospace;
  font-size: 0.8rem;
  font-weight: 600;
  letter-spacing: 0.02em;
  background: var(--paper-alt);
  color: var(--ink);
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 7px 16px;
  cursor: pointer;
}

.plan-btn:hover {
  border-color: var(--accent);
}

.plan-btn-danger {
  color: var(--accent-deep);
}

.planner-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 12px;
  margin-bottom: 10px;
}

.day-column {
  background: var(--paper-alt);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 160px;
}

.day-column-header {
  font-family: "IBM Plex Mono", monospace;
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--ink-soft);
}

.day-slot {
  flex: 1;
  border: 2px dashed var(--line);
  border-radius: 10px;
  display: flex;
  align-items: stretch;
  transition: border-color 0.12s ease, background 0.12s ease;
}

.day-slot.is-drag-over {
  border-color: var(--accent);
  background: var(--paper);
}

.day-slot.is-filled {
  border-style: solid;
  border-color: var(--line);
}

.day-slot-empty {
  flex: 1;
  background: none;
  border: none;
  color: var(--ink-soft);
  font-size: 0.82rem;
  font-family: "Libre Franklin", system-ui, sans-serif;
  cursor: pointer;
  padding: 14px 10px;
  text-align: center;
}

.day-slot-empty:hover {
  color: var(--ink);
}

.day-slot-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 10px;
  border-left: 4px solid var(--accent);
  border-radius: 8px;
}

.day-slot-card h4 {
  margin: 0;
  font-size: 0.92rem;
  font-weight: 600;
  color: var(--ink);
}

.day-slot-card-footer {
  margin-top: auto;
  display: flex;
  justify-content: space-between;
  gap: 6px;
}

.day-remove-btn {
  font-family: "IBM Plex Mono", monospace;
  background: var(--paper);
  border: 1px solid var(--line);
  color: var(--accent-deep);
  border-radius: 6px;
  width: 28px;
  height: 28px;
  line-height: 1;
  cursor: pointer;
  flex: none;
}

.day-slot-card .card-full-text {
  font-size: 0.8rem;
}

/* Modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(33, 29, 26, 0.55);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  z-index: 100;
}

.modal-overlay[hidden] {
  display: none;
}

.modal {
  background: var(--paper-alt);
  border-radius: var(--radius);
  max-width: 560px;
  width: 100%;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.35);
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--line);
}

.modal-header h3 {
  margin: 0;
  font-size: 1rem;
}

.modal-close {
  background: none;
  border: none;
  font-size: 1.3rem;
  line-height: 1;
  cursor: pointer;
  color: var(--ink-soft);
}

.modal-body {
  padding: 16px 20px 20px;
  overflow-y: auto;
}

.picker-list {
  list-style: none;
  margin: 12px 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.picker-item {
  display: flex;
  align-items: baseline;
  gap: 10px;
  flex-wrap: wrap;
  background: var(--paper);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 10px 12px;
  cursor: pointer;
}

.picker-item:hover {
  border-color: var(--accent);
}

.picker-item h4 {
  margin: 0;
  font-size: 0.9rem;
  color: var(--ink);
}

/* Footer */
footer.site-footer {
  text-align: center;
  color: var(--ink-soft);
  font-size: 0.85rem;
  padding: 40px 0 30px;
}

@media (max-width: 480px) {
  .hero h1 {
    font-size: 1.7rem;
  }
}
```

- [ ] **Step 2: Manual verification**

There's nothing to render yet (no HTML references this file until Task 4), so verification here is just: `python3 -m json.tool /dev/null 2>/dev/null; true` is not applicable — instead run a quick syntax sanity check with a CSS-aware tool if available, otherwise visually re-read the file for unmatched braces. Confirm the file has balanced `{`/`}`:

Run: `cd ~/workouts && python3 -c "s=open('styles.css').read(); print(s.count('{'), s.count('}'))"`
Expected: both numbers equal.

- [ ] **Step 3: Commit**

```bash
cd ~/workouts
git add styles.css
git commit -m "Add styles.css with the site's visual identity"
```

---

## Task 4: Page skeleton — `index.html` + data-loading stub

**Files:**
- Create: `index.html`
- Create: `script.js` (stub — replaced/extended in Tasks 5–7)

**Interfaces:**
- Consumes: `styles.css` (Task 3), `assets/logic.js` (Task 2), `data/workouts.json` (Task 1).
- Produces: the DOM structure and element IDs that Tasks 5–7 query: `#library-grid`, `#library-empty`, `#filter-bar`, `#search-input`, `#planner-grid`, `#planner-clear`, `#planner-copy-link`, `#picker-modal`, `#picker-modal-title`, `#picker-filter-bar`, `#picker-search-input`, `#picker-list`, `#picker-close`. Also produces the global `window.WORKOUTS` (populated after fetch resolves) that later script.js code branches rely on existing before rendering.

- [ ] **Step 1: Create `index.html`**

```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>My Workout Planner</title>
<meta name="description" content="A personal library of workouts with a drag-and-drop weekly planner." />
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Oswald:wght@500;600;700&family=Libre+Franklin:ital,wght@0,400;0,500;0,600;0,700;1,400&family=IBM+Plex+Mono:wght@500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="styles.css" />
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Ctext y='.9em' font-size='90'%3E%F0%9F%8F%8B%3C/text%3E%3C/svg%3E" />
</head>
<body>

<header class="site-header">
  <div class="wrap">
    <a class="brand" href="index.html">🏋 My Workout Planner</a>
    <nav class="site-nav">
      <a href="index.html#planner">Planner</a>
      <a href="index.html#library">Library</a>
    </nav>
  </div>
</header>

<div class="wrap">

  <section class="hero">
    <p class="eyebrow">Personal training log &middot; 93 sessions</p>
    <h1>Plan Your Training Week</h1>
    <p>A browsable library of past workouts &mdash; drag any one onto a day below to build a repeatable weekly plan.</p>
  </section>

  <section id="planner">
    <h2 class="section-title">Weekly Planner</h2>
    <p class="section-hint">Drag a workout from the library onto a day, or tap an empty day to pick one. The page URL updates as you go &mdash; copy it anytime to share this exact week.</p>

    <div class="planner-controls">
      <button type="button" id="planner-copy-link" class="plan-btn">Copy link</button>
      <button type="button" id="planner-clear" class="plan-btn plan-btn-danger">Clear week</button>
    </div>

    <div id="planner-grid" class="planner-grid"></div>
  </section>

  <section id="library">
    <h2 class="section-title">Workout Library</h2>

    <div id="filter-bar" class="filter-bar">
      <button type="button" class="filter-chip is-active" data-category="all">All</button>
      <button type="button" class="filter-chip" data-category="strength">Strength</button>
      <button type="button" class="filter-chip" data-category="conditioning">Conditioning</button>
      <button type="button" class="filter-chip" data-category="benchmark">Benchmark</button>
      <button type="button" class="filter-chip" data-category="tabata">Tabata</button>
      <input type="text" id="search-input" class="search-input" placeholder="Search movements or names&hellip;" />
    </div>

    <div id="library-grid" class="library-grid"></div>
    <p id="library-empty" class="empty-state" hidden>No workouts match your filters.</p>
  </section>

</div>

<div id="picker-modal" class="modal-overlay" hidden>
  <div class="modal">
    <div class="modal-header">
      <h3 id="picker-modal-title">Assign a workout</h3>
      <button type="button" id="picker-close" class="modal-close" aria-label="Close">&times;</button>
    </div>
    <div class="modal-body">
      <div id="picker-filter-bar" class="filter-bar">
        <button type="button" class="filter-chip is-active" data-category="all">All</button>
        <button type="button" class="filter-chip" data-category="strength">Strength</button>
        <button type="button" class="filter-chip" data-category="conditioning">Conditioning</button>
        <button type="button" class="filter-chip" data-category="benchmark">Benchmark</button>
        <button type="button" class="filter-chip" data-category="tabata">Tabata</button>
        <input type="text" id="picker-search-input" class="search-input" placeholder="Search movements or names&hellip;" />
      </div>
      <ul id="picker-list" class="picker-list"></ul>
    </div>
  </div>
</div>

<footer class="site-footer">
  <div class="wrap">
    Personal workout log &mdash; built as a static site, no backend required.
  </div>
</footer>

<script src="assets/logic.js"></script>
<script src="script.js"></script>

</body>
</html>
```

- [ ] **Step 2: Create the `script.js` stub**

Create `script.js`:

```js
(function () {
  'use strict';

  window.WORKOUTS = [];

  fetch('data/workouts.json')
    .then(function (res) { return res.json(); })
    .then(function (workouts) {
      window.WORKOUTS = workouts;
      // eslint-disable-next-line no-console
      console.log('Loaded ' + workouts.length + ' workouts');
    })
    .catch(function (err) {
      // eslint-disable-next-line no-console
      console.error('Failed to load workouts.json', err);
    });
})();
```

- [ ] **Step 3: Manual verification**

Run: `cd ~/workouts && python3 -m http.server 8000` (leave running), then in a browser open `http://localhost:8000/` and open the DevTools console.

Expected:
- Page renders the header, hero, empty planner/library section headings, and footer with the new charcoal/paper/iron-red styling from Task 3.
- Console prints `Loaded 93 workouts` with no errors.

Stop the server with Ctrl+C when done.

- [ ] **Step 4: Commit**

```bash
cd ~/workouts
git add index.html script.js
git commit -m "Add page skeleton and data-loading stub"
```

---

## Task 5: Library rendering, filtering, and search

**Files:**
- Modify: `script.js` (replace the stub body, keep the `fetch` call)

**Interfaces:**
- Consumes: `window.WORKOUTS` (Task 4), `DAY_LABELS`, `filterWorkouts`, `formatDateLabel` (Task 2, globals from `assets/logic.js`), DOM elements `#library-grid`, `#library-empty`, `#filter-bar`, `#search-input` (Task 4).
- Produces: `renderLibrary()` function and module-level `state = {category: 'all', query: ''}` that Task 6/7 read and extend (Task 6 adds `state.plan`; Task 7 adds expand/assign behavior reusing `renderLibrary`'s card markup shape).

- [ ] **Step 1: Replace `script.js` with library rendering + filtering**

```js
(function () {
  'use strict';

  var libraryGrid = document.getElementById('library-grid');
  var libraryEmpty = document.getElementById('library-empty');
  var filterBar = document.getElementById('filter-bar');
  var searchInput = document.getElementById('search-input');

  var state = {
    category: 'all',
    query: '',
  };

  window.WORKOUTS = [];

  function escapeHtml(str) {
    var div = document.createElement('div');
    div.textContent = str == null ? '' : str;
    return div.innerHTML;
  }

  function snippet(text, maxLines) {
    var lines = text.split('\n').filter(function (l) { return l.trim() !== ''; });
    return lines.slice(0, maxLines).join('\n');
  }

  function buildCard(workout) {
    var card = document.createElement('article');
    card.className = 'workout-card';
    card.dataset.id = workout.id;
    card.draggable = true;

    card.innerHTML =
      '<span class="badge badge-' + workout.category + '">' +
        escapeHtml(workout.category) +
        '<span class="badge-date">' + escapeHtml(formatDateLabel(workout.date)) + '</span>' +
      '</span>' +
      '<h3>' + escapeHtml(workout.title) + '</h3>' +
      '<p class="card-snippet">' + escapeHtml(snippet(workout.text, 2)) + '&hellip;</p>' +
      '<p class="card-full-text">' + escapeHtml(workout.text) + '</p>';

    card.addEventListener('dragstart', function (e) {
      card.classList.add('is-dragging');
      e.dataTransfer.setData('text/plain', workout.id);
      e.dataTransfer.effectAllowed = 'copy';
    });
    card.addEventListener('dragend', function () {
      card.classList.remove('is-dragging');
    });

    return card;
  }

  function byDateDescending(a, b) {
    return b.date.localeCompare(a.date);
  }

  function renderLibrary() {
    var filtered = filterWorkouts(window.WORKOUTS, state).slice().sort(byDateDescending);
    libraryGrid.innerHTML = '';
    filtered.forEach(function (w) {
      libraryGrid.appendChild(buildCard(w));
    });
    libraryEmpty.hidden = filtered.length !== 0;
  }

  filterBar.addEventListener('click', function (e) {
    var chip = e.target.closest ? e.target.closest('.filter-chip') : null;
    if (!chip) return;
    Array.prototype.forEach.call(filterBar.querySelectorAll('.filter-chip'), function (c) {
      c.classList.remove('is-active');
    });
    chip.classList.add('is-active');
    state.category = chip.dataset.category;
    renderLibrary();
  });

  searchInput.addEventListener('input', function () {
    state.query = searchInput.value;
    renderLibrary();
  });

  fetch('data/workouts.json')
    .then(function (res) { return res.json(); })
    .then(function (workouts) {
      window.WORKOUTS = workouts;
      renderLibrary();
    })
    .catch(function (err) {
      // eslint-disable-next-line no-console
      console.error('Failed to load workouts.json', err);
    });

  window.__renderLibrary = renderLibrary;
})();
```

Note: `Element.closest` is used above — supported in all evergreen browsers, no polyfill needed for a personal static site. `byDateDescending` gives the "most-recent-first" card order the spec calls for, independent of `data/workouts.json`'s own ascending on-disk order (Task 1 sorts the file ascending; this sorts a copy for display only, via `.slice()` so the underlying array order used elsewhere is untouched).

- [ ] **Step 2: Manual verification**

Run: `cd ~/workouts && python3 -m http.server 8000`, open `http://localhost:8000/#library`.

Expected:
- 93 cards render with badge/title/snippet, most-recent-first (the first card's badge date should be the newest, 2026-07-06 / "Jul 6, 2026").
- Clicking "Strength" chip narrows the grid to only strength-category cards (compare count against `python3 -c "import json;print(sum(1 for w in json.load(open('data/workouts.json')) if w['category']=='strength'))"` which should print 57).
- Typing "deadlift" in the search box narrows results to workouts mentioning deadlifts.
- Clearing the search box and clicking "All" restores all 93 cards.
- No console errors.

- [ ] **Step 3: Commit**

```bash
cd ~/workouts
git add script.js
git commit -m "Render workout library with category filter and search"
```

---

## Task 6: Weekly planner — drag-and-drop assignment + persistence

**Files:**
- Modify: `script.js`

**Interfaces:**
- Consumes: `DAYS`, `DAY_LABELS`, `emptyPlan`, `encodePlan`, `decodePlan`, `formatDateLabel` (Task 2 globals); `state`, `buildCard`'s dragstart wiring, `renderLibrary` (Task 5, same file).
- Produces: `state.plan` (object keyed by day code), `renderPlanner()`, `persistPlan()`, `loadPlan()`, `findWorkoutById(id)` — Task 7 calls `persistPlan()` and `renderPlanner()` after assigning a workout from the modal or from an expanded card.

- [ ] **Step 1: Add planner state, persistence, and drag-and-drop to `script.js`**

Insert the following additions into `script.js` (add near the top, after `var state = {...}`, and wire up the new pieces — full resulting file shown below since multiple regions change):

```js
(function () {
  'use strict';

  var libraryGrid = document.getElementById('library-grid');
  var libraryEmpty = document.getElementById('library-empty');
  var filterBar = document.getElementById('filter-bar');
  var searchInput = document.getElementById('search-input');
  var plannerGrid = document.getElementById('planner-grid');
  var plannerClearBtn = document.getElementById('planner-clear');
  var plannerCopyLinkBtn = document.getElementById('planner-copy-link');

  var PLAN_STORAGE_KEY = 'workout-planner-plan-v1';
  var PLAN_URL_PARAM = 'plan';

  var state = {
    category: 'all',
    query: '',
    plan: emptyPlan(),
  };

  window.WORKOUTS = [];

  function escapeHtml(str) {
    var div = document.createElement('div');
    div.textContent = str == null ? '' : str;
    return div.innerHTML;
  }

  function snippet(text, maxLines) {
    var lines = text.split('\n').filter(function (l) { return l.trim() !== ''; });
    return lines.slice(0, maxLines).join('\n');
  }

  function findWorkoutById(id) {
    for (var i = 0; i < window.WORKOUTS.length; i++) {
      if (window.WORKOUTS[i].id === id) return window.WORKOUTS[i];
    }
    return null;
  }

  function buildCard(workout) {
    var card = document.createElement('article');
    card.className = 'workout-card';
    card.dataset.id = workout.id;
    card.draggable = true;

    card.innerHTML =
      '<span class="badge badge-' + workout.category + '">' +
        escapeHtml(workout.category) +
        '<span class="badge-date">' + escapeHtml(formatDateLabel(workout.date)) + '</span>' +
      '</span>' +
      '<h3>' + escapeHtml(workout.title) + '</h3>' +
      '<p class="card-snippet">' + escapeHtml(snippet(workout.text, 2)) + '&hellip;</p>' +
      '<p class="card-full-text">' + escapeHtml(workout.text) + '</p>';

    card.addEventListener('dragstart', function (e) {
      card.classList.add('is-dragging');
      e.dataTransfer.setData('text/plain', workout.id);
      e.dataTransfer.effectAllowed = 'copy';
    });
    card.addEventListener('dragend', function () {
      card.classList.remove('is-dragging');
    });

    return card;
  }

  function byDateDescending(a, b) {
    return b.date.localeCompare(a.date);
  }

  function renderLibrary() {
    var filtered = filterWorkouts(window.WORKOUTS, state).slice().sort(byDateDescending);
    libraryGrid.innerHTML = '';
    filtered.forEach(function (w) {
      libraryGrid.appendChild(buildCard(w));
    });
    libraryEmpty.hidden = filtered.length !== 0;
  }

  function persistPlan() {
    try {
      localStorage.setItem(PLAN_STORAGE_KEY, encodePlan(state.plan));
    } catch (e) { /* localStorage unavailable — plan still works via URL/session */ }
    try {
      var url = new URL(window.location.href);
      url.searchParams.set(PLAN_URL_PARAM, encodePlan(state.plan));
      window.history.replaceState(null, '', url.toString());
    } catch (e) { /* ignore */ }
  }

  function loadPlan() {
    try {
      var url = new URL(window.location.href);
      var fromUrl = url.searchParams.get(PLAN_URL_PARAM);
      if (fromUrl) {
        var decoded = decodePlan(fromUrl);
        if (decoded) return decoded;
      }
    } catch (e) { /* ignore */ }
    try {
      var stored = localStorage.getItem(PLAN_STORAGE_KEY);
      if (stored) {
        var decodedStored = decodePlan(stored);
        if (decodedStored) return decodedStored;
      }
    } catch (e) { /* ignore */ }
    return emptyPlan();
  }

  function assignWorkout(day, workoutId) {
    state.plan[day] = workoutId;
    persistPlan();
    renderPlanner();
  }

  function clearDay(day) {
    state.plan[day] = null;
    persistPlan();
    renderPlanner();
  }

  function buildDaySlotContent(day) {
    var workoutId = state.plan[day];
    if (!workoutId) {
      var emptyBtn = document.createElement('button');
      emptyBtn.type = 'button';
      emptyBtn.className = 'day-slot-empty';
      emptyBtn.textContent = 'Tap or drag a workout here';
      emptyBtn.addEventListener('click', function () {
        if (typeof window.__openPickerForDay === 'function') {
          window.__openPickerForDay(day);
        }
      });
      return emptyBtn;
    }

    var workout = findWorkoutById(workoutId);
    var wrap = document.createElement('div');
    wrap.className = 'day-slot-card';
    if (!workout) {
      wrap.innerHTML = '<h4>Workout no longer available</h4>';
      return wrap;
    }

    wrap.innerHTML =
      '<span class="badge badge-' + workout.category + '">' + escapeHtml(workout.category) + '</span>' +
      '<h4>' + escapeHtml(workout.title) + '</h4>';

    var footer = document.createElement('div');
    footer.className = 'day-slot-card-footer';

    var removeBtn = document.createElement('button');
    removeBtn.type = 'button';
    removeBtn.className = 'day-remove-btn';
    removeBtn.setAttribute('aria-label', 'Remove');
    removeBtn.textContent = '×';
    removeBtn.addEventListener('click', function () {
      clearDay(day);
    });

    footer.appendChild(removeBtn);
    wrap.appendChild(footer);
    return wrap;
  }

  function renderPlanner() {
    plannerGrid.innerHTML = '';
    DAYS.forEach(function (day) {
      var column = document.createElement('div');
      column.className = 'day-column';

      var header = document.createElement('div');
      header.className = 'day-column-header';
      header.textContent = DAY_LABELS[day];
      column.appendChild(header);

      var slot = document.createElement('div');
      slot.className = 'day-slot' + (state.plan[day] ? ' is-filled' : '');
      slot.dataset.day = day;
      slot.appendChild(buildDaySlotContent(day));

      slot.addEventListener('dragover', function (e) {
        e.preventDefault();
        slot.classList.add('is-drag-over');
      });
      slot.addEventListener('dragleave', function () {
        slot.classList.remove('is-drag-over');
      });
      slot.addEventListener('drop', function (e) {
        e.preventDefault();
        slot.classList.remove('is-drag-over');
        var workoutId = e.dataTransfer.getData('text/plain');
        if (workoutId) assignWorkout(day, workoutId);
      });

      column.appendChild(slot);
      plannerGrid.appendChild(column);
    });
  }

  filterBar.addEventListener('click', function (e) {
    var chip = e.target.closest ? e.target.closest('.filter-chip') : null;
    if (!chip) return;
    Array.prototype.forEach.call(filterBar.querySelectorAll('.filter-chip'), function (c) {
      c.classList.remove('is-active');
    });
    chip.classList.add('is-active');
    state.category = chip.dataset.category;
    renderLibrary();
  });

  searchInput.addEventListener('input', function () {
    state.query = searchInput.value;
    renderLibrary();
  });

  plannerClearBtn.addEventListener('click', function () {
    state.plan = emptyPlan();
    persistPlan();
    renderPlanner();
  });

  plannerCopyLinkBtn.addEventListener('click', function () {
    persistPlan();
    var link = window.location.href;
    var originalText = 'Copy link';

    function showMessage(text, delay) {
      plannerCopyLinkBtn.textContent = text;
      setTimeout(function () { plannerCopyLinkBtn.textContent = originalText; }, delay);
    }

    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(link).then(
        function () { showMessage('Copied!', 1500); },
        function () { showMessage('Copy failed', 2500); }
      );
    } else {
      showMessage('Copy failed', 2500);
    }
  });

  fetch('data/workouts.json')
    .then(function (res) { return res.json(); })
    .then(function (workouts) {
      window.WORKOUTS = workouts;
      state.plan = loadPlan();
      renderLibrary();
      renderPlanner();
    })
    .catch(function (err) {
      // eslint-disable-next-line no-console
      console.error('Failed to load workouts.json', err);
    });

  window.__renderLibrary = renderLibrary;
  window.__renderPlanner = renderPlanner;
  window.__assignWorkout = assignWorkout;
  window.__findWorkoutById = findWorkoutById;
})();
```

This fully replaces the file's contents (Task 5's version plus the planner additions integrated in place, since the two regions interleave inside the same closure).

- [ ] **Step 2: Manual verification**

Run: `cd ~/workouts && python3 -m http.server 8000`, open `http://localhost:8000/#planner`.

Expected:
- 7 day columns render (Monday–Sunday), each with an empty "Tap or drag a workout here" slot.
- Dragging a library card onto a day slot assigns it: the slot now shows the category badge, title, and a remove (×) button.
- Dragging a different card onto an already-filled day replaces its contents (no duplicate/stacking).
- Clicking the remove (×) button empties that day's slot again.
- Clicking "Clear week" empties all 7 days.
- Reloading the page (F5) preserves whatever was assigned (via `localStorage`).
- After assigning a few days, the address bar's `?plan=` query updates; copying that URL, opening it in a new private/incognito window (so `localStorage` is empty) reproduces the same week from the URL alone.
- Clicking "Copy link" shows "Copied!" briefly (browser may show a clipboard permission prompt once).

- [ ] **Step 3: Commit**

```bash
cd ~/workouts
git add script.js
git commit -m "Add drag-and-drop weekly planner with localStorage/URL persistence"
```

---

## Task 7: Card expand/collapse, in-card day assignment, and mobile tap-to-assign modal

**Files:**
- Modify: `script.js`

**Interfaces:**
- Consumes: everything from Tasks 5–6 in the same file (`buildCard`, `renderLibrary`, `state`, `DAYS`, `DAY_LABELS`, `assignWorkout`, `renderPlanner`, `filterWorkouts`, `findWorkoutById`), plus Task 4's modal DOM elements `#picker-filter-bar` and `#picker-search-input`.
- Produces: `window.__openPickerForDay(day)` (already referenced by Task 6's `buildDaySlotContent` — this task supplies the real implementation, replacing the no-op lookup), plus in-card expand/collapse and an "assign to day" row on expanded cards. The modal gets its own `pickerState = {category: 'all', query: ''}`, independent of the library's `state`, so opening the picker never disturbs the main library's current filter/search.

- [ ] **Step 1: Extend `buildCard` to support expand/collapse and in-card day assignment, and implement the picker modal**

Apply these changes to `script.js`:

1. Add modal element references near the top, alongside the other `document.getElementById` calls:

```js
  var pickerModal = document.getElementById('picker-modal');
  var pickerModalTitle = document.getElementById('picker-modal-title');
  var pickerFilterBar = document.getElementById('picker-filter-bar');
  var pickerSearchInput = document.getElementById('picker-search-input');
  var pickerList = document.getElementById('picker-list');
  var pickerClose = document.getElementById('picker-close');
  var pickerDay = null;
  var pickerState = { category: 'all', query: '' };
```

2. Replace the `buildCard` function with this version, which adds a click-to-expand toggle and an assign-row of day buttons:

```js
  function buildAssignRow(workoutId) {
    var row = document.createElement('div');
    row.className = 'assign-row';
    DAYS.forEach(function (day) {
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'day-pick-btn';
      btn.textContent = day;
      btn.addEventListener('click', function (e) {
        e.stopPropagation();
        assignWorkout(day, workoutId);
      });
      row.appendChild(btn);
    });
    return row;
  }

  function buildCard(workout) {
    var card = document.createElement('article');
    card.className = 'workout-card';
    card.dataset.id = workout.id;
    card.draggable = true;

    card.innerHTML =
      '<span class="badge badge-' + workout.category + '">' +
        escapeHtml(workout.category) +
        '<span class="badge-date">' + escapeHtml(formatDateLabel(workout.date)) + '</span>' +
      '</span>' +
      '<h3>' + escapeHtml(workout.title) + '</h3>' +
      '<p class="card-snippet">' + escapeHtml(snippet(workout.text, 2)) + '&hellip;</p>' +
      '<p class="card-full-text">' + escapeHtml(workout.text) + '</p>';

    card.appendChild(buildAssignRow(workout.id));

    card.addEventListener('click', function () {
      card.classList.toggle('is-expanded');
    });

    card.addEventListener('dragstart', function (e) {
      card.classList.add('is-dragging');
      e.dataTransfer.setData('text/plain', workout.id);
      e.dataTransfer.effectAllowed = 'copy';
    });
    card.addEventListener('dragend', function () {
      card.classList.remove('is-dragging');
    });

    return card;
  }
```

3. Add the picker modal implementation (place near `renderPlanner`/`assignWorkout`):

```js
  function buildPickerItem(workout) {
    var li = document.createElement('li');
    li.className = 'picker-item';
    li.innerHTML =
      '<span class="badge badge-' + workout.category + '">' + escapeHtml(workout.category) + '</span>' +
      '<h4>' + escapeHtml(workout.title) + '</h4>';
    li.addEventListener('click', function () {
      if (pickerDay) assignWorkout(pickerDay, workout.id);
      closePicker();
    });
    return li;
  }

  function renderPickerList() {
    pickerList.innerHTML = '';
    var items = filterWorkouts(window.WORKOUTS, pickerState).slice().sort(byDateDescending);
    items.forEach(function (w) {
      pickerList.appendChild(buildPickerItem(w));
    });
  }

  function resetPickerFilters() {
    pickerState = { category: 'all', query: '' };
    pickerSearchInput.value = '';
    Array.prototype.forEach.call(pickerFilterBar.querySelectorAll('.filter-chip'), function (c) {
      c.classList.toggle('is-active', c.dataset.category === 'all');
    });
  }

  function openPickerForDay(day) {
    pickerDay = day;
    pickerModalTitle.textContent = 'Assign a workout to ' + DAY_LABELS[day];
    resetPickerFilters();
    renderPickerList();
    pickerModal.hidden = false;
  }

  function closePicker() {
    pickerModal.hidden = true;
    pickerDay = null;
  }

  pickerFilterBar.addEventListener('click', function (e) {
    var chip = e.target.closest ? e.target.closest('.filter-chip') : null;
    if (!chip) return;
    Array.prototype.forEach.call(pickerFilterBar.querySelectorAll('.filter-chip'), function (c) {
      c.classList.remove('is-active');
    });
    chip.classList.add('is-active');
    pickerState.category = chip.dataset.category;
    renderPickerList();
  });

  pickerSearchInput.addEventListener('input', function () {
    pickerState.query = pickerSearchInput.value;
    renderPickerList();
  });

  pickerClose.addEventListener('click', closePicker);
  pickerModal.addEventListener('click', function (e) {
    if (e.target === pickerModal) closePicker();
  });

  window.__openPickerForDay = openPickerForDay;
```

- [ ] **Step 2: Manual verification**

Run: `cd ~/workouts && python3 -m http.server 8000`, open `http://localhost:8000/`.

Expected:
- Clicking a library card (not dragging) expands it in place to show the full workout text and a row of 7 day-abbreviation buttons (MON–SUN).
- Clicking one of those day buttons assigns the workout to that day in the planner section without navigating away, and does not toggle the card's expand state (verify `stopPropagation` prevents the click from also collapsing the card).
- Clicking the card body again (not a day button) collapses it back to the snippet view.
- On the planner, clicking an **empty** day slot opens the picker modal titled "Assign a workout to <Day>", listing all 93 workouts most-recent-first, with its own category chips and search box reset to "All"/empty each time it opens.
- Inside the modal, clicking a category chip or typing in its search box narrows `#picker-list` the same way the library does, without affecting the main library's filter/search state underneath.
- Clicking an item in the picker modal assigns it to that day and closes the modal; the day slot updates immediately.
- Clicking the modal's × button, or clicking the dark overlay outside the modal box, closes it without assigning anything.
- Using Chrome DevTools' device toolbar (mobile emulation), confirm tapping an empty day slot still opens the modal (this is the primary mobile assignment path, since native HTML5 drag-and-drop is unreliable on touch).

- [ ] **Step 3: Commit**

```bash
cd ~/workouts
git add script.js
git commit -m "Add card expand/collapse, in-card day assignment, and mobile picker modal"
```

---

## Task 8: README update and final end-to-end QA pass

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: nothing new — this task documents the finished site.
- Produces: nothing consumed by other tasks (final task).

- [ ] **Step 1: Update `README.md`**

Replace the contents of `README.md`:

```markdown
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
```

- [ ] **Step 2: Final end-to-end manual QA pass**

Run: `cd ~/workouts && python3 -m http.server 8000`, open `http://localhost:8000/`, and walk through the full spec checklist:

- [ ] Library renders all 93 cards on load.
- [ ] Category chips (All/Strength/Conditioning/Benchmark/Tabata) each narrow the grid correctly; counts match `data/workouts.json` (57/16/15/5 for the four categories).
- [ ] Search box filters by both title and movement text.
- [ ] Clicking a card expands it inline with full text and 7 day-assign buttons; clicking again collapses it.
- [ ] Dragging a card onto a planner day assigns it; dragging a second card onto the same day replaces it (never stacks).
- [ ] Tapping an empty day (or using the in-card day buttons) assigns without drag-and-drop.
- [ ] The picker modal's own category chips and search box filter its list independently of the library's filters.
- [ ] Removing a day (×) empties that slot.
- [ ] "Clear week" empties all 7 days.
- [ ] Reloading the page preserves the planned week.
- [ ] Opening the page's `?plan=...` URL in a fresh private window reproduces the same week.
- [ ] "Copy link" copies the current URL to the clipboard.
- [ ] No errors in the browser console throughout.

Also re-run the automated checks one last time:

Run: `cd ~/workouts && python3 -m unittest tests.test_build_workouts_json -v && node --test tests/logic.test.js`
Expected: all green.

- [ ] **Step 3: Commit**

```bash
cd ~/workouts
git add README.md
git commit -m "Document the workout planner site in README"
```
