(function () {
  function classifyStatus(text) {
    var value = (text || '').trim().toLowerCase();
    if (!value) return 'isc-info';

    var positive = ['active', 'paid', 'published', 'yes', 'delivered', 'processing', 'packed', 'shipped', 'connected', 'completed'];
    var negative = ['inactive', 'unpaid', 'unpublished', 'no', 'cancelled', 'canceled', 'failed', 'error', 'missing', 'blocked'];
    var warn = ['pending', 'partial', 'partially allocated, waiting for stock', 'warning'];

    if (positive.indexOf(value) >= 0) return 'isc-positive';
    if (negative.indexOf(value) >= 0) return 'isc-negative';
    if (warn.indexOf(value) >= 0) return 'isc-warn';
    return 'isc-info';
  }

  function enhanceSidebar() {
    var modules = document.querySelectorAll('#nav-sidebar .module');
    modules.forEach(function (module, index) {
      var caption = module.querySelector('caption');
      if (!caption || caption.querySelector('.isc-app-toggle')) return;

      var current = module.classList.contains('current-app') || module.querySelector('.current-model');
      var key = 'idara.sidebar.module.' + index;
      var stored = localStorage.getItem(key);
      var collapsed = stored === null ? !current : stored === '1';

      var toggle = document.createElement('button');
      toggle.type = 'button';
      toggle.className = 'isc-app-toggle';
      toggle.textContent = collapsed ? 'Show' : 'Hide';
      toggle.setAttribute('aria-expanded', collapsed ? 'false' : 'true');

      toggle.addEventListener('click', function () {
        module.classList.toggle('isc-collapsed');
        var nowCollapsed = module.classList.contains('isc-collapsed');
        toggle.textContent = nowCollapsed ? 'Show' : 'Hide';
        toggle.setAttribute('aria-expanded', nowCollapsed ? 'false' : 'true');
        localStorage.setItem(key, nowCollapsed ? '1' : '0');
      });

      caption.appendChild(toggle);

      if (collapsed) {
        module.classList.add('isc-collapsed');
      }
    });
  }

  function decorateStatusCells() {
    var selector = [
      '#result_list td.field-status',
      '#result_list td.field-is_active',
      '#result_list td.field-is_paid',
      '#result_list td.field-coin_status'
    ].join(',');

    var cells = document.querySelectorAll(selector);
    cells.forEach(function (cell) {
      if (cell.querySelector('.isc-status-pill')) return;
      if (cell.querySelector('img.boolean-icon')) return;
      if (cell.querySelector('a')) return;

      var text = (cell.textContent || '').trim();
      if (!text || text === '-') return;

      var pill = document.createElement('span');
      pill.className = 'isc-status-pill ' + classifyStatus(text);
      pill.textContent = text;

      cell.textContent = '';
      cell.appendChild(pill);
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    enhanceSidebar();
    decorateStatusCells();
  });
})();
