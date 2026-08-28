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
