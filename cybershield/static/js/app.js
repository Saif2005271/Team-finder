/* ══════════════════════════════════════════════════════
   CyberShield — Main Application JS
   All seven modules wired to the FastAPI backend.
   ══════════════════════════════════════════════════════ */

/* ── Matrix rain background ─────────────────────────── */
(function initMatrix() {
  const canvas = document.getElementById("matrix-canvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const chars = "アイウエオカキクケコサシスセソタチツテトナニヌネノABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@#$%&";
  let cols, drops;

  function resize() {
    canvas.width  = window.innerWidth;
    canvas.height = window.innerHeight;
    cols  = Math.floor(canvas.width / 16);
    drops = Array(cols).fill(1);
  }

  function draw() {
    ctx.fillStyle = "rgba(10,10,15,0.05)";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = "#00ff41";
    ctx.font = "14px monospace";
    drops.forEach((y, i) => {
      const ch = chars[Math.floor(Math.random() * chars.length)];
      ctx.fillText(ch, i * 16, y * 16);
      if (y * 16 > canvas.height && Math.random() > 0.975) drops[i] = 0;
      drops[i]++;
    });
  }

  resize();
  window.addEventListener("resize", resize);
  setInterval(draw, 50);
})();


/* ── Navigation ──────────────────────────────────────── */
document.querySelectorAll(".nav-item").forEach(item => {
  item.addEventListener("click", () => {
    document.querySelectorAll(".nav-item").forEach(n => n.classList.remove("active"));
    document.querySelectorAll(".panel").forEach(p => p.classList.remove("active"));
    item.classList.add("active");
    const target = item.dataset.panel;
    const panel  = document.getElementById("panel-" + target);
    if (panel) panel.classList.add("active");

    // Lazy-load panel content on first visit
    if (target === "threats" && !panel.dataset.loaded) {
      panel.dataset.loaded = "1";
      loadThreatFeed();
    }
    if (target === "webrtc" && !panel.dataset.loaded) {
      panel.dataset.loaded = "1";
      initWebRTC();
    }
    if (target === "dns" && !panel.dataset.loaded) {
      panel.dataset.loaded = "1";
      runDNSLeak();
    }
    if (target === "stalkerware" && !panel.dataset.loaded) {
      panel.dataset.loaded = "1";
      loadQuiz();
    }
  });
});


/* ── Helpers ─────────────────────────────────────────── */
function el(id)    { return document.getElementById(id); }
function qs(sel)   { return document.querySelector(sel); }
function qsa(sel)  { return document.querySelectorAll(sel); }

function loading(containerId, msg = "Scanning…") {
  el(containerId).innerHTML =
    `<div class="loading-text"><div class="spinner"></div>${msg}</div>`;
}

function sevClass(sev) {
  return { critical: "rf-critical", high: "rf-high", medium: "rf-medium", low: "rf-low" }[sev] || "rf-low";
}

function sevBadge(sev) {
  return `<span class="sev sev-${sev}">${sev}</span>`;
}

function riskMeter(score, level, color, summary) {
  return `
  <div class="risk-meter" style="background:rgba(0,0,0,0.3)">
    <div class="risk-score-circle" style="color:${color};border-color:${color};box-shadow:0 0 16px ${color}44">
      <span class="risk-score-num">${Math.round(score)}</span>
      <span class="risk-score-label">/ 100</span>
    </div>
    <div>
      <div class="risk-level-text" style="color:${color};text-shadow:0 0 8px ${color}">${level}</div>
      <div class="risk-summary">${summary || ""}</div>
    </div>
  </div>`;
}

function factorsList(factors) {
  if (!factors || !factors.length) return `<p class="text-dim small">No risk factors detected.</p>`;
  return factors.map(f => `
    <div class="risk-factor ${sevClass(f.severity)}">
      <div class="rf-body">
        <div class="rf-title">${sevBadge(f.severity)} &nbsp;${f.title || f.factor || ""}</div>
        <div class="rf-desc">${f.description}</div>
      </div>
    </div>`).join("");
}

async function postJSON(url, body) {
  const r = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return r.json();
}

function fmtDate(str) {
  if (!str) return "";
  try { return new Date(str).toLocaleDateString(undefined, { year:"numeric", month:"short", day:"numeric" }); }
  catch { return str.slice(0, 10); }
}


/* ═══════════════════════════════════════════════════════
   MODULE 1 — Location & Privacy Auditor
   ═══════════════════════════════════════════════════════ */
async function scanIPOnly() {
  loading("location-result", "Fetching IP geolocation data…");
  try {
    const data = await postJSON("/api/location/analyze", {});
    renderLocation(data);
  } catch (e) {
    el("location-result").innerHTML = `<p class="text-red">Error: ${e.message}</p>`;
  }
}

function requestGPS() {
  if (!navigator.geolocation) {
    return alert("Geolocation is not supported by your browser.");
  }
  loading("location-result", "Requesting GPS permission from browser…");
  navigator.geolocation.getCurrentPosition(
    async pos => {
      const { latitude, longitude, accuracy } = pos.coords;
      try {
        const data = await postJSON("/api/location/analyze", { latitude, longitude, accuracy });
        renderLocation(data);
      } catch (e) {
        el("location-result").innerHTML = `<p class="text-red">Error: ${e.message}</p>`;
      }
    },
    err => {
      el("location-result").innerHTML = `
        <div class="card">
          <p class="text-yellow">⚠ GPS permission denied or unavailable (${err.message}).</p>
          <p class="text-dim mt-8 small">IP-based analysis will still be performed without GPS data.</p>
        </div>`;
      scanIPOnly();
    }
  );
}

function renderLocation(d) {
  if (d.error) { el("location-result").innerHTML = `<p class="text-red">${d.error}</p>`; return; }

  const ip  = d.ip_location || {};
  const gps = d.gps;
  const r   = d.risk || {};

  let html = riskMeter(r.score || 0, r.level || "—", r.color || "#00ff41", "");
  html += `<div style="margin-bottom:8px"><strong class="text-cyan mono small">RISK FACTORS</strong></div>`;
  html += factorsList(r.factors || []);

  html += `<div class="card mt-16">
    <div class="card-title">IP Geolocation Report</div>
    <table class="info-table">
      <tr><td>Public IP</td><td class="text-green mono">${d.ip || "—"}</td></tr>
      <tr><td>City</td><td>${ip.city || "—"}</td></tr>
      <tr><td>Region</td><td>${ip.region || "—"}</td></tr>
      <tr><td>Country</td><td>${ip.country_name || ip.country || "—"}</td></tr>
      <tr><td>ISP / Org</td><td>${ip.org || "—"}</td></tr>
      <tr><td>ASN</td><td>${ip.asn || "—"}</td></tr>
      <tr><td>Timezone</td><td>${ip.timezone || "—"}</td></tr>
      <tr><td>Latitude / Lon</td><td>${ip.latitude || "—"} / ${ip.longitude || "—"}</td></tr>
    </table>
  </div>`;

  if (gps) {
    html += `<div class="card">
      <div class="card-title">Browser GPS Coordinates</div>
      <table class="info-table">
        <tr><td>Latitude</td><td class="text-red mono">${gps.latitude}</td></tr>
        <tr><td>Longitude</td><td class="text-red mono">${gps.longitude}</td></tr>
        <tr><td>Accuracy</td><td>${gps.accuracy_meters ? gps.accuracy_meters.toFixed(0) + " m" : "—"}</td></tr>
      </table>
    </div>`;
  }

  // Tracking methods education
  if (d.tracking_methods) {
    html += `<div class="card">
      <div class="card-title">How You Are Tracked — Educational Overview</div>
      <div class="grid-2">`;
    for (const [, m] of Object.entries(d.tracking_methods)) {
      const isPassive = m.passive;
      html += `<div class="tracking-card">
        <div class="tracking-card-header">
          <span class="tracking-name">${m.name}</span>
          <span class="tracking-accuracy">${m.accuracy}</span>
        </div>
        <span class="tracking-passive ${isPassive ? "passive-yes" : "passive-no"}">
          ${isPassive ? "🔴 No permission required" : "🟢 Requires user permission"}
        </span>
        <div class="tracking-desc">${m.description}</div>
      </div>`;
    }
    html += `</div></div>`;
  }

  el("location-result").innerHTML = html;
}

el("btn-scan-ip")?.addEventListener("click", scanIPOnly);
el("btn-request-gps")?.addEventListener("click", requestGPS);


/* ═══════════════════════════════════════════════════════
   MODULE 2 — Device Compromise / Breach Checker
   ═══════════════════════════════════════════════════════ */
el("btn-check-breach")?.addEventListener("click", async () => {
  const query = el("breach-input").value.trim();
  const type  = el("breach-type").value;
  if (!query) return;

  loading("breach-result", `Checking ${type} against breach databases…`);

  try {
    const data = await postJSON("/api/breach/check", { query, type });
    renderBreach(data, type);
  } catch (e) {
    el("breach-result").innerHTML = `<p class="text-red">Error: ${e.message}</p>`;
  }
});

function renderBreach(d, type) {
  if (d.error) { el("breach-result").innerHTML = `<p class="text-red">${d.error}</p>`; return; }

  if (d.network_restricted) {
    el("breach-result").innerHTML = `
      <div class="card" style="border-color:var(--yellow)">
        <div class="card-title" style="color:var(--yellow)">⚠ Network Restriction — Cloud Environment</div>
        <p class="small">${d.message}</p>
        <div class="card mt-16" style="background:var(--surface2)">
          <div class="card-title" style="color:var(--cyan)">How k-Anonymity Works (For Local Use)</div>
          <p class="small text-dim" style="line-height:1.8">${d.how_it_works}</p>
        </div>
        <div class="mt-16">
          <a href="${d.direct_url}" target="_blank" class="btn btn-cyan">🔗 Check Directly at HIBP</a>
        </div>
      </div>`;
    return;
  }

  if (d.demo) {
    el("breach-result").innerHTML = `
      <div class="card">
        <div class="card-title" style="color:var(--yellow)">⚠ API Key Required</div>
        <p>${d.message}</p>
        <p class="mt-8 text-dim small">${d.instructions}</p>
        <div class="terminal mt-16">${JSON.stringify(d.sample_output, null, 2)}</div>
      </div>`;
    return;
  }

  let html = "";
  if (d.breached) {
    const color = d.severity === "critical" ? "var(--red)" : "var(--orange)";
    html += riskMeter(
      d.severity === "critical" ? 95 : 75,
      d.breached ? "BREACHED" : "SAFE",
      color,
      d.message || `Found in ${d.breach_count || 1} breach${d.breach_count > 1 ? "es" : ""}`
    );

    if (type === "password" && d.count) {
      html += `<div class="card">
        <div class="card-title">Password Breach Details</div>
        <table class="info-table">
          <tr><td>Times seen in breaches</td><td class="text-red mono bold">${d.count.toLocaleString()}</td></tr>
          <tr><td>Severity</td><td>${sevBadge(d.severity)}</td></tr>
          <tr><td>Method</td><td class="text-dim">k-Anonymity (SHA-1 prefix) — your password was never transmitted</td></tr>
        </table>
      </div>`;
    }

    if (type === "email" && d.breaches) {
      html += `<div class="card">
        <div class="card-title">Breach Details (${d.breach_count} found)</div>`;
      d.breaches.forEach(b => {
        html += `<div style="padding:10px 0;border-bottom:1px solid var(--border)">
          <div class="flex flex-wrap mb-8">
            <span class="bold">${b.name || "Unknown"}</span>
            <span class="text-dim small">${b.domain || ""}</span>
            <span class="text-dim small" style="margin-left:auto">${fmtDate(b.date)}</span>
          </div>
          <div class="article-tags">
            ${(b.data_types || []).map(t => `<span class="article-tag">${t}</span>`).join("")}
          </div>
          ${b.pwn_count ? `<div class="text-dim small mt-8">${b.pwn_count.toLocaleString()} accounts affected</div>` : ""}
        </div>`;
      });
      html += `</div>`;
    }
  } else {
    html += riskMeter(5, "NOT FOUND", "#00ff41", d.message || "Not found in known breach databases.");
  }

  // Recommendations
  if (d.recommendations?.length) {
    html += `<div class="card">
      <div class="card-title">Recommendations</div>
      <ul style="padding-left:16px;line-height:2">
        ${d.recommendations.map(r => `<li class="small">${r}</li>`).join("")}
      </ul>
    </div>`;
  }

  el("breach-result").innerHTML = html;
}


/* ═══════════════════════════════════════════════════════
   MODULE 3 — Phishing / URL Analyzer
   ═══════════════════════════════════════════════════════ */
el("btn-analyze-url")?.addEventListener("click", analyzeURL);
el("phishing-input")?.addEventListener("keydown", e => { if (e.key === "Enter") analyzeURL(); });

async function analyzeURL() {
  const url = el("phishing-input").value.trim();
  if (!url) return;
  loading("phishing-result", "Running 10-point URL analysis…");
  try {
    const data = await postJSON("/api/phishing/analyze", { url });
    renderPhishing(data);
  } catch (e) {
    el("phishing-result").innerHTML = `<p class="text-red">Error: ${e.message}</p>`;
  }
}

function renderPhishing(d) {
  if (d.error) { el("phishing-result").innerHTML = `<p class="text-red">${d.error}</p>`; return; }

  let html = riskMeter(
    d.risk_score,
    d.risk_level,
    d.risk_color,
    `${d.checks_flagged} of ${d.total_checks} checks flagged`
  );

  // Score bar
  html += `<div class="card">
    <div class="card-title">URL Analysis Summary</div>
    <table class="info-table">
      <tr><td>Submitted URL</td><td class="mono small" style="word-break:break-all">${d.url}</td></tr>
      <tr><td>Hostname</td><td class="mono text-cyan">${d.parsed?.hostname || "—"}</td></tr>
      <tr><td>Registered Domain</td><td class="mono">${d.parsed?.registered_domain || "—"}</td></tr>
      <tr><td>TLD</td><td class="mono">${d.parsed?.tld || "—"}</td></tr>
      <tr><td>Protocol</td><td class="${d.parsed?.scheme === "https" ? "text-green" : "text-red"} mono">${d.parsed?.scheme || "—"}</td></tr>
      <tr><td>Subdomain</td><td class="mono">${d.parsed?.subdomain || "(none)"}</td></tr>
      <tr><td>Domain Age</td><td>${d.domain_age?.days_old != null ? `${d.domain_age.days_old} days (${d.domain_age.status})` : "Unknown"}</td></tr>
      <tr><td>Registration Date</td><td>${d.domain_age?.registration_date || "Unknown"}</td></tr>
    </table>
  </div>`;

  // Homograph detail
  if (d.homograph_analysis) {
    const hg = d.homograph_analysis;
    html += `<div class="card">
      <div class="card-title">Homograph / IDN Analysis</div>
      <table class="info-table">
        <tr><td>Suspicious chars detected</td><td class="${hg.detected ? "text-red" : "text-green"}">${hg.detected ? "YES ⚠" : "None"}</td></tr>
        <tr><td>Mixed Unicode scripts</td><td>${hg.mixed_scripts ? `<span class="text-red">YES — ${hg.scripts.join(", ")}</span>` : "No"}</td></tr>
        ${hg.suspicious_chars.length ? `<tr><td>Confusable chars</td><td class="text-red mono small">${hg.suspicious_chars.join("<br>")}</td></tr>` : ""}
      </table>
      <p class="text-dim small mt-8">
        IDN (Internationalized Domain Name) homograph attacks use visually identical Unicode characters
        (e.g., Cyrillic 'а' vs Latin 'a') to spoof trusted domains. Modern browsers show the punycode
        form (xn--) when mixed scripts are detected.
      </p>
    </div>`;
  }

  html += `<div class="card-title mt-16">Detailed Risk Factors</div>`;
  html += factorsList(d.risk_factors || []);

  el("phishing-result").innerHTML = html;
}


/* ═══════════════════════════════════════════════════════
   MODULE 4 — Stalkerware Checklist
   ═══════════════════════════════════════════════════════ */
let _quizAnswers = {};

async function loadQuiz() {
  loading("quiz-container", "Loading diagnostic questions…");
  try {
    const data = await fetch("/api/stalkerware/questions").then(r => r.json());
    renderQuiz(data.questions);
  } catch (e) {
    el("quiz-container").innerHTML = `<p class="text-red">Error loading quiz: ${e.message}</p>`;
  }
}

function renderQuiz(questions) {
  _quizAnswers = {};
  let html = `<p class="text-dim small mb-16">Answer honestly — all processing is local to your browser session. No answers are stored.</p>`;

  questions.forEach(q => {
    html += `
    <div class="quiz-question" id="qq-${q.id}">
      <div class="quiz-q-icon">${q.icon}</div>
      <div class="quiz-q-body">
        <div class="quiz-q-cat">${q.category}</div>
        <div class="quiz-q-text">${q.question}</div>
      </div>
      <div class="quiz-toggle">
        <label class="toggle-switch" title="Toggle Yes/No">
          <input type="checkbox" class="quiz-cb" data-qid="${q.id}" />
          <div class="toggle-track"></div>
          <div class="toggle-thumb"></div>
        </label>
        <span class="toggle-label">YES</span>
      </div>
    </div>`;
  });

  el("quiz-container").innerHTML = html;
  el("btn-assess")?.classList.remove("hidden");

  qsa(".quiz-cb").forEach(cb => {
    cb.addEventListener("change", () => {
      _quizAnswers[cb.dataset.qid] = cb.checked;
      const row = el("qq-" + cb.dataset.qid);
      if (cb.checked) row.classList.add("answered-yes");
      else            row.classList.remove("answered-yes");
    });
  });
}

el("btn-assess")?.addEventListener("click", async () => {
  const answers = Object.entries(_quizAnswers).map(([question_id, answer]) => ({ question_id, answer }));
  loading("assessment-result", "Calculating risk score…");
  try {
    const data = await postJSON("/api/stalkerware/assess", { answers });
    renderAssessment(data);
    el("assessment-result").scrollIntoView({ behavior: "smooth" });
  } catch (e) {
    el("assessment-result").innerHTML = `<p class="text-red">Error: ${e.message}</p>`;
  }
});

function renderAssessment(d) {
  let html = riskMeter(d.score, d.level, d.color, d.summary);

  // Progress bar
  html += `<div class="progress-bar-wrap" style="height:8px;margin-bottom:20px">
    <div class="progress-bar-fill" style="width:${d.score}%;background:${d.color}"></div>
  </div>`;

  if (d.triggered_factors?.length) {
    html += `<div class="card">
      <div class="card-title">Triggered Indicators</div>`;
    d.triggered_factors.forEach(f => {
      html += `<div style="padding:10px 0;border-bottom:1px solid var(--border)">
        <div class="flex mb-8">
          <span>${f.icon}</span>
          <span class="bold small">${f.category}</span>
          <span class="sev sev-high" style="margin-left:auto">+${f.weight} pts</span>
        </div>
        <div class="text-dim small">${f.explanation}</div>
      </div>`;
    });
    html += `</div>`;
  }

  if (d.remediation?.length) {
    html += `<div class="card-title mt-16">Remediation Guide</div>`;
    d.remediation.forEach(step => {
      const cls = `rem-${step.priority}`;
      html += `<div class="remediation-step ${cls}">
        <div class="rem-priority" style="color:${priorityColor(step.priority)}">${step.priority}</div>
        <div class="rem-title">${step.title}</div>
        <div class="rem-desc">${step.description}</div>
        ${step.ios    ? `<div class="rem-platform">🍎 iOS: ${step.ios}</div>` : ""}
        ${step.android ? `<div class="rem-platform" style="color:var(--green)">🤖 Android: ${step.android}</div>` : ""}
        ${step.resources ? `<ul style="margin-top:8px;padding-left:16px">${step.resources.map(r=>`<li class="small text-dim">${r}</li>`).join("")}</ul>` : ""}
      </div>`;
    });
  }

  el("assessment-result").innerHTML = html;
}

function priorityColor(p) {
  return { IMMEDIATE:"var(--red)", HIGH:"var(--orange)", ONGOING:"var(--cyan)", SAFETY:"#c084fc" }[p] || "var(--text)";
}


/* ═══════════════════════════════════════════════════════
   MODULE 5 — WebRTC Leak Test
   ═══════════════════════════════════════════════════════ */
async function initWebRTC() {
  loading("webrtc-result", "Initialising WebRTC peer connection to discover IPs…");

  const discoveredIPs = new Set();

  async function gatherIPs() {
    return new Promise(resolve => {
      const pc = new RTCPeerConnection({ iceServers: [
        { urls: "stun:stun.l.google.com:19302" },
        { urls: "stun:stun1.l.google.com:19302" },
        { urls: "stun:stun.cloudflare.com:3478" },
      ]});
      pc.createDataChannel("");
      pc.onicecandidate = e => {
        if (!e.candidate) { pc.close(); resolve(); return; }
        const sdp = e.candidate.candidate;
        const ipRe = /([0-9]{1,3}(\.[0-9]{1,3}){3}|[a-f0-9]{1,4}(:[a-f0-9]{0,4}){2,7})/gi;
        let m;
        while ((m = ipRe.exec(sdp)) !== null) {
          const ip = m[1];
          if (!ip.endsWith(".local") && ip !== "0.0.0.0") {
            discoveredIPs.add(ip);
          }
        }
      };
      pc.createOffer().then(o => pc.setLocalDescription(o));
      setTimeout(resolve, 5000);
    });
  }

  try {
    await gatherIPs();
    const data = await postJSON("/api/webrtc/report", {
      discovered_ips: [...discoveredIPs],
    });
    renderWebRTC(data, discoveredIPs);
  } catch (e) {
    el("webrtc-result").innerHTML = `<p class="text-red">Error: ${e.message}</p>`;
  }
}

function renderWebRTC(d, rawIPs) {
  const leaked = d.leak_detected;
  let html = riskMeter(
    leaked ? 90 : (d.webrtc_private_ips?.length ? 30 : 5),
    d.risk_level,
    d.risk_color,
    d.summary
  );

  html += `<div class="card">
    <div class="card-title">IP Discovery Results</div>
    <table class="info-table">
      <tr><td>Server-detected IP</td><td class="text-cyan mono">${d.server_detected_ip}</td></tr>
      <tr><td>WebRTC discovered IPs</td>
        <td>${[...rawIPs].map(ip => {
          const isPrivate = /^(10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[01])\.|127\.|169\.254\.|::1)/.test(ip);
          const isLeaked  = d.leaked_ips?.includes(ip);
          const cls = isLeaked ? "ip-public" : isPrivate ? "ip-private" : "ip-safe";
          return `<span class="ip-chip ${cls}">${isLeaked ? "⚠ " : ""}${ip}</span>`;
        }).join("") || '<span class="text-dim">None discovered</span>'}</td>
      </tr>
      <tr><td>Leaked IPs</td>
          <td>${d.leaked_ips?.length ? d.leaked_ips.map(ip=>`<span class="ip-chip ip-public">⚠ ${ip}</span>`).join("") : '<span class="text-green">None</span>'}</td>
      </tr>
    </table>
  </div>`;

  html += `<div class="card">
    <div class="card-title">How WebRTC Leaks Work</div>
    <p class="small text-dim" style="line-height:1.8">${d.technical_detail?.what_is_webrtc || ""}</p>
    <p class="small text-dim mt-8" style="line-height:1.8">${d.technical_detail?.why_vpns_fail || ""}</p>
  </div>`;

  if (d.remediation?.length) {
    html += `<div class="card">
      <div class="card-title">How to Fix This</div>
      <ul style="padding-left:16px;line-height:2.2">
        ${d.remediation.map(r => `<li class="small">${r}</li>`).join("")}
      </ul>
    </div>`;
  }

  el("webrtc-result").innerHTML = html;
}

el("btn-retest-webrtc")?.addEventListener("click", () => {
  el("panel-webrtc").dataset.loaded = "1";
  initWebRTC();
});


/* ═══════════════════════════════════════════════════════
   MODULE 6 — DNS Leak Test
   ═══════════════════════════════════════════════════════ */
async function runDNSLeak() {
  loading("dns-result", "Probing DNS resolvers via multiple DoH endpoints…");
  try {
    const data = await fetch("/api/dns/check").then(r => r.json());
    renderDNS(data);
  } catch (e) {
    el("dns-result").innerHTML = `<p class="text-red">Error: ${e.message}</p>`;
  }
}

function renderDNS(d) {
  let html = riskMeter(
    d.isp_leak_detected ? 80 : 10,
    d.risk_level,
    d.risk_color,
    d.explanation
  );

  html += `<div class="card">
    <div class="card-title">Detected DNS Resolvers</div>`;

  if (d.resolvers_detected?.length) {
    d.resolvers_detected.forEach(r => {
      const isSecure = r.is_known_secure;
      const isISP    = r.is_isp;
      html += `<div class="resolver-row">
        <span class="resolver-ip">${r.ip}</span>
        <span class="resolver-name">${r.name}</span>
        <span class="resolver-provider">${r.provider}</span>
        <span class="resolver-status">${
          isSecure ? '<span class="sev sev-low">SECURE</span>' :
          isISP    ? '<span class="sev sev-critical">ISP</span>' :
                     '<span class="sev sev-medium">UNKNOWN</span>'
        }</span>
      </div>`;
      if (r.note) html += `<p class="small text-dim" style="padding:0 12px 8px">${r.note}</p>`;
    });
  } else {
    html += `<p class="text-dim small">No resolvers detected.</p>`;
  }
  html += `</div>`;

  html += `<div class="card">
    <div class="card-title">How DNS Leaks Affect You</div>
    <p class="small text-dim" style="line-height:1.8">${d.how_dns_works}</p>
  </div>`;

  if (d.recommendations?.length) {
    html += `<div class="card">
      <div class="card-title">Recommendations</div>`;
    d.recommendations.forEach(rec => {
      html += `<div style="padding:10px 0;border-bottom:1px solid var(--border)">
        <div class="bold small mb-8">${rec.title}</div>
        <div class="text-dim small">${rec.description}</div>
      </div>`;
    });
    html += `</div>`;
  }

  if (d.secure_dns_options?.length) {
    html += `<div class="card">
      <div class="card-title">Recommended Secure DNS Providers</div>
      <div class="grid-2">`;
    d.secure_dns_options.forEach(opt => {
      html += `<div class="tracking-card">
        <div class="tracking-card-header">
          <span class="tracking-name">${opt.name}</span>
          <span class="tracking-accuracy mono">${opt.ip}</span>
        </div>
        <div class="tracking-desc text-dim small">${opt.privacy}</div>
        <div class="rem-platform mt-8">${opt.doh}</div>
      </div>`;
    });
    html += `</div></div>`;
  }

  el("dns-result").innerHTML = html;
}

el("btn-retest-dns")?.addEventListener("click", () => {
  el("panel-dns").dataset.loaded = "1";
  runDNSLeak();
});


/* ═══════════════════════════════════════════════════════
   MODULE 7 — Threat Intel Newsfeed
   ═══════════════════════════════════════════════════════ */
let _allArticles = [];
let _activeFilter = "all";

async function loadThreatFeed() {
  loading("feed-container", "Fetching live threat intelligence feeds…");
  try {
    const data = await fetch("/api/threats/feed?limit=40").then(r => r.json());
    _allArticles = data.articles || [];
    renderFeedStats(data.stats);
    renderFeed(_allArticles);
    el("btn-refresh-feed")?.classList.remove("hidden");
  } catch (e) {
    el("feed-container").innerHTML = `<p class="text-red">Error fetching feeds: ${e.message}</p>`;
  }
}

function renderFeedStats(stats) {
  if (!stats) return;
  el("feed-stats").innerHTML = `
    <div class="stat-chip">
      <div class="num text-red">${stats.critical || 0}</div>
      <div class="lbl">Critical</div>
    </div>
    <div class="stat-chip">
      <div class="num text-orange">${stats.high || 0}</div>
      <div class="lbl">High</div>
    </div>
    <div class="stat-chip">
      <div class="num text-cyan">${stats.sources_online || 0}/${stats.sources_total || 0}</div>
      <div class="lbl">Sources</div>
    </div>
    <div class="stat-chip">
      <div class="num text-green">${_allArticles.length}</div>
      <div class="lbl">Articles</div>
    </div>`;
}

function renderFeed(articles) {
  if (!articles.length) {
    el("feed-container").innerHTML = `<p class="text-dim">No articles to display.</p>`;
    return;
  }

  el("feed-container").innerHTML = articles.map(a => {
    const sevBorderCls = `sev-${a.severity}-border`;
    return `
    <div class="article-card ${sevBorderCls}" onclick="window.open('${a.url}','_blank')">
      <div class="article-meta">
        <span class="article-source">${a.source}</span>
        ${sevBadge(a.severity)}
        <span class="article-date">${fmtDate(a.published)}</span>
      </div>
      <div class="article-title">${a.title}</div>
      ${a.summary ? `<div class="article-summary">${a.summary}</div>` : ""}
      ${a.tags?.length ? `<div class="article-tags">${a.tags.map(t=>`<span class="article-tag">${t}</span>`).join("")}</div>` : ""}
    </div>`;
  }).join("");
}

qsa(".feed-filter-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    qsa(".feed-filter-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    _activeFilter = btn.dataset.filter;
    const filtered = _activeFilter === "all"
      ? _allArticles
      : _allArticles.filter(a =>
          a.severity === _activeFilter ||
          a.tags?.some(t => t.toLowerCase() === _activeFilter)
        );
    renderFeed(filtered);
  });
});

el("btn-refresh-feed")?.addEventListener("click", () => {
  _activeFilter = "all";
  qsa(".feed-filter-btn").forEach(b => b.classList.remove("active"));
  qs('.feed-filter-btn[data-filter="all"]')?.classList.add("active");
  loadThreatFeed();
});

/* ── Dashboard panel — run IP lookup on load ── */
window.addEventListener("DOMContentLoaded", async () => {
  try {
    const ip = await fetch("/api/location/ip").then(r => r.json());
    const el_ip = el("dash-ip");
    if (el_ip) el_ip.textContent = ip.ip || ip.error || "—";
    const el_city = el("dash-city");
    if (el_city) el_city.textContent = ip.city ? `${ip.city}, ${ip.country_name || ip.country || ""}` : "—";
    const el_isp = el("dash-isp");
    if (el_isp) el_isp.textContent = ip.org || "—";
  } catch {}
});
