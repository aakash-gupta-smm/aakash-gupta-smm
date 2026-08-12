gsap.registerPlugin(ScrollTrigger, ScrollToPlugin);

const FINE_POINTER = window.matchMedia('(hover: hover) and (pointer: fine)').matches;
const REDUCED = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

/* ── SCROLL PROGRESS ──────────────────────────────────────── */
const progress = document.getElementById('progress');
function updateProgress() {
  const max = document.documentElement.scrollHeight - window.innerHeight;
  progress.style.width = max > 0 ? `${(window.scrollY / max) * 100}%` : '0%';
}
window.addEventListener('scroll', updateProgress, { passive: true });
updateProgress();

/* ── CUSTOM CURSOR ────────────────────────────────────────── */
if (FINE_POINTER) {
  const cursor = document.getElementById('cursor');
  const follower = document.getElementById('cursor-follower');

  window.addEventListener('mousemove', (e) => {
    gsap.set(cursor, { x: e.clientX, y: e.clientY });
    gsap.to(follower, { x: e.clientX, y: e.clientY, duration: 0.18, ease: 'power2.out' });
  });

  const hoverables = 'a, button, .case-card, .service-card, .contact-card, .step, .timeline-content';
  document.querySelectorAll(hoverables).forEach(el => {
    el.addEventListener('mouseenter', () => {
      gsap.to(follower, { scale: 2.2, borderColor: 'rgba(255,91,4,0.85)', duration: 0.25 });
      gsap.to(cursor, { scale: 0.4, duration: 0.25 });
    });
    el.addEventListener('mouseleave', () => {
      gsap.to(follower, { scale: 1, borderColor: 'rgba(255,255,255,0.35)', duration: 0.25 });
      gsap.to(cursor, { scale: 1, duration: 0.25 });
    });
  });
}

/* ── MAGNETIC BUTTONS ─────────────────────────────────────── */
if (FINE_POINTER && !REDUCED) {
  document.querySelectorAll('.magnetic').forEach(el => {
    el.addEventListener('pointermove', (e) => {
      const r = el.getBoundingClientRect();
      const x = e.clientX - (r.left + r.width / 2);
      const y = e.clientY - (r.top + r.height / 2);
      gsap.to(el, { x: x * 0.28, y: y * 0.35, duration: 0.5, ease: 'power3.out' });
    });
    el.addEventListener('pointerleave', () => {
      gsap.to(el, { x: 0, y: 0, duration: 0.6, ease: 'elastic.out(1, 0.4)' });
    });
  });
}

/* ── NAV ──────────────────────────────────────────────────── */
const nav = document.getElementById('nav');
window.addEventListener('scroll', () => {
  nav.classList.toggle('scrolled', window.scrollY > 60);
}, { passive: true });

/* ── HERO INTRO ───────────────────────────────────────────── */
gsap.timeline({ defaults: { ease: 'power4.out' } })
  .fromTo('.hero-tag', { opacity: 0, y: 18 }, { opacity: 1, y: 0, duration: 0.7 }, 0.15)
  .fromTo('.hero-title .line-inner',
    { yPercent: 108 },
    { yPercent: 0, duration: 1.05, stagger: 0.11 }, 0.25)
  .fromTo('.hero-sub', { opacity: 0, y: 18 }, { opacity: 1, y: 0, duration: 0.75 }, 0.9)
  .fromTo('.hero-actions', { opacity: 0, y: 18 }, { opacity: 1, y: 0, duration: 0.75 }, 1.05)
  .fromTo('.hero-statement', { opacity: 0, y: 18 }, { opacity: 1, y: 0, duration: 0.75 }, 0.95)
  .fromTo('.hero-circle', { scale: 0.7, opacity: 0 }, { scale: 1, opacity: 1, duration: 1.1 }, 0.4)
  .fromTo('.hero-cutout', { opacity: 0, y: 40 }, { opacity: 1, y: 0, duration: 1 }, 0.6)
  .fromTo('.pill', { opacity: 0, scale: 0.85 }, { opacity: 1, scale: 1, duration: 0.5, stagger: 0.09 }, 1.1)
  .fromTo('.hero-scroll', { opacity: 0 }, { opacity: 1, duration: 0.8 }, 1.8);

/* ── COUNTERS ─────────────────────────────────────────────── */
document.querySelectorAll('[data-count]').forEach(el => {
  const target = parseInt(el.dataset.count, 10);
  const suffix = el.dataset.suffix ?? '';
  gsap.to({ v: 0 }, {
    v: target, duration: 1.6, ease: 'power2.out',
    scrollTrigger: { trigger: el, start: 'top 92%' },
    onUpdate() { el.textContent = Math.round(this.targets()[0].v) + suffix; }
  });
});

/* ── SCROLL REVEALS ───────────────────────────────────────── */
gsap.utils.toArray('.reveal').forEach(el => {
  if (el.closest('.hero')) return;   // hero is driven by the intro timeline
  gsap.fromTo(el,
    { opacity: 0, y: 34 },
    {
      opacity: 1, y: 0, duration: 0.8, ease: 'power3.out',
      scrollTrigger: { trigger: el, start: 'top 88%' }
    });
});

function staggerIn(items, trigger, vars = {}) {
  if (!document.querySelector(trigger)) return;
  gsap.fromTo(items,
    { opacity: 0, y: 44, ...vars.from },
    {
      opacity: 1, y: 0, duration: 0.75, stagger: 0.1, ease: 'power3.out',
      scrollTrigger: { trigger, start: 'top 82%' }, ...vars.to
    });
}

staggerIn('.step', '.steps');
staggerIn('.service-card', '.services-grid');
staggerIn('.timeline-item', '.timeline', { from: { x: -34, y: 0 }, to: { x: 0, y: 0, stagger: 0.16 } });
staggerIn('.contact-card', '.contact-grid', { from: { x: -26, y: 0 }, to: { x: 0, y: 0 } });

/* ── TIMELINE PROGRESS LINE ───────────────────────────────── */
const tlProgress = document.getElementById('timeline-progress');
if (tlProgress) {
  gsap.to(tlProgress, {
    height: '100%', ease: 'none',
    scrollTrigger: { trigger: '.timeline', start: 'top 70%', end: 'bottom 75%', scrub: 0.6 }
  });
}

/* ── HERO PARALLAX ────────────────────────────────────────── */
/* The old build animated '.hero::before' — GSAP cannot target pseudo-elements,
   so it silently did nothing. Parallax the real photo instead. */
if (!REDUCED) {
  gsap.to('.hero-cutout', {
    yPercent: 14, ease: 'none',
    scrollTrigger: { trigger: '.hero', start: 'top top', end: 'bottom top', scrub: 1.2 }
  });
}

/* ── PROJECTS ─────────────────────────────────────────────── */
const esc = (s) => String(s ?? '').replace(/[&<>"']/g,
  c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

function caseBlock(label, text, extraClass = '') {
  if (!text) return '';
  return `<div class="case-block ${extraClass}">
            <div class="case-label">${esc(label)}</div>
            <p>${esc(text)}</p>
          </div>`;
}

async function loadCases() {
  const grid = document.getElementById('cases');
  const empty = document.getElementById('work-empty');

  try {
    const res = await fetch('data/portfolio.json');
    if (!res.ok) throw new Error(res.status);
    const data = await res.json();

    if (!data.projects?.length) { empty.style.display = 'block'; return; }

    data.projects.forEach(p => {
      // Practice work is labelled so nothing reads as client work that isn't.
      const isPractice = p.kind === 'practice';

      const card = document.createElement('article');
      card.className = 'case-card';
      card.innerHTML = `
        <div class="case-head">
          ${p.client ? `<span class="case-client">${esc(p.client)}</span>` : ''}
          <span class="case-tag${isPractice ? ' practice' : ''}">${
            esc(isPractice ? 'Practice Project' : (p.category || 'Project'))}</span>
          ${p.date ? `<span class="case-date">${esc(p.date)}</span>` : ''}
        </div>

        <h3>${esc(p.title)}</h3>

        ${p.metrics?.length ? `<div class="case-metrics">${
          p.metrics.map(m => `
            <div class="metric">
              <span class="metric-value">${esc(m.value)}</span>
              <span class="metric-label">${esc(m.label)}</span>
            </div>`).join('')}</div>` : ''}

        <div class="case-body">
          ${caseBlock('The problem', p.problem)}
          ${caseBlock('What I did', p.approach)}
          ${caseBlock(p.outcome_label || 'The outcome', p.outcome, 'outcome')}
        </div>

        ${p.tools?.length ? `<div class="case-tools">${
          p.tools.map(t => `<span>${esc(t)}</span>`).join('')}</div>` : ''}`;

      grid.appendChild(card);

      gsap.fromTo(card, { opacity: 0, y: 44 }, {
        opacity: 1, y: 0, duration: 0.8, ease: 'power3.out',
        scrollTrigger: { trigger: card, start: 'top 86%' }
      });
    });

    ScrollTrigger.refresh();
  } catch {
    empty.style.display = 'block';
  }
}
loadCases();

/* ── PROCESS RAIL ─────────────────────────────────────────── */
const stepsProgress = document.getElementById('steps-progress');
if (stepsProgress) {
  gsap.to(stepsProgress, {
    height: '100%', ease: 'none',
    scrollTrigger: { trigger: '.steps', start: 'top 72%', end: 'bottom 78%', scrub: 0.6 }
  });
}
staggerIn('.step', '.steps', { from: { x: -28, y: 0 }, to: { x: 0, y: 0, stagger: 0.12 } });
staggerIn('.service-card', '.services-grid');

/* ── ANCHOR SCROLL ────────────────────────────────────────── */
/* Previously this called gsap scrollTo without ScrollToPlugin loaded, so
   preventDefault fired and nothing scrolled — every nav link was dead. */
document.querySelectorAll('a[href^="#"]').forEach(a => {
  a.addEventListener('click', e => {
    const target = document.querySelector(a.getAttribute('href'));
    if (!target) return;
    e.preventDefault();
    gsap.to(window, {
      scrollTo: { y: target, autoKill: true },
      duration: REDUCED ? 0 : 1,
      ease: 'power3.inOut'
    });
  });
});
