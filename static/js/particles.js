/**
 * Interactive Particle System + Floating Widgets
 * Adds a canvas-based particle field that reacts to mouse movement,
 * and floating glassmorphism widget elements with live micro-data.
 */
(function () {
  "use strict";

  const reduceMotion =
    window.matchMedia &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (reduceMotion) return;

  /* ===================================================
     1.  PARTICLE CANVAS
     =================================================== */
  const canvas = document.createElement("canvas");
  canvas.id = "particleCanvas";
  canvas.setAttribute("aria-hidden", "true");
  document.body.prepend(canvas);

  const ctx = canvas.getContext("2d");
  let W, H;

  const resize = () => {
    W = canvas.width = window.innerWidth;
    H = canvas.height = window.innerHeight;
  };
  resize();
  window.addEventListener("resize", resize, { passive: true });

  // Pointer tracking for interaction
  const pointer = { x: -9999, y: -9999, active: false };
  window.addEventListener(
    "mousemove",
    (e) => {
      pointer.x = e.clientX;
      pointer.y = e.clientY;
      pointer.active = true;
    },
    { passive: true }
  );
  window.addEventListener("mouseleave", () => (pointer.active = false));

  // Particle config
  const PARTICLE_COUNT = 65;
  const CONNECT_DIST = 130;
  const MOUSE_RADIUS = 180;

  // Theme colours matching --a:#FF8A65, --c:#FFB4A2
  const palette = [
    { r: 255, g: 138, b: 101 }, // coral
    { r: 255, g: 180, b: 162 }, // peach
    { r: 255, g: 214, b: 201 }, // cream
    { r: 74, g: 44, b: 42 },    // dark brown (subtle)
  ];

  class Particle {
    constructor() {
      this.reset();
    }
    reset() {
      this.x = Math.random() * W;
      this.y = Math.random() * H;
      this.vx = (Math.random() - 0.5) * 0.45;
      this.vy = (Math.random() - 0.5) * 0.45;
      this.radius = Math.random() * 2.4 + 0.8;
      const c = palette[Math.floor(Math.random() * palette.length)];
      this.color = c;
      this.alpha = Math.random() * 0.45 + 0.15;
      this.baseAlpha = this.alpha;
      // Pulse
      this.pulseSpeed = Math.random() * 0.008 + 0.003;
      this.pulsePhase = Math.random() * Math.PI * 2;
    }
    update(t) {
      // Drift
      this.x += this.vx;
      this.y += this.vy;

      // Pulse brightness
      this.alpha =
        this.baseAlpha + Math.sin(t * this.pulseSpeed + this.pulsePhase) * 0.12;

      // Mouse repulsion
      if (pointer.active) {
        const dx = this.x - pointer.x;
        const dy = this.y - (pointer.y + window.scrollY);
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < MOUSE_RADIUS && dist > 0) {
          const force = (1 - dist / MOUSE_RADIUS) * 1.6;
          this.vx += (dx / dist) * force * 0.15;
          this.vy += (dy / dist) * force * 0.15;
        }
      }

      // Velocity damping
      this.vx *= 0.992;
      this.vy *= 0.992;

      // Wrap edges
      if (this.x < -10) this.x = W + 10;
      if (this.x > W + 10) this.x = -10;
      if (this.y < -10) this.y = H + 10;
      if (this.y > H + 10) this.y = -10;
    }
    draw() {
      const { r, g, b } = this.color;
      ctx.beginPath();
      ctx.arc(this.x, this.y - window.scrollY, this.radius, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(${r},${g},${b},${this.alpha})`;
      ctx.fill();
    }
  }

  const particles = Array.from(
    { length: PARTICLE_COUNT },
    () => new Particle()
  );

  // Connection lines
  function drawConnections() {
    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        const a = particles[i];
        const b = particles[j];
        const dx = a.x - b.x;
        const dy = a.y - b.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < CONNECT_DIST) {
          const opacity = (1 - dist / CONNECT_DIST) * 0.12;
          ctx.beginPath();
          ctx.moveTo(a.x, a.y - window.scrollY);
          ctx.lineTo(b.x, b.y - window.scrollY);
          ctx.strokeStyle = `rgba(255,138,101,${opacity})`;
          ctx.lineWidth = 0.6;
          ctx.stroke();
        }
      }
    }

    // Lines from pointer to nearby particles
    if (pointer.active) {
      const py = pointer.y + window.scrollY;
      for (const p of particles) {
        const dx = p.x - pointer.x;
        const dy = p.y - py;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < MOUSE_RADIUS) {
          const opacity = (1 - dist / MOUSE_RADIUS) * 0.18;
          ctx.beginPath();
          ctx.moveTo(pointer.x, pointer.y);
          ctx.lineTo(p.x, p.y - window.scrollY);
          ctx.strokeStyle = `rgba(255,180,162,${opacity})`;
          ctx.lineWidth = 0.8;
          ctx.stroke();
        }
      }
    }
  }

  let frame = 0;
  function animateParticles() {
    frame++;
    ctx.clearRect(0, 0, W, H);
    for (const p of particles) {
      p.update(frame);
      p.draw();
    }
    drawConnections();
    requestAnimationFrame(animateParticles);
  }
  requestAnimationFrame(animateParticles);

  /* ===================================================
     2.  SOFT 3D ELEGANT ORBS
     =================================================== */
  const orbContainer = document.createElement("div");
  orbContainer.className = "orb-container";
  orbContainer.setAttribute("aria-hidden", "true");
  document.body.prepend(orbContainer);

  function createOrb(config) {
    const el = document.createElement("div");
    el.className = "soft-orb";
    Object.assign(el.style, config.style || {});
    el.style.width = config.size + "px";
    el.style.height = config.size + "px";
    el.dataset.floatSpeed = config.speed || 1;
    el.dataset.floatAmpX = config.ampX || 15;
    el.dataset.floatAmpY = config.ampY || 20;
    el.dataset.floatPhase = Math.random() * Math.PI * 2;
    el.dataset.parallaxDepth = config.depth || 0.1;

    el.cardTiltX = 0;
    el.cardTiltY = 0;
    el.targetTiltX = 0;
    el.targetTiltY = 0;

    orbContainer.appendChild(el);
    return el;
  }

  const orbs = [
    { size: 220, style: { top: "15vh", left: "6%" }, speed: 0.6, ampX: 20, ampY: 30, depth: 0.15 },
    { size: 320, style: { top: "55vh", right: "4%" }, speed: 0.4, ampX: 30, ampY: 40, depth: 0.35 },
    { size: 140, style: { top: "30vh", right: "22%" }, speed: 0.8, ampX: 15, ampY: 20, depth: 0.2 },
    { size: 90,  style: { top: "80vh", left: "12%" }, speed: 0.9, ampX: 10, ampY: 15, depth: 0.4 },
    { size: 180, style: { top: "45vh", left: "38%" }, speed: 0.5, ampX: 25, ampY: 25, depth: 0.05 },
    { size: 260, style: { top: "85vh", right: "15%" }, speed: 0.45, ampX: 22, ampY: 28, depth: 0.25 },
  ];

  const orbEls = orbs.map(createOrb);

  /* ===================================================
     3.  SMOOTH PARALLAX & ELEGANT 3D ENGINE
     =================================================== */
  let wFrame = 0;
  let targetScrollY = window.scrollY;
  let currentScrollY = window.scrollY;

  window.addEventListener("scroll", () => {
    targetScrollY = window.scrollY;
  }, { passive: true });

  window.addEventListener("mousemove", (e) => {
    const screenX = window.innerWidth / 2;
    const screenY = window.innerHeight / 2;
    const dxScreen = e.clientX - screenX;
    const dyScreen = e.clientY - screenY;

    orbEls.forEach((el) => {
      // 3D Tilt targets based on cursor relative to screen centre
      // Subtle elegant rotation for the spheres to give a glass-refraction feel
      el.targetTiltX = (dyScreen / screenY) * -15; 
      el.targetTiltY = (dxScreen / screenX) * 15;  
    });
  }, { passive: true });

  function animateOrbs() {
    wFrame++;
    currentScrollY += (targetScrollY - currentScrollY) * 0.08; 

    orbEls.forEach((el) => {
      const speed = parseFloat(el.dataset.floatSpeed);
      const ampX = parseFloat(el.dataset.floatAmpX);
      const ampY = parseFloat(el.dataset.floatAmpY);
      const phase = parseFloat(el.dataset.floatPhase);
      const depth = parseFloat(el.dataset.parallaxDepth);
      
      const t = wFrame * 0.012;
      const dx = Math.sin(t * speed + phase) * ampX;
      
      // Calculate parallax translation
      const parallaxY = -currentScrollY * depth;
      const dy = Math.cos(t * speed * 0.7 + phase) * ampY + parallaxY;
      
      // Smoothly interpolate current tilt towards target tilt
      el.cardTiltX += (el.targetTiltX - el.cardTiltX) * 0.08;
      el.cardTiltY += (el.targetTiltY - el.cardTiltY) * 0.08;

      // Apply 3D matrix: perspective, position, rotation
      el.style.transform = `perspective(1000px) translate3d(${dx}px, ${dy}px, 0) rotateX(${el.cardTiltX}deg) rotateY(${el.cardTiltY}deg)`;
    });

    requestAnimationFrame(animateOrbs);
  }
  requestAnimationFrame(animateOrbs);
})();
