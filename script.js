(function () {
  'use strict';

  var libraryGrid = document.getElementById('library-grid');
  var libraryEmpty = document.getElementById('library-empty');
  var filterBar = document.getElementById('filter-bar');
  var searchInput = document.getElementById('search-input');
  var plannerGrid = document.getElementById('planner-grid');
  var plannerClearBtn = document.getElementById('planner-clear');
  var plannerCopyLinkBtn = document.getElementById('planner-copy-link');
  var plannerSmartFillBtn = document.getElementById('planner-smart-fill');
  var pickerModal = document.getElementById('picker-modal');
  var pickerModalTitle = document.getElementById('picker-modal-title');
  var pickerFilterBar = document.getElementById('picker-filter-bar');
  var pickerSearchInput = document.getElementById('picker-search-input');
  var pickerList = document.getElementById('picker-list');
  var pickerClose = document.getElementById('picker-close');
  var pickerDay = null;
  var pickerState = { category: 'all', query: '' };

  var PLAN_STORAGE_KEY = 'workout-planner-plan-v1';
  var PLAN_URL_PARAM = 'plan';

  var state = {
    category: 'all',
    query: '',
    plan: emptyPlan(),
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

  function findWorkoutById(id) {
    for (var i = 0; i < window.WORKOUTS.length; i++) {
      if (window.WORKOUTS[i].id === id) return window.WORKOUTS[i];
    }
    return null;
  }

  function buildAssignRow(workoutId) {
    var row = document.createElement('div');
    row.className = 'assign-row';
    DAYS.forEach(function (day) {
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'day-pick-btn';
      btn.textContent = day;
      btn.addEventListener('click', function (e) {
        e.stopPropagation();
        assignWorkout(day, workoutId);
      });
      row.appendChild(btn);
    });
    return row;
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
      '<h3><a href="workouts/' + encodeURIComponent(workout.id) + '.html">' +
        escapeHtml(workout.title) + '</a></h3>' +
      '<p class="card-snippet">' + escapeHtml(snippet(workout.text, 2)) + '&hellip;</p>' +
      '<p class="card-full-text">' + escapeHtml(workout.text) + '</p>';

    card.querySelector('h3 a').addEventListener('click', function (e) {
      e.stopPropagation();
    });

    card.appendChild(buildAssignRow(workout.id));

    card.addEventListener('click', function () {
      card.classList.toggle('is-expanded');
    });

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

  function persistPlan() {
    try {
      localStorage.setItem(PLAN_STORAGE_KEY, encodePlan(state.plan));
    } catch (e) { /* localStorage unavailable — plan still works via URL/session */ }
    try {
      var url = new URL(window.location.href);
      url.searchParams.set(PLAN_URL_PARAM, encodePlan(state.plan));
      window.history.replaceState(null, '', url.toString());
    } catch (e) { /* ignore */ }
  }

  function loadPlan() {
    try {
      var url = new URL(window.location.href);
      var fromUrl = url.searchParams.get(PLAN_URL_PARAM);
      if (fromUrl) {
        var decoded = decodePlan(fromUrl);
        if (decoded) return decoded;
      }
    } catch (e) { /* ignore */ }
    try {
      var stored = localStorage.getItem(PLAN_STORAGE_KEY);
      if (stored) {
        var decodedStored = decodePlan(stored);
        if (decodedStored) return decodedStored;
      }
    } catch (e) { /* ignore */ }
    return emptyPlan();
  }

  function assignWorkout(day, workoutId) {
    state.plan[day] = workoutId;
    persistPlan();
    renderPlanner();
  }

  function clearDay(day) {
    state.plan[day] = null;
    persistPlan();
    renderPlanner();
  }

  function buildDaySlotContent(day) {
    var workoutId = state.plan[day];
    if (!workoutId) {
      var emptyBtn = document.createElement('button');
      emptyBtn.type = 'button';
      emptyBtn.className = 'day-slot-empty';
      emptyBtn.textContent = 'Tap or drag a workout here';
      emptyBtn.addEventListener('click', function () {
        if (typeof window.__openPickerForDay === 'function') {
          window.__openPickerForDay(day);
        }
      });
      return emptyBtn;
    }

    var workout = findWorkoutById(workoutId);
    var wrap = document.createElement('div');
    wrap.className = 'day-slot-card';
    if (!workout) {
      wrap.innerHTML = '<h4>Workout no longer available</h4>';
      return wrap;
    }

    wrap.innerHTML =
      '<span class="badge badge-' + workout.category + '">' + escapeHtml(workout.category) + '</span>' +
      '<h4><a href="workouts/' + encodeURIComponent(workout.id) + '.html">' +
        escapeHtml(workout.title) + '</a></h4>';

    var footer = document.createElement('div');
    footer.className = 'day-slot-card-footer';

    var removeBtn = document.createElement('button');
    removeBtn.type = 'button';
    removeBtn.className = 'day-remove-btn';
    removeBtn.setAttribute('aria-label', 'Remove');
    removeBtn.textContent = '×';
    removeBtn.addEventListener('click', function () {
      clearDay(day);
    });

    footer.appendChild(removeBtn);
    wrap.appendChild(footer);
    return wrap;
  }

  function renderPlanner() {
    plannerGrid.innerHTML = '';
    DAYS.forEach(function (day) {
      var column = document.createElement('div');
      column.className = 'day-column';

      var header = document.createElement('div');
      header.className = 'day-column-header';
      header.textContent = DAY_LABELS[day];
      column.appendChild(header);

      var slot = document.createElement('div');
      slot.className = 'day-slot' + (state.plan[day] ? ' is-filled' : '');
      slot.dataset.day = day;
      slot.appendChild(buildDaySlotContent(day));

      slot.addEventListener('dragover', function (e) {
        e.preventDefault();
        slot.classList.add('is-drag-over');
      });
      slot.addEventListener('dragleave', function () {
        slot.classList.remove('is-drag-over');
      });
      slot.addEventListener('drop', function (e) {
        e.preventDefault();
        slot.classList.remove('is-drag-over');
        var workoutId = e.dataTransfer.getData('text/plain');
        if (workoutId) assignWorkout(day, workoutId);
      });

      column.appendChild(slot);
      plannerGrid.appendChild(column);
    });
  }

  function buildPickerItem(workout) {
    var li = document.createElement('li');
    li.className = 'picker-item';
    li.innerHTML =
      '<span class="badge badge-' + workout.category + '">' + escapeHtml(workout.category) + '</span>' +
      '<h4>' + escapeHtml(workout.title) + '</h4>';
    li.addEventListener('click', function () {
      if (pickerDay) assignWorkout(pickerDay, workout.id);
      closePicker();
    });
    return li;
  }

  function renderPickerList() {
    pickerList.innerHTML = '';
    var items = filterWorkouts(window.WORKOUTS, pickerState).slice().sort(byDateDescending);
    items.forEach(function (w) {
      pickerList.appendChild(buildPickerItem(w));
    });
  }

  function resetPickerFilters() {
    pickerState = { category: 'all', query: '' };
    pickerSearchInput.value = '';
    Array.prototype.forEach.call(pickerFilterBar.querySelectorAll('.filter-chip'), function (c) {
      c.classList.toggle('is-active', c.dataset.category === 'all');
    });
  }

  function openPickerForDay(day) {
    pickerDay = day;
    pickerModalTitle.textContent = 'Assign a workout to ' + DAY_LABELS[day];
    resetPickerFilters();
    renderPickerList();
    pickerModal.hidden = false;
  }

  function closePicker() {
    pickerModal.hidden = true;
    pickerDay = null;
  }

  pickerFilterBar.addEventListener('click', function (e) {
    var chip = e.target.closest ? e.target.closest('.filter-chip') : null;
    if (!chip) return;
    Array.prototype.forEach.call(pickerFilterBar.querySelectorAll('.filter-chip'), function (c) {
      c.classList.remove('is-active');
    });
    chip.classList.add('is-active');
    pickerState.category = chip.dataset.category;
    renderPickerList();
  });

  pickerSearchInput.addEventListener('input', function () {
    pickerState.query = pickerSearchInput.value;
    renderPickerList();
  });

  pickerClose.addEventListener('click', closePicker);
  pickerModal.addEventListener('click', function (e) {
    if (e.target === pickerModal) closePicker();
  });

  window.__openPickerForDay = openPickerForDay;

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

  plannerClearBtn.addEventListener('click', function () {
    state.plan = emptyPlan();
    persistPlan();
    renderPlanner();
  });

  plannerSmartFillBtn.addEventListener('click', function () {
    state.plan = pickWeekPlan(window.WORKOUTS);
    persistPlan();
    renderPlanner();
  });

  plannerCopyLinkBtn.addEventListener('click', function () {
    persistPlan();
    var link = window.location.href;
    var originalText = 'Copy link';

    function showMessage(text, delay) {
      plannerCopyLinkBtn.textContent = text;
      setTimeout(function () { plannerCopyLinkBtn.textContent = originalText; }, delay);
    }

    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(link).then(
        function () { showMessage('Copied!', 1500); },
        function () { showMessage('Copy failed', 2500); }
      );
    } else {
      showMessage('Copy failed', 2500);
    }
  });

  fetch('data/workouts.json')
    .then(function (res) { return res.json(); })
    .then(function (workouts) {
      window.WORKOUTS = workouts;
      state.plan = loadPlan();
      renderLibrary();
      renderPlanner();
    })
    .catch(function (err) {
      // eslint-disable-next-line no-console
      console.error('Failed to load workouts.json', err);
    });

  window.__renderLibrary = renderLibrary;
  window.__renderPlanner = renderPlanner;
  window.__assignWorkout = assignWorkout;
  window.__findWorkoutById = findWorkoutById;
})();
