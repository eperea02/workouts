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
ALLOWED_BODY_FOCUS = {'lower', 'upper', 'total', 'cardio'}


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
            for key in ('id', 'date', 'weekdayLabel', 'title', 'category', 'bodyFocus', 'text'):
                self.assertIn(key, w)
            self.assertTrue(w['id'])
            self.assertTrue(w['date'])
            self.assertTrue(w['title'])
            self.assertTrue(w['text'])
            self.assertIn(w['category'], ALLOWED_CATEGORIES)
            self.assertIn(w['bodyFocus'], ALLOWED_BODY_FOCUS)

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


class ClassifyBodyFocusTest(unittest.TestCase):
    def test_non_strength_categories_are_always_cardio(self):
        for category in ('conditioning', 'tabata', 'benchmark'):
            self.assertEqual(
                bwj.classify_body_focus(category, 'Bench Press Bench Press Bench Press'),
                'cardio',
            )

    def test_squat_and_clean_heavy_text_is_lower(self):
        text = (
            'Hang Squat Clean 5-5-5-3-3\n'
            'Rx+ TnG Squat Clean 5-5-5-3-3\n\n'
            '5 Rounds For Time:\n'
            '100y Sled @.75BW Rx+ BW\n'
            '8ea Lateral KB Snatch 35/26 Rx+ 53/35\n'
            '12 Burpees'
        )
        self.assertEqual(bwj.classify_body_focus('strength', text), 'lower')

    def test_bench_dip_chin_up_heavy_text_is_upper(self):
        text = (
            '4 Rounds:\n'
            '6-10 Dips Rx+ Strict HSPU\n'
            '8-12 Chin Ups\n'
            '30 Outside Circles\n'
            '15-20 Hollow Rock\n\n'
            '7 Rounds:\n'
            'Max Bench Press @ 55%\n'
            '80y Sled Push or Pull\n'
            '8 H2H KB Cleans 53/35 Rx+ 70/53'
        )
        self.assertEqual(bwj.classify_body_focus('strength', text), 'upper')

    def test_evenly_mixed_lower_and_upper_text_is_total(self):
        text = '5 Deadlift\n5 Bench Press\n5 Pull Ups\n5 Squats'
        self.assertEqual(bwj.classify_body_focus('strength', text), 'total')

    def test_erg_row_does_not_count_as_upper_body_row(self):
        # "Row" alone means a cardio machine piece (400m Row, Cal Row), not
        # the upper-body pulling exercise — it must not flip a deadlift day
        # to "upper" just because it also has an erg row for conditioning.
        text = (
            'Deadlift\n10x2 OTM 65-75%\nRx+ add chains @60-70%\n\n'
            '3 Rounds:\n400m Row\n75 Heavy Ropes\n20 Thrusters 45/33'
        )
        self.assertEqual(bwj.classify_body_focus('strength', text), 'lower')

    def test_equipment_qualified_row_counts_as_upper_body(self):
        text = '5 Rounds:\n8-10 DB Bench Press\n10 Bent Over Rows\n20 Alt Hammer Curl'
        self.assertEqual(bwj.classify_body_focus('strength', text), 'upper')

    def test_plural_movement_names_are_matched(self):
        # OCR'd workouts usually list movements in plural ("Squats", "Cleans",
        # "Pull Ups") — the classifier must match those, not just singular forms.
        text = '4 Sets For Max Load:\n5 Deadlifts\n5 Hang Squat Cleans\n5 Wall Balls'
        self.assertEqual(bwj.classify_body_focus('strength', text), 'lower')

    def test_no_matching_keywords_defaults_to_total(self):
        self.assertEqual(bwj.classify_body_focus('strength', 'Max effort AirDyne calories'), 'total')


if __name__ == '__main__':
    unittest.main()
