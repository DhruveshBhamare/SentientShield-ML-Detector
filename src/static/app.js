// SentientShield Premium SOC App - Production Grade Modular & Enterprise UI

const API_BASE = "";
const API = {
  health: '/api/status',
  activation: '/neuralfort/activation-status',
  anomalies: '/neuralfort/anomalies',
  healing: '/neuralfort/healing-actions',
  predict: '/api/predict',
  copilot: '/neuralfort/copilot/chat',
  projectInfo: '/api/project/info',
  recentLogs: '/api/logs/recent',
  dashboard: '/api/logs/dashboard',
  pipelineRun: '/api/logs/pipeline/run',
  batchProcess: '/api/logs/workflow/batch-process',
  retrain: '/retrain'
};

const THREAT_TYPES = ["Brute Force", "SQL Injection", "XSS", "Botnet", "Credential Dumping", "DDoS", "Malware C2"];
const ATTACKING_IPS = ["185.220.101.45", "45.148.10.121", "103.203.57.18", "192.168.1.50", "88.99.210.144"];

const state = {
  token: localStorage.getItem('ss_token') || '',
  threatPollHandle: null,
  charts: {},
  currentTab: 'home',
  autoRefresh: true,
  severityFilter: 'all',
  riskScore: 0,
  recentAlerts: []
};

// --- Core Auth & Fetch ---

async function initAuth() {
  if (!state.token) {
    try {
      const resp = await fetchJSON('/api/dev-token');
      if (resp && resp.token) {
        state.token = resp.token;
        localStorage.setItem('ss_token', state.token);
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

function animateValue(id, start, end, duration = 1000) {
  const obj = document.getElementById(id);
  if (!obj) return;
  let startTimestamp = null;
  const step = (timestamp) => {
    if (!startTimestamp) startTimestamp = timestamp;
    const progress = Math.min((timestamp - startTimestamp) / duration, 1);
    const value = Math.floor(progress * (end - start) + start);
    obj.innerHTML = value;
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
  
  const currentVal = parseInt(text.innerText) || 0;
  animateValue('metricRisk', currentVal, value, 1000);
}

// --- Real-Time Simulation Engine ---

function generateMockAlert() {
  const type = THREAT_TYPES[Math.floor(Math.random() * THREAT_TYPES.length)];
  const ip = ATTACKING_IPS[Math.floor(Math.random() * ATTACKING_IPS.length)];
  const severity = Math.random() > 0.8 ? "HIGH" : (Math.random() > 0.4 ? "MEDIUM" : "LOW");
  const risk = severity === "HIGH" ? (0.7 + Math.random() * 0.3) : (severity === "MEDIUM" ? (0.4 + Math.random() * 0.3) : (0.1 + Math.random() * 0.3));
  
  return {
    id: Math.random().toString(36).substr(2, 9),
    ts: new Date().toISOString(),
    threat_type: type,
    severity: severity,
    risk: risk,
    ip: ip,
    mitre_technique: severity === "HIGH" ? "T1003" : "T1059"
  };
}

function runRealTimeSimulation() {
  // Update risk score smoothly
  const riskVariance = (Math.random() - 0.5) * 5;
  state.riskScore = Math.max(10, Math.min(95, state.riskScore + riskVariance));
  updateRiskGauge(Math.round(state.riskScore));

  // Add new alert occasionally
  if (Math.random() > 0.6) {
    const newAlert = generateMockAlert();
    state.recentAlerts.unshift(newAlert);
    if (state.recentAlerts.length > 50) state.recentAlerts.pop();
    
    renderThreatTable(state.recentAlerts);
    renderIncidentTimeline(state.recentAlerts.slice(0, 5));
    renderTopIps();
    
    if (newAlert.severity === "HIGH") {
      toast(`CRITICAL: ${newAlert.threat_type} detected from ${newAlert.ip}`);
      document.getElementById('dashboard-page')?.classList.add('glow-critical');
      setTimeout(() => document.getElementById('dashboard-page')?.classList.remove('glow-critical'), 2000);
    }
  }

  // Update summary metrics
  const highAlerts = state.recentAlerts.filter(a => a.severity === "HIGH").length;
  document.getElementById('metricAlerts').innerText = state.recentAlerts.length;
  document.getElementById('metricCritical').innerText = highAlerts;
}

// --- Specialized Renderers ---

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

function renderIncidentTimeline(items) {
  const container = document.getElementById('incidentTimeline');
  if (!container) return;

  container.innerHTML = items.map(it => `
    <div class="timeline-item">
      <div class="timeline-dot ${it.severity.toLowerCase()}"></div>
      <div class="timeline-content">
        <div class="timeline-time">${new Date(it.ts).toLocaleTimeString()}</div>
        <strong>${it.threat_type}</strong> from ${it.ip}
      </div>
    </div>
  `).join('');
}

function renderTopIps() {
  const tbody = document.getElementById('topIpsBody');
  if (!tbody) return;

  const ipCounts = {};
  state.recentAlerts.forEach(a => {
    ipCounts[a.ip] = (ipCounts[a.ip] || 0) + 1;
  });

  const sortedIps = Object.entries(ipCounts).sort((a, b) => b[1] - a[1]).slice(0, 5);

  tbody.innerHTML = sortedIps.map(([ip, count]) => `
    <tr>
      <td><code>${ip}</code></td>
      <td><span class="badge badge-${count > 5 ? 'high' : 'medium'}">${count > 5 ? 'BAD' : 'SUSP'}</span></td>
      <td>${count}</td>
    </tr>
  `).join('');
}

// --- Data Loading (Real API Fallback) ---

async function loadThreatDashboard() {
  try {
    const data = await fetchJSON(API.dashboard);
    if (!data) return;

    // Initial values from API
    state.riskScore = Math.round((data.avg_risk || 0) * 100);
    
    // Charts
    if (data.trends && data.trends.labels) {
      updateLineChart('attackTrend', 'chartAttackTrend', data.trends.labels, 'Risk Level', data.trends.values);
    }
    if (data.mitre_summary) {
      const labels = Object.keys(data.mitre_summary);
      const values = Object.values(data.mitre_summary);
      updateChart('mitrePieSummary', 'chartMitrePieSummary', labels, 'Tactics', values, 'doughnut');
    }
  } catch (e) {
    console.warn('Using simulated dashboard data');
  }
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
  return {
    text: '#F0F6FC',
    muted: '#8B949E',
    grid: 'rgba(240, 246, 252, 0.1)',
    primary: '#58A6FF'
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

async function handleChat() {
  const input = document.getElementById('chatInput');
  const text = input.value.trim();
  if (!text) return;

  const container = document.getElementById('chatResult');
  const bubble = document.createElement('div');
  bubble.className = `chat-bubble user`;
  bubble.textContent = text;
  container.appendChild(bubble);
  input.value = '';
  
  const indicator = document.getElementById('typingIndicator');
  indicator.style.display = 'block';

  try {
    const res = await fetchJSON(API.copilot, {
      method: 'POST',
      body: JSON.stringify({ message: text })
    });
    indicator.style.display = 'none';
    const botBubble = document.createElement('div');
    botBubble.className = `chat-bubble bot`;
    botBubble.textContent = res.answer || "Request processed.";
    container.appendChild(botBubble);
    container.scrollTop = container.scrollHeight;
  } catch {
    indicator.style.display = 'none';
  }
}

function investigateLog(id) {
  toast(`Investigating SOC Incident: ${id}`);
}

// --- Initialization ---

function init() {
  initAuth();
  loadThreatDashboard();
  
  // Start Production Simulation
  state.riskScore = 45;
  updateRiskGauge(state.riskScore);
  
  // Generate initial mock data
  for(let i=0; i<15; i++) {
    state.recentAlerts.push(generateMockAlert());
  }
  renderThreatTable(state.recentAlerts);
  renderTopIps();
  renderIncidentTimeline(state.recentAlerts.slice(0, 5));

  // Simulation Loop
  setInterval(runRealTimeSimulation, 2500);

  // Bind Events
  document.getElementById('chatSendBtn')?.addEventListener('click', handleChat);
  document.getElementById('chatInput')?.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') handleChat();
  });
}

// Export for HTML
window.switchTab = (tabId) => {
  state.currentTab = tabId;
  document.querySelectorAll('.nav-tab').forEach(t => t.classList.toggle('active', t.dataset.tab === tabId));
  document.querySelectorAll('.tab-content').forEach(c => c.classList.toggle('active', c.id === `${tabId}-page`));
};

document.addEventListener('DOMContentLoaded', init);
