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
ALLOWED_P90X_DAYS = {'legs_back', 'chest_back', 'shoulders_arms', 'plyometrics', None}


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
            for key in ('id', 'date', 'weekdayLabel', 'title', 'category', 'p90xDay', 'text'):
                self.assertIn(key, w)
            self.assertTrue(w['id'])
            self.assertTrue(w['date'])
            self.assertTrue(w['title'])
            self.assertTrue(w['text'])
            self.assertIn(w['category'], ALLOWED_CATEGORIES)
            self.assertIn(w['p90xDay'], ALLOWED_P90X_DAYS)

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


class ClassifyP90xDayTest(unittest.TestCase):
    def test_squat_deadlift_lunge_heavy_text_is_legs_back(self):
        text = (
            'Hang Squat Clean 5-5-5-3-3\n'
            'Rx+ TnG Squat Clean 5-5-5-3-3\n\n'
            '5 Rounds For Time:\n'
            '100y Sled @.75BW Rx+ BW\n'
            '8ea Lateral KB Snatch 35/26 Rx+ 53/35\n'
            '5 Reverse Lunges'
        )
        self.assertEqual(bwj.classify_p90x_day(text), 'legs_back')

    def test_bench_pull_up_chin_up_heavy_text_is_chest_back(self):
        text = (
            '4 Rounds:\n'
            '8-12 Chin Ups\n'
            '10 Pull Ups\n'
            '30 Outside Circles\n\n'
            '7 Rounds:\n'
            'Max Bench Press @ 55%\n'
            '10 Push Ups'
        )
        self.assertEqual(bwj.classify_p90x_day(text), 'chest_back')

    def test_curl_dip_tricep_overhead_press_heavy_text_is_shoulders_arms(self):
        text = (
            '5 Rounds:\n'
            '10 Overhead Press\n'
            '10ea Alt Hammer Curls\n'
            '10 Dips\n'
            '10 Tricep Extensions\n'
            '10 Lateral Raises'
        )
        self.assertEqual(bwj.classify_p90x_day(text), 'shoulders_arms')

    def test_jump_burpee_heavy_text_is_plyometrics(self):
        text = (
            'Tabata:\n'
            '20 Box Jumps\n'
            '20 Burpees\n'
            '20 Jumping Jacks\n'
            '20 Broad Jumps\n'
            '20 Mountain Climbers'
        )
        self.assertEqual(bwj.classify_p90x_day(text), 'plyometrics')

    def test_erg_row_does_not_count_as_chest_back_row(self):
        # "Row" alone means a cardio machine piece (400m Row, Cal Row), not
        # the chest/back pulling exercise — it must not flip a deadlift day
        # to chest_back just because it also has an erg row for conditioning.
        text = (
            'Deadlift\n10x2 OTM 65-75%\nRx+ add chains @60-70%\n\n'
            '3 Rounds:\n400m Row\n75 Heavy Ropes\n20 Thrusters 45/33'
        )
        self.assertEqual(bwj.classify_p90x_day(text), 'legs_back')

    def test_equipment_qualified_row_counts_as_chest_back(self):
        text = '5 Rounds:\n8-10 DB Bench Press\n10 Bent Over Rows\n5 Chin Ups'
        self.assertEqual(bwj.classify_p90x_day(text), 'chest_back')

    def test_bare_press_without_qualifier_does_not_count_toward_either_upper_day(self):
        # Bare "Press" is ambiguous between bench press (chest_back) and
        # overhead press (shoulders_arms) — it shouldn't be silently
        # attributed to either, only a qualified phrase should count.
        text = '5 Rounds:\nPress 5-5-5\nPress 3-3-3'
        self.assertIsNone(bwj.classify_p90x_day(text))

    def test_qualified_press_variants_are_disambiguated(self):
        self.assertEqual(bwj.classify_p90x_day('5x5 Bench Press'), 'chest_back')
        self.assertEqual(bwj.classify_p90x_day('5x5 Overhead Press'), 'shoulders_arms')

    def test_plural_movement_names_are_matched(self):
        # OCR'd workouts usually list movements in plural ("Squats", "Cleans",
        # "Pull Ups") — the classifier must match those, not just singular forms.
        text = '4 Sets For Max Load:\n5 Deadlifts\n5 Hang Squat Cleans\n5 Wall Balls'
        self.assertEqual(bwj.classify_p90x_day(text), 'legs_back')

    def test_no_matching_keywords_returns_none(self):
        self.assertIsNone(bwj.classify_p90x_day('Max effort AirDyne calories'))


if __name__ == '__main__':
    unittest.main()
