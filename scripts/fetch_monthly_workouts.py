"""Monthly updater: qrfy page -> data/workouts_raw_extracted.json.

Looks up the workout images on the Academy qrfy page, transcribes any image
it has not imported before with the Claude API (vision), and appends the
result to the raw dataset in the same text format as the hand-entered
workouts. The usual generators then rebuild data/workouts.json and
workouts/*.html (see .github/workflows/monthly-workouts.yml).

Images already imported are tracked by filename in
data/qrfy_imported_images.json, so re-running never duplicates a workout and
never spends API credits on an image it has seen.

Requires ANTHROPIC_API_KEY (only when there is something new to transcribe).
"""
import argparse
import datetime
import json
import os
import re
import sys
import urllib.request

PAGE_URI = 'F607kMZ_UD'
API_URL = 'https://qrfy.io/api/qr/uri/{0}'
IMAGE_URL = 'https://img.qrfy.com/img/original/{0}'
SOURCE_LABEL = 'qrfy.io/p/{0}'
DEFAULT_MODEL = 'claude-sonnet-5'
README_COUNT_PATTERNS = [
    (re.compile(r'cataloging \d+ workouts'), 'cataloging {0} workouts'),
    (re.compile(r'the \d+ workouts shown'), 'the {0} workouts shown'),
]

PROMPT = """This is a photo or slide of one group-training workout table. \
Transcribe it faithfully by calling record_workout.

- title: the heading above the table (e.g. "November Lower Body").
- groups: one entry per block of the table, in order. Blocks are separated by \
blank rows; a "Finisher" row is its own block. Each block is a list of \
exercises.
- Each exercise: name is the full label exactly as written, including its \
code (e.g. "A1: Barbell Bench Press"); rest is the REST cell or null if blank; \
lines holds one string per sets/reps row, written "<sets> x <reps> @ <weight>" \
using the SETS, REPS and weight columns (e.g. "3 x 10 @ 135+/85+"). Rows with \
a blank exercise cell continue the exercise above them. If a row has its own \
rest, or the weight cell is empty, keep that information in the line text.
- Copy numbers, units and spelling exactly as shown, including typos. Do not \
guess. If a cell is unreadable, ambiguous or oddly placed, transcribe your \
best reading and add a short note describing it to notes.
- If this image is not a workout table, set is_workout to false."""

RECORD_TOOL = {
    'name': 'record_workout',
    'description': 'Record the transcribed workout table.',
    'input_schema': {
        'type': 'object',
        'properties': {
            'is_workout': {'type': 'boolean'},
            'title': {'type': 'string'},
            'groups': {
                'type': 'array',
                'items': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'name': {'type': 'string'},
                            'rest': {'type': ['string', 'null']},
                            'lines': {'type': 'array', 'items': {'type': 'string'}},
                        },
                        'required': ['name', 'rest', 'lines'],
                    },
                },
            },
            'notes': {'type': 'array', 'items': {'type': 'string'}},
        },
        'required': ['is_workout', 'title', 'groups', 'notes'],
    },
}

ASCII_REPLACEMENTS = {
    '‘': "'", '’': "'", '“': '"', '”': '"',
    '–': '-', '—': '-', ' ': ' ',
}


def to_ascii(text):
    for src, dst in ASCII_REPLACEMENTS.items():
        text = text.replace(src, dst)
    return text


def fetch_image_names(uri=PAGE_URI):
    """Image filenames currently on the page, via the page's own public API."""
    req = urllib.request.Request(
        API_URL.format(uri),
        data=b'{}',
        headers={'Content-Type': 'application/json',
                 'User-Agent': 'workouts-monthly-updater'},
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return parse_image_names(json.load(resp))


def parse_image_names(api_json):
    images = (api_json.get('data') or {}).get('images') or []
    names = [n for n in images if isinstance(n, str) and n]
    if not names:
        raise RuntimeError('qrfy page returned no images - has the page layout changed?')
    return names


def format_workout(workout):
    """Render a record_workout result in the site's plain-text format."""
    parts = [to_ascii(workout['title']).strip()]
    for group in workout['groups']:
        lines = []
        for exercise in group:
            head = to_ascii(exercise['name']).strip()
            if exercise.get('rest'):
                head += ' ({0} rest)'.format(to_ascii(exercise['rest']).strip())
            lines.append(head)
            lines.extend(to_ascii(line).strip() for line in exercise['lines'])
        parts.append('\n'.join(lines))
    return '\n\n'.join(parts)


def transcribe(image_url, model=None):
    """Transcribe one workout image with the Claude API. Returns the tool input."""
    import anthropic

    client = anthropic.Anthropic()
    message = client.messages.create(
        model=model or os.environ.get('ANTHROPIC_MODEL') or DEFAULT_MODEL,
        max_tokens=4096,
        tools=[RECORD_TOOL],
        tool_choice={'type': 'tool', 'name': RECORD_TOOL['name']},
        messages=[{
            'role': 'user',
            'content': [
                {'type': 'image', 'source': {'type': 'url', 'url': image_url}},
                {'type': 'text', 'text': PROMPT},
            ],
        }],
    )
    for block in message.content:
        if block.type == 'tool_use':
            return block.input
    raise RuntimeError('model returned no transcription for ' + image_url)


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def update_readme_counts(readme_path, count):
    if not os.path.exists(readme_path):
        return
    with open(readme_path, encoding='utf-8') as f:
        text = f.read()
    for pattern, template in README_COUNT_PATTERNS:
        text = pattern.sub(template.format(count), text)
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(text)


def run(image_names, raw_path, seen_path, transcribe_fn, today,
        category='strength', max_new=6, source=SOURCE_LABEL.format(PAGE_URI)):
    """Import every unseen image. Returns a list of {title, image, notes}."""
    raw = load_json(raw_path, [])
    seen = load_json(seen_path, [])
    new_names = [n for n in image_names if n not in seen]
    if len(new_names) > max_new:
        raise RuntimeError(
            '{0} new images found (limit {1}); refusing to import - check the page'
            .format(len(new_names), max_new))

    weekday = datetime.date.fromisoformat(today).strftime('%A').upper()
    added = []
    for name in new_names:
        url = IMAGE_URL.format(name)
        result = transcribe_fn(url)
        seen.append(name)
        if not result.get('is_workout') or not result.get('groups'):
            continue
        raw.append({
            'file': source,
            'date': today,
            'weekday_label': weekday,
            'title': None,
            'raw_text': format_workout(result),
            'category': category,
            'is_workout': True,
        })
        added.append({'title': to_ascii(result['title']).strip(), 'image': url,
                      'notes': [to_ascii(n) for n in result.get('notes', [])]})

    if new_names:
        with open(raw_path, 'w', encoding='utf-8') as f:
            f.write(json.dumps(raw, indent=2))
        with open(seen_path, 'w', encoding='utf-8') as f:
            f.write(json.dumps(seen, indent=2) + '\n')
    return added


def render_summary(added):
    lines = ['Automated monthly import from the Academy qrfy page.', '',
             'These workouts were transcribed from images by an AI model. '
             '**Please compare each against its image before merging** - a '
             'misread number is easy to miss.', '']
    for item in added:
        lines.append('### {0}'.format(item['title']))
        lines.append('[Source image]({0})'.format(item['image']))
        for note in item['notes']:
            lines.append('- Note: ' + note)
        lines.append('')
    lines.append('Merging publishes to GitHub Pages. Close the PR to discard.')
    return '\n'.join(lines) + '\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--uri', default=PAGE_URI)
    parser.add_argument('--raw', default='data/workouts_raw_extracted.json')
    parser.add_argument('--seen', default='data/qrfy_imported_images.json')
    parser.add_argument('--readme', default='README.md')
    parser.add_argument('--summary', help='write a PR description to this path')
    parser.add_argument('--today', default=datetime.date.today().isoformat())
    parser.add_argument('--max-new', type=int, default=6)
    args = parser.parse_args(argv)

    names = fetch_image_names(args.uri)
    seen = load_json(args.seen, [])
    if any(n not in seen for n in names) and not os.environ.get('ANTHROPIC_API_KEY'):
        sys.exit('New workout images found but ANTHROPIC_API_KEY is not set '
                 '(add it as a repository secret).')

    added = run(names, args.raw, args.seen, transcribe, args.today,
                max_new=args.max_new, source=SOURCE_LABEL.format(args.uri))
    if args.summary:
        with open(args.summary, 'w', encoding='utf-8') as f:
            f.write(render_summary(added))
    if not added:
        print('No new workouts.')
        return 0

    update_readme_counts(args.readme, len(load_json(args.raw, [])))
    print('Added {0} workouts: {1}'.format(
        len(added), ', '.join(a['title'] for a in added)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
