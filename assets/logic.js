// Pure planner logic — no DOM access. Loaded as a plain <script> tag in the
// browser (exposes globals) and required directly from Node tests.

var DAYS = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN'];

var DAY_LABELS = {
  MON: 'Monday',
  TUE: 'Tuesday',
  WED: 'Wednesday',
  THU: 'Thursday',
  FRI: 'Friday',
  SAT: 'Saturday',
  SUN: 'Sunday',
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

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    DAYS: DAYS,
    DAY_LABELS: DAY_LABELS,
    formatDateLabel: formatDateLabel,
    emptyPlan: emptyPlan,
    encodePlan: encodePlan,
    decodePlan: decodePlan,
    filterWorkouts: filterWorkouts,
  };
}
