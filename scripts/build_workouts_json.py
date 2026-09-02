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

# P90X Phase 1 day-type classification. Each workout is scored against all
# four keyword sets; the highest-scoring type wins (ties broken by
# P90X_DAY_PRIORITY), and a workout with zero hits in every set gets no
# p90xDay tag (None) — it's still browsable in the library and manually
# assignable to any day, it's just not auto-matched by "Plan my week".

LEGS_BACK_RE = re.compile(
    r'\b(?:squats?|deadlifts?|lunges?|cleans?|snatch(?:es)?|sumo|jerks?|'
    r'swings?|step[- ]ups?|wall balls?|thrusters?)\b',
    re.IGNORECASE,
)

CHEST_BACK_RE = re.compile(
    r'\b(?:bench(?:es)?|chest|push[- ]?ups?|pull[- ]?ups?|chin[- ]?ups?|'
    r'muscle[- ]?ups?|lat pulldowns?|'
    r'(?:bench|chest|incline|decline|close[- ]grip|narrow[- ]grip)\s+press(?:es)?|'
    # "row" alone is ambiguous — it also means an erg/cardio piece
    # ("400m Row", "Cal Row"), so only count it as chest/back work when a
    # strength-equipment qualifier precedes it (e.g. "Bent Over Row").
    r'(?:bent[- ]over|supinated bent|t[- ]?bar|db|bb|barbell|ring|'
    r'seated|inverted|cable)\s+rows?)\b',
    re.IGNORECASE,
)

SHOULDERS_ARMS_RE = re.compile(
    r'\b(?:curls?|dips?|triceps?|skull crushers?|lateral raises?|upright rows?|'
    r'thrusters?|'
    r'(?:overhead|shoulder|military|push|strict|seated|standing|arnold)\s+press(?:es)?)\b',
    re.IGNORECASE,
)

PLYOMETRICS_RE = re.compile(
    r'\b(?:jump(?:ing)?s?|burpees?|jump ropes?|double[- ]unders?|plyo\w*|'
    r'high knees?|mountain climbers?|hops?)\b',
    re.IGNORECASE,
)

P90X_DAY_PRIORITY = ['legs_back', 'chest_back', 'shoulders_arms', 'plyometrics']


def classify_p90x_day(text):
    scores = {
        'legs_back': len(LEGS_BACK_RE.findall(text)),
        'chest_back': len(CHEST_BACK_RE.findall(text)),
        'shoulders_arms': len(SHOULDERS_ARMS_RE.findall(text)),
        'plyometrics': len(PLYOMETRICS_RE.findall(text)),
    }
    top_score = max(scores.values())
    if top_score == 0:
        return None
    for day_type in P90X_DAY_PRIORITY:
        if scores[day_type] == top_score:
            return day_type
    return None


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
            'p90xDay': classify_p90x_day(text),
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
