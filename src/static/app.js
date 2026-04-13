// Premium frontend app: data fetch, charts, token handling

const API_BASE = window.location.origin;

const API = {
  health: '/api/status',
  activation: '/neuralfort/activation-status',
  anomalies: '/neuralfort/anomalies',
  healing: '/neuralfort/healing-actions',
  predict: '/api/predict',
  copilot: '/neuralfort/copilot/chat',
  projectInfo: '/api/project/info',
  projectModels: '/api/project/models',
  projectArtifacts: '/api/project/artifacts',
  projectRequirements: '/api/project/requirements',
};

const state = {
  token: localStorage.getItem('ss_token') || '',
  threatPollHandle: null,
  threatMonitorHandle: null,
  charts: {},
  seedInProgress: false,
};

const SEED_KEY = 'ss_seeded_v1';

function setToken(token) {
  state.token = token || '';
  if (state.token) localStorage.setItem('ss_token', state.token);
  else localStorage.removeItem('ss_token');
}

async function initAuth() {
  if (!state.token) {
    try {
      const resp = await fetchJSON('/api/dev-token');
      if (resp && resp.token) {
        setToken(resp.token);
        toast('Dev token acquired');
      }
    } catch {}
  }
}

async function fetchJSON(url, opts = {}) {
  const absoluteUrl = /^https?:\/\//i.test(url) ? url : `${API_BASE}${url.startsWith('/') ? url : `/${url}`}`;
  const baseHeaders = { 'Content-Type': 'application/json' };
  if (state.token) baseHeaders['Authorization'] = `Bearer ${state.token}`;
  const headers = Object.assign(baseHeaders, opts.headers || {});
  const res = await fetch(absoluteUrl, { ...opts, headers });
  if (res.status === 401 && !url.includes('/api/dev-token')) {
    try {
      const resp = await fetch(`${API_BASE}/api/dev-token`, { headers: { 'Content-Type': 'application/json' } });
      if (resp.ok) {
        const data = await resp.json();
        if (data && data.token) setToken(data.token);
      }
    } catch {}
    const retryHeaders = { 'Content-Type': 'application/json' };
    if (state.token) retryHeaders['Authorization'] = `Bearer ${state.token}`;
    const retry = await fetch(absoluteUrl, { ...opts, headers: Object.assign(retryHeaders, opts.headers || {}) });
    if (!retry.ok) throw new Error(`HTTP ${retry.status}: ${await retry.text()}`);
    const data = await retry.json();
    console.log('[SentientShield] API', absoluteUrl, data);
    return data;
  }
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
  const data = await res.json();
  console.log('[SentientShield] API', absoluteUrl, data);
  return data;
}

function toast(msg, timeout = 3000) {
  const el = document.getElementById('toast');
  if (!el) return;
  el.textContent = msg;
  el.classList.add('show');
  setTimeout(() => el.classList.remove('show'), timeout);
}

function setChip(id, text, status = 'ok') {
  const el = document.getElementById(id);
  if (!el) return;
  el.className = `chip ${status}`;
  el.innerHTML = `<span class="dot"></span>${text}`;
}

function getPageType() {
  const b = document.body;
  return (b && b.dataset && b.dataset.page) ? b.dataset.page : 'overview';
}

async function loadCoreStatus() {
  try {
    const health = await fetchJSON(API.health);
    const ts = health.server_time || health.timestamp || health.last_updated;
    const healthText = ts ? `Healthy • ${new Date(ts).toLocaleString()}` : 'Healthy';
    setChip('healthChip', healthText, 'ok');
    setChip('headerHealthChip', healthText, 'ok');
  } catch {
    setChip('healthChip', 'Unreachable', 'bad');
    setChip('headerHealthChip', 'Unreachable', 'bad');
  }
  try {
    const act = await fetchJSON(API.activation);
    const active = (act && (act.is_activated || act.activated || act.active || act.status === 'active')) ? true : false;
    const actText = active ? 'Activated' : 'Inactive';
    const status = active ? 'ok' : 'warn';
    setChip('activationChip', actText, status);
    setChip('headerActivationChip', actText, status);
  } catch {
    setChip('activationChip', 'Unknown', 'warn');
    setChip('headerActivationChip', 'Unknown', 'warn');
  }
}

async function loadOverview() {
  // Live project overview sections
  await initAuth();
  try {
    const info = await fetchJSON(API.projectInfo);
    const nameEl = document.getElementById('projName');
    const verEl = document.getElementById('projVersion');
    const descEl = document.getElementById('projDesc');
    const modelEl = document.getElementById('projModel');
    const metricsEl = document.getElementById('projMetrics');
    const classesEl = document.getElementById('projClasses');
    const trainedEl = document.getElementById('projLastTrained');
    if (nameEl) nameEl.textContent = info.name || '—';
    if (verEl) verEl.textContent = info.version || '—';
    if (descEl) descEl.textContent = info.description || '—';
    if (modelEl) modelEl.textContent = info.model?.best_model || '—';
    if (classesEl) classesEl.textContent = (info.model?.label_classes || []).join(', ') || '—';
    if (trainedEl) trainedEl.textContent = info.model?.last_trained_at || '—';
    if (metricsEl) metricsEl.textContent = info.model?.metrics ? JSON.stringify(info.model.metrics) : '—';
    // Update metric bars if available
    updateMetricsBars(info.model?.metrics || null);
  } catch (e) {
    const ids = ['projName','projVersion','projDesc','projModel','projMetrics','projClasses','projLastTrained'];
    ids.forEach(id => { const el = document.getElementById(id); if (el) el.textContent = 'Unauthorized or unavailable'; });
    updateMetricsBars(null);
  }

  try {
    const models = await fetchJSON(API.projectModels);
    const preEl = document.getElementById('projPreproc');
    const candEl = document.getElementById('projCandidates');
    if (preEl) preEl.innerHTML = (models.preprocessing || []).map(p => `<li>${p}</li>`).join('') || '<li>—</li>';
    if (candEl) candEl.innerHTML = (models.candidates || []).map(c => `<li>${c.name} (${c.package}, ${c.type})</li>`).join('') || '<li>—</li>';
  } catch (e) {
    const preEl = document.getElementById('projPreproc');
    const candEl = document.getElementById('projCandidates');
    if (preEl) preEl.innerHTML = '<li>Unauthorized or unavailable</li>';
    if (candEl) candEl.innerHTML = '<li>Unauthorized or unavailable</li>';
  }

  try {
    const arts = await fetchJSON(API.projectArtifacts);
    const listEl = document.getElementById('projArtifactsList');
    if (listEl) {
      const items = (arts.artifacts || []).map(a => `<div class="item"><div class="badge">${a.exists ? 'OK' : 'Missing'}</div><div>${a.file}</div><div>${a.size_bytes ?? '—'}</div></div>`);
      listEl.innerHTML = items.join('') || '<div class="item"><div class="badge">No data</div><div></div><div></div></div>';
    }
  } catch (e) {
    const listEl = document.getElementById('projArtifactsList');
    if (listEl) listEl.innerHTML = '<div class="item"><div class="badge">Unauthorized or unavailable</div><div></div><div></div></div>';
  }

  try {
    const req = await fetchJSON(API.projectRequirements);
    const pkgEl = document.getElementById('projPackages');
    if (pkgEl) pkgEl.innerHTML = (req.packages || []).map(p => `<li>${p}</li>`).join('') || '<li>—</li>';
  } catch (e) {
    const pkgEl = document.getElementById('projPackages');
    if (pkgEl) pkgEl.innerHTML = '<li>Unauthorized or unavailable</li>';
  }
}

function setText(id, text) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = text;
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function randInt(min, max) {
  const a = Math.ceil(min);
  const b = Math.floor(max);
  return Math.floor(Math.random() * (b - a + 1)) + a;
}

function setMetricNumberSmooth(id, target, duration = 900) {
  const el = document.getElementById(id);
  if (!el) return;
  const cur = Number(String(el.textContent || '').replace(/[^\d.-]/g, ''));
  const next = Number(target);
  if (!Number.isFinite(next)) return;
  if (!Number.isFinite(cur)) {
    el.textContent = String(next);
    return;
  }
  if (cur === next) return;
  const start = performance.now();
  const from = cur;
  const to = next;
  const step = (t) => {
    const p = Math.min(1, (t - start) / Math.max(1, duration));
    const v = Math.round(from + (to - from) * p);
    el.textContent = String(v);
    if (p < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

function renderWaitingThreatFeed() {
  setText('metricAlerts', '—');
  setText('metricCritical', '—');
  setText('metricRisk', '—');
  const alertsEl = document.getElementById('alertsList');
  if (alertsEl) {
    alertsEl.innerHTML = '<div class="card" style="padding:12px;">Waiting for threat intelligence feed</div>';
  }
  const mitreBody = document.querySelector('#mitreTable tbody');
  if (mitreBody) {
    mitreBody.innerHTML = '<tr><td colspan="3">Waiting for threat intelligence feed</td></tr>';
  }
  renderThreatMonitorNoData();
}

function renderThreatMonitorNoData() {
  const tbody = document.getElementById('threatTableBody');
  if (!tbody) return;
  tbody.innerHTML = '<tr><td colspan="5">No threats detected yet (waiting for live feed)</td></tr>';
}

function renderThreatMonitorRows(items) {
  const tbody = document.getElementById('threatTableBody');
  if (!tbody) return;
  if (!items || !items.length) {
    renderThreatMonitorNoData();
    return;
  }
  tbody.innerHTML = items.slice(0, 20).map(it => {
    const ts = it.ts ? new Date(it.ts).toLocaleString() : '—';
    const thr = it.threat_type ?? '—';
    const sev = it.severity ?? '—';
    const risk = it.risk != null ? Number(it.risk).toFixed(2) : '—';
    return `<tr>
      <td>${ts}</td>
      <td>${thr}</td>
      <td>${sev}</td>
      <td>${risk}</td>
      <td>Investigate</td>
    </tr>`;
  }).join('');
}

async function loadThreatMonitorOnce() {
  await initAuth();
  try {
    const resp = await fetchJSON('/api/logs/recent?limit=20');
    console.log('[SentientShield] threatMonitor', resp);
    const items = resp?.items || [];
    renderThreatMonitorRows(items);
  } catch (e) {
    console.log('[SentientShield] threatMonitor error', e);
    renderThreatMonitorNoData();
  }
}

function startThreatMonitorPolling() {
  if (state.threatMonitorHandle) return;
  loadThreatMonitorOnce();
  state.threatMonitorHandle = setInterval(loadThreatMonitorOnce, 10000);
}

async function seedInitialEventsOnce() {
  if (localStorage.getItem(SEED_KEY) === '1') return false;
  if (state.seedInProgress) return false;
  state.seedInProgress = true;
  await initAuth();

  const samples = [
    "Brute force login attempt from 185.220.101.45",
    "SQL injection attempt using UNION SELECT",
    "XSS attack detected <script>alert(1)</script>",
    "Botnet traffic from 45.148.10.121",
  ];

  try {
    const results = [];
    for (let i = 0; i < Math.min(3, samples.length); i++) {
      const message = samples[i];
      const r = await fetchJSON('/api/logs/pipeline/run', {
        method: 'POST',
        body: JSON.stringify({ message, ingest: true, report: true }),
      });
      results.push(r);
      loadThreatDashboardOnce();
      loadThreatMonitorOnce();
      if (i < 2) await sleep(randInt(10000, 15000));
    }
    console.log('[SentientShield] seed results', results);
    localStorage.setItem(SEED_KEY, '1');
    loadThreatDashboardOnce();
    loadThreatMonitorOnce();
    return true;
  } catch (e) {
    console.log('[SentientShield] seed error', e);
    return false;
  } finally {
    state.seedInProgress = false;
  }
}

function logNoData(name, items) {
  if (!items || !items.length) console.log('NO DATA FROM API', name);
}

function updateRiskGaugeValue(avgRisk) {
  const numeric = Number(avgRisk);
  if (Number.isNaN(numeric)) return;
  const pct = Math.max(0, Math.min(100, Math.round(numeric * 100)));
  if (typeof window.updateRiskGauge === 'function') {
    window.updateRiskGauge(pct);
    return;
  }
  const circle = document.getElementById('riskGaugeCircle');
  const text = document.getElementById('metricRisk');
  if (!circle || !text) return;
  const radius = circle.r.baseVal.value;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (pct / 100) * circumference;
  circle.style.strokeDasharray = `${circumference} ${circumference}`;
  circle.style.strokeDashoffset = offset;
  text.textContent = String(pct);
}

function ensureChart(key, canvasId, configFactory) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || typeof Chart === 'undefined') return null;
  if (state.charts[key]) return state.charts[key];
  const ctx = canvas.getContext('2d');
  const config = configFactory();
  state.charts[key] = new Chart(ctx, config);
  return state.charts[key];
}

function updateChart(key, canvasId, labels, datasetLabel, values, type = 'bar') {
  const hasScales = type !== 'doughnut' && type !== 'pie';
  const chart = ensureChart(key, canvasId, () => ({
    type,
    data: { labels: [], datasets: [{ label: datasetLabel, data: [], backgroundColor: '#4f7cff', borderColor: '#4f7cff' }] },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      ...(hasScales ? { scales: { x: { grid: { display: false } }, y: { beginAtZero: true } } } : {}),
    },
  }));
  if (!chart) return;
  const curLabels = chart.data.labels || [];
  const curData = chart.data.datasets[0].data || [];
  const idxByLabel = new Map(curLabels.map((l, i) => [l, i]));
  for (let i = 0; i < labels.length; i++) {
    const l = labels[i];
    const v = values[i];
    if (idxByLabel.has(l)) {
      curData[idxByLabel.get(l)] = v;
    } else {
      curLabels.push(l);
      curData.push(v);
      idxByLabel.set(l, curLabels.length - 1);
    }
  }
  chart.data.labels = curLabels;
  chart.data.datasets[0].label = datasetLabel;
  chart.data.datasets[0].data = curData;
  chart.update();
}

function updateLineChart(key, canvasId, labels, datasetLabel, values) {
  const chart = ensureChart(key, canvasId, () => ({
    type: 'line',
    data: { labels: [], datasets: [{ label: datasetLabel, data: [], borderColor: '#4f7cff', backgroundColor: 'rgba(79,124,255,0.15)', tension: 0.25, fill: true }] },
    options: { responsive: true, plugins: { legend: { display: false } }, scales: { x: { grid: { display: false } }, y: { beginAtZero: true } } },
  }));
  if (!chart) return;
  const curLabels = chart.data.labels || [];
  const curData = chart.data.datasets[0].data || [];
  const idxByLabel = new Map(curLabels.map((l, i) => [l, i]));
  for (let i = 0; i < labels.length; i++) {
    const l = labels[i];
    const v = values[i];
    if (idxByLabel.has(l)) {
      curData[idxByLabel.get(l)] = v;
    } else {
      curLabels.push(l);
      curData.push(v);
      idxByLabel.set(l, curLabels.length - 1);
    }
  }
  const maxPoints = 60;
  if (curLabels.length > maxPoints) {
    const extra = curLabels.length - maxPoints;
    curLabels.splice(0, extra);
    curData.splice(0, extra);
  }
  chart.data.labels = curLabels;
  chart.data.datasets[0].label = datasetLabel;
  chart.data.datasets[0].data = curData;
  chart.update();
}

function updateMitreTable(items) {
  const tbody = document.querySelector('#mitreTable tbody');
  if (!tbody) return;
  if (!items || !items.length) {
    tbody.innerHTML = '<tr><td colspan="3">Waiting for threat intelligence feed</td></tr>';
    return;
  }
  tbody.innerHTML = items.slice(0, 20).map(it => {
    const tactic = it.tactic ?? '—';
    const tech = it.technique_id ?? '—';
    const count = it.count ?? 0;
    return `<tr><td>${tactic}</td><td>${tech}</td><td>${count}</td></tr>`;
  }).join('');
}

function updateAlertsList(items) {
  const el = document.getElementById('alertsList');
  if (!el) return;
  if (!items || !items.length) {
    el.innerHTML = '<div class="card" style="padding:12px;">Waiting for threat intelligence feed</div>';
    return;
  }
  el.innerHTML = items.slice(0, 15).map(it => {
    const ts = it.ts ? new Date(it.ts).toLocaleString() : '—';
    const sev = it.severity || '—';
    const thr = it.threat_type || '—';
    const msg = it.message || '';
    return `<div class="card" style="padding:12px;">
      <div style="display:flex; justify-content:space-between; gap:10px;">
        <div><strong>${sev.toUpperCase()}</strong> • ${thr}</div>
        <div style="color: var(--muted); font-size: 0.85rem;">${ts}</div>
      </div>
      <div style="margin-top:8px; color: var(--muted);">${msg}</div>
    </div>`;
  }).join('');
}

async function loadThreatDashboardOnce() {
  await initAuth();

  try {
    const [
      riskGauge,
      mitreDist,
      riskTrends,
      attackFreq,
      mitreTable,
      recentEvents,
    ] = await Promise.all([
      fetchJSON('/api/logs/metrics/risk-gauge'),
      fetchJSON('/api/logs/trends/mitre-distribution?limit=10'),
      fetchJSON('/api/logs/trends/risk-trends?bucket=day&limit=14'),
      fetchJSON('/api/logs/trends/frequency?bucket=hour&limit=24'),
      fetchJSON('/api/logs/mitre-table?limit=20'),
      fetchJSON('/api/logs/events/recent?limit=25'),
    ]);

    const avgRisk = Number(riskGauge?.avg ?? 0);

    const recentItems = recentEvents?.items || [];
    const today = new Date().toISOString().slice(0, 10);
    const totalCount = recentItems.filter(e => (e.ts || '').startsWith(today)).length;
    const criticalCount = recentItems.filter(e => (e.ts || '').startsWith(today) && String(e.severity || '').toLowerCase() === 'critical').length;
    setMetricNumberSmooth('metricAlerts', totalCount);
    setMetricNumberSmooth('metricCritical', criticalCount);
    updateRiskGaugeValue(avgRisk);

    if (!recentItems.length) {
      renderWaitingThreatFeed();
      await seedInitialEventsOnce();
    }

    const freqItems = attackFreq?.items || [];
    logNoData('/api/logs/trends/frequency', freqItems);
    if (freqItems.length) {
      updateLineChart(
        'attackTrend',
        'chartAttackTrend',
        freqItems.map(i => i.time || ''),
        'Alerts',
        freqItems.map(i => Number(i.count || 0))
      );
    }

    const mitreItems = mitreDist?.items || [];
    logNoData('/api/logs/trends/mitre-distribution', mitreItems);
    if (mitreItems.length) {
      updateChart(
        'mitrePie',
        'chartMitrePie',
        mitreItems.map(i => i.technique_id || '—'),
        'MITRE Techniques',
        mitreItems.map(i => Number(i.count || 0)),
        'doughnut'
      );
    }

    const riskItems = riskTrends?.items || [];
    logNoData('/api/logs/trends/risk-trends', riskItems);
    if (riskItems.length) {
      updateLineChart(
        'riskTrend',
        'riskTrendChart',
        riskItems.map(i => i.time || ''),
        'Avg Risk',
        riskItems.map(i => Math.round(Number(i.avg_risk || 0) * 100) / 100)
      );
    }

    updateMitreTable(mitreTable?.items || []);
    updateAlertsList(recentEvents?.items || []);
  } catch (e) {
    console.log('[SentientShield] dashboard poll error', e);
    renderWaitingThreatFeed();
    await seedInitialEventsOnce();
  }
}

function startThreatPolling() {
  if (state.threatPollHandle) return;
  loadThreatDashboardOnce();
  state.threatPollHandle = setInterval(loadThreatDashboardOnce, 10000);
}

async function loadLists() {
  try {
    const anomaliesResp = await fetchJSON(API.anomalies);
    const anomalies = anomaliesResp?.recent_anomalies || anomaliesResp || [];
    renderList('anomalyList', anomalies, 'severity', 'timestamp');
    renderAnomalyChart(anomalies);
  } catch (e) {
    renderList('anomalyList', [], 'severity', 'timestamp');
  }
  try {
    const healingResp = await fetchJSON(API.healing);
    const healing = healingResp?.recent_actions || healingResp || [];
    renderList('healingList', healing, 'action_type', 'timestamp');
  } catch (e) {
    renderList('healingList', [], 'action_type', 'timestamp');
  }
  try {
    const llmResp = await fetchJSON('/neuralfort/llm-insights');
    const insights = llmResp?.insights?.key_findings || [];
    renderSimpleList('llmList', insights);
  } catch (e) {
    renderSimpleList('llmList', []);
  }
}

function renderList(id, items, keyA, keyB) {
  const el = document.getElementById(id);
  if (!el) return;
  if (!items.length) {
    el.innerHTML = '<div class="item"><div class="badge">No data</div><div></div><div></div></div>';
    return;
  }
  el.innerHTML = items.slice(0, 20).map(it => {
    const a = it[keyA] ?? '—';
    const b = it[keyB] ? new Date(it[keyB]).toLocaleString() : '—';
    return `<div class="item"><div class="badge">${a}</div><div>${it.message || it.detail || ''}</div><div>${b}</div></div>`;
  }).join('');
}

function renderAnomalyChart(items) {
  const ctx = document.getElementById('anomalyChart');
  if (!ctx) return;
  const counts = {};
  items.forEach(it => { const k = it.type || 'unknown'; counts[k] = (counts[k] || 0) + 1; });
  const labels = Object.keys(counts);
  const data = labels.map(k => counts[k]);
  if (!labels.length) return;
  // Chart.js via CDN expected in HTML
  new Chart(ctx, {
    type: 'bar',
    data: { labels, datasets: [{ label: 'Anomalies', data, backgroundColor: '#4f7cff' }] },
    options: { responsive: true, plugins: { legend: { display: false } }, scales: { x: { grid: { display: false } }, y: { beginAtZero: true } } }
  });
}

function renderSimpleList(id, items) {
  const el = document.getElementById(id);
  if (!el) return;
  if (!items.length) {
    el.innerHTML = '<div class="item"><div class="badge">No insights</div><div></div><div></div></div>';
    return;
  }
  el.innerHTML = items.slice(0, 10).map(msg => `<div class="item"><div class="badge">Insight</div><div>${msg}</div><div></div></div>`).join('');
}

// Metric bars rendering
function updateMetricsBars(metrics) {
  const pEl = document.getElementById('metricsPrecisionBar');
  const rEl = document.getElementById('metricsRecallBar');
  const fEl = document.getElementById('metricsF1Bar');
  const aEl = document.getElementById('metricsAUCBar');
  const toPct = (v) => {
    if (v == null || isNaN(v)) return 0;
    const x = typeof v === 'string' ? parseFloat(v) : v;
    const pct = x > 1 ? x : x * 100;
    return Math.max(0, Math.min(100, pct));
  };
  if (!metrics) {
    if (pEl) pEl.style.width = '0%';
    if (rEl) rEl.style.width = '0%';
    if (fEl) fEl.style.width = '0%';
    if (aEl) aEl.style.width = '0%';
    return;
  }
  const precision = metrics.precision ?? metrics.Precision ?? null;
  const recall = metrics.recall ?? metrics.Recall ?? null;
  const f1 = metrics.f1 ?? metrics.f1_score ?? metrics.F1 ?? null;
  const auc = metrics.auc ?? metrics.roc_auc ?? metrics.AUC ?? null;
  if (pEl) pEl.style.width = toPct(precision) + '%';
  if (rEl) rEl.style.width = toPct(recall) + '%';
  if (fEl) fEl.style.width = toPct(f1) + '%';
  if (aEl) aEl.style.width = toPct(auc) + '%';
}

async function onPredictSubmit(ev) {
  ev.preventDefault();
  const btn = document.getElementById('predictBtn');
  btn.disabled = true;
  try {
    const form = ev.currentTarget;
    const payload = {
      request_type: form.request_type.value,
      headers: form.headers.value,
      payload_size: Number(form.payload_size.value || 0),
      response_time: Number(form.response_time.value || 0),
      ip_reputation: Number(form.ip_reputation.value || 0),
      url: form.url.value,
      user_agent: form.user_agent.value,
      anomaly_score: Number(form.anomaly_score.value || 0),
    };
    const headers = { 'Content-Type': 'application/json' };
    if (state.token) headers['Authorization'] = `Bearer ${state.token}`;
    const res = await fetchJSON(API.predict, { method: 'POST', body: JSON.stringify(payload), headers });
    renderPrediction(res);
    toast('Prediction completed');
  } catch (e) {
    toast(`Predict error: ${e.message}`);
  } finally {
    btn.disabled = false;
  }
}

function renderPrediction(result) {
  const el = document.getElementById('predictResult');
  if (!el) return;
  if (!result) { el.innerHTML = ''; return; }
  const probs = result.probabilities || {};
  const top = result.predicted_label || '—';
  const model = result.model || '—';
  const conf = result.confidence != null ? `${(result.confidence * 100).toFixed(1)}%` : '—';
  const probList = Object.entries(probs).map(([k, v]) => `<div class="item"><div class="badge">${k}</div><div></div><div>${(v*100).toFixed(1)}%</div></div>`).join('');
  el.innerHTML = `
    <div class="card">
      <h3>Predicted Label</h3>
      <div class="value">${top}</div>
      <div class="subtitle">Model: ${model} • Confidence: ${conf}</div>
    </div>
    <div class="list">${probList || '<div class="item"><div class="badge">No probabilities</div><div></div><div></div></div>'}</div>
  `;
}

function bindEvents() {
  const form = document.getElementById('predictForm');
  if (form) form.addEventListener('submit', onPredictSubmit);
  const tokenInput = document.getElementById('tokenInput');
  const saveTokenBtn = document.getElementById('saveTokenBtn');
  if (tokenInput && saveTokenBtn) {
    tokenInput.value = state.token;
    saveTokenBtn.addEventListener('click', () => {
      setToken(tokenInput.value.trim());
      const ts = document.getElementById('tokenStatus');
      if (ts) ts.textContent = state.token ? 'Token saved' : 'No token saved';
      toast(state.token ? 'Token saved' : 'Token cleared');
    });
  }

  const retrainBtn = document.getElementById('retrainButton');
  if (retrainBtn) {
    retrainBtn.addEventListener('click', triggerRetrain);
  }

  const inferenceBtn = document.getElementById('inferenceButton');
  if (inferenceBtn) {
    inferenceBtn.addEventListener('click', () => {
       const form = document.getElementById('predictForm');
       if (form) {
         // Fill with random test data
         form.request_type.value = Math.random() > 0.5 ? 'POST' : 'GET';
         form.payload_size.value = Math.floor(Math.random() * 5000) + 100;
         form.response_time.value = Math.floor(Math.random() * 1000) + 10;
         form.ip_reputation.value = Math.floor(Math.random() * 100);
         form.url.value = '/api/v1/user/data';
         form.user_agent.value = 'Mozilla/5.0 (TestBot)';
         form.anomaly_score.value = (Math.random()).toFixed(2);
         // Auto submit
         form.dispatchEvent(new Event('submit'));
       }
    });
  }

  // Bind new buttons
  bindButton('pipeBtn', handlePipeline);
  bindButton('socGenBtn', handleSocReport);
  bindButton('logSeverityBtn', () => handleLogAction('classify-severity'));
  bindButton('logTypeBtn', () => handleLogAction('predict-type'));
  bindButton('logFilterBtn', () => handleLogAction('filter-alert'));
  bindButton('logIngestBtn', handleLogIngest);
  bindButton('logSimilarBtn', handleLogSimilar);
  bindButton('logZeroShotBtn', handleLogZeroShot);
  bindButton('refreshAlertsBtn', loadThreatDashboardOnce);
  bindButton('batchProcessBtn', () => handleBatchProcess());
  bindButton('demo9LogsBtn', run9LogsDemo);
}

function bindButton(id, handler) {
  const btn = document.getElementById(id);
  if (btn) btn.addEventListener('click', handler);
}


async function handlePipeline() {
  const log = getValue('pipeLog');
  if (!log) return toast('Please enter a log');
  const asset = getValue('pipeAsset');
  const title = getValue('pipeTitle');
  
  toast('Injecting event…');
  loadThreatDashboardOnce();
  loadThreatMonitorOnce();
  const res = await apiCall('/api/logs/pipeline/run', { 
    message: log, 
    asset_value: parseFloat(asset) || 0.5,
    ingest: true,
    report: true,
    title: title
  });
  console.log('[SentientShield] injection response (pipeline)', res);
  renderJsonResult('pipeResult', res);
  loadThreatDashboardOnce();
  loadThreatMonitorOnce();
}

async function handleSocReport() {
  const raw = getValue('socLogs');
  const title = (getValue('socTitle') || 'SOC Report').trim();
  const lines = String(raw || '')
    .split('\n')
    .map(s => s.trim())
    .filter(Boolean);

  if (!lines.length) {
    toast('Please enter logs');
    return;
  }

  const combined = lines.join('. ').replace(/\s+/g, ' ').trim();
  if (!combined) {
    toast('Please enter logs');
    return;
  }

  const analysis = analyzeLogsForSoc(combined);
  const recommendations = [];
  if (analysis.threats.includes('SQL Injection')) recommendations.push('Add WAF rules and parameterized queries; block UNION/select patterns.');
  if (analysis.threats.includes('Cross-Site Scripting (XSS)')) recommendations.push('Sanitize/encode output; enable CSP; validate inputs server-side.');
  if (analysis.threats.includes('Brute Force / Credential Attack')) recommendations.push('Enable rate limiting, MFA, account lockouts, and IP reputation checks.');
  if (analysis.threats.includes('Botnet / DDoS Activity')) recommendations.push('Enable DDoS protection, autoscaling, and upstream traffic filtering.');
  if (analysis.threats.includes('Suspicious Privileged Access')) recommendations.push('Audit privileged access, enforce least privilege, and rotate credentials.');
  if (analysis.threats.includes('Ransomware Indicators')) recommendations.push('Isolate affected hosts; verify backups; monitor for lateral movement.');
  if (!recommendations.length) recommendations.push('Continue monitoring; enrich indicators and validate alert context.');

  let apiResp = null;
  let apiErr = '';
  try {
    apiResp = await fetchJSON('/api/logs/pipeline/run', {
      method: 'POST',
      body: JSON.stringify({ message: combined, ingest: false, report: true }),
    });
  } catch (e) {
    apiErr = e?.message || String(e);
  }

  console.log('[SentientShield] socReport api response', apiResp);
  if (!apiResp && apiErr) console.log('[SentientShield] socReport api error', apiErr);

  const rawReport = (apiResp && (apiResp.report || apiResp.soc_report)) ? (apiResp.report || apiResp.soc_report) : '';
  if (!rawReport) console.log('NO DATA FROM API', '/api/logs/pipeline/run (soc_report)');

  renderSocReportPanel({
    title,
    summary: `Processed ${lines.length} log line(s). Detected ${analysis.hitsCount} threat signal(s).`,
    threats: analysis.threats,
    mitre: analysis.mitre,
    riskScore: analysis.riskScore,
    recommendations,
    rawReport,
    error: apiErr ? `Report generation failed; showing fallback report. Error: ${apiErr}` : '',
  });
}

async function handleBatchProcess(customLogs = null) {
  const logs = customLogs || getValue('batchLogs');
  if (!logs) return toast('Please enter logs or use demo button');
  const logList = Array.isArray(logs) ? logs : logs.split('\n').filter(l => l.trim());
  
  const btn = document.getElementById('batchProcessBtn');
  const originalText = btn.innerText;
  btn.innerText = 'Triggering Workflow...';
  btn.disabled = true;

  try {
    const res = await apiCall('/api/logs/workflow/batch-process', { logs: logList });
    renderJsonResult('batchResult', res);
    toast('Workflow task triggered successfully');
  } finally {
    btn.innerText = originalText;
    btn.disabled = false;
  }
}

function run9LogsDemo() {
  const sampleLogs = [
    "SELECT * FROM users WHERE id = 1 OR 1=1; --",
    "<script>alert('XSS_ATTACK_DETECTED')</script>",
    "Failed login attempt for user admin from 192.168.1.100 - multiple attempts in 5 seconds",
    "GET /../../../../etc/passwd HTTP/1.1",
    "Your account has been suspended. Click here to verify: http://secure-sentient-shield.com/login",
    "Suspicious outbound connection to 45.23.11.2 port 4444 (Reverse Shell pattern)",
    "System health check: All components operational. Memory usage: 45%",
    "Insider Threat Alert: Unauthorized access to sensitive financial data by user 'marketing_assistant' at 3 AM",
    "Ransomware Activity: Mass file encryption detected on /shared/finance_records. AES key exchange observed to 103.45.12.9"
  ];
  const el = document.getElementById('batchLogs');
  if (el) el.value = sampleLogs.join('\n');
  handleBatchProcess(sampleLogs);
}

async function handleLogAction(action) {
  const log = getValue('logInput');
  if (!log) return toast('Please enter a log');
  const res = await apiCall(`/api/logs/${action}`, { message: log });
  renderJsonResult('logResult', res);
}

async function handleLogIngest() {
   const log = getValue('logInput');
   if (!log) return toast('Please enter a log');
   toast('Injecting event…');
   loadThreatDashboardOnce();
   loadThreatMonitorOnce();
   const res = await apiCall('/api/logs/pipeline/run', { message: log, ingest: true, report: true });
   console.log('[SentientShield] injection response (event)', res);
   renderJsonResult('logResult', res);
   loadThreatDashboardOnce();
   loadThreatMonitorOnce();
}

async function handleLogSimilar() {
   const log = getValue('logInput');
   if (!log) return toast('Please enter a log');
   const res = await apiCall('/api/logs/similar', { query: log });
   renderJsonResult('logResult', res);
}

async function handleLogZeroShot() {
   const log = getValue('logInput');
   const labels = getValue('zsLabels');
   if (!log) return toast('Please enter a log');
   const labelList = labels ? labels.split(',').map(s => s.trim()) : null;
   const res = await apiCall('/api/logs/zero-shot', { message: log, labels: labelList });
   renderJsonResult('logResult', res);
}

function getValue(id) {
  const el = document.getElementById(id);
  return el ? el.value : '';
}

function escapeHtml(s) {
  return String(s ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function analyzeLogsForSoc(logText) {
  const text = String(logText || '');
  const hits = [];

  const rules = [
    { key: 'sql', re: /\b(sql|sqli)\b|union\s+select|or\s+1=1|information_schema|sleep\(\d+\)/i, name: 'SQL Injection', risk: 35, mitre: { id: 'T1190', tactic: 'Initial Access', technique: 'Exploit Public-Facing Application' } },
    { key: 'xss', re: /\b(xss)\b|<script|onerror=|javascript:/i, name: 'Cross-Site Scripting (XSS)', risk: 25, mitre: { id: 'T1059', tactic: 'Execution', technique: 'Command and Scripting Interpreter' } },
    { key: 'brute', re: /\b(brute|credential stuffing|password spray)\b|failed login|login attempt/i, name: 'Brute Force / Credential Attack', risk: 20, mitre: { id: 'T1110', tactic: 'Credential Access', technique: 'Brute Force' } },
    { key: 'botnet', re: /\b(botnet|ddos)\b|high rate requests|traffic spike/i, name: 'Botnet / DDoS Activity', risk: 25, mitre: { id: 'T1498', tactic: 'Impact', technique: 'Network Denial of Service' } },
    { key: 'admin', re: /\b(admin login|privileged|root)\b|suspicious admin/i, name: 'Suspicious Privileged Access', risk: 20, mitre: { id: 'T1078', tactic: 'Defense Evasion', technique: 'Valid Accounts' } },
    { key: 'ransom', re: /\b(ransom|encrypt(ion)?|mass file)\b/i, name: 'Ransomware Indicators', risk: 45, mitre: { id: 'T1486', tactic: 'Impact', technique: 'Data Encrypted for Impact' } },
  ];

  for (const r of rules) {
    if (r.re.test(text)) hits.push(r);
  }

  const threats = hits.map(h => h.name);
  const mitre = [];
  const mitreSeen = new Set();
  for (const h of hits) {
    const k = h.mitre.id;
    if (!mitreSeen.has(k)) {
      mitreSeen.add(k);
      mitre.push(h.mitre);
    }
  }

  let riskScore = 10;
  for (const h of hits) riskScore += h.risk;
  riskScore = Math.max(0, Math.min(100, Math.round(riskScore)));

  const recs = [];
  if (hits.find(h => h.key === 'sql')) recs.push('Add WAF rules and parameterized queries; block UNION/select patterns.');
  if (hits.find(h => h.key === 'xss')) recs.push('Sanitize/encode output; enable CSP; validate inputs server-side.');
  if (hits.find(h => h.key === 'brute')) recs.push('Enable rate limiting, MFA, account lockouts, and IP reputation checks.');
  if (hits.find(h => h.key === 'botnet')) recs.push('Enable DDoS protection, autoscaling, and upstream traffic filtering.');
  if (hits.find(h => h.key === 'admin')) recs.push('Audit privileged access, enforce least privilege, and rotate credentials.');
  if (hits.find(h => h.key === 'ransom')) recs.push('Isolate affected hosts; verify backups; monitor for lateral movement.');
  if (!recs.length) recs.push('Continue monitoring; enrich indicators and validate alert context.');

  return { threats, mitre, riskScore, hitsCount: hits.length };
}

function renderSocReportPanel({ title, summary, threats, mitre, riskScore, recommendations, rawReport, error }) {
  const el = document.getElementById('socResult');
  if (!el) return;

  const threatHtml = threats.length
    ? `<ul>${threats.map(t => `<li>${escapeHtml(t)}</li>`).join('')}</ul>`
    : `<div style="color: var(--muted);">No specific threat keywords detected.</div>`;

  const mitreHtml = mitre.length
    ? `<table class="table" style="margin-top:8px;">
        <thead><tr><th>Technique</th><th>Tactic</th><th>Name</th></tr></thead>
        <tbody>${mitre.map(m => `<tr><td>${escapeHtml(m.id)}</td><td>${escapeHtml(m.tactic)}</td><td>${escapeHtml(m.technique)}</td></tr>`).join('')}</tbody>
      </table>`
    : `<div style="color: var(--muted);">No MITRE mapping available.</div>`;

  const recHtml = recommendations.length
    ? `<ul>${recommendations.map(r => `<li>${escapeHtml(r)}</li>`).join('')}</ul>`
    : '';

  const rawHtml = rawReport
    ? `<div style="margin-top:12px;">
        <h4 style="margin:0 0 6px 0;">Generated Narrative</h4>
        <pre style="white-space: pre-wrap; margin:0;">${escapeHtml(rawReport)}</pre>
      </div>`
    : '';

  const errHtml = error
    ? `<div style="margin-top:12px; color: var(--danger-color);">${escapeHtml(error)}</div>`
    : '';

  el.innerHTML = `
    <div class="card" style="white-space: normal;">
      <h3 style="margin:0 0 8px 0;">${escapeHtml(title || 'SOC Report')}</h3>
      <div style="color: var(--muted); margin-bottom: 10px;">${escapeHtml(summary || '')}</div>
      <h4 style="margin:12px 0 6px 0;">Threats</h4>
      ${threatHtml}
      <h4 style="margin:12px 0 6px 0;">MITRE Mapping</h4>
      ${mitreHtml}
      <h4 style="margin:12px 0 6px 0;">Risk Score</h4>
      <div style="font-size:1.2rem; font-weight:800;">${escapeHtml(riskScore)}</div>
      <h4 style="margin:12px 0 6px 0;">Recommendations</h4>
      ${recHtml}
      ${rawHtml}
      ${errHtml}
    </div>
  `;
}

async function apiCall(url, body) {
   try {
     const headers = { 'Content-Type': 'application/json' };
     if (state.token) headers['Authorization'] = `Bearer ${state.token}`;
     return await fetchJSON(url, { method: 'POST', body: JSON.stringify(body), headers });
   } catch (e) {
     toast(`Error: ${e.message}`);
     return { error: e.message };
   }
}

async function handleChat(text) {
  const typingIndicator = document.getElementById('typingIndicator');
  if (typingIndicator) typingIndicator.style.display = 'block';
  try {
    const res = await fetch(API.copilot, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${state.token}`
      },
      body: JSON.stringify({ message: text })
    });
    const data = await res.json();
    if (typingIndicator) typingIndicator.style.display = 'none';
    
    const botResponse = data.answer || "I'm sorry, I couldn't process that request.";
    if (typeof addChatMessage === 'function') {
      addChatMessage(botResponse, 'bot');
    } else {
      console.log("Bot:", botResponse);
    }
    
    if (data.sources && data.sources.length > 0) {
      console.log("Sources:", data.sources);
    }
    return data;
  } catch (e) {
    if (typingIndicator) typingIndicator.style.display = 'none';
    toast(`Chat error: ${e.message}`);
  }
}

function renderJsonResult(id, data) {
  const el = document.getElementById(id);
  if (!el) return;
  el.innerHTML = `<pre class="code-block" style="max-height: 300px; overflow: auto; background: rgba(0,0,0,0.3); padding: 10px; border-radius: 8px;">${JSON.stringify(data, null, 2)}</pre>`;
}

async function triggerRetrain() {
  const statusEl = document.getElementById('retrainStatus');
  try {
    if (statusEl) statusEl.textContent = 'Running…';
    const res = await fetchJSON('/retrain', { method: 'POST' });
    if (statusEl) statusEl.textContent = 'Completed';
    toast('Retrain triggered');
  } catch (e) {
    if (statusEl) statusEl.textContent = 'Error';
    toast(`Retrain failed: ${e.message}`);
  }
}

function init() {
  const page = getPageType();
  loadCoreStatus();
  if (page === 'overview') {
    loadOverview();
    loadLists();
    bindEvents(); // Added bindEvents call
    seedInitialEventsOnce();
    startThreatPolling();
    startThreatMonitorPolling();
  }
  if (page === 'model') {
    initAuth();
    loadLists();
    bindEvents();
  }
}

document.addEventListener('DOMContentLoaded', init);
