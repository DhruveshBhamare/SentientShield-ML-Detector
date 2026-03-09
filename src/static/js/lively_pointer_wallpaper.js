/*
  Lively-style Pointer Reactive Wallpaper
  - Particle field with soft connections
  - Subtle parallax and glow
  - Pointer attraction + ripple pulses
*/
(function () {
  const canvas = document.getElementById('lively-wallpaper');
  if (!canvas) return;

  const dpr = Math.max(1, Math.min(2, window.devicePixelRatio || 1));
  const ctx = canvas.getContext('2d');

  const page = (document.body && document.body.dataset && document.body.dataset.page) || 'overview';
  const prefersReduced = !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);

  const themes = {
    overview: {
      bgA1: 'rgba(8, 10, 25, 0.35)',
      bgA2: 'rgba(10, 8, 30, 0.35)',
      palette: ['#69d1ff', '#7a6cff', '#c07aff', '#66ffcc'],
      parallax: 8,
      densityScale: 0.9,
    },
    model: {
      bgA1: 'rgba(6, 12, 16, 0.38)',
      bgA2: 'rgba(8, 14, 20, 0.38)',
      palette: ['#3cd2c7', '#2aa1ff', '#5d7cff', '#29f0b8'],
      parallax: 10,
      densityScale: 1.0,
    },
    neuralfort: {
      bgA1: 'rgba(14, 8, 24, 0.42)',
      bgA2: 'rgba(18, 10, 28, 0.42)',
      palette: ['#9c6bff', '#ff6adf', '#7f59ff', '#ff9ef2'],
      parallax: 12,
      densityScale: 1.1,
    }
  };
  const theme = themes[page] || themes.overview;

  let width = 0, height = 0;
  let particles = [];
  let pointer = { x: 0, y: 0, active: false };
  let ripples = [];
  let frame = 0;
  let enabled = true;
  let lastTime = 0;

  function resize() {
    width = window.innerWidth;
    height = window.innerHeight;
    canvas.width = Math.floor(width * dpr);
    canvas.height = Math.floor(height * dpr);
    canvas.style.width = width + 'px';
    canvas.style.height = height + 'px';
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    initParticles();
  }

  function rand(min, max) { return Math.random() * (max - min) + min; }
  function choice(arr) { return arr[Math.floor(Math.random() * arr.length)]; }

  function initParticles() {
    const base = (width * height) / 60000;
    const rmScale = prefersReduced ? 0.6 : 1.0;
    const count = Math.floor(base * theme.densityScale * rmScale);
    particles = new Array(count).fill(0).map(() => ({
      x: rand(0, width),
      y: rand(0, height),
      vx: rand(-0.22, 0.22),
      vy: rand(-0.22, 0.22),
      r: rand(1.6, 3.0),
      c: choice(theme.palette)
    }));
  }

  function drawBackground() {
    const g = ctx.createLinearGradient(0, 0, width, height);
    g.addColorStop(0, theme.bgA1);
    g.addColorStop(1, theme.bgA2);
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, width, height);

    const rg = ctx.createRadialGradient(width * 0.5, height * 0.45, 0, width * 0.5, height * 0.45, Math.max(width, height) * 0.6);
    rg.addColorStop(0, 'rgba(255,255,255,0.05)');
    rg.addColorStop(1, 'rgba(255,255,255,0.0)');
    ctx.fillStyle = rg;
    ctx.fillRect(0, 0, width, height);
  }

  function updateParticles() {
    const motionScale = prefersReduced ? 0.6 : 1.0;
    const ax = (pointer.active ? (pointer.x - width / 2) / width : 0) * 0.15 * motionScale;
    const ay = (pointer.active ? (pointer.y - height / 2) / height : 0) * 0.15 * motionScale;
    ctx.save();
    ctx.translate(ax * theme.parallax, ay * theme.parallax);

    for (let p of particles) {
      p.x += p.vx;
      p.y += p.vy;

      // Wrap around
      if (p.x < -10) p.x = width + 10;
      if (p.x > width + 10) p.x = -10;
      if (p.y < -10) p.y = height + 10;
      if (p.y > height + 10) p.y = -10;

      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = p.c;
      ctx.globalAlpha = 0.6;
      ctx.fill();
    }
    ctx.restore();
  }

  function loop(time) {
    if (!enabled) return;
    requestAnimationFrame(loop);
    
    // Throttle for performance
    const delta = time - lastTime;
    if (delta < 16) return; 
    lastTime = time;

    ctx.clearRect(0, 0, width, height);
    drawBackground();
    updateParticles();
  }

  // Init
  resize();
  window.addEventListener('resize', resize);
  window.addEventListener('mousemove', e => {
    pointer.x = e.clientX;
    pointer.y = e.clientY;
    pointer.active = true;
  });
  requestAnimationFrame(loop);

})();

