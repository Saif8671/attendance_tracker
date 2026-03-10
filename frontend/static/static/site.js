function initTabs(containerId, defaultTab) {
  const root = document.getElementById(containerId);
  if (!root) return;
  const buttons = root.querySelectorAll('[data-tab]');
  const panes = root.querySelectorAll('[data-pane]');

  function activate(tab) {
    buttons.forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
    panes.forEach(p => p.classList.toggle('active', p.dataset.pane === tab));
  }

  buttons.forEach(btn => btn.addEventListener('click', () => {
    activate(btn.dataset.tab);
    const url = new URL(window.location);
    url.searchParams.set('tab', btn.dataset.tab);
    history.replaceState({}, '', url);
  }));

  const fromUrl = new URLSearchParams(window.location.search).get('tab');
  activate(fromUrl || defaultTab || buttons[0]?.dataset.tab);
}

function filterTable(inputId, tableId) {
  const q = (document.getElementById(inputId)?.value || '').toLowerCase().trim();
  const rows = document.querySelectorAll(`#${tableId} tbody tr`);
  rows.forEach(r => {
    const t = r.innerText.toLowerCase();
    r.style.display = t.includes(q) ? '' : 'none';
  });
}

function setupMobileSidebar() {
  const btn = document.getElementById('mobileMenuBtn');
  const side = document.getElementById('appSidebar');
  if (!btn || !side) return;
  btn.addEventListener('click', () => side.classList.toggle('open'));
}

document.addEventListener('DOMContentLoaded', setupMobileSidebar);
