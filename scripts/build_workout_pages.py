"""One-off generator: data/workouts.json -> workouts/<id>.html.

Generates one static, self-contained detail page per workout — no JS,
no fetch — so each workout has a real, bookmarkable URL. Re-run after
regenerating data/workouts.json to keep the pages in sync (stale pages
for workouts that no longer exist are removed automatically).
"""
import glob
import html
import json
import os

MONTH_NAMES = [
    'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
]


def format_date_label(date_str):
    year, month, day = date_str.split('-')
    return '{0} {1}, {2}'.format(MONTH_NAMES[int(month) - 1], int(day), year)


def render_workout_page(workout):
    title = html.escape(workout['title'])
    category = html.escape(workout['category'])
    date_label = format_date_label(workout['date'])
    text = html.escape(workout['text'])

    return """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{title} — My Workout Planner</title>
<meta name="description" content="{title} — a {category} workout from {date_label}." />
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Oswald:wght@500;600;700&family=Libre+Franklin:ital,wght@0,400;0,500;0,600;0,700;1,400&family=IBM+Plex+Mono:wght@500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="../styles.css" />
<link rel="icon" type="image/png" sizes="32x32" href="../assets/icon-32.png" />
<link rel="icon" type="image/png" sizes="16x16" href="../assets/icon-16.png" />
<link rel="apple-touch-icon" href="../assets/icon-180.png" />
</head>
<body>

<header class="site-header">
  <div class="wrap">
    <a class="brand" href="../index.html">\U0001F3CB My Workout Planner</a>
    <nav class="site-nav">
      <a href="../index.html#planner">Planner</a>
      <a href="../index.html#library">Library</a>
    </nav>
  </div>
</header>

<div class="wrap">

  <a class="back-link" href="../index.html#library">&larr; Back to library</a>

  <article class="detail-card">
    <header class="detail-banner">
      <p class="eyebrow">{category} &middot; {date_label}</p>
      <h1>{title}</h1>
    </header>
    <div class="detail-body">
      <pre class="detail-text">{text}</pre>
    </div>
  </article>

</div>

<footer class="site-footer">
  <div class="wrap">
    Personal workout log &mdash; built as a static site, no backend required.
  </div>
</footer>

</body>
</html>
""".format(title=title, category=category, date_label=date_label, text=text)


def build(workouts, out_dir):
    os.makedirs(out_dir, exist_ok=True)

    current_ids = {w['id'] for w in workouts}
    for existing in glob.glob(os.path.join(out_dir, '*.html')):
        stem = os.path.splitext(os.path.basename(existing))[0]
        if stem not in current_ids:
            os.remove(existing)

    written = []
    for workout in workouts:
        out_path = os.path.join(out_dir, workout['id'] + '.html')
        with open(out_path, 'w') as f:
            f.write(render_workout_page(workout))
        written.append(out_path)

    return written


if __name__ == '__main__':
    with open('data/workouts.json') as f:
        all_workouts = json.load(f)
    paths = build(all_workouts, 'workouts')
    print('Wrote {0} workout pages to workouts/'.format(len(paths)))
