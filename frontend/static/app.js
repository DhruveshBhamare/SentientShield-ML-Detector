// Premium frontend app: data fetch, charts, token handling

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
};

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
  const baseHeaders = { 'Content-Type': 'application/json' };
  if (state.token) baseHeaders['Authorization'] = `Bearer ${state.token}`;
  const headers = Object.assign(baseHeaders, opts.headers || {});
  const res = await fetch(url, { ...opts, headers });
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
  return res.json();
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
  bindButton('riskBtn', handleRiskScore);
  bindButton('pipeBtn', handlePipeline);
  bindButton('cveEnrichBtn', handleCveEnrich);
  bindButton('cveSearchBtn', handleCveSearch);
  bindButton('socGenBtn', handleSocReport);
  bindButton('attckMapBtn', handleAttckMap);
  bindButton('logSeverityBtn', () => handleLogAction('classify-severity'));
  bindButton('logTypeBtn', () => handleLogAction('predict-type'));
  bindButton('logFilterBtn', () => handleLogAction('filter-alert'));
  bindButton('logIngestBtn', handleLogIngest);
  bindButton('logSimilarBtn', handleLogSimilar);
  bindButton('logZeroShotBtn', handleLogZeroShot);
  bindButton('refreshAlertsBtn', loadLists);
  bindButton('refreshTrendsBtn', () => { window.location.reload(); }); // Simple reload for trends for now
}

function bindButton(id, handler) {
  const btn = document.getElementById(id);
  if (btn) btn.addEventListener('click', handler);
}

async function handleRiskScore() {
  const log = getValue('riskLog');
  const asset = getValue('riskAsset');
  if (!log) return toast('Please enter a log line');
  const res = await apiCall('/api/logs/risk-score', { message: log, asset_value: parseFloat(asset) || 0.5 });
  renderJsonResult('riskResult', res);
}

async function handlePipeline() {
  const log = getValue('pipeLog');
  if (!log) return toast('Please enter a log');
  const asset = getValue('pipeAsset');
  const ingest = document.getElementById('pipeIngest')?.checked;
  const soc = document.getElementById('pipeSoc')?.checked;
  const title = getValue('pipeTitle');
  
  const res = await apiCall('/api/logs/pipeline/run', { 
    message: log, 
    asset_value: parseFloat(asset) || 0.5,
    ingest: !!ingest,
    soc_report: !!soc,
    title: title
  });
  renderJsonResult('pipeResult', res);
}

async function handleCveEnrich() {
  const log = getValue('cveLog');
  if (!log) return toast('Please enter a log with CVE');
  const res = await apiCall('/api/logs/cve-enrich', { message: log });
  renderJsonResult('cveResult', res);
}

async function handleCveSearch() {
  const query = getValue('cveQuery');
  if (!query) return toast('Please enter a query');
  const res = await apiCall('/api/logs/cve-search', { query: query });
  renderJsonResult('cveResult', res);
}

async function handleSocReport() {
  const logs = getValue('socLogs');
  if (!logs) return toast('Please enter logs');
  const logList = logs.split('\n').filter(l => l.trim());
  const res = await apiCall('/api/logs/soc-report', { logs: logList, title: getValue('socTitle') });
  const el = document.getElementById('socResult');
  if (el && res.report) {
     el.innerHTML = `<div class="card" style="white-space: pre-wrap;">${res.report}</div>`;
  } else {
     renderJsonResult('socResult', res);
  }
}

async function handleAttckMap() {
  const log = getValue('attckInput');
  if (!log) return toast('Please enter a log');
  const res = await apiCall('/api/logs/attck-map', { message: log });
  renderJsonResult('attckResult', res);
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
   const res = await apiCall('/api/logs/ingest', { logs: [log] });
   renderJsonResult('logResult', res);
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
  }
}

document.addEventListener('DOMContentLoaded', init);
