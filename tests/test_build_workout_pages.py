import os
import sys
import tempfile
import shutil
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

import build_workout_pages as bwp

SAMPLE_WORKOUT = {
    'id': '2025-11-10-jackie',
    'date': '2025-11-10',
    'weekdayLabel': 'MONDAY',
    'title': 'Jackie',
    'category': 'benchmark',
    'bodyFocus': 'cardio',
    'text': '5x5 Sumo Deadlift @2011\n\nJackie\nFor Time:\n1000m Row\n50 Thrusters 45/33\n30 Pull Ups',
}

UNESCAPED_WORKOUT = {
    'id': '2025-12-12-squat-box-otm-50-80',
    'date': '2025-12-12',
    'weekdayLabel': 'FRIDAY',
    'title': 'Squat Box OTM 50->80%',
    'category': 'strength',
    'bodyFocus': 'lower',
    'text': 'Squat Box OTM 50->80%\n5-5-5-3-3-3-2-2-2-2\nRx+ Squat Box w/Chains & bands',
}


class RenderWorkoutPageTest(unittest.TestCase):
    def test_includes_title_category_and_formatted_date(self):
        html = bwp.render_workout_page(SAMPLE_WORKOUT)
        self.assertIn('Jackie', html)
        self.assertIn('benchmark', html)
        self.assertIn('Nov 10, 2025', html)

    def test_includes_full_workout_text(self):
        html = bwp.render_workout_page(SAMPLE_WORKOUT)
        self.assertIn('1000m Row', html)
        self.assertIn('50 Thrusters 45/33', html)

    def test_escapes_html_special_characters(self):
        html = bwp.render_workout_page(UNESCAPED_WORKOUT)
        self.assertNotIn('50->80%\n5', html)  # raw '>' must not appear unescaped
        self.assertIn('50-&gt;80%', html)
        self.assertIn('w/Chains &amp; bands', html)

    def test_has_back_link_to_library(self):
        html = bwp.render_workout_page(SAMPLE_WORKOUT)
        self.assertIn('../index.html#library', html)


class BuildTest(unittest.TestCase):
    def setUp(self):
        self.out_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.out_dir, ignore_errors=True)

    def test_writes_one_file_per_workout(self):
        written = bwp.build([SAMPLE_WORKOUT, UNESCAPED_WORKOUT], self.out_dir)
        self.assertEqual(len(written), 2)
        self.assertTrue(os.path.exists(os.path.join(self.out_dir, '2025-11-10-jackie.html')))
        self.assertTrue(os.path.exists(os.path.join(self.out_dir, '2025-12-12-squat-box-otm-50-80.html')))

    def test_removes_stale_files_not_in_current_workouts(self):
        stale_path = os.path.join(self.out_dir, 'no-longer-exists.html')
        with open(stale_path, 'w') as f:
            f.write('<html>stale</html>')
        bwp.build([SAMPLE_WORKOUT], self.out_dir)
        self.assertFalse(os.path.exists(stale_path))
        self.assertTrue(os.path.exists(os.path.join(self.out_dir, '2025-11-10-jackie.html')))


if __name__ == '__main__':
    unittest.main()
