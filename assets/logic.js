// Pure planner logic — no DOM access. Loaded as a plain <script> tag in the
// browser (exposes globals) and required directly from Node tests.

var DAYS = ['MON', 'TUE', 'WED', 'THU', 'FRI'];

var DAY_LABELS = {
  MON: 'Monday',
  TUE: 'Tuesday',
  WED: 'Wednesday',
  THU: 'Thursday',
  FRI: 'Friday',
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

var SMART_FILL_SLOTS = {
  MON: 'lower',
  TUE: 'cardio',
  WED: 'upper',
  THU: 'cardio',
  FRI: 'total',
};

function pickRandom(list, randomFn) {
  return list[Math.floor(randomFn() * list.length)];
}

function pickWeekPlan(workouts, randomFn) {
  randomFn = randomFn || Math.random;
  var plan = emptyPlan();

  var cardioPool = workouts.filter(function (w) { return w.bodyFocus === 'cardio'; });

  // MON, WED, FRI: independent picks by body focus.
  var mon = workouts.filter(function (w) { return w.bodyFocus === SMART_FILL_SLOTS.MON; });
  plan.MON = mon.length ? pickRandom(mon, randomFn).id : null;

  // TUE and THU are both "cardio" — pick two distinct workouts when possible
  // so the two cardio days of the week don't repeat the same workout.
  var tuePick = cardioPool.length ? pickRandom(cardioPool, randomFn) : null;
  plan.TUE = tuePick ? tuePick.id : null;

  var wed = workouts.filter(function (w) { return w.bodyFocus === SMART_FILL_SLOTS.WED; });
  plan.WED = wed.length ? pickRandom(wed, randomFn).id : null;

  var thuPool = cardioPool.length > 1
    ? cardioPool.filter(function (w) { return !tuePick || w.id !== tuePick.id; })
    : cardioPool;
  var thuPick = thuPool.length ? pickRandom(thuPool, randomFn) : null;
  plan.THU = thuPick ? thuPick.id : null;

  var fri = workouts.filter(function (w) { return w.bodyFocus === SMART_FILL_SLOTS.FRI; });
  plan.FRI = fri.length ? pickRandom(fri, randomFn).id : null;

  return plan;
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
    pickWeekPlan: pickWeekPlan,
  };
}
