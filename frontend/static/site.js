/* AttendX site.js — Tabs, mobile menu, table filter, toasts, counters */
'use strict';

// ── Tabs ─────────────────────────────────────────────────────────────────────
function initTabs(containerId, activeTab) {
  const c = document.getElementById(containerId);
  if (!c) return;
  const buttons = c.querySelectorAll('[data-tab]');
  const panes   = c.querySelectorAll('[data-pane]');

  function activate(name) {
    buttons.forEach(b => b.classList.toggle('active', b.dataset.tab === name));
    panes.forEach(p => p.classList.toggle('active', p.dataset.pane === name));
  }

  buttons.forEach(b => b.addEventListener('click', () => activate(b.dataset.tab)));
  activate(activeTab || (buttons[0] && buttons[0].dataset.tab) || 'overview');
}

// ── Mobile sidebar ───────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  const btn  = document.getElementById('mobileMenuBtn');
  const side = document.getElementById('appSidebar');
  if (btn && side) {
    btn.addEventListener('click', () => side.classList.toggle('open'));
    document.addEventListener('click', e => {
      if (!side.contains(e.target) && e.target !== btn) side.classList.remove('open');
    });
  }

  // Animate metric counters
  document.querySelectorAll('.metric .value[data-count]').forEach(el => {
    const target = parseInt(el.dataset.count, 10);
    let current = 0;
    const step  = Math.ceil(target / 40);
    const timer = setInterval(() => {
      current = Math.min(current + step, target);
      el.textContent = current;
      if (current >= target) clearInterval(timer);
    }, 25);
  });
});

// ── Table filter ─────────────────────────────────────────────────────────────
function filterTable(inputId, tableId) {
  const q   = document.getElementById(inputId).value.toLowerCase();
  const tbl = document.getElementById(tableId);
  if (!tbl) return;
  tbl.querySelectorAll('tbody tr').forEach(row => {
    row.style.display = row.textContent.toLowerCase().includes(q) ? '' : 'none';
  });
}

// ── Toast ─────────────────────────────────────────────────────────────────────
function showToast(msg, type = 'info') {
  let container = document.getElementById('toastContainer');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toastContainer';
    document.body.appendChild(container);
  }
  const t = document.createElement('div');
  t.className = 'toast';
  t.textContent = msg;
  if (type === 'error')   t.style.borderColor = 'rgba(239,68,68,.5)';
  if (type === 'success') t.style.borderColor = 'rgba(16,185,129,.5)';
  container.appendChild(t);
  setTimeout(() => t.remove(), 3500);
}

// ── Expose globals ────────────────────────────────────────────────────────────
window.initTabs    = initTabs;
window.filterTable = filterTable;
window.showToast   = showToast;
