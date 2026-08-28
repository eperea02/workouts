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
