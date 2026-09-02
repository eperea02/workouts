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

// P90X Phase 1 day-type rotation (Kenpo X dropped to fit a 5-day week).
var DAY_PURPOSE_LABELS = {
  MON: 'Chest, Back & Abs',
  TUE: 'Plyometrics',
  WED: 'Shoulders & Arms',
  THU: 'Yoga X',
  FRI: 'Legs & Back',
};

// Maps each day to the p90xDay tag "Plan my week" should draw from.
// THU (Yoga X) has no matching workout content in the library, so it's
// left out of auto-fill entirely — pick something by hand instead.
var P90X_FOCUS_BY_DAY = {
  MON: 'chest_back',
  TUE: 'plyometrics',
  WED: 'shoulders_arms',
  FRI: 'legs_back',
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
  var p90xDay = opts.p90xDay || 'all';
  var query = (opts.query || '').trim().toLowerCase();
  return workouts.filter(function (w) {
    if (category !== 'all' && w.category !== category) return false;
    if (p90xDay !== 'all' && w.p90xDay !== p90xDay) return false;
    if (!query) return true;
    return (
      w.title.toLowerCase().indexOf(query) !== -1 ||
      w.text.toLowerCase().indexOf(query) !== -1
    );
  });
}

function pickRandom(list, randomFn) {
  return list[Math.floor(randomFn() * list.length)];
}

function pickWeekPlan(workouts, randomFn) {
  randomFn = randomFn || Math.random;
  var plan = emptyPlan();

  DAYS.forEach(function (day) {
    var focus = P90X_FOCUS_BY_DAY[day];
    if (!focus) return; // THU (Yoga X): no auto-fill, left blank
    var matches = workouts.filter(function (w) { return w.p90xDay === focus; });
    plan[day] = matches.length ? pickRandom(matches, randomFn).id : null;
  });

  return plan;
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    DAYS: DAYS,
    DAY_LABELS: DAY_LABELS,
    DAY_PURPOSE_LABELS: DAY_PURPOSE_LABELS,
    P90X_FOCUS_BY_DAY: P90X_FOCUS_BY_DAY,
    formatDateLabel: formatDateLabel,
    emptyPlan: emptyPlan,
    encodePlan: encodePlan,
    decodePlan: decodePlan,
    filterWorkouts: filterWorkouts,
    pickWeekPlan: pickWeekPlan,
  };
}
