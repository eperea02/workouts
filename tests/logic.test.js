const test = require('node:test');
const assert = require('node:assert');
const {
  DAYS,
  DAY_LABELS,
  formatDateLabel,
  emptyPlan,
  encodePlan,
  decodePlan,
  filterWorkouts,
} = require('../assets/logic.js');

test('DAYS has the 7 day codes in week order', () => {
  assert.deepStrictEqual(DAYS, ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']);
});

test('DAY_LABELS has a full name for every day code', () => {
  DAYS.forEach((d) => {
    assert.strictEqual(typeof DAY_LABELS[d], 'string');
    assert.ok(DAY_LABELS[d].length > 0);
  });
});

test('formatDateLabel formats an ISO date without timezone drift', () => {
  assert.strictEqual(formatDateLabel('2025-11-10'), 'Nov 10, 2025');
  assert.strictEqual(formatDateLabel('2026-01-02'), 'Jan 2, 2026');
  assert.strictEqual(formatDateLabel('2025-12-31'), 'Dec 31, 2025');
});

test('emptyPlan has all 7 days set to null', () => {
  const plan = emptyPlan();
  assert.strictEqual(Object.keys(plan).length, 7);
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
