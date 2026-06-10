// ── GSAP + ScrollTrigger ────────────────────────────────────
gsap.registerPlugin(ScrollTrigger);

// ── CUSTOM CURSOR ───────────────────────────────────────────
const cursor = document.getElementById('cursor');
const follower = document.getElementById('cursor-follower');

document.addEventListener('mousemove', (e) => {
  gsap.to(cursor, { x: e.clientX, y: e.clientY, duration: 0 });
  gsap.to(follower, { x: e.clientX, y: e.clientY, duration: 0.15 });
});

document.querySelectorAll('a, button, .skill-card, .project-card, .contact-card').forEach(el => {
  el.addEventListener('mouseenter', () => {
    gsap.to(follower, { scale: 2.5, borderColor: 'rgba(124,106,247,0.8)', duration: 0.2 });
    gsap.to(cursor, { scale: 0.5, duration: 0.2 });
  });
  el.addEventListener('mouseleave', () => {
    gsap.to(follower, { scale: 1, borderColor: 'rgba(124,106,247,0.4)', duration: 0.2 });
    gsap.to(cursor, { scale: 1, duration: 0.2 });
  });
});

// ── NAV SCROLL ──────────────────────────────────────────────
const nav = document.getElementById('nav');
window.addEventListener('scroll', () => {
  nav.classList.toggle('scrolled', window.scrollY > 60);
});

// ── HERO TITLE ANIMATION ────────────────────────────────────
const heroLines = document.querySelectorAll('.reveal-line');
gsap.fromTo(heroLines,
  { y: '100%', opacity: 0 },
  { y: '0%', opacity: 1, duration: 1, stagger: 0.12, ease: 'power4.out', delay: 0.3 }
);

// Hero tag + sub + actions
gsap.fromTo('.hero-tag', { opacity: 0, y: 20 }, { opacity: 1, y: 0, duration: 0.8, delay: 0.1, ease: 'power3.out' });
gsap.fromTo('.hero-sub', { opacity: 0, y: 20 }, { opacity: 1, y: 0, duration: 0.8, delay: 0.9, ease: 'power3.out' });
gsap.fromTo('.hero-actions', { opacity: 0, y: 20 }, { opacity: 1, y: 0, duration: 0.8, delay: 1.1, ease: 'power3.out' });
gsap.fromTo('.hero-stats .stat', { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 0.8, stagger: 0.15, delay: 1.3, ease: 'power3.out' });
gsap.fromTo('.hero-scroll', { opacity: 0 }, { opacity: 1, duration: 1, delay: 2 });

// ── COUNTER ANIMATION ───────────────────────────────────────
function animateCounters() {
  document.querySelectorAll('.stat-num').forEach(el => {
    const target = parseInt(el.dataset.count);
    gsap.to({ val: 0 }, {
      val: target, duration: 2, ease: 'power2.out', delay: 1.3,
      onUpdate: function () { el.textContent = Math.round(this.targets()[0].val); }
    });
  });
}
animateCounters();

// ── SCROLL REVEAL ───────────────────────────────────────────
gsap.utils.toArray('.reveal').forEach(el => {
  gsap.fromTo(el,
    { opacity: 0, y: 40 },
    {
      opacity: 1, y: 0, duration: 0.8, ease: 'power3.out',
      scrollTrigger: { trigger: el, start: 'top 88%', toggleActions: 'play none none none' }
    }
  );
});

// ── SKILL CARDS STAGGER ─────────────────────────────────────
gsap.fromTo('.skill-card',
  { opacity: 0, y: 50 },
  {
    opacity: 1, y: 0, duration: 0.7, stagger: 0.1, ease: 'power3.out',
    scrollTrigger: { trigger: '.skills-grid', start: 'top 80%' }
  }
);

// ── CONTACT CARDS STAGGER ───────────────────────────────────
gsap.fromTo('.contact-card',
  { opacity: 0, x: -30 },
  {
    opacity: 1, x: 0, duration: 0.7, stagger: 0.12, ease: 'power3.out',
    scrollTrigger: { trigger: '.contact-grid', start: 'top 85%' }
  }
);

// ── TIMELINE ITEMS ──────────────────────────────────────────
gsap.fromTo('.timeline-item',
  { opacity: 0, x: -40 },
  {
    opacity: 1, x: 0, duration: 0.8, stagger: 0.2, ease: 'power3.out',
    scrollTrigger: { trigger: '.timeline', start: 'top 80%' }
  }
);

// ── BACKGROUND PARALLAX ─────────────────────────────────────
gsap.to('.hero::before', {
  y: 100,
  scrollTrigger: { trigger: '.hero', scrub: 2 }
});

// ── LOAD PROJECTS FROM JSON ─────────────────────────────────
async function loadProjects() {
  try {
    const res = await fetch('data/portfolio.json');
    const data = await res.json();
    const grid = document.getElementById('projects-grid');
    const empty = document.getElementById('work-empty');

    if (!data.projects || data.projects.length === 0) {
      empty.style.display = 'block';
      return;
    }

    data.projects.forEach(project => {
      const card = document.createElement('div');
      card.className = 'project-card reveal';
      card.innerHTML = `
        <div class="project-thumb">${project.emoji || '💼'}</div>
        <div class="project-info">
          <div class="project-tag">${project.category || 'Project'}</div>
          <h3>${project.title}</h3>
          <p>${project.description}</p>
        </div>
      `;
      grid.appendChild(card);

      // Animate new card
      gsap.fromTo(card,
        { opacity: 0, y: 40 },
        {
          opacity: 1, y: 0, duration: 0.7, ease: 'power3.out',
          scrollTrigger: { trigger: card, start: 'top 88%' }
        }
      );
    });

  } catch (e) {
    document.getElementById('work-empty').style.display = 'block';
  }
}

loadProjects();

// ── SMOOTH ANCHOR SCROLL ────────────────────────────────────
document.querySelectorAll('a[href^="#"]').forEach(a => {
  a.addEventListener('click', e => {
    e.preventDefault();
    const target = document.querySelector(a.getAttribute('href'));
    if (target) {
      gsap.to(window, { scrollTo: target, duration: 1, ease: 'power3.inOut' });
    }
  });
});
