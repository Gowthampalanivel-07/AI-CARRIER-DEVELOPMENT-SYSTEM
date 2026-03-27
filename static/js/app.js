(function () {
  const sections = Array.from(document.querySelectorAll(".route[data-route]"));
  const navButtons = Array.from(document.querySelectorAll(".nav-link[data-nav]"));

  const modal = document.getElementById("modal");
  const modalBackdrop = document.getElementById("modalBackdrop");
  const closeModalBtn = document.getElementById("closeModal");
  const modalCta = document.getElementById("modalCta");
  const modalTitle = document.querySelector(".modal-title");
  const modalContent = document.getElementById("modalContent");
  const openOnboarding = document.getElementById("openOnboarding");
  const openExport = document.getElementById("openExport");

  // AI FAB & Modal
  const aiBtn = document.getElementById("aiBtn");
  const aiModal = document.getElementById("aiModal");
  const closeAiModal = document.getElementById("closeAiModal");
  const aiSkeleton = document.getElementById("aiSkeleton");
  const aiLiveInsights = document.getElementById("aiLiveInsights");

  const assessForm = document.getElementById("assessForm");
  const submitBtn = document.getElementById("submitBtn");

  const placementsWrap = document.getElementById("placements");
  const gapsWrap = document.getElementById("skillGaps");
  const roadmapWrap = document.getElementById("roadmap");
  const aiNotes = document.getElementById("aiNotes");

  const placementsSkeleton = document.getElementById("placementsSkeleton");
  const gapsSkeleton = document.getElementById("gapsSkeleton");

  const previewTarget = document.getElementById("previewTarget");
  const previewExp = document.getElementById("previewExp");
  const previewSkillsCount = document.getElementById("previewSkillsCount");
  const previewLevel = document.getElementById("previewLevel");

  let currentRoute = "home";
  let lastResult = null;
  let lastProfile = null;
  let onboardingHtml = null;

  const preferredReduceMotion =
    window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function getRouteFromHash() {
    const h = String(window.location.hash || "").replace("#", "").trim().toLowerCase();
    if (!h) return "home";
    if (h === "assess" || h === "results" || h === "dashboard" || h === "home") return h;
    return "home";
  }

  function setSectionHidden(section, hidden) {
    if (hidden) {
      section.setAttribute("hidden", "");
    } else {
      section.removeAttribute("hidden");
    }
  }

  function showRoute(route) {
    const to = sections.find((s) => s.getAttribute("data-route") === route) || sections[0];
    const from = sections.find((s) => s.getAttribute("data-route") === currentRoute) || sections[0];
    if (from === to) return;

    setSectionHidden(to, false);

    if (!preferredReduceMotion) {
      from.classList.add("page-fade-out");
      setTimeout(() => {
        setSectionHidden(from, true);
        to.classList.remove("page-fade-out");
        to.classList.add("page-fade-in");
        currentRoute = route;
        window.scrollTo({ top: 0, behavior: "smooth" });
        setTimeout(() => to.classList.remove("page-fade-in"), 380);
      }, 210);
    } else {
      setSectionHidden(from, true);
      currentRoute = route;
      window.scrollTo({ top: 0 });
    }

    // Update hash for shareable navigation.
    window.location.hash = route === "home" ? "" : route;
  }

  function navigate(route) {
    if (route === currentRoute) return;
    showRoute(route);
    if (route === "dashboard" && lastProfile && window.renderUnifiedDashboard) {
      window.renderUnifiedDashboard(lastProfile, "");
    }
  }

  function parseSkills(str) {
    if (!str) return [];
    return String(str)
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean)
      .slice(0, 30);
  }

  function levelLabel(years) {
    const y = Number(years);
    if (!Number.isFinite(y)) return "—";
    if (y < 1) return "Starter";
    if (y < 3) return "Intermediate";
    return "Advanced";
  }

  function updatePreview() {
    const form = assessForm;
    const fd = new FormData(form);
    const target = fd.get("target_role") ? String(fd.get("target_role")).trim() : "";
    const exp = fd.get("experience_years") ? String(fd.get("experience_years")).trim() : "";
    const skillsRaw = fd.get("skills") ? String(fd.get("skills")) : "";

    const skills = parseSkills(skillsRaw);
    previewTarget.textContent = target || "—";
    previewExp.textContent = exp ? exp : "—";
    previewSkillsCount.textContent = skills.length ? String(skills.length) : "—";
    previewLevel.textContent = levelLabel(exp);
  }

  function setLoadingUI(isLoading) {
    if (!submitBtn) return;
    submitBtn.classList.toggle("is-loading", isLoading);
    submitBtn.disabled = isLoading;

    placementsSkeleton.hidden = !isLoading;
    gapsSkeleton.hidden = !isLoading;

    placementsWrap.innerHTML = "";
    gapsWrap.innerHTML = "";
    roadmapWrap.innerHTML = "";
    aiNotes.textContent = "—";
  }

  function priorityBadge(priority) {
    const p = Number(priority);
    const color =
      p >= 5 ? "rgba(255,77,109,.18)" : p >= 4 ? "rgba(124,92,255,.18)" : "rgba(53,214,255,.12)";
    const border =
      p >= 5 ? "rgba(255,77,109,.35)" : p >= 4 ? "rgba(124,92,255,.35)" : "rgba(53,214,255,.30)";
    return `<span class="card-conf" style="background:${color}; border-color:${border}">Priority ${p}</span>`;
  }

  function renderPlacements(items) {
    placementsWrap.innerHTML = "";
    items.forEach((rec) => {
      const card = document.createElement("div");
      card.className = "card";
      card.setAttribute("role", "button");
      card.setAttribute("tabindex", "0");
      card.dataset.cardRole = rec.role;
      card.innerHTML = `
        <div class="card-head">
          <div class="card-role">${escapeHtml(rec.role)}</div>
          <div class="card-conf">${escapeHtml(String(Math.round(rec.confidence * 100)))}%</div>
        </div>
        <div class="card-why">${escapeHtml(rec.why_it_fits || "")}</div>
        <div class="card-qs">
          ${(rec.quick_start || []).slice(0, 3).map((t) => `<span class="tag">${escapeHtml(t)}</span>`).join("")}
        </div>
      `;
      // Morphing: click a card to open it in the modal.
      card.addEventListener("click", () => openResultsModal({ mode: "card", cardRole: rec.role }));
      card.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") openResultsModal({ mode: "card", cardRole: rec.role });
      });
      placementsWrap.appendChild(card);
    });
  }

  function renderGaps(items) {
    gapsWrap.innerHTML = "";
    items.forEach((g) => {
      const card = document.createElement("div");
      card.className = "card";
      card.innerHTML = `
        <div class="card-head">
          <div class="card-role">${escapeHtml(g.gap)}</div>
          <div>${priorityBadge(g.priority)}</div>
        </div>
        <div class="card-why">${escapeHtml(g.suggested_next_step || "")}</div>
      `;
      gapsWrap.appendChild(card);
    });
  }

  function renderRoadmap(steps) {
    roadmapWrap.innerHTML = "";
    steps.forEach((s) => {
      const el = document.createElement("div");
      el.className = "phase";
      el.innerHTML = `
        <div class="phase-time">${escapeHtml(s.timeframe || "")}</div>
        <div class="phase-goal">${escapeHtml(s.goal || "")}</div>
        <div class="phase-actions">
          ${(s.actions || []).slice(0, 4).map((a) => `<div class="line">• ${escapeHtml(a)}</div>`).join("")}
        </div>
      `;
      roadmapWrap.appendChild(el);
    });
  }

  function escapeHtml(str) {
    return String(str)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function openModal() {
    if (!modal || !modalBackdrop) return;
    modal.hidden = false;
    modalBackdrop.hidden = false;
    modal.setAttribute("aria-hidden", "false");
    if (!preferredReduceMotion) {
      modal.style.animation = "pageFadeIn .25s var(--ease) forwards";
    }
  }

  function closeModal() {
    if (!modal || !modalBackdrop) return;
    modal.hidden = true;
    modalBackdrop.hidden = true;
    modal.setAttribute("aria-hidden", "true");
  }

  function openAiModal() {
    if (!aiModal || !modalBackdrop) return;
    aiModal.hidden = false;
    modalBackdrop.hidden = false;
    aiModal.setAttribute("aria-hidden", "false");
    
    // Simulate AI thinking time to process form state
    aiSkeleton.hidden = false;
    aiLiveInsights.hidden = true;
    aiLiveInsights.innerHTML = "";
    
    setTimeout(() => {
      // Read current form state
      const fd = new FormData(assessForm);
      const target = fd.get("target_role") ? String(fd.get("target_role")).trim() : "your target role";
      const exp = fd.get("experience_years") ? String(fd.get("experience_years")).trim() : "some experience";
      const skillsRaw = fd.get("skills") ? String(fd.get("skills")) : "";
      const skills = parseSkills(skillsRaw);
      
      let insightText = "";
      if (skills.length === 0) {
        insightText = `I need more context! Add some skills and your target role so I can generate an accurate roadmap for you.`;
      } else {
        insightText = `Based on your profile, you are positioning yourself for <strong>${escapeHtml(target)}</strong> roles with ${escapeHtml(exp)} years of experience. You currently have ${skills.length} core skills mapped.<br/><br/>`;
        
        if (skills.length < 3) {
          insightText += "💡 <strong>Tip:</strong> You might want to list more foundational skills like Git, problem-solving, or specific framework tools.";
        } else {
          insightText += "🔥 <strong>Insight:</strong> You have a solid base! Focusing on an end-to-end project applying these skills will drastically improve your matching confidence.";
        }
      }

      aiSkeleton.hidden = true;
      aiLiveInsights.hidden = false;
      aiLiveInsights.innerHTML = insightText;
    }, 1200);
  }

  function closeAiModalFunc() {
    if (!aiModal || !modalBackdrop) return;
    aiModal.hidden = true;
    modalBackdrop.hidden = true;
    aiModal.setAttribute("aria-hidden", "true");
  }

  function setModalForOnboarding() {
    if (!onboardingHtml) onboardingHtml = modalContent.innerHTML;
    modalTitle.textContent = "Placement guide";
    modalCta.textContent = "Start your assessment";
    modalCta.onclick = () => {
      closeModal();
      navigate("assess");
    };
    modalContent.innerHTML = onboardingHtml;
    window.__loadModalLottie && window.__loadModalLottie();
  }

  function setModalForResults(result) {
    modalTitle.textContent = "Your plan";
    modalCta.textContent = "Back to Assessment";
    modalCta.onclick = () => {
      closeModal();
      navigate("assess");
    };

    const placements = (result.placement_recommendations || []).slice(0, 3);
    const gaps = (result.skill_gaps || []).slice(0, 4);
    const steps = (result.roadmap_steps || []).slice(0, 4);

    modalContent.innerHTML = `
      <div class="modal-grid">
        <div class="modal-step glass">
          <div class="modal-step-title">Placements</div>
          <div class="modal-step-body">
            ${placements.map((p) => `<div style="margin-top:8px"><b>${escapeHtml(p.role)}</b> · ${Math.round(p.confidence * 100)}%</div>`).join("")}
          </div>
        </div>
        <div class="modal-step glass">
          <div class="modal-step-title">Top gaps</div>
          <div class="modal-step-body">
            ${gaps.map((g) => `<div style="margin-top:8px"><b>${escapeHtml(g.gap)}</b> (P${escapeHtml(String(g.priority))})</div>`).join("")}
          </div>
        </div>
        <div class="modal-step glass">
          <div class="modal-step-title">Next 3 phases</div>
          <div class="modal-step-body">
            ${steps
              .slice(0, 3)
              .map((s) => `<div style="margin-top:8px"><b>${escapeHtml(s.timeframe)}</b> · ${escapeHtml(s.goal)}</div>`)
              .join("")}
          </div>
        </div>
      </div>

      <div class="modal-lottie-row glass">
        <div class="modal-lottie" id="modalLottie"></div>
        <div class="modal-lottie-text">
          <div class="modal-lottie-title">AI guidance summary</div>
          <div class="modal-lottie-sub">${escapeHtml(result.ai_notes || "")}</div>
        </div>
      </div>
    `;
    window.__loadModalLottie && window.__loadModalLottie();
  }

  function morphCardToModal(cardEl) {
    const fromRect = cardEl.getBoundingClientRect();
    // The modal might be `hidden` initially; ensure it's visible before measuring.
    modal.hidden = false;
    modalBackdrop.hidden = false;
    modal.setAttribute("aria-hidden", "false");
    const toRect = modal.getBoundingClientRect();

    const ghost = document.createElement("div");
    ghost.className = "card";
    ghost.style.position = "fixed";
    ghost.style.left = fromRect.left + "px";
    ghost.style.top = fromRect.top + "px";
    ghost.style.width = fromRect.width + "px";
    ghost.style.height = fromRect.height + "px";
    ghost.style.zIndex = 95;
    ghost.style.pointerEvents = "none";
    ghost.innerHTML = cardEl.innerHTML;
    document.body.appendChild(ghost);

    const endX = toRect.left - fromRect.left;
    const endY = toRect.top - fromRect.top;
    const scaleX = toRect.width / fromRect.width;
    const scaleY = toRect.height / fromRect.height;

    const duration = preferredReduceMotion ? 0 : 260;
    ghost.animate(
      [
        { transform: "translate(0px,0px) scale(1)", opacity: 1 },
        { transform: `translate(${endX}px, ${endY}px) scale(${scaleX}, ${scaleY})`, opacity: 0.0 },
      ],
      { duration, easing: "cubic-bezier(.2,.8,.2,1)", fill: "forwards" }
    );

    setTimeout(() => {
      ghost.remove();
    }, duration + 20);
  }

  function openResultsModal(opts) {
    if (!lastResult) return;
    const cardEl = opts && opts.cardRole ? placementsWrap.querySelector(`[data-card-role="${opts.cardRole}"]`) : null;

    // Update modal content first so the morph feels like a transform.
    setModalForResults(lastResult);
    if (cardEl) morphCardToModal(cardEl);
    else openModal();
  }

  // Nav
  navButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const r = btn.getAttribute("data-nav");
      navigate(r);
    });
  });

  // Onboarding modal
  if (openOnboarding) {
    openOnboarding.addEventListener("click", () => {
      setModalForOnboarding();
      openModal();
    });
  }
  if (closeModalBtn) closeModalBtn.addEventListener("click", closeModal);
  if (aiBtn) aiBtn.addEventListener("click", openAiModal);
  if (closeAiModal) closeAiModal.addEventListener("click", closeAiModalFunc);
  
  if (modalBackdrop) {
    modalBackdrop.addEventListener("click", () => {
      closeModal();
      closeAiModalFunc();
    });
  }

  // Ensure escape closes modal.
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      if (modal && !modal.hidden) closeModal();
      if (aiModal && !aiModal.hidden) closeAiModalFunc();
    }
  });

  // Export JSON
  if (openExport) {
    openExport.addEventListener("click", () => {
      if (!lastResult) return;
      const blob = new Blob([JSON.stringify(lastResult, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `assessment_${lastResult.submission_id || "unknown"}.json`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    });
  }

  // Form: live preview micro-interactions
  if (assessForm) {
    const liveEls = assessForm.querySelectorAll("input");
    liveEls.forEach((el) => {
      el.addEventListener("input", updatePreview);
      el.addEventListener("focus", () => el.classList.add("is-focus"));
      el.addEventListener("blur", () => el.classList.remove("is-focus"));
    });
    updatePreview();
  }

  // Kinetic typography
  function animateKineticWords() {
    const words = Array.from(document.querySelectorAll(".kinetic-word"));
    if (!words.length) return;

    if (window.gsap) {
      words.forEach((w, i) => {
        const delay = i * 0.06;
        window.gsap.to(w, {
          opacity: 1,
          y: 0,
          scale: 1,
          filter: "blur(0px)",
          duration: 0.7,
          delay,
          ease: "power3.out",
        });
      });
    } else {
      // Fallback: show immediately
      words.forEach((w) => w.classList.add("is-visible"));
    }
  }

  // Submit assessment
  if (assessForm) {
    assessForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      if (!assessForm) return;

      const fd = new FormData(assessForm);
      const payload = {
        name: fd.get("name") ? String(fd.get("name")).trim() : null,
        email: fd.get("email") ? String(fd.get("email")).trim() : null,
        target_role: String(fd.get("target_role")).trim(),
        experience_years: Number(fd.get("experience_years")),
        skills: parseSkills(String(fd.get("skills"))),
        interests: parseSkills(String(fd.get("interests") || "")),
      };

      if (!payload.target_role || !payload.skills.length || !Number.isFinite(payload.experience_years)) {
        return;
      }

      const originalSubmitText = submitBtn.querySelector(".submit-text").textContent;
      submitBtn.querySelector(".submit-text").textContent = "AI Analyzing profile...";
      setLoadingUI(true);
      navigate("results");

      // Typewriter function
      function typeWriter(element, text, speed = 25) {
        element.innerHTML = "";
        element.classList.add("ai-typewriter");
        let i = 0;
        function type() {
          if (i < text.length) {
            element.innerHTML += escapeHtml(text.charAt(i));
            i++;
            setTimeout(type, speed);
          } else {
            element.classList.remove("ai-typewriter");
          }
        }
        type();
      }

      try {
        const r = await fetch("/api/assess", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        if (!r.ok) throw new Error(await r.text());
        const result = await r.json();
        lastResult = result;
        lastProfile = payload;

        renderPlacements(result.placement_recommendations || []);
        renderGaps(result.skill_gaps || []);
        renderRoadmap(result.roadmap_steps || []);
        aiNotes.textContent = result.ai_notes || "";

        placementsSkeleton.hidden = true;
        gapsSkeleton.hidden = true;
        
        // Deep AI typing effect for notes
        typeWriter(aiNotes, result.ai_notes || "Processed via AI mapping.");

        if (window.renderUnifiedDashboard) {
          window.renderUnifiedDashboard(payload, "");
        }

      } catch (err) {
        typeWriter(aiNotes, "Failed to connect to the AI engine. Try again.");
      } finally {
        submitBtn.querySelector(".submit-text").textContent = originalSubmitText;
        setLoadingUI(false);
      }
    });
  }

  // Init route on load
  const initial = getRouteFromHash();
  currentRoute = initial;
  sections.forEach((s) => setSectionHidden(s, s.getAttribute("data-route") !== initial));

  animateKineticWords();
  // Default: store onboarding content for modal restore.
  if (modalContent) onboardingHtml = modalContent.innerHTML;
})();

