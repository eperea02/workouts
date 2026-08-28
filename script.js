(function () {
  'use strict';

  window.WORKOUTS = [];

  fetch('data/workouts.json')
    .then(function (res) { return res.json(); })
    .then(function (workouts) {
      window.WORKOUTS = workouts;
      // eslint-disable-next-line no-console
      console.log('Loaded ' + workouts.length + ' workouts');
    })
    .catch(function (err) {
      // eslint-disable-next-line no-console
      console.error('Failed to load workouts.json', err);
    });
})();
