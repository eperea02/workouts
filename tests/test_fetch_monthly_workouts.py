import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

import build_workouts_json as bwj
import fetch_monthly_workouts as fmw

SAMPLE = {
    'is_workout': True,
    'title': 'December Upper Body',
    'groups': [
        [
            {'name': 'A1: Barbell Bench Press', 'rest': '30 sec',
             'lines': ['1 x 15 @ Bar', '3 x 5 @ 125+/65lb+']},
            {'name': 'A2: Cable Row', 'rest': '90 sec', 'lines': ['5 x 15 each @ 35+/20+']},
        ],
        [
            {'name': 'Finisher: Ski Erg Sprint', 'rest': None, 'lines': ['2 x 250M, AFAP']},
        ],
    ],
    'notes': ['B2 rest was blank'],
}


class FormatWorkoutTest(unittest.TestCase):
    def test_matches_site_text_format(self):
        self.assertEqual(
            fmw.format_workout(SAMPLE),
            'December Upper Body\n\n'
            'A1: Barbell Bench Press (30 sec rest)\n1 x 15 @ Bar\n3 x 5 @ 125+/65lb+\n'
            'A2: Cable Row (90 sec rest)\n5 x 15 each @ 35+/20+\n\n'
            'Finisher: Ski Erg Sprint\n2 x 250M, AFAP')

    def test_output_is_ascii(self):
        workout = dict(SAMPLE, title='December “Total” Body',
                       groups=[[{'name': 'D1: DB Curls - 21’s', 'rest': None,
                                 'lines': ['3 x 21 (7-7-7)']}]])
        text = fmw.format_workout(workout)
        text.encode('ascii')
        self.assertIn("21's", text)
        self.assertTrue(text.startswith('December "Total" Body'))


class ParseImageNamesTest(unittest.TestCase):
    def test_returns_names_in_order(self):
        api = {'data': {'images': ['a.webp', 'b.webp']}}
        self.assertEqual(fmw.parse_image_names(api), ['a.webp', 'b.webp'])

    def test_raises_when_no_images(self):
        for api in ({}, {'data': {}}, {'data': {'images': []}}):
            with self.assertRaises(RuntimeError):
                fmw.parse_image_names(api)


class RunTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.raw = os.path.join(self.dir.name, 'raw.json')
        self.seen = os.path.join(self.dir.name, 'seen.json')
        with open(self.raw, 'w') as f:
            json.dump([], f)
        with open(self.seen, 'w') as f:
            json.dump(['old.webp'], f)
        self.calls = []

    def tearDown(self):
        self.dir.cleanup()

    def fake(self, url):
        self.calls.append(url)
        return SAMPLE

    def read(self, path):
        with open(path) as f:
            return json.load(f)

    def test_imports_only_unseen_images(self):
        added = fmw.run(['old.webp', 'new.webp'], self.raw, self.seen, self.fake, '2026-12-01')
        self.assertEqual(self.calls, [fmw.IMAGE_URL.format('new.webp')])
        self.assertEqual([a['title'] for a in added], ['December Upper Body'])
        self.assertEqual(self.read(self.seen), ['old.webp', 'new.webp'])
        record, = self.read(self.raw)
        self.assertEqual(record['date'], '2026-12-01')
        self.assertEqual(record['weekday_label'], 'TUESDAY')
        self.assertEqual(record['category'], 'strength')
        self.assertTrue(record['is_workout'])
        self.assertIsNone(record['title'])

    def test_second_run_is_a_no_op(self):
        fmw.run(['new.webp'], self.raw, self.seen, self.fake, '2026-12-01')
        self.calls.clear()
        added = fmw.run(['new.webp'], self.raw, self.seen, self.fake, '2026-12-02')
        self.assertEqual(added, [])
        self.assertEqual(self.calls, [])
        self.assertEqual(len(self.read(self.raw)), 1)

    def test_non_workout_image_is_marked_seen_but_not_added(self):
        added = fmw.run(['logo.webp'], self.raw, self.seen,
                        lambda url: {'is_workout': False, 'title': '', 'groups': [], 'notes': []},
                        '2026-12-01')
        self.assertEqual(added, [])
        self.assertEqual(self.read(self.raw), [])
        self.assertIn('logo.webp', self.read(self.seen))

    def test_refuses_when_too_many_new_images(self):
        names = ['n{0}.webp'.format(i) for i in range(7)]
        with self.assertRaises(RuntimeError):
            fmw.run(names, self.raw, self.seen, self.fake, '2026-12-01')
        self.assertEqual(self.calls, [])
        self.assertEqual(self.read(self.raw), [])

    def test_failed_transcription_changes_nothing(self):
        def boom(url):
            raise RuntimeError('api down')
        with self.assertRaises(RuntimeError):
            fmw.run(['new.webp'], self.raw, self.seen, boom, '2026-12-01')
        self.assertEqual(self.read(self.raw), [])
        self.assertEqual(self.read(self.seen), ['old.webp'])

    def test_new_record_flows_through_the_site_build(self):
        fmw.run(['new.webp'], self.raw, self.seen, self.fake, '2026-12-01')
        out = os.path.join(self.dir.name, 'workouts.json')
        workout, = bwj.build(self.raw, out)
        self.assertEqual(workout['id'], '2026-12-01-december-upper-body')
        self.assertEqual(workout['title'], 'December Upper Body')
        self.assertEqual(workout['p90xDay'], 'chest_back')


class ReadmeCountTest(unittest.TestCase):
    def test_updates_both_counts(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'README.md')
            with open(path, 'w') as f:
                f.write('A site cataloging 102 workouts (x).\n- the 102 workouts shown\n')
            fmw.update_readme_counts(path, 105)
            with open(path) as f:
                text = f.read()
        self.assertEqual(text, 'A site cataloging 105 workouts (x).\n- the 105 workouts shown\n')


if __name__ == '__main__':
    unittest.main()
