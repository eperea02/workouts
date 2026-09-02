const test = require('node:test');
const assert = require('node:assert');
const {
  DAYS,
  DAY_LABELS,
  DAY_PURPOSE_LABELS,
  P90X_FOCUS_BY_DAY,
  formatDateLabel,
  emptyPlan,
  encodePlan,
  decodePlan,
  filterWorkouts,
  pickWeekPlan,
} = require('../assets/logic.js');

test('DAYS has the 5 weekday codes in order', () => {
  assert.deepStrictEqual(DAYS, ['MON', 'TUE', 'WED', 'THU', 'FRI']);
});

test('DAY_LABELS has a full name for every day code', () => {
  DAYS.forEach((d) => {
    assert.strictEqual(typeof DAY_LABELS[d], 'string');
    assert.ok(DAY_LABELS[d].length > 0);
  });
});

test('DAY_PURPOSE_LABELS has a P90X day-type label for every day code', () => {
  DAYS.forEach((d) => {
    assert.strictEqual(typeof DAY_PURPOSE_LABELS[d], 'string');
    assert.ok(DAY_PURPOSE_LABELS[d].length > 0);
  });
});

test('P90X_FOCUS_BY_DAY has no entry for THU (Yoga X is manual-pick only)', () => {
  assert.strictEqual(P90X_FOCUS_BY_DAY.THU, undefined);
  ['MON', 'TUE', 'WED', 'FRI'].forEach((d) => {
    assert.strictEqual(typeof P90X_FOCUS_BY_DAY[d], 'string');
  });
});

test('formatDateLabel formats an ISO date without timezone drift', () => {
  assert.strictEqual(formatDateLabel('2025-11-10'), 'Nov 10, 2025');
  assert.strictEqual(formatDateLabel('2026-01-02'), 'Jan 2, 2026');
  assert.strictEqual(formatDateLabel('2025-12-31'), 'Dec 31, 2025');
});

test('emptyPlan has all 5 days set to null', () => {
  const plan = emptyPlan();
  assert.strictEqual(Object.keys(plan).length, 5);
  DAYS.forEach((d) => assert.strictEqual(plan[d], null));
});

test('encodePlan/decodePlan round-trip a partially filled plan', () => {
  const plan = emptyPlan();
  plan.MON = '2025-11-10-jackie';
  plan.FRI = '2025-12-05-strength';
  const encoded = encodePlan(plan);
  assert.strictEqual(typeof encoded, 'string');
  const decoded = decodePlan(encoded);
  assert.deepStrictEqual(decoded, plan);
});

test('encodePlan/decodePlan round-trip an empty plan', () => {
  const plan = emptyPlan();
  assert.deepStrictEqual(decodePlan(encodePlan(plan)), plan);
});

test('decodePlan returns null for malformed input', () => {
  assert.strictEqual(decodePlan('not json'), null);
  assert.strictEqual(decodePlan('{}'), null);
  assert.strictEqual(decodePlan('[1,2,3]'), null);
  assert.strictEqual(decodePlan('[]'), null);
});

const SAMPLE_WORKOUTS = [
  { id: '1', title: 'Jackie', category: 'benchmark', text: 'row thrusters pull ups' },
  { id: '2', title: 'Box Squat', category: 'strength', text: 'box squat 5x5' },
  { id: '3', title: 'Tabata Circuit', category: 'tabata', text: 'ski cals push ups' },
];

test('filterWorkouts with no options returns everything', () => {
  const result = filterWorkouts(SAMPLE_WORKOUTS, {});
  assert.strictEqual(result.length, 3);
});

test('filterWorkouts filters by category', () => {
  const result = filterWorkouts(SAMPLE_WORKOUTS, { category: 'strength' });
  assert.deepStrictEqual(result.map((w) => w.id), ['2']);
});

test('filterWorkouts filters by search query across title and text, case-insensitively', () => {
  const result = filterWorkouts(SAMPLE_WORKOUTS, { query: 'THRUSTER' });
  assert.deepStrictEqual(result.map((w) => w.id), ['1']);
});

test('filterWorkouts combines category and query filters', () => {
  const result = filterWorkouts(SAMPLE_WORKOUTS, { category: 'benchmark', query: 'squat' });
  assert.strictEqual(result.length, 0);
});

test('filterWorkouts category "all" matches every category', () => {
  const result = filterWorkouts(SAMPLE_WORKOUTS, { category: 'all' });
  assert.strictEqual(result.length, 3);
});

const P90X_TAGGED_WORKOUTS = [
  { id: '1', title: 'Bench Day', category: 'strength', text: 'bench press', p90xDay: 'chest_back' },
  { id: '2', title: 'Overhead Day', category: 'strength', text: 'overhead press', p90xDay: 'shoulders_arms' },
];

test('filterWorkouts filters by p90xDay', () => {
  const result = filterWorkouts(P90X_TAGGED_WORKOUTS, { p90xDay: 'shoulders_arms' });
  assert.deepStrictEqual(result.map((w) => w.id), ['2']);
});

test('filterWorkouts p90xDay "all" matches every workout', () => {
  const result = filterWorkouts(P90X_TAGGED_WORKOUTS, { p90xDay: 'all' });
  assert.strictEqual(result.length, 2);
});

const WORKOUTS_BY_P90X_DAY = [
  { id: 'legs-back-1', p90xDay: 'legs_back' },
  { id: 'chest-back-1', p90xDay: 'chest_back' },
  { id: 'shoulders-arms-1', p90xDay: 'shoulders_arms' },
  { id: 'plyo-1', p90xDay: 'plyometrics' },
];

function alwaysZero() {
  return 0;
}

test('pickWeekPlan assigns MON=chest_back, TUE=plyometrics, WED=shoulders_arms, FRI=legs_back', () => {
  const plan = pickWeekPlan(WORKOUTS_BY_P90X_DAY, alwaysZero);
  assert.strictEqual(plan.MON, 'chest-back-1');
  assert.strictEqual(plan.TUE, 'plyo-1');
  assert.strictEqual(plan.WED, 'shoulders-arms-1');
  assert.strictEqual(plan.FRI, 'legs-back-1');
});

test('pickWeekPlan leaves THU (Yoga X) blank — no auto-fill match exists', () => {
  const plan = pickWeekPlan(WORKOUTS_BY_P90X_DAY, alwaysZero);
  assert.strictEqual(plan.THU, null);
});

test('pickWeekPlan returns exactly the 5 weekday keys', () => {
  const plan = pickWeekPlan(WORKOUTS_BY_P90X_DAY, alwaysZero);
  assert.deepStrictEqual(Object.keys(plan).sort(), [...DAYS].sort());
});

test('pickWeekPlan leaves a slot null when no workout matches that day-type', () => {
  const noShouldersArms = [
    { id: 'legs-back-1', p90xDay: 'legs_back' },
    { id: 'chest-back-1', p90xDay: 'chest_back' },
  ];
  const plan = pickWeekPlan(noShouldersArms, alwaysZero);
  assert.strictEqual(plan.WED, null);
  assert.strictEqual(plan.TUE, null);
});
