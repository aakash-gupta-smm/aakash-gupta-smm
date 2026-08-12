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

  const hoverables = 'a, button, .skill-card, .project-card, .contact-card, .about-card, .timeline-content';
  document.querySelectorAll(hoverables).forEach(el => {
    el.addEventListener('mouseenter', () => {
      gsap.to(follower, { scale: 2.2, borderColor: 'rgba(124,106,247,0.75)', duration: 0.25 });
      gsap.to(cursor, { scale: 0.4, duration: 0.25 });
    });
    el.addEventListener('mouseleave', () => {
      gsap.to(follower, { scale: 1, borderColor: 'rgba(124,106,247,0.35)', duration: 0.25 });
      gsap.to(cursor, { scale: 1, duration: 0.25 });
    });
  });
}

/* ── SPOTLIGHT CARDS ──────────────────────────────────────── */
/* Feeds the cursor position to the CSS radial gradients as --mx/--my. */
function bindSpotlight(el) {
  el.addEventListener('pointermove', (e) => {
    const r = el.getBoundingClientRect();
    el.style.setProperty('--mx', `${e.clientX - r.left}px`);
    el.style.setProperty('--my', `${e.clientY - r.top}px`);
  });
}
document.querySelectorAll('.spotlight').forEach(bindSpotlight);

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
  .fromTo('.hero-photo', { opacity: 0, scale: 0.9 }, { opacity: 1, scale: 1, duration: 1 }, 0.6)
  .fromTo('.hero-stats .stat', { opacity: 0, y: 26 }, { opacity: 1, y: 0, duration: 0.7, stagger: 0.12 }, 1.2)
  .fromTo('.hero-scroll', { opacity: 0 }, { opacity: 1, duration: 0.8 }, 1.8);

/* ── COUNTERS ─────────────────────────────────────────────── */
document.querySelectorAll('.stat-num').forEach(el => {
  const target = parseInt(el.dataset.count, 10);
  gsap.to({ v: 0 }, {
    v: target, duration: 1.8, delay: 1.3, ease: 'power2.out',
    onUpdate() { el.textContent = Math.round(this.targets()[0].v); }
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

staggerIn('.skill-card', '.skills-grid');
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
  gsap.to('.hero-photo', {
    yPercent: 14, ease: 'none',
    scrollTrigger: { trigger: '.hero', start: 'top top', end: 'bottom top', scrub: 1.2 }
  });
}

/* ── PROJECTS ─────────────────────────────────────────────── */
const esc = (s) => String(s ?? '').replace(/[&<>"']/g,
  c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

async function loadProjects() {
  const grid = document.getElementById('projects-grid');
  const empty = document.getElementById('work-empty');

  try {
    const res = await fetch('data/portfolio.json');
    if (!res.ok) throw new Error(res.status);
    const data = await res.json();

    if (!data.projects?.length) { empty.style.display = 'block'; return; }

    data.projects.forEach(p => {
      const card = document.createElement('div');
      card.className = 'project-card spotlight';
      card.innerHTML = `
        <div class="project-thumb">${esc(p.emoji || '💼')}</div>
        <div class="project-info">
          <div class="project-tag">${esc(p.category || 'Project')}</div>
          <h3>${esc(p.title)}</h3>
          <p>${esc(p.description)}</p>
          ${p.highlights?.length ? `<ul class="project-highlights">${
            p.highlights.map(h => `<li>${esc(h)}</li>`).join('')}</ul>` : ''}
          ${p.tools?.length ? `<div class="project-tools">${
            p.tools.map(t => `<span>${esc(t)}</span>`).join('')}</div>` : ''}
        </div>`;
      grid.appendChild(card);
      bindSpotlight(card);

      gsap.fromTo(card, { opacity: 0, y: 40 }, {
        opacity: 1, y: 0, duration: 0.75, ease: 'power3.out',
        scrollTrigger: { trigger: card, start: 'top 88%' }
      });
    });

    ScrollTrigger.refresh();
  } catch {
    empty.style.display = 'block';
  }
}
loadProjects();

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
