(function () {
  'use strict';

  var libraryGrid = document.getElementById('library-grid');
  var libraryEmpty = document.getElementById('library-empty');
  var filterBar = document.getElementById('filter-bar');
  var searchInput = document.getElementById('search-input');

  var state = {
    category: 'all',
    query: '',
  };

  window.WORKOUTS = [];

  function escapeHtml(str) {
    var div = document.createElement('div');
    div.textContent = str == null ? '' : str;
    return div.innerHTML;
  }

  function snippet(text, maxLines) {
    var lines = text.split('\n').filter(function (l) { return l.trim() !== ''; });
    return lines.slice(0, maxLines).join('\n');
  }

  function buildCard(workout) {
    var card = document.createElement('article');
    card.className = 'workout-card';
    card.dataset.id = workout.id;
    card.draggable = true;

    card.innerHTML =
      '<span class="badge badge-' + workout.category + '">' +
        escapeHtml(workout.category) +
        '<span class="badge-date">' + escapeHtml(formatDateLabel(workout.date)) + '</span>' +
      '</span>' +
      '<h3>' + escapeHtml(workout.title) + '</h3>' +
      '<p class="card-snippet">' + escapeHtml(snippet(workout.text, 2)) + '&hellip;</p>' +
      '<p class="card-full-text">' + escapeHtml(workout.text) + '</p>';

    card.addEventListener('dragstart', function (e) {
      card.classList.add('is-dragging');
      e.dataTransfer.setData('text/plain', workout.id);
      e.dataTransfer.effectAllowed = 'copy';
    });
    card.addEventListener('dragend', function () {
      card.classList.remove('is-dragging');
    });

    return card;
  }

  function byDateDescending(a, b) {
    return b.date.localeCompare(a.date);
  }

  function renderLibrary() {
    var filtered = filterWorkouts(window.WORKOUTS, state).slice().sort(byDateDescending);
    libraryGrid.innerHTML = '';
    filtered.forEach(function (w) {
      libraryGrid.appendChild(buildCard(w));
    });
    libraryEmpty.hidden = filtered.length !== 0;
  }

  filterBar.addEventListener('click', function (e) {
    var chip = e.target.closest ? e.target.closest('.filter-chip') : null;
    if (!chip) return;
    Array.prototype.forEach.call(filterBar.querySelectorAll('.filter-chip'), function (c) {
      c.classList.remove('is-active');
    });
    chip.classList.add('is-active');
    state.category = chip.dataset.category;
    renderLibrary();
  });

  searchInput.addEventListener('input', function () {
    state.query = searchInput.value;
    renderLibrary();
  });

  fetch('data/workouts.json')
    .then(function (res) { return res.json(); })
    .then(function (workouts) {
      window.WORKOUTS = workouts;
      renderLibrary();
    })
    .catch(function (err) {
      // eslint-disable-next-line no-console
      console.error('Failed to load workouts.json', err);
    });

  window.__renderLibrary = renderLibrary;
})();
