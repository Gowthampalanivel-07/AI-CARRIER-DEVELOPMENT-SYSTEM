(function () {
  let skillsChart = null;
  let lastProfile = null;
  let lastResumeText = "";
  const TOKEN_KEY = "ai_placement_auth_token";
  const EMAIL_KEY = "ai_placement_auth_email";

  function getUserKey() {
    const key = "ai_placement_user_key";
    let v = localStorage.getItem(key);
    if (!v) {
      v = "user-" + Math.random().toString(36).slice(2, 10);
      localStorage.setItem(key, v);
    }
    return v;
  }

  function getToken() {
    return localStorage.getItem(TOKEN_KEY) || "";
  }

  function setToken(token, email) {
    localStorage.setItem(TOKEN_KEY, token || "");
    if (email) localStorage.setItem(EMAIL_KEY, email);
  }

  async function apiFetch(url, options) {
    const opts = options ? { ...options } : {};
    opts.headers = { ...(opts.headers || {}) };
    const token = getToken();
    if (token) opts.headers.Authorization = `Bearer ${token}`;
    return fetch(url, opts);
  }

  function escapeHtml(str) {
    return String(str)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function renderCardList(containerId, items, mapFn) {
    const el = document.getElementById(containerId);
    if (!el) return;
    el.innerHTML = "";
    (items || []).forEach((item) => {
      const card = document.createElement("div");
      card.className = "card";
      card.innerHTML = mapFn(item);
      el.appendChild(card);
    });
  }

  async function trackActivity(eventType, entityType, entityId, metadata) {
    try {
      await apiFetch("/api/activity", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_key: getUserKey(),
          event_type: eventType,
          entity_type: entityType || null,
          entity_id: entityId || null,
          metadata: metadata || {},
        }),
      });
    } catch (_e) {
      // Silent fail: tracking should never block UX.
    }
  }

  function renderChart(skillLevels) {
    const canvas = document.getElementById("skillsChart");
    if (!canvas || !window.Chart) return;
    const labels = (skillLevels || []).map((s) => s.skill);
    const values = (skillLevels || []).map((s) => s.level);
    if (skillsChart) skillsChart.destroy();
    skillsChart = new window.Chart(canvas, {
      type: "bar",
      data: {
        labels,
        datasets: [
          {
            label: "Skill Level",
            data: values,
            backgroundColor: "rgba(255,138,101,0.55)",
            borderColor: "rgba(255,180,162,0.9)",
            borderWidth: 1,
            borderRadius: 8,
          },
        ],
      },
      options: {
        responsive: true,
        plugins: { legend: { labels: { color: "#4A2C2A" } } },
        scales: {
          x: { ticks: { color: "rgba(74,44,42,.8)" }, grid: { color: "rgba(74,44,42,.08)" } },
          y: { ticks: { color: "rgba(74,44,42,.8)" }, grid: { color: "rgba(74,44,42,.08)" }, suggestedMax: 100 },
        },
      },
    });
  }

  async function askAssistant(profile) {
    const inp = document.getElementById("assistantMessage");
    const out = document.getElementById("assistantReply");
    const btn = document.getElementById("assistantAskBtn");
    if (!inp || !out || !btn) return;
    const message = String(inp.value || "").trim();
    if (!message) return;
    trackActivity("assistant_query", "assistant", "chat", { length: message.length });
    btn.disabled = true;
    out.textContent = "Thinking...";
    try {
      const r = await apiFetch("/api/assistant", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ profile, message }),
      });
      if (!r.ok) throw new Error(await r.text());
      const data = await r.json();
      out.textContent = data.reply || "No response generated.";
    } catch (_e) {
      out.textContent = "Assistant is unavailable right now. Try again.";
    } finally {
      btn.disabled = false;
    }
  }

  async function uploadResumeAndParse(profile) {
    const fileInput = document.getElementById("resumeFile");
    const summary = document.getElementById("resumeParseSummary");
    if (!fileInput || !summary) return;
    const file = fileInput.files && fileInput.files[0];
    if (!file) {
      summary.textContent = "Select a resume file first.";
      return;
    }
    const fd = new FormData();
    fd.append("file", file);
    fd.append("user_key", getUserKey());
    summary.textContent = "Parsing resume...";
    try {
      const r = await apiFetch("/api/resume/upload", { method: "POST", body: fd });
      if (!r.ok) throw new Error(await r.text());
      const parsed = await r.json();
      summary.textContent = parsed.summary || "Resume parsed.";
      trackActivity("resume_upload", "resume", file.name, { skills: parsed.skills || [] });

      const mergedSkills = Array.from(new Set([...(profile.skills || []), ...(parsed.skills || [])]));
      const updated = { ...profile, skills: mergedSkills };
      lastProfile = updated;
      lastResumeText = `Extracted skills: ${(parsed.skills || []).join(", ")}`;
      window.renderUnifiedDashboard(updated, lastResumeText);
    } catch (_e) {
      summary.textContent = "Resume parsing failed.";
    }
  }

  async function ingestDataset() {
    const kind = document.getElementById("datasetKind");
    const fileInput = document.getElementById("datasetFile");
    const status = document.getElementById("datasetIngestStatus");
    if (!kind || !fileInput || !status) return;
    const file = fileInput.files && fileInput.files[0];
    if (!file) {
      status.textContent = "Select a CSV/JSON dataset file.";
      return;
    }
    const fd = new FormData();
    fd.append("kind", kind.value);
    fd.append("source", file.name);
    fd.append("file", file);
    status.textContent = "Ingesting dataset...";
    try {
      const r = await apiFetch("/api/datasets/ingest", { method: "POST", body: fd });
      if (!r.ok) throw new Error(await r.text());
      const data = await r.json();
      status.textContent = `Ingested ${data.ingested_count} ${data.kind} records from ${file.name}.`;
      trackActivity("dataset_ingest", "dataset", data.kind, { count: data.ingested_count });
      if (lastProfile) {
        window.renderUnifiedDashboard(lastProfile, lastResumeText);
      }
    } catch (_e) {
      status.textContent = "Dataset ingestion failed. Check file format and columns.";
    }
  }

  function attachDashboardHandlers(profile) {
    const uploadBtn = document.getElementById("resumeUploadBtn");
    if (uploadBtn) uploadBtn.onclick = () => uploadResumeAndParse(profile);
    const ingestBtn = document.getElementById("datasetIngestBtn");
    if (ingestBtn) ingestBtn.onclick = () => ingestDataset();
  }

  async function registerOrLogin(mode) {
    const emailEl = document.getElementById("authEmail");
    const passEl = document.getElementById("authPassword");
    const statusEl = document.getElementById("authStatus");
    if (!emailEl || !passEl || !statusEl) return;
    const email = String(emailEl.value || "").trim();
    const password = String(passEl.value || "").trim();
    if (!email || password.length < 8) {
      statusEl.textContent = "Enter valid email and password (8+ chars).";
      return;
    }
    statusEl.textContent = mode === "register" ? "Creating account..." : "Signing in...";
    try {
      const r = await fetch(`/api/auth/${mode}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password, full_name: "Student" }),
      });
      if (!r.ok) throw new Error(await r.text());
      const data = await r.json();
      setToken(data.access_token, data.email);
      statusEl.textContent = `Signed in as ${data.email}`;
    } catch (_e) {
      statusEl.textContent = "Auth failed. Check credentials.";
    }
  }

  function attachAuthHandlers() {
    const regBtn = document.getElementById("authRegisterBtn");
    const loginBtn = document.getElementById("authLoginBtn");
    const retrainBtn = document.getElementById("retrainBtn");
    const retrainStatus = document.getElementById("retrainStatus");
    if (regBtn) regBtn.onclick = () => registerOrLogin("register");
    if (loginBtn) loginBtn.onclick = () => registerOrLogin("login");
    if (retrainBtn) {
      retrainBtn.onclick = async () => {
        if (!retrainStatus) return;
        retrainStatus.textContent = "Starting retrain job...";
        try {
          const r = await apiFetch("/api/retrain/start", { method: "POST" });
          if (!r.ok) throw new Error(await r.text());
          retrainStatus.textContent = "Retraining started. Checking status...";
          setTimeout(async () => {
            const s = await apiFetch("/api/retrain/status");
            const data = await s.json();
            retrainStatus.textContent = `Model ready. Events: ${data.trained_on_events || 0}`;
          }, 1600);
        } catch (_e) {
          retrainStatus.textContent = "Retrain failed. Sign in first.";
        }
      };
    }
  }

  window.renderUnifiedDashboard = async function (profile, resumeText) {
    lastProfile = profile;
    lastResumeText = resumeText || "";
    try {
      const r = await apiFetch("/api/unified-insights", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          profile,
          resume_text: resumeText || null,
          user_key: getUserKey(),
        }),
      });
      if (!r.ok) throw new Error(await r.text());
      const data = await r.json();

      const profileEl = document.getElementById("dashProfile");
      const careerScore = document.getElementById("careerScore");
      const growthScore = document.getElementById("growthScore");
      if (profileEl) {
        profileEl.innerHTML = `<b>${escapeHtml(data.profile.name)}</b><br/>Target: ${escapeHtml(
          data.profile.target_role
        )}<br/>Skills: ${escapeHtml(String((data.profile.skills || []).slice(0, 8).join(", ")))}<br/>${
          escapeHtml(data.profile.resume_parse?.summary || "")
        }`;
      }
      if (careerScore) careerScore.textContent = `${data.dashboard.career_score}% Ready`;
      if (growthScore) growthScore.textContent = `+${data.dashboard.growth_percent_weekly}% this week`;

      renderChart(data.dashboard.skill_levels || []);

      renderCardList("dashTimeline", data.dashboard.timeline || [], (x) => {
        return `<div class="card-role">${escapeHtml(x.event)}</div><div class="card-why">${escapeHtml(x.date)}</div>`;
      });

      renderCardList("dashInsights", data.insights.skill_gap_analysis || [], (x) => {
        return `<div class="card-head"><div class="card-role skill-click" data-skill="${escapeHtml(
          x.skill
        )}">${escapeHtml(x.skill)}</div><div class="card-conf">${
          x.importance
        }</div></div>`;
      });
      const insightsRoot = document.getElementById("dashInsights");
      if (insightsRoot) {
        const n = document.createElement("div");
        n.className = "card";
        n.innerHTML = `<div class="card-role">Next Best Action</div><div class="card-why">${escapeHtml(
          data.insights.next_best_action || ""
        )}</div>`;
        insightsRoot.prepend(n);
      }

      renderCardList("dashJobs", data.jobs.matches || [], (x) => {
        return `<div class="card-head"><div class="card-role job-click" data-jobid="${escapeHtml(
          x.id
        )}" data-jobtitle="${escapeHtml(x.title)}">${escapeHtml(x.title)} · ${escapeHtml(
          x.company
        )}</div><div class="card-conf">${x.match_score}%</div></div><div class="card-why">${escapeHtml(
          x.location
        )} · ₹${x.salary_lpa} LPA</div>`;
      });

      renderCardList("dashLearning", data.learning.recommended_courses || [], (x) => {
        return `<div class="card-role course-click" data-course="${escapeHtml(x.title)}">${escapeHtml(
          x.title
        )}</div><div class="card-why">${escapeHtml(
          x.provider
        )} · relevance ${escapeHtml(String(x.relevance))}</div>`;
      });

      renderCardList("dashNotifications", data.jobs.notifications || [], (x) => {
        return `<div class="card-why">${escapeHtml(x)}</div>`;
      });

      const btn = document.getElementById("assistantAskBtn");
      if (btn) {
        btn.onclick = () => askAssistant(profile);
      }
      attachDashboardHandlers(profile);

      document.querySelectorAll(".job-click").forEach((el) => {
        el.addEventListener("click", () => {
          trackActivity("job_click", "job", el.getAttribute("data-jobid"), { title: el.getAttribute("data-jobtitle") });
        });
      });
      document.querySelectorAll(".course-click").forEach((el) => {
        el.addEventListener("click", () => {
          trackActivity("course_click", "course", el.getAttribute("data-course"), {});
        });
      });
      document.querySelectorAll(".skill-click").forEach((el) => {
        el.addEventListener("click", () => {
          const skill = el.getAttribute("data-skill");
          trackActivity("skill_focus", "skill", skill, {});
        });
      });
    } catch (_e) {
      const profileEl = document.getElementById("dashProfile");
      if (profileEl) profileEl.textContent = "Could not load unified insights.";
    }
  };
  attachAuthHandlers();
})();

