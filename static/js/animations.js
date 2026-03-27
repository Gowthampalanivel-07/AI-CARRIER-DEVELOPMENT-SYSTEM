(function () {
  const els = Array.from(document.querySelectorAll("[data-anim]"));
  if (els.length === 0) return;

  const reduceMotion =
    window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const delayForEl = (el) => {
    const v = el.getAttribute("data-anim-delay");
    if (!v) return 0;
    const n = Number(v);
    return Number.isFinite(n) ? n / 1000 : 0;
  };

  if (reduceMotion) {
    els.forEach((el) => el.classList.add("is-visible"));
    return;
  }

  // Prefer GSAP + ScrollTrigger if loaded.
  if (window.gsap && window.ScrollTrigger) {
    els.forEach((el) => {
      const kind = el.getAttribute("data-anim") || "fade-up";
      let from = { autoAlpha: 0, y: 16, scale: 0.98, filter: "blur(6px)" };
      let to = { autoAlpha: 1, y: 0, scale: 1, filter: "blur(0px)", duration: 0.85, ease: "power3.out" };

      if (kind === "zoom-in") {
        from = { autoAlpha: 0, y: 0, scale: 0.96, filter: "blur(8px)" };
        to = { autoAlpha: 1, y: 0, scale: 1, filter: "blur(0px)", duration: 0.75, ease: "power3.out" };
      } else if (kind === "slide-in") {
        from = { autoAlpha: 0, y: 0, x: -18, scale: 0.98, filter: "blur(6px)" };
        to = { autoAlpha: 1, y: 0, x: 0, scale: 1, filter: "blur(0px)", duration: 0.8, ease: "power3.out" };
      }

      const d = delayForEl(el);
      window.gsap.fromTo(
        el,
        from,
        {
          ...to,
          delay: d,
          scrollTrigger: {
            trigger: el,
            start: "top 85%",
            once: true,
          },
        }
      );
    });
    return;
  }

  // IntersectionObserver fallback.
  const io = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        const el = entry.target;
        const d = delayForEl(el);
        window.setTimeout(() => el.classList.add("is-visible"), d * 1000);
        io.unobserve(el);
      }
    },
    { threshold: 0.12 }
  );

  els.forEach((el) => io.observe(el));
})();

