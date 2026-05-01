// SentientShield Premium SOC App - Modular & Enterprise Grade

const API_BASE = "";
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
  recentLogs: '/api/logs/recent',
  dashboard: '/api/logs/dashboard',
  pipelineRun: '/api/logs/pipeline/run',
  batchProcess: '/api/logs/workflow/batch-process',
  retrain: '/retrain'
};

const state = {
  token: localStorage.getItem('ss_token') || '',
  threatPollHandle: null,
  charts: {},
  currentTab: 'home',
  autoRefresh: true,
  severityFilter: 'all'
};

const SEED_KEY = 'ss_seeded_v1';

// --- Core Auth & Fetch ---

function setToken(token) {
  state.token = token || '';
  if (state.token) localStorage.setItem('ss_token', state.token);
  else localStorage.removeItem('ss_token');
}

async function initAuth() {
  if (!state.token) {
    try {
      const resp = await fetchJSON('/api/dev-token');
      if (resp && resp.token) setToken(resp.token);
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
    await initAuth();
    const retryHeaders = { 'Content-Type': 'application/json' };
    if (state.token) retryHeaders['Authorization'] = `Bearer ${state.token}`;
    const retry = await fetch(absoluteUrl, { ...opts, headers: Object.assign(retryHeaders, opts.headers || {}) });
    return await retry.json();
  }
  
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

// --- UI Helpers ---

function toast(msg, timeout = 3000) {
  const el = document.getElementById('toast');
  if (!el) return;
  el.textContent = msg;
  el.className = 'toast show';
  setTimeout(() => el.className = 'toast', timeout);
}

function typeAI(text, elementId) {
  const el = document.getElementById(elementId);
  if (!el) return;
  el.textContent = '';
  let i = 0;
  const interval = setInterval(() => {
    if (i < text.length) {
      el.textContent += text.charAt(i);
      i++;
    } else {
      clearInterval(interval);
    }
  }, 25);
}

function animateValue(id, start, end, duration = 1000) {
  const obj = document.getElementById(id);
  if (!obj) return;
  let startTimestamp = null;
  const step = (timestamp) => {
    if (!startTimestamp) startTimestamp = timestamp;
    const progress = Math.min((timestamp - startTimestamp) / duration, 1);
    obj.innerHTML = Math.floor(progress * (end - start) + start);
    if (progress < 1) window.requestAnimationFrame(step);
  };
  window.requestAnimationFrame(step);
}

function updateRiskGauge(value) {
  const circle = document.getElementById('riskGaugeCircle');
  const text = document.getElementById('metricRisk');
  if (!circle || !text) return;
  
  const radius = circle.r.baseVal.value;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (value / 100) * circumference;
  
  circle.style.strokeDasharray = `${circumference} ${circumference}`;
  circle.style.strokeDashoffset = offset;
  
  animateValue('metricRisk', parseInt(text.innerText) || 0, value, 1500);
}

// --- Data Loading ---

async function loadCoreStatus() {
  try {
    const health = await fetchJSON(API.health);
    const healthText = health.status === 'ok' ? 'System Online' : 'System Issues';
    const chip = document.getElementById('headerHealthChip');
    if (chip) {
      chip.className = `chip ${health.status === 'ok' ? 'ok' : 'bad'}`;
      chip.innerHTML = `<span class="dot"></span>${healthText}`;
    }
  } catch {
    const chip = document.getElementById('headerHealthChip');
    if (chip) {
      chip.className = 'chip bad';
      chip.innerHTML = '<span class="dot"></span>Connection Lost';
    }
  }
}

async function loadThreatDashboard() {
  try {
    const data = await fetchJSON(API.dashboard);
    if (!data) return;

    animateValue('metricAlerts', 0, data.total_alerts || 0);
    animateValue('metricCritical', 0, data.critical_alerts || 0);
    updateRiskGauge(Math.round((data.avg_risk || 0) * 100));

    // Update Trend Chart
    if (data.trends && data.trends.labels) {
      updateLineChart('attackTrend', 'chartAttackTrend', data.trends.labels, 'Risk Level', data.trends.values);
    }

    // Update Summary Pie
    if (data.mitre_summary) {
      const labels = Object.keys(data.mitre_summary);
      const values = Object.values(data.mitre_summary);
      updateChart('mitrePieSummary', 'chartMitrePieSummary', labels, 'Tactics', values, 'doughnut');
    }
  } catch (e) {
    console.error('Dashboard load failed', e);
  }
}

async function loadThreatMonitor() {
  if (!state.autoRefresh && state.currentTab !== 'threats') return;
  
  try {
    const resp = await fetchJSON(`${API.recentLogs}?limit=50`);
    const items = resp?.items || [];
    renderThreatTable(items);
  } catch (e) {
    console.error('Threat monitor load failed', e);
  }
}

function renderThreatTable(items) {
  const tbody = document.getElementById('threatTableBody');
  if (!tbody) return;

  const filtered = items.filter(it => {
    if (state.severityFilter === 'all') return true;
    return (it.severity || '').toLowerCase() === state.severityFilter;
  });

  tbody.innerHTML = filtered.slice(0, 20).map(it => {
    const ts = it.ts ? new Date(it.ts).toLocaleTimeString() : '—';
    const sevClass = (it.severity || 'low').toLowerCase();
    const risk = it.risk != null ? (it.risk * 100).toFixed(0) : '0';
    
    return `<tr>
      <td>${ts}</td>
      <td>${it.threat_type || 'Unknown'}</td>
      <td><span class="badge badge-${sevClass}">${it.severity || 'LOW'}</span></td>
      <td><div style="font-weight:700;">${risk}%</div></td>
      <td><button class="btn btn-secondary btn-sm" onclick="investigateLog('${it.id}')">Investigate</button></td>
    </tr>`;
  }).join('');
}

async function loadMitreData() {
  try {
    const data = await fetchJSON(API.dashboard);
    if (data.mitre_stats) {
      const labels = Object.keys(data.mitre_stats);
      const values = Object.values(data.mitre_stats);
      updateChart('mitrePieFull', 'chartMitrePie', labels, 'Techniques', values, 'pie');
      
      const tbody = document.querySelector('#mitreTable tbody');
      if (tbody) {
        tbody.innerHTML = data.mitre_details ? data.mitre_details.map(m => `
          <tr>
            <td>${m.tactic}</td>
            <td><code>${m.technique_id}</code></td>
            <td>${m.count}</td>
          </tr>
        `).join('') : '<tr><td colspan="3">No techniques mapped</td></tr>';
      }
    }
  } catch {}
}

// --- Charting ---

function ensureChart(key, canvasId, configFactory) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || typeof Chart === 'undefined') return null;
  if (state.charts[key]) return state.charts[key];
  const ctx = canvas.getContext('2d');
  state.charts[key] = new Chart(ctx, configFactory());
  return state.charts[key];
}

function getChartColors() {
  const isDark = document.body.classList.contains('dark-theme');
  return {
    text: isDark ? '#F0F6FC' : '#111827',
    muted: isDark ? '#8B949E' : '#4B5563',
    grid: isDark ? 'rgba(240, 246, 252, 0.1)' : '#E5E7EB',
    primary: isDark ? '#58A6FF' : '#2563EB',
    secondary: isDark ? '#BC8CFF' : '#7C3AED'
  };
}

function updateChart(key, canvasId, labels, datasetLabel, values, type = 'bar') {
  const colors = getChartColors();
  const chart = ensureChart(key, canvasId, () => ({
    type,
    data: { labels, datasets: [{ label: datasetLabel, data: values, backgroundColor: colors.primary, borderColor: colors.primary }] },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { 
        legend: { display: type === 'doughnut' || type === 'pie', labels: { color: colors.text } },
        tooltip: { backgroundColor: colors.text === '#FFFFFF' ? '#161B22' : '#FFFFFF', titleColor: colors.primary, bodyColor: colors.text }
      },
      scales: type !== 'doughnut' && type !== 'pie' ? {
        x: { grid: { display: false }, ticks: { color: colors.muted } },
        y: { beginAtZero: true, grid: { color: colors.grid }, ticks: { color: colors.muted } }
      } : {}
    }
  }));

  if (chart) {
    chart.data.labels = labels;
    chart.data.datasets[0].data = values;
    chart.update();
  }
}

function updateLineChart(key, canvasId, labels, datasetLabel, values) {
  const colors = getChartColors();
  const chart = ensureChart(key, canvasId, () => ({
    type: 'line',
    data: { labels, datasets: [{ label: datasetLabel, data: values, borderColor: colors.primary, backgroundColor: colors.primary + '20', fill: true, tension: 0.4 }] },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { display: false }, ticks: { color: colors.muted } },
        y: { beginAtZero: true, grid: { color: colors.grid }, ticks: { color: colors.muted } }
      }
    }
  }));

  if (chart) {
    chart.data.labels = labels;
    chart.data.datasets[0].data = values;
    chart.update();
  }
}

// --- Features ---

async function handleSocGenerate() {
  const logs = document.getElementById('socLogs').value;
  const title = document.getElementById('socTitle').value || 'SOC Analysis Report';
  if (!logs) return toast('Please enter logs');

  const btn = document.getElementById('socGenBtn');
  btn.disabled = true;
  btn.textContent = 'Generating...';

  try {
    const res = await fetchJSON(API.pipelineRun, {
      method: 'POST',
      body: JSON.stringify({ message: logs, ingest: false, report: true })
    });
    
    const resultEl = document.getElementById('socResult');
    const report = res.report || res.soc_report || 'No report generated.';
    
    resultEl.innerHTML = `
      <div class="report-preview">
        <h4>${title}</h4>
        <div style="font-size: 0.875rem; white-space: pre-wrap; margin-top: 1rem;">${report}</div>
      </div>
    `;
    document.getElementById('reportActions').style.display = 'flex';
  } catch (e) {
    toast('Report generation failed');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Generate Report';
  }
}

async function handleBatchProcess() {
  const logs = document.getElementById('batchLogs').value;
  if (!logs) return toast('Please enter logs');
  
  const logList = logs.split('\n').filter(l => l.trim());
  const btn = document.getElementById('batchProcessBtn');
  btn.disabled = true;
  
  try {
    const res = await fetchJSON(API.batchProcess, {
      method: 'POST',
      body: JSON.stringify({ logs: logList })
    });
    document.getElementById('batchResult').innerHTML = `<pre style="font-size: 0.75rem; background: #f0f0f0; padding: 10px;">${JSON.stringify(res, null, 2)}</pre>`;
    toast('Batch processing complete');
  } catch (e) {
    toast('Batch processing failed');
  } finally {
    btn.disabled = false;
  }
}

async function handleChat() {
  const input = document.getElementById('chatInput');
  const text = input.value.trim();
  if (!text) return;

  addChatMessage(text, 'user');
  input.value = '';
  
  const indicator = document.getElementById('typingIndicator');
  indicator.style.display = 'block';

  try {
    const res = await fetchJSON(API.copilot, {
      method: 'POST',
      body: JSON.stringify({ message: text })
    });
    indicator.style.display = 'none';
    addChatMessage(res.answer || "I'm sorry, I couldn't process that request.", 'bot');
  } catch (e) {
    indicator.style.display = 'none';
    toast('Chat connection error');
  }
}

function addChatMessage(text, sender) {
  const container = document.getElementById('chatResult');
  const bubble = document.createElement('div');
  bubble.className = `chat-bubble ${sender}`;
  bubble.textContent = text;
  container.appendChild(bubble);
  container.scrollTop = container.scrollHeight;
}

function investigateLog(id) {
  toast(`Investigating log entry: ${id}`);
  // In a real app, this would open a detail modal or tab
}

async function triggerRetrain() {
  const statusEl = document.getElementById('retrainStatus');
  try {
    statusEl.textContent = 'Retraining in progress...';
    await fetchJSON(API.retrain, { method: 'POST' });
    statusEl.textContent = 'Retrain completed successfully.';
    toast('Model retrained');
  } catch (e) {
    statusEl.textContent = 'Retrain failed.';
    toast('Retrain error');
  }
}

// --- Initialization ---

function bindEvents() {
  document.getElementById('socGenBtn')?.addEventListener('click', handleSocGenerate);
  document.getElementById('chatSendBtn')?.addEventListener('click', handleChat);
  document.getElementById('chatInput')?.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') handleChat();
  });
  document.getElementById('severityFilter')?.addEventListener('change', (e) => {
    state.severityFilter = e.target.value;
    loadThreatMonitor();
  });
  document.getElementById('autoRefreshToggle')?.addEventListener('change', (e) => {
    state.autoRefresh = e.target.checked;
  });
  document.getElementById('refreshAlertsBtn')?.addEventListener('click', loadThreatMonitor);
  
  // Pipeline button
  document.getElementById('pipeBtn')?.addEventListener('click', async () => {
    const log = document.getElementById('pipeLog').value;
    const asset = document.getElementById('pipeAsset').value;
    const ingest = document.getElementById('pipeIngest').checked;
    const report = document.getElementById('pipeSoc').checked;
    
    if (!log) return toast('Please enter a log');
    
    try {
      const res = await fetchJSON(API.pipelineRun, {
        method: 'POST',
        body: JSON.stringify({ message: log, asset_value: parseFloat(asset), ingest, report })
      });
      document.getElementById('pipeResult').innerHTML = `<pre style="font-size: 0.75rem; background: #f0f0f0; padding: 10px;">${JSON.stringify(res, null, 2)}</pre>`;
      toast('Pipeline executed');
      if (ingest) loadThreatDashboard();
    } catch (e) {
      toast('Pipeline error');
    }
  });
}

function init() {
  initAuth();
  bindEvents();
  loadCoreStatus();
  
  // Start background loops
  setInterval(loadCoreStatus, 30000);
  setInterval(() => {
    loadThreatDashboard();
    loadThreatMonitor();
  }, 10000);

  // Initial load
  loadThreatDashboard();
  loadThreatMonitor();
}

// Export functions needed by inline scripts
window.switchTab = (tabId) => {
  state.currentTab = tabId;
  document.querySelectorAll('.nav-tab').forEach(t => {
    t.classList.toggle('active', t.dataset.tab === tabId);
  });
  document.querySelectorAll('.tab-content').forEach(c => {
    c.classList.toggle('active', c.id === `${tabId}-page`);
  });

  if (tabId === 'home') {
    document.body.classList.add('dark-theme');
  } else {
    document.body.classList.remove('dark-theme');
  }

  if (tabId === 'dashboard') loadThreatDashboard();
  if (tabId === 'threats') loadThreatMonitor();
  if (tabId === 'mitre') loadMitreData();
};

window.typeAI = typeAI;
window.handleBatchProcess = handleBatchProcess;
window.triggerRetrain = triggerRetrain;
window.run9LogsDemo = () => {
  const sampleLogs = [
    "SELECT * FROM users WHERE id = 1 OR 1=1; --",
    "<script>alert('XSS_ATTACK_DETECTED')</script>",
    "Failed login attempt for user admin from 192.168.1.100",
    "GET /../../../../etc/passwd HTTP/1.1",
    "Suspicious outbound connection to 45.23.11.2 port 4444"
  ];
  document.getElementById('batchLogs').value = sampleLogs.join('\n');
};

document.addEventListener('DOMContentLoaded', init);
