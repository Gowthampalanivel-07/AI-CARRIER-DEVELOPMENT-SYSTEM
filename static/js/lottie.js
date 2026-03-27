(function () {
  function showSvgSpinner(container) {
    container.innerHTML = "";
    const svgNS = "http://www.w3.org/2000/svg";
    const w = 220;
    const h = 220;

    const svg = document.createElementNS(svgNS, "svg");
    svg.setAttribute("viewBox", `0 0 ${w} ${h}`);
    svg.setAttribute("width", "100%");
    svg.setAttribute("height", "100%");
    svg.style.display = "block";

    const circleBg = document.createElementNS(svgNS, "circle");
    circleBg.setAttribute("cx", "110");
    circleBg.setAttribute("cy", "110");
    circleBg.setAttribute("r", "46");
    circleBg.setAttribute("stroke", "rgba(255,255,255,.14)");
    circleBg.setAttribute("stroke-width", "10");
    circleBg.setAttribute("fill", "none");

    const circle = document.createElementNS(svgNS, "circle");
    circle.setAttribute("cx", "110");
    circle.setAttribute("cy", "110");
    circle.setAttribute("r", "46");
    circle.setAttribute("stroke", "rgba(124,92,255,.9)");
    circle.setAttribute("stroke-width", "10");
    circle.setAttribute("fill", "none");
    circle.setAttribute("stroke-linecap", "round");

    svg.appendChild(circleBg);
    svg.appendChild(circle);

    let start = null;
    const dur = 900;
    const tick = (t) => {
      if (!start) start = t;
      const elapsed = (t - start) % dur;
      const p = elapsed / dur;
      const dash = 2 * Math.PI * 46;
      const offset = dash * (1 - p);
      circle.style.strokeDasharray = `${dash * 0.55} ${dash}`;
      circle.style.strokeDashoffset = offset;
      requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);

    container.appendChild(svg);
  }

  async function loadLottieInto(containerId, url) {
    const container = document.getElementById(containerId);
    if (!container) return;

    if (!window.lottie) {
      showSvgSpinner(container);
      return;
    }

    try {
      container.innerHTML = "";
      // lottie-web handles fetch internally; keep it simple.
      window.lottie.loadAnimation({
        container,
        renderer: "svg",
        loop: true,
        autoplay: true,
        path: url,
        rendererSettings: { preserveAspectRatio: "xMidYMid meet" },
      });
    } catch (e) {
      showSvgSpinner(container);
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    // Remote Lottie JSON with deterministic UI fallback.
    // If the request fails (offline environment), we show an SVG spinner.
    const heroUrl = "https://assets10.lottiefiles.com/packages/lf20_jcikwtux.json";
    const modalUrl = "https://assets10.lottiefiles.com/packages/lf20_jcikwtux.json";

    // Start with hero; modal will reuse the same function on open.
    loadLottieInto("heroLottie", heroUrl);

    window.__loadModalLottie = function () {
      loadLottieInto("modalLottie", modalUrl);
    };
  });
})();

