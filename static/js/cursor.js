(function () {
  const follower = document.querySelector(".cursor-follower");
  const dot = document.querySelector(".cursor-dot");

  if (!follower || !dot) return;

  let mouseX = -100,
    mouseY = -100;
  let curX = mouseX,
    curY = mouseY;
  const speed = 0.18;

  const raf = () => {
    curX += (mouseX - curX) * speed;
    curY += (mouseY - curY) * speed;
    follower.style.left = curX + "px";
    follower.style.top = curY + "px";
    dot.style.left = mouseX + "px";
    dot.style.top = mouseY + "px";
    requestAnimationFrame(raf);
  };

  const onMove = (e) => {
    mouseX = e.clientX;
    mouseY = e.clientY;
  };

  const reduceMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (!reduceMotion) {
    window.addEventListener("mousemove", onMove, { passive: true });
    requestAnimationFrame(raf);
  } else {
    follower.style.display = "none";
    dot.style.display = "none";
  }

  window.addEventListener("mousedown", () => follower.classList.add("is-down"));
  window.addEventListener("mouseup", () => follower.classList.remove("is-down"));

  // Magnetic buttons: subtle push/pull based on pointer position.
  const magneticEls = document.querySelectorAll(".magnetic");
  magneticEls.forEach((el) => {
    let rect = null;
    let targetX = 0;
    let targetY = 0;
    let x = 0;
    let y = 0;
    const strength = 0.22;

    const onEnter = () => {
      rect = el.getBoundingClientRect();
    };

    const onMove = (e) => {
      if (!rect) rect = el.getBoundingClientRect();
      const cx = rect.left + rect.width / 2;
      const cy = rect.top + rect.height / 2;
      const dx = e.clientX - cx;
      const dy = e.clientY - cy;
      targetX = dx * strength;
      targetY = dy * strength;
    };

    const onLeave = () => {
      rect = null;
      targetX = 0;
      targetY = 0;
    };

    const tick = () => {
      x += (targetX - x) * 0.22;
      y += (targetY - y) * 0.22;
      el.style.transform = `translate3d(${x}px, ${y}px, 0)`;
      requestAnimationFrame(tick);
    };

    el.addEventListener("mouseenter", onEnter);
    el.addEventListener("mousemove", onMove, { passive: true });
    el.addEventListener("mouseleave", onLeave);
    requestAnimationFrame(tick);
  });
})();

