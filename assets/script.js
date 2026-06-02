(function() {
  const KEY = 'system-internals-theme';
  const root = document.documentElement;
  const btn = document.getElementById('theme-toggle');

  function getMode() {
    const stored = localStorage.getItem(KEY);
    return (stored === 'light' || stored === 'dark') ? stored : 'auto';
  }
  function effective(mode) {
    if (mode === 'auto') {
      return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
    return mode;
  }
  function apply(mode) {
    root.setAttribute('data-theme', mode);
    const eff = effective(mode);
    if (btn) {
      btn.textContent = eff === 'dark' ? '☀️ Light' : '🌙 Dark';
      btn.title = mode === 'auto'
        ? '시스템 설정 따름 — 클릭으로 ' + (eff === 'dark' ? 'Light' : 'Dark') + ' 고정'
        : (mode === 'dark' ? '클릭으로 Light' : '클릭으로 Dark');
    }
  }
  apply(getMode());
  if (window.matchMedia) {
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
      if (getMode() === 'auto') apply('auto');
    });
  }
  if (btn) {
    btn.addEventListener('click', () => {
      const cur = effective(getMode());
      const next = cur === 'dark' ? 'light' : 'dark';
      localStorage.setItem(KEY, next);
      apply(next);
    });
  }

  const headings = Array.from(document.querySelectorAll('h1.stage-heading, h2.section-heading'));
  const tocLinks = new Map();
  document.querySelectorAll('.toc-list a').forEach(a => {
    const href = a.getAttribute('href');
    if (href && href.startsWith('#')) tocLinks.set(href.slice(1), a);
  });

  const ACTIVATE_LINE = 80;

  function updateActive() {
    let current = null;
    for (const h of headings) {
      const top = h.getBoundingClientRect().top;
      if (top - ACTIVATE_LINE <= 0) current = h;
      else break;
    }

    document.querySelectorAll('.toc-list a.active').forEach(a => {
      a.classList.remove('active');
    });

    if (!current) return;

    const link = tocLinks.get(current.id);
    if (!link) return;

    link.classList.add('active');

    const sidebar = document.querySelector('.sidebar');
    if (!sidebar) return;
    const sbRect = sidebar.getBoundingClientRect();
    const linkRect = link.getBoundingClientRect();
    const margin = 40;

    if (linkRect.top < sbRect.top + margin) {
      sidebar.scrollTop += (linkRect.top - sbRect.top - margin);
    } else if (linkRect.bottom > sbRect.bottom - margin) {
      sidebar.scrollTop += (linkRect.bottom - sbRect.bottom + margin);
    }
  }

  let ticking = false;
  window.addEventListener('scroll', () => {
    if (!ticking) {
      window.requestAnimationFrame(() => { updateActive(); ticking = false; });
      ticking = true;
    }
  }, { passive: true });
  window.addEventListener('resize', () => {
    if (!ticking) {
      window.requestAnimationFrame(() => { updateActive(); ticking = false; });
      ticking = true;
    }
  }, { passive: true });
  updateActive();
})();
