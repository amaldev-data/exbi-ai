// Configuration management
const API_KEY_SETTINGS = "agentic_analytics_api_url";
const DEFAULT_API_URL = "https://exbi-ai.onrender.com";

function getApiUrl() {
  return localStorage.getItem(API_KEY_SETTINGS) || DEFAULT_API_URL;
}

function setApiUrl(url) {
  localStorage.setItem(API_KEY_SETTINGS, url);
}

// Global project reference state
let currentProjectId = null;
let currentProjectData = null;
let currentAudienceView = "Executive Leadership";
let pollInterval = null;
let lastLogCount = 0;
let dashboardInitialized = false;
let reportInitialized = false;

// Dynamic Category Color Assignment Engine
const CATEGORY_PALETTE = [
  '#3B82F6', // Blue
  '#10B981', // Emerald
  '#F59E0B', // Amber
  '#8B5CF6', // Purple
  '#F43F5E', // Rose
  '#06B6D4', // Cyan
  '#F97316', // Orange
  '#64748B'  // Slate
];
let globalCategoryColorMap = {};
let globalColorIndex = 0;

function getCategoryColor(categoryName) {
  const key = String(categoryName).trim().toLowerCase();
  if (globalCategoryColorMap[key]) {
    return globalCategoryColorMap[key];
  }
  const color = CATEGORY_PALETTE[globalColorIndex % CATEGORY_PALETTE.length];
  globalCategoryColorMap[key] = color;
  globalColorIndex++;
  return color;
}

function resetCategoryColors() {
  globalCategoryColorMap = {};
  globalColorIndex = 0;
}

// Global wizard state
let wizardState = {
  projectId: null,
  filename: "",
  currentStep: 1,
  role: "",
  objectives: [],
  decision: "",
  audience: "",
  datasetInfo: null,
  recommendations: [],
  selectedAnalyses: [],
  toggles: {
    forecasting: true,
    anomaly: true,
    segmentation: true,
    reports: true,
    aiRecommendations: true
  }
};

function renderAudienceSpecificDashboard() {
  if (!currentProjectData) return;
  
  const kpis = currentProjectData.dashboard_spec.kpis;
  const charts = currentProjectData.dashboard_spec.charts;
  const cert = currentProjectData.approval_certificate;
  const qual = currentProjectData.quality_report;
  
  renderKPIs(kpis, cert);
  renderCharts(charts);
  renderGovernanceInfo(cert, qual);
}

// Setup on page load
document.addEventListener("DOMContentLoaded", () => {
  window.addEventListener("beforeunload", () => {
    if (currentProjectId) {
      const blob = new Blob([JSON.stringify({ project_id: currentProjectId })], { type: 'application/json' });
      navigator.sendBeacon(`${getApiUrl()}/api/session/clear`, blob);
    }
  });

  const urlInput = document.getElementById("backend-url-input");
  if (urlInput) {
    urlInput.value = getApiUrl();
  }
  
  // Check server connection
  checkServerConnection();

  // Erase any previous project data from both local and session storage to start clean
  localStorage.removeItem("current_project_id");
  sessionStorage.removeItem("current_project_id");
  currentProjectId = null;

  // Initially hide all sections to avoid layout flashing during splash load
  const views = ["workspace", "dashboard", "reports"];
  views.forEach(v => {
    const viewEl = document.getElementById(`view-${v}`);
    if (viewEl) viewEl.style.display = "none";
  });

  // Read project_id from URL if explicitly passed
  const urlParams = new URLSearchParams(window.location.search);
  const urlProjId = urlParams.get("project_id");
  if (urlProjId) {
    currentProjectId = urlProjId;
    sessionStorage.setItem("current_project_id", urlProjId);
    window.history.replaceState({}, document.title, window.location.pathname);
  }

  // 2-Second Fullscreen Startup Splash Loader
  setTimeout(() => {
    const splash = document.getElementById("startup-splash-loader");
    if (splash) {
      splash.style.opacity = "0";
      setTimeout(() => {
        splash.style.visibility = "hidden";
      }, 500);
    }
    
    // Set default view (workspace hero section)
    if (currentProjectId) {
      checkProjectStatusAndInit();
    } else {
      switchSection("workspace");
    }
  }, 2000);

  // Highlight navigation tab on scroll (Workspace vs About)
  window.addEventListener("scroll", () => {
    const viewWorkspace = document.getElementById("view-workspace");
    const discoveryCard = document.getElementById("discovery-results-card");
    if (viewWorkspace && viewWorkspace.style.display !== "none" && (!discoveryCard || discoveryCard.style.display !== "block")) {
      const aboutSec = document.getElementById("about-section");
      if (aboutSec) {
        const rect = aboutSec.getBoundingClientRect();
        const workspaceTab = document.getElementById("nav-workspace-tab");
        const aboutTab = document.getElementById("nav-about-tab");
        
        if (rect.top <= 200) {
          if (workspaceTab) workspaceTab.classList.remove("active");
          if (aboutTab) aboutTab.classList.add("active");
        } else {
          if (workspaceTab) workspaceTab.classList.add("active");
          if (aboutTab) aboutTab.classList.remove("active");
        }
      }
    }
  });
});

// Switch Views in Single Page Application (SPA)
function switchSection(section) {
  const views = ["workspace", "dashboard", "reports"];
  
  // Verify permissions for dashboard and reports
  if (section === "dashboard" || section === "reports") {
    const projId = currentProjectId || sessionStorage.getItem("current_project_id");
    if (!projId) {
      alert("Please upload a dataset or load a sample first to unlock this section.");
      switchSection("workspace");
      return;
    }
  }

  if (section === "about") {
    switchSection("workspace");
    
    const heroSec = document.getElementById("workspace-section");
    if (heroSec) heroSec.style.display = "flex";
    const aboutSec = document.getElementById("about-section");
    if (aboutSec) aboutSec.style.display = "block";
    const discoveryCard = document.getElementById("discovery-results-card");
    if (discoveryCard) discoveryCard.style.display = "none";
    
    setTimeout(() => {
      const target = document.getElementById("about-section");
      if (target) {
        target.scrollIntoView({ behavior: "smooth", block: "start" });
      }
      
      views.forEach(v => {
        const tab = document.getElementById(`nav-${v}-tab`);
        if (tab) tab.classList.remove("active");
      });
      const aboutTab = document.getElementById("nav-about-tab");
      if (aboutTab) aboutTab.classList.add("active");
    }, 50);
    return;
  }

  if (section === "workspace") {
    window.scrollTo({ top: 0, behavior: "smooth" });
    
    const heroSec = document.getElementById("workspace-section");
    const aboutSec = document.getElementById("about-section");
    const discoveryCard = document.getElementById("discovery-results-card");
    if (discoveryCard && discoveryCard.style.display !== "block") {
      if (heroSec) heroSec.style.display = "flex";
      if (aboutSec) aboutSec.style.display = "block";
    }
  }

  // Update navbar links active classes
  views.forEach(v => {
    const tab = document.getElementById(`nav-${v}-tab`);
    const viewEl = document.getElementById(`view-${v}`);
    if (tab && viewEl) {
      if (v === section) {
        tab.classList.add("active");
        viewEl.style.display = "block";
      } else {
        tab.classList.remove("active");
        viewEl.style.display = "none";
      }
    }
  });

  const aboutTab = document.getElementById("nav-about-tab");
  if (aboutTab && section !== "about") {
    aboutTab.classList.remove("active");
  }

  // Section specific initializers
  if (section === "dashboard") {
    initDashboard();
  } else if (section === "reports") {
    initReportPreview();
  }
}

async function checkProjectStatusAndInit() {
  try {
    const res = await fetch(`${getApiUrl()}/api/project/${currentProjectId}`);
    if (res.ok) {
      const proj = await res.json();
      if (proj.status === "completed") {
        switchSection("dashboard");
      } else {
        switchSection("workspace");
      }
    } else {
      switchSection("workspace");
    }
  } catch (err) {
    switchSection("workspace");
  }
}

async function checkServerConnection() {
  const statusBadge = document.getElementById("server-status-badge");
  if (!statusBadge) return;
  
  try {
    const res = await fetch(`${getApiUrl()}/`);
    if (res.ok) {
      statusBadge.className = "badge bg-success-subtle text-success border border-success-subtle";
      statusBadge.innerText = "Online";
    } else {
      throw new Error();
    }
  } catch (err) {
    statusBadge.className = "badge bg-danger-subtle text-danger border border-danger-subtle";
    statusBadge.innerText = "Offline (Localhost:8000)";
  }
}

// Save Settings Event
function saveSettings() {
  const urlInput = document.getElementById("backend-url-input");
  if (urlInput) {
    setApiUrl(urlInput.value.trim());
    alert("Settings saved. Re-checking server connectivity...");
    checkServerConnection();
  }
}

// Loading Screen Animation State & Helpers
const WORKFLOW_LOGS = [
  // Phase 1 (Stage 1)
  { phase: 1, tag: "[DISCOVERY]", msg: "Reading dataset schema...", colorClass: "discovery" },
  { phase: 1, tag: "[DISCOVERY]", msg: "Detecting column types...", colorClass: "discovery" },
  { phase: 1, tag: "[DISCOVERY]", msg: "Identifying business domain...", colorClass: "discovery" },
  { phase: 1, tag: "[DISCOVERY]", msg: "Generating metadata profile...", colorClass: "discovery" },
  
  // Phase 2 (Stage 2)
  { phase: 2, tag: "[ANALYSIS]", msg: "Understanding business context...", colorClass: "analysis" },
  { phase: 2, tag: "[ANALYSIS]", msg: "Selecting relevant analyses...", colorClass: "analysis" },
  { phase: 2, tag: "[ANALYSIS]", msg: "Generating business insights...", colorClass: "analysis" },
  
  // Phase 3 (Stage 3)
  { phase: 3, tag: "[VISUALIZATION]", msg: "Validating variables...", colorClass: "visualization" },
  { phase: 3, tag: "[VISUALIZATION]", msg: "Selecting chart types...", colorClass: "visualization" },
  { phase: 3, tag: "[VISUALIZATION]", msg: "Building dashboard layout...", colorClass: "visualization" },
  
  // Phase 4 (Stage 4)
  { phase: 4, tag: "[REPORTING]", msg: "Preparing executive summary...", colorClass: "reporting" },
  { phase: 4, tag: "[REPORTING]", msg: "Generating recommendations...", colorClass: "reporting" },
  { phase: 4, tag: "[REPORTING]", msg: "Building business report...", colorClass: "reporting" },
  
  // Phase 5 (Stage 5)
  { phase: 5, tag: "[SYSTEM]", msg: "Analysis completed successfully.", colorClass: "system" },
  { phase: 5, tag: "[SYSTEM]", msg: "Dashboard ready.", colorClass: "system" },
  { phase: 5, tag: "[SYSTEM]", msg: "Report generated.", colorClass: "system" }
];

let currentLogIndex = 0;
let activePhase = 1;
let typingTimeout = null;
let delayTimeout = null;
let currentLineMsgSpan = null;
let isCurrentlyTyping = false;
let thinkingDotsInterval = null;
let activeLoaderTimeouts = [];
let animationFinished = false;
let isTransitioning = false;

function setLoaderTimeout(fn, ms) {
  const id = setTimeout(fn, ms);
  activeLoaderTimeouts.push(id);
  return id;
}

function clearLoaderTimeouts() {
  activeLoaderTimeouts.forEach(id => clearTimeout(id));
  activeLoaderTimeouts = [];
}

function startThinkingDotsAnimation() {
  const textEl = document.getElementById("terminal-thinking-label");
  if (!textEl) return;
  let dots = 0;
  if (thinkingDotsInterval) clearInterval(thinkingDotsInterval);
  thinkingDotsInterval = setInterval(() => {
    dots = (dots + 1) % 5;
    let dotStr = ".".repeat(dots);
    textEl.innerText = `Thinking ${dotStr}`;
  }, 400);
}

function stopThinkingDotsAnimation() {
  if (thinkingDotsInterval) {
    clearInterval(thinkingDotsInterval);
    thinkingDotsInterval = null;
  }
}

function updateStepperUI(stage) {
  const bar = document.getElementById("stepper-progress-bar");
  if (bar) {
    const pct = ((stage - 1) / 4) * 100;
    bar.style.width = pct + "%";
  }
  
  for (let i = 1; i <= 5; i++) {
    const circle = document.getElementById(`circle-loader-${i}`);
    const item = document.getElementById(`step-loader-${i}`);
    if (circle && item) {
      item.classList.remove("active", "completed");
      circle.classList.remove("running", "completed");
      
      if (i < stage) {
        item.classList.add("completed");
        circle.classList.add("completed");
        circle.innerText = "✓";
      } else if (i === stage) {
        item.classList.add("active");
        circle.classList.add("running");
        circle.innerText = "◉";
      } else {
        circle.innerText = "○";
      }
    }
  }
}

function resetTerminalAnimation() {
  currentLogIndex = 0;
  activePhase = 1;
  animationFinished = false;
  isTransitioning = false;
  
  if (typingTimeout) clearTimeout(typingTimeout);
  if (delayTimeout) clearTimeout(delayTimeout);
  typingTimeout = null;
  delayTimeout = null;
  currentLineMsgSpan = null;
  isCurrentlyTyping = false;
  
  stopThinkingDotsAnimation();
  clearLoaderTimeouts();
  
  const container = document.getElementById("thinking-logs");
  if (container) container.innerHTML = "";
  
  const label = document.getElementById("terminal-thinking-label");
  if (label) {
    label.innerText = "Thinking";
    label.className = "thinking-text";
  }
}

function startTerminalAnimation() {
  resetTerminalAnimation();
  playLogs();
}

function playLogs() {
  if (currentLogIndex >= WORKFLOW_LOGS.length) return;
  const log = WORKFLOW_LOGS[currentLogIndex];
  if (log.phase > activePhase) return;
  
  isCurrentlyTyping = true;
  typeLogLine(log.tag, log.msg, log.colorClass, () => {
    isCurrentlyTyping = false;
    currentLogIndex++;
    delayTimeout = setTimeout(playLogs, 300);
  });
}

function typeLogLine(tag, msg, colorClass, callback) {
  const container = document.getElementById("thinking-logs");
  if (!container) {
    callback();
    return;
  }
  
  const line = document.createElement("div");
  line.className = "terminal-log-line";
  
  const tagSpan = document.createElement("span");
  tagSpan.className = `log-tag ${colorClass}`;
  tagSpan.innerText = tag + " ";
  line.appendChild(tagSpan);
  
  const msgSpan = document.createElement("span");
  msgSpan.className = "log-msg";
  line.appendChild(msgSpan);
  
  container.appendChild(line);
  container.scrollTop = container.scrollHeight;
  
  currentLineMsgSpan = msgSpan;
  let charIdx = 0;
  
  function nextChar() {
    if (charIdx < msg.length) {
      msgSpan.innerText += msg[charIdx++];
      container.scrollTop = container.scrollHeight;
      typingTimeout = setTimeout(nextChar, 40);
    } else {
      currentLineMsgSpan = null;
      callback();
    }
  }
  nextChar();
}

function advanceActivePhase(newPhase) {
  activePhase = newPhase;
  
  if (typingTimeout) clearTimeout(typingTimeout);
  if (delayTimeout) clearTimeout(delayTimeout);
  typingTimeout = null;
  delayTimeout = null;
  
  const container = document.getElementById("thinking-logs");
  if (!container) return;
  
  if (isCurrentlyTyping && currentLogIndex < WORKFLOW_LOGS.length) {
    const currentLog = WORKFLOW_LOGS[currentLogIndex];
    if (currentLineMsgSpan) {
      currentLineMsgSpan.innerText = currentLog.msg;
    }
    isCurrentlyTyping = false;
    currentLogIndex++;
  }
  
  while (currentLogIndex < WORKFLOW_LOGS.length) {
    const log = WORKFLOW_LOGS[currentLogIndex];
    if (log.phase < newPhase) {
      const line = document.createElement("div");
      line.className = "terminal-log-line";
      
      const tagSpan = document.createElement("span");
      tagSpan.className = `log-tag ${log.colorClass}`;
      tagSpan.innerText = log.tag + " ";
      line.appendChild(tagSpan);
      
      const msgSpan = document.createElement("span");
      msgSpan.className = "log-msg";
      msgSpan.innerText = log.msg;
      line.appendChild(msgSpan);
      
      container.appendChild(line);
      currentLogIndex++;
    } else {
      break;
    }
  }
  
  container.scrollTop = container.scrollHeight;
  playLogs();
}

function completeTransition() {
  if (isTransitioning) return;
  isTransitioning = true;
  
  stopThinkingDotsAnimation();
  
  if (typingTimeout) clearTimeout(typingTimeout);
  if (delayTimeout) clearTimeout(delayTimeout);
  typingTimeout = null;
  delayTimeout = null;
  
  const container = document.getElementById("thinking-logs");
  if (container) {
    container.innerHTML = "";
    WORKFLOW_LOGS.forEach(log => {
      const line = document.createElement("div");
      line.className = "terminal-log-line";
      const tagSpan = document.createElement("span");
      tagSpan.className = `log-tag ${log.colorClass}`;
      tagSpan.innerText = log.tag + " ";
      line.appendChild(tagSpan);
      const msgSpan = document.createElement("span");
      msgSpan.className = "log-msg";
      msgSpan.innerText = log.msg;
      line.appendChild(msgSpan);
      container.appendChild(line);
    });
    container.scrollTop = container.scrollHeight;
  }
  
  const label = document.getElementById("terminal-thinking-label");
  if (label) {
    label.innerText = "Completed";
    label.className = "thinking-text text-success";
  }
  
  updateStepperUI(6);
  
  setTimeout(() => {
    const overlay = document.getElementById("thinking-overlay");
    if (overlay) {
      overlay.classList.add("fade-out");
      document.body.classList.remove("thinking-active");
      
      setTimeout(() => {
        overlay.style.display = "none";
        overlay.classList.remove("fade-out");
        
        switchSection("dashboard");
        
        const dbView = document.getElementById("view-dashboard");
        if (dbView) {
          dbView.classList.add("fade-in");
          setTimeout(() => {
            dbView.classList.remove("fade-in");
            dbView.style.opacity = "1";
          }, 300);
        }
      }, 300);
    }
  }, 500);
}

function getSearchQueryForFilename(filename) {
  return filename || "dataset.csv";
}

async function uploadDataset(file) {
  const overlay = document.getElementById("thinking-overlay");
  const logsContainer = document.getElementById("thinking-logs");
  
  dashboardInitialized = false;
  lastLogCount = 0;
  pipelineLogCount = 0;
  currentProjectData = null;
  resetCategoryColors();
  
  if (overlay) {
    overlay.style.display = "flex";
    document.body.classList.add("thinking-active");
    const filenameDisplay = document.getElementById("terminal-filename-display");
    if (filenameDisplay) {
      filenameDisplay.innerText = file.name;
    }
  }
  if (logsContainer) logsContainer.innerHTML = "";
  
  resetTerminalAnimation();
  
  updateStepperUI(1);
  startThinkingDotsAnimation();

  const formData = new FormData();
  formData.append("file", file);

  const uploadPromise = fetch(`${getApiUrl()}/api/upload`, {
    method: "POST",
    body: formData
  });

  animateDiscoveryWorkflow(uploadPromise);
}

async function loadSampleDataset(type) {
  const overlay = document.getElementById("thinking-overlay");
  const logsContainer = document.getElementById("thinking-logs");
  
  dashboardInitialized = false;
  lastLogCount = 0;
  pipelineLogCount = 0;
  currentProjectData = null;
  resetCategoryColors();
  
  if (overlay) {
    overlay.style.display = "flex";
    document.body.classList.add("thinking-active");
    const filenameDisplay = document.getElementById("terminal-filename-display");
    if (filenameDisplay) {
      filenameDisplay.innerText = "sample_" + type + ".csv";
    }
  }
  if (logsContainer) logsContainer.innerHTML = "";
  
  resetTerminalAnimation();
  updateStepperUI(1);
  startThinkingDotsAnimation();

  const formData = new FormData();
  formData.append("dataset_type", type);

  const samplePromise = fetch(`${getApiUrl()}/api/sample`, {
    method: "POST",
    body: formData
  });

  animateDiscoveryWorkflow(samplePromise);
}

function animateDiscoveryWorkflow(apiPromise) {
  playLogs();
  
  setTimeout(async () => {
    try {
      const res = await apiPromise;
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Server upload failed.");
      }
      
      const data = await res.json();
      currentProjectId = data.project_id;
      sessionStorage.setItem("current_project_id", data.project_id);

      advanceActivePhase(2);
      updateStepperUI(2);

      setTimeout(() => {
        stopThinkingDotsAnimation();
        const overlay = document.getElementById("thinking-overlay");
        if (overlay) {
          overlay.classList.add("fade-out");
          document.body.classList.remove("thinking-active");
          setTimeout(() => {
            overlay.style.display = "none";
            overlay.classList.remove("fade-out");
            
            const heroSection = document.getElementById("workspace-section");
            if (heroSection) heroSection.style.display = "none";
            
            handleDiscoverySuccess(data);
          }, 300);
        }
      }, 500);

    } catch (err) {
      resetTerminalAnimation();
      const overlay = document.getElementById("thinking-overlay");
      if (overlay) {
        overlay.style.display = "none";
        document.body.classList.remove("thinking-active");
      }
      alert("Verification Failed: " + err.message);
    }
  }, 1500);
}

function handleDiscoverySuccess(data) {
  const wizardCard = document.getElementById("discovery-wizard-card");
  if (wizardCard) wizardCard.style.display = "block";

  wizardState.projectId = data.project_id;
  wizardState.filename = data.filename || "Uploaded Dataset";
  wizardState.datasetInfo = data.dataset_info;
  wizardState.recommendations = data.recommendations || [];
  
  const domainBadge = document.getElementById("wizard-dataset-domain-badge");
  if (domainBadge) domainBadge.innerText = `${data.dataset_info.business_discovery.business_domain} Dataset Detected`;
  
  const filenameEl = document.getElementById("wizard-dataset-filename");
  if (filenameEl) filenameEl.innerText = data.filename || "dataset.csv";

  wizardState.selectedAnalyses = wizardState.recommendations
    .filter(r => r.recommended)
    .map(r => r.id);
    
  renderAIRecommendationsList();
}

function getAnalysisIcon(id, title) {
  const t = (title || "").toLowerCase();
  const i = (id || "").toLowerCase();
  
  if (t.includes("revenue") || t.includes("sales") || t.includes("profit") || t.includes("margin") || t.includes("financial") || i.includes("sales") || i.includes("profit")) {
    return '<i class="bi bi-currency-dollar"></i>';
  }
  if (t.includes("customer") || t.includes("demographic") || t.includes("seg") || i.includes("customer") || i.includes("seg")) {
    return '<i class="bi bi-people"></i>';
  }
  if (t.includes("churn") || t.includes("retention") || t.includes("risk") || i.includes("churn")) {
    return '<i class="bi bi-shield-exclamation"></i>';
  }
  if (t.includes("hr") || t.includes("attrition") || t.includes("employee") || i.includes("hr") || i.includes("attrition")) {
    return '<i class="bi bi-person-x"></i>';
  }
  if (t.includes("forecasting") || t.includes("time series") || t.includes("trend") || i.includes("forecast")) {
    return '<i class="bi bi-graph-up"></i>';
  }
  return '<i class="bi bi-bar-chart"></i>';
}

function renderAIRecommendationsList() {
  const container = document.getElementById("wizard-recommendations-list");
  if (!container) return;
  container.innerHTML = "";

  if (wizardState.recommendations.length === 0) {
    container.innerHTML = `<div class="col-12 text-center text-muted small">No recommendations generated.</div>`;
    return;
  }

  wizardState.recommendations.forEach(rec => {
    const isChecked = wizardState.selectedAnalyses.includes(rec.id);
    const col = document.createElement("div");
    col.className = ""; // flex grid will handle sizing via wrapper grid
    
    col.innerHTML = `
      <div class="recommender-card ${isChecked ? 'active' : ''}" onclick="toggleRecommendation('${rec.id}')">
        ${rec.recommended ? '<span class="recommended-badge">Recommended</span>' : ''}
        <div class="selection-check-icon">
          <i class="bi bi-check-lg"></i>
        </div>
        <div class="card-icon-wrapper">
          ${getAnalysisIcon(rec.id, rec.title)}
        </div>
        <div class="card-title-text">${rec.title}</div>
        <div class="card-desc-text" title="${rec.description}">${rec.description}</div>
      </div>
    `;
    container.appendChild(col);
  });
}

function toggleRecommendation(id) {
  const idx = wizardState.selectedAnalyses.indexOf(id);
  if (idx > -1) {
    wizardState.selectedAnalyses.splice(idx, 1);
  } else {
    wizardState.selectedAnalyses.push(id);
  }
  renderAIRecommendationsList();
}

let deliverableToggles = {
  dashboard: true,
  report: true
};

function toggleDeliverable(type) {
  deliverableToggles[type] = !deliverableToggles[type];
  const card = document.getElementById(`card-deliverable-${type}`);
  const chk = document.getElementById(`chk-deliverable-${type}`);
  const icon = document.getElementById(`chk-deliverable-${type}-icon`);
  if (card && chk) {
    if (deliverableToggles[type]) {
      card.classList.add("active");
      chk.checked = true;
      if (icon) icon.style.display = "flex";
    } else {
      card.classList.remove("active");
      chk.checked = false;
      if (icon) icon.style.display = "none";
    }
  }
}

let pipelineLogCount = 0;
let progressPollInterval = null;

async function startAnalyticsWorkflow() {
  const projId = wizardState.projectId || currentProjectId;
  if (!projId) {
    alert("Select a dataset first.");
    return;
  }

  const selected = wizardState.selectedAnalyses;
  if (selected.length === 0) {
    alert("Please select at least one analysis module.");
    return;
  }

  const wizardCard = document.getElementById("discovery-wizard-card");
  if (wizardCard) wizardCard.style.display = "none";
  
  const overlay = document.getElementById("thinking-overlay");
  
  dashboardInitialized = false;
  lastLogCount = 0;
  pipelineLogCount = 0;
  currentProjectData = null;
  resetCategoryColors();
  
  resetTerminalAnimation();
  
  if (overlay) {
    overlay.style.display = "flex";
    document.body.classList.add("thinking-active");
    const filenameDisplay = document.getElementById("terminal-filename-display");
    if (filenameDisplay) {
      filenameDisplay.innerText = wizardState.filename || "dataset.csv";
    }
  }
  
  // Start the 6.5s fixed timeline animation
  updateStepperUI(1);
  startThinkingDotsAnimation();
  startTerminalAnimation();
  
  // Run Timeline sequence
  // Stage 1 -> 2 after 1.5s
  setLoaderTimeout(() => {
    updateStepperUI(2);
    advanceActivePhase(2);
    
    // Stage 2 -> 3 after 1.5s
    setLoaderTimeout(() => {
      updateStepperUI(3);
      advanceActivePhase(3);
      
      // Stage 3 -> 4 after 1.5s
      setLoaderTimeout(() => {
        updateStepperUI(4);
        advanceActivePhase(4);
        
        // Stage 4 -> 5 after 1.5s
        setLoaderTimeout(() => {
          updateStepperUI(5);
          advanceActivePhase(5);
          
          // Stage 5 -> Complete check after 0.5s (at 6.5s total)
          setLoaderTimeout(() => {
            animationFinished = true;
            if (currentProjectData) {
              completeTransition();
            }
          }, 500);
          
        }, 1500);
      }, 1500);
    }, 1500);
  }, 1500);

  const payload = {
    analyses: selected,
    problem: "Standard Automated Business Analysis",
    decision: "Executive Report & Dashboard Generation",
    objective: "Provide business metrics and actionable insights",
    audience: "Executive Leadership",
    level: "Standard"
  };

  try {
    const res = await fetch(`${getApiUrl()}/api/execute/${projId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Failed to trigger analysis.");
    }
    
    pollPipelineProgress(projId);
  } catch (err) {
    resetTerminalAnimation();
    if (overlay) overlay.style.display = "none";
    document.body.classList.remove("thinking-active");
    alert("Error starting execution: " + err.message);
  }
}

function pollPipelineProgress(projId) {
  if (progressPollInterval) clearInterval(progressPollInterval);
  
  progressPollInterval = setInterval(async () => {
    try {
      const projRes = await fetch(`${getApiUrl()}/api/project/${projId}`);
      if (!projRes.ok) return;
      const project = await projRes.json();
      
      if (project.status === "completed") {
        clearInterval(progressPollInterval);
        progressPollInterval = null;
        
        currentProjectData = project;
        
        // Pre-render dashboard
        const runView = document.getElementById("running-state-view");
        if (runView) runView.style.display = "none";
        
        const badge = document.getElementById("processing-badge");
        if (badge) {
          badge.className = "badge bg-success-subtle text-success border border-success-subtle px-3 py-1.5 fs-7 font-monospace";
          badge.innerText = "Completed";
        }
        
        renderAudienceSpecificDashboard();
        
        const completedDashboardContent = document.getElementById("completed-dashboard-content");
        if (completedDashboardContent) completedDashboardContent.style.display = "block";
        
        const downloadsSectionCard = document.getElementById("downloads-section-card");
        if (downloadsSectionCard) downloadsSectionCard.style.display = "block";
        
        // Trigger completion transition if animation is done
        if (animationFinished) {
          completeTransition();
        }
      } else if (project.status === "failed") {
        clearInterval(progressPollInterval);
        progressPollInterval = null;
        resetTerminalAnimation();
        const overlay = document.getElementById("thinking-overlay");
        if (overlay) {
          overlay.style.display = "none";
          document.body.classList.remove("thinking-active");
        }
        alert("Workflow calculation failed.");
      }
    } catch (err) {
      console.error("Error polling pipeline progress:", err);
    }
  }, 1000);
}

// DASHBOARD INITIALIZER
function initDashboard() {
  if (dashboardInitialized) return;
  dashboardInitialized = true;

  document.getElementById("project-ref-id").innerText = currentProjectId;
  
  pollProjectDetails();
  pollLogs();
  pollInterval = setInterval(() => {
    pollProjectDetails();
    pollLogs();
  }, 1500);
}

async function pollProjectDetails() {
  try {
    const res = await fetch(`${getApiUrl()}/api/project/${currentProjectId}`);
    if (!res.ok) return;
    const project = await res.json();
    
    updateNodeVisualizerStates(project.status);
    
    if (project.status === "completed") {
      clearInterval(pollInterval);
      
      const badge = document.getElementById("processing-badge");
      if (badge) {
        badge.className = "badge bg-success-subtle text-success border border-success-subtle px-3 py-1.5 fs-7 font-monospace";
        badge.innerText = "Completed";
      }
      
      const runView = document.getElementById("running-state-view");
      if (runView) runView.style.display = "none";
      
      currentProjectData = project;
      renderAudienceSpecificDashboard();
      
      document.getElementById("completed-dashboard-content").style.display = "block";
      document.getElementById("downloads-section-card").style.display = "block";
    } else if (project.status === "failed") {
      clearInterval(pollInterval);
      const badge = document.getElementById("processing-badge");
      if (badge) {
        badge.className = "badge bg-danger-subtle text-danger border border-danger-subtle px-3 py-1.5 fs-7 font-monospace";
        badge.innerText = "Failed";
      }
    } else {
      const badge = document.getElementById("processing-badge");
      if (badge) {
        badge.className = "badge bg-secondary-subtle text-muted border border-secondary px-3 py-1.5 fs-7 font-monospace";
        badge.innerText = "Running Tasks...";
      }
    }
  } catch (err) {
    console.error("Error polling details:", err);
  }
}

function updateNodeVisualizerStates(status) {
  const nodes = ["intake", "strategy", "quality", "insights", "viz", "report", "exec"];
  nodes.forEach(node => {
    const step = document.getElementById(`node-${node}`);
    const stat = document.getElementById(`status-${node}`);
    if (step && stat) {
      if (status === "completed") {
        step.className = "step-item completed";
        stat.innerHTML = `<span class="text-success"><i class="bi bi-check-circle-fill"></i> Done</span>`;
      } else if (status === "running") {
        step.className = "step-item active";
        stat.innerHTML = `<span class="text-white">Active</span>`;
      }
    }
  });
}

async function pollLogs() {
  try {
    const res = await fetch(`${getApiUrl()}/api/project/${currentProjectId}/logs`);
    if (!res.ok) return;
    const logs = await res.json();
    
    if (logs.length > lastLogCount) {
      const container = document.getElementById("terminal-logs-container");
      if (!container) return;
      
      for (let i = lastLogCount; i < logs.length; i++) {
        const log = logs[i];
        const line = document.createElement("div");
        line.className = "thinking-log-line";
        
        let agentName = log.agent_name || "Manager";
        line.innerHTML = `
          <span style="color: var(--text-muted); font-size: 0.75rem;">[${log.timestamp.split(" ")[1]}]</span>
          <span style="color: var(--text-secondary); font-weight: 500;">[${agentName}]</span>
          <span>${log.message}</span>
        `;
        container.appendChild(line);
      }
      container.scrollTop = container.scrollHeight;
      lastLogCount = logs.length;
    }
  } catch (err) {
    console.error("Error polling logs:", err);
  }
}

function getKpiMetadata(title, value) {
  const t = String(title).toLowerCase();
  
  let icon = '<i class="bi bi-bar-chart"></i>';
  let color = "#64748B"; // Default Slate
  
  if (t.includes("revenue") || t.includes("sales") || t.includes("income") || t.includes("amount") || t.includes("ticket size")) {
    icon = '<i class="bi bi-currency-dollar"></i>';
    color = "#3B82F6"; // Blue
  } else if (t.includes("profit") || t.includes("margin") || t.includes("gain") || t.includes("earnings")) {
    icon = '<i class="bi bi-graph-up-arrow"></i>';
    color = "#10B981"; // Green
  } else if (t.includes("cost") || t.includes("expense") || t.includes("spend") || t.includes("loss")) {
    icon = '<i class="bi bi-cash-stack"></i>';
    color = "#F97316"; // Orange
  } else if (t.includes("risk") || t.includes("attrition") || t.includes("churn") || t.includes("error") || t.includes("fail")) {
    icon = '<i class="bi bi-exclamation-triangle"></i>';
    color = "#F43F5E"; // Red
  } else if (t.includes("growth") || t.includes("velocity") || t.includes("rate") || t.includes("percent")) {
    icon = '<i class="bi bi-arrow-up-right-circle"></i>';
    color = "#8B5CF6"; // Purple
  } else if (t.includes("confidence") || t.includes("score") || t.includes("governance") || t.includes("compliance")) {
    icon = '<i class="bi bi-shield-check"></i>';
    color = "#10B981"; // Emerald
  } else if (t.includes("volume") || t.includes("count") || t.includes("headcount")) {
    icon = '<i class="bi bi-people"></i>';
    color = "#06B6D4"; // Cyan
  }
  
  let path = "M 0 15 L 10 12 L 20 18 L 30 10 L 40 8 L 50 14 L 60 6 L 70 10 L 80 5";
  let delta = "+3.5%";
  let deltaLabel = "vs last period";
  let isUp = true;
  
  if (t.includes("risk") || t.includes("attrition") || t.includes("churn")) {
    path = "M 0 5 L 10 12 L 20 10 L 30 18 L 40 15 L 50 22 L 60 18 L 70 24 L 80 28";
    delta = "-1.2%";
    deltaLabel = "reduction";
    isUp = true;
  } else if (t.includes("confidence") || t.includes("score")) {
    path = "M 0 8 L 10 6 L 20 8 L 30 5 L 40 5 L 50 6 L 60 4 L 70 5 L 80 4";
    delta = "100%";
    deltaLabel = "compliance";
    isUp = true;
  } else if (t.includes("cost") || t.includes("expense")) {
    path = "M 0 8 L 10 12 L 20 10 L 30 15 L 40 18 L 50 14 L 60 22 L 70 20 L 80 25";
    delta = "-2.4%";
    deltaLabel = "optimization";
    isUp = true;
  }
  
  return { icon, path, color, delta, deltaLabel, isUp };
}

function renderKPIs(kpis, cert) {
  const kpisRow = document.getElementById("kpis-container-row");
  if (!kpisRow) return;
  kpisRow.innerHTML = "";
  
  const list = [...kpis];
  const confScore = cert ? cert.overall_confidence_score : 95;
  
  if (list.length < 3) {
    while (list.length < 3) {
      list.push({ title: "Metric", value: "0", description: "Placeholder" });
    }
  }
  
  list.push({
    title: "Confidence Score",
    value: `${confScore}%`,
    description: "Overall data reliability certificate rating"
  });
  
  list.forEach((kpi, idx) => {
    const cardMeta = getKpiMetadata(kpi.title, kpi.value);
    const col = document.createElement("div");
    col.className = "col-lg-3 col-md-6 mb-3";
    
    const deltaClass = cardMeta.isUp ? "kpi-delta-up" : "kpi-delta-down";
    const deltaIcon = cardMeta.isUp ? "bi-arrow-up-short" : "bi-arrow-down-short";
    
    col.innerHTML = `
      <div class="kpi-card-redesign" style="border-top: 3px solid ${cardMeta.color};">
        <div class="kpi-card-header">
          <span class="kpi-card-title">${kpi.title}</span>
          <span class="kpi-card-icon" style="color: ${cardMeta.color} !important;">${cardMeta.icon}</span>
        </div>
        <div class="kpi-card-body">
          <div class="kpi-card-value">${kpi.value}</div>
          <div class="kpi-card-sparkline">
            <svg width="70" height="24" viewBox="0 0 80 30" style="overflow: visible;">
              <path d="${cardMeta.path}" fill="none" stroke="${cardMeta.color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
          </div>
        </div>
        <div class="kpi-card-footer">
          <span class="kpi-card-delta ${deltaClass}">
            <i class="bi ${deltaIcon}"></i>${cardMeta.delta}
          </span>
          <span class="kpi-card-desc">${cardMeta.deltaLabel} &bull; ${kpi.description}</span>
        </div>
      </div>
    `;
    kpisRow.appendChild(col);
  });
}

let activeChartObjects = [];
function renderCharts(charts) {
  const chartsRow = document.getElementById("charts-container-row");
  if (!chartsRow) return;
  chartsRow.innerHTML = "";
  
  activeChartObjects.forEach(c => c.destroy());
  activeChartObjects = [];
  
  if (!charts || charts.length === 0) {
    chartsRow.innerHTML = '<div class="col-12 text-center text-muted small py-4">No compatible charts generated for this dataset.</div>';
    return;
  }
  
  charts.forEach(chart => {
    const col = document.createElement("div");
    col.className = "col-lg-6 col-md-12 mb-4";
    
    col.innerHTML = `
      <div class="chart-card-redesign" id="card_container_${chart.id}">
        <div class="chart-card-header d-flex justify-content-between align-items-center mb-3">
          <div>
            <h6 class="chart-card-title">${chart.title}</h6>
            <span class="chart-card-subtitle">${chart.description || ''}</span>
          </div>
          <div class="chart-card-actions">
            <button class="chart-action-btn" onclick="exportChart('${chart.id}')" title="Export Data"><i class="bi bi-download"></i></button>
            <button class="chart-action-btn" onclick="toggleFullscreen('card_container_${chart.id}')" title="Toggle Fullscreen"><i class="bi bi-fullscreen"></i></button>
          </div>
        </div>
        <div class="chart-card-body" style="position: relative; height: 300px;">
          <canvas id="canvas_${chart.id}"></canvas>
        </div>
      </div>
    `;
    chartsRow.appendChild(col);
    
    setTimeout(() => {
      const canvas = document.getElementById(`canvas_${chart.id}`);
      if (!canvas) return;
      const ctx = canvas.getContext('2d');
      
      const isPieOrDoughnut = chart.type === "pie" || chart.type === "doughnut";
      const isBar = chart.type === "bar" || chart.type === "horizontalBar" || chart.type === "horizontal_bar";
      const isLine = chart.type === "line";
      const isScatter = chart.type === "scatter";
      
      const datasets = chart.datasets.map(dataset => {
        let fill = false;
        let backgroundColor = '#3B82F6';
        let borderColor = '#3B82F6';
        
        if (isLine) {
          if (chart.datasets.length === 1) {
            fill = true;
            const gradient = ctx.createLinearGradient(0, 0, 0, 240);
            gradient.addColorStop(0, 'rgba(59, 130, 246, 0.22)');
            gradient.addColorStop(1, 'rgba(59, 130, 246, 0.00)');
            backgroundColor = gradient;
            borderColor = '#3B82F6';
          } else {
            fill = false;
            borderColor = getCategoryColor(dataset.label);
            backgroundColor = borderColor;
          }
        } else if (isBar) {
          if (chart.datasets.length === 1) {
            backgroundColor = chart.labels.map(l => getCategoryColor(l));
            borderColor = backgroundColor;
          } else {
            borderColor = getCategoryColor(dataset.label);
            backgroundColor = borderColor;
          }
        } else if (isPieOrDoughnut) {
          backgroundColor = chart.labels.map(l => getCategoryColor(l));
          borderColor = '#111827';
        } else if (isScatter) {
          if (chart.datasets.length === 1) {
            borderColor = '#3B82F6';
            backgroundColor = '#3B82F6';
          } else {
            borderColor = getCategoryColor(dataset.label);
            backgroundColor = borderColor;
          }
        }
        
        return {
          label: dataset.label,
          data: dataset.data,
          backgroundColor: backgroundColor,
          borderColor: borderColor,
          borderWidth: isLine ? 2.5 : 1,
          fill: fill,
          tension: isLine ? 0.4 : 0,
          pointBackgroundColor: isLine ? '#FFFFFF' : undefined,
          pointBorderColor: isLine ? (chart.datasets.length === 1 ? '#3B82F6' : getCategoryColor(dataset.label)) : undefined,
          pointBorderWidth: isLine ? 2 : undefined,
          pointRadius: isLine ? 4 : undefined,
          pointHoverRadius: isLine ? 6 : undefined
        };
      });
      
      const configOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: chart.type === "pie" || chart.type === "doughnut" || chart.datasets.length > 1,
            position: chart.type === "pie" || chart.type === "doughnut" ? 'right' : 'bottom',
            labels: {
              color: 'rgba(255, 255, 255, 0.6)',
              boxWidth: 10,
              font: { family: 'Inter', size: 11 }
            }
          },
          tooltip: {
            backgroundColor: '#1F2937',
            titleColor: '#FFFFFF',
            bodyColor: '#E5E7EB',
            borderColor: 'rgba(255,255,255,0.08)',
            borderWidth: 1,
            padding: 10,
            font: { family: 'Inter' },
            callbacks: {
              label: function(context) {
                const label = context.label || '';
                const value = context.parsed || context.raw;
                if (context.chart.config.type === 'pie' || context.chart.config.type === 'doughnut') {
                  const dataset = context.dataset;
                  const total = dataset.data.reduce((sum, val) => sum + val, 0);
                  const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                  return `${label}: ${value} (${percentage}%)`;
                }
                return `${context.dataset.label || ''}: ${value}`;
              }
            }
          }
        },
        scales: (chart.type !== "pie" && chart.type !== "doughnut") ? {
          y: {
            grid: {
              color: 'rgba(255, 255, 255, 0.05)',
              borderDash: [4, 4]
            },
            ticks: {
              color: 'rgba(255, 255, 255, 0.5)',
              font: { family: 'Inter', size: 10 }
            }
          },
          x: {
            grid: {
              display: false
            },
            ticks: {
              color: 'rgba(255, 255, 255, 0.5)',
              font: { family: 'Inter', size: 10 }
            }
          }
        } : {}
      };
      
      let chartType = chart.type;
      if (chart.type === "horizontalBar" || chart.type === "horizontal_bar") {
        chartType = "bar";
        configOptions.indexAxis = 'y';
      } else if (chart.type === "pie" || chart.type === "doughnut") {
        if (chart.labels && chart.labels.length > 8) {
          chartType = "bar";
          configOptions.indexAxis = 'y';
          datasets.forEach(d => {
            d.backgroundColor = chart.labels.map(l => getCategoryColor(l));
            d.borderColor = d.backgroundColor;
          });
          configOptions.plugins.legend.display = false;
          configOptions.scales = {
            y: {
              grid: { color: 'rgba(255, 255, 255, 0.05)', borderDash: [4, 4] },
              ticks: { color: 'rgba(255, 255, 255, 0.5)', font: { family: 'Inter', size: 10 } }
            },
            x: {
              grid: { display: false },
              ticks: { color: 'rgba(255, 255, 255, 0.5)', font: { family: 'Inter', size: 10 } }
            }
          };
        } else {
          chartType = "doughnut";
        }
      }
      
      const newChart = new Chart(ctx, {
        type: chartType,
        data: {
          labels: chart.labels,
          datasets: datasets
        },
        options: configOptions
      });
      activeChartObjects.push(newChart);
    }, 50);
  });
}

function renderGovernanceInfo(cert, qual) {
  const score = cert ? cert.overall_confidence_score : 95;
  document.getElementById("gov-score").innerText = `${score}%`;
  document.getElementById("gov-officer").innerText = cert ? cert.signoff_officer : "Gary Stone";
  document.getElementById("gov-verdict").innerText = cert ? cert.governance_verdict : "Data validation check completed successfully.";
  
  // Set stroke-dashoffset for radial progress SVG
  const circumference = 251.2;
  const offset = circumference - (score / 100) * circumference;
  const circle = document.getElementById("gov-radial-circle");
  if (circle) {
    circle.setAttribute("stroke-dashoffset", offset);
  }
  
  // Set audit timestamp
  const timestampEl = document.getElementById("gov-timestamp");
  if (timestampEl) {
    const now = new Date();
    const formatted = now.toISOString().replace('T', ' ').substring(0, 16);
    timestampEl.innerText = formatted;
  }
  
  // Set Data Quality scorecard values
  if (qual) {
    const pct = qual.before_rows > 0 ? Math.round((qual.after_rows / qual.before_rows) * 100) : 100;
    const summaryText = `${qual.after_rows.toLocaleString()} of ${qual.before_rows.toLocaleString()} retained (${qual.rows_dropped} dropped)`;
    const summaryLabel = document.getElementById("val-rows-summary");
    if (summaryLabel) summaryLabel.innerText = summaryText;
    const progressBar = document.getElementById("val-rows-progress");
    if (progressBar) {
      progressBar.style.width = `${pct}%`;
      progressBar.setAttribute("aria-valuenow", pct);
    }
  }
}

// Fullscreen toggle action helper
function toggleFullscreen(elementId) {
  const el = document.getElementById(elementId);
  if (!el) return;
  
  if (el.classList.contains("fullscreen-card")) {
    el.classList.remove("fullscreen-card");
    document.body.style.overflow = "";
  } else {
    document.querySelectorAll(".fullscreen-card").forEach(c => c.classList.remove("fullscreen-card"));
    el.classList.add("fullscreen-card");
    document.body.style.overflow = "hidden";
  }
}

// Chart data export helper
function exportChart(chartId) {
  const chartObj = activeChartObjects.find(c => c.canvas.id === `canvas_${chartId}`);
  if (!chartObj) return;
  
  const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify({
    title: chartObj.options.plugins.title ? chartObj.options.plugins.title.text : chartId,
    labels: chartObj.data.labels,
    datasets: chartObj.data.datasets.map(d => ({ label: d.label, data: d.data }))
  }, null, 2));
  
  const downloadAnchor = document.createElement('a');
  downloadAnchor.setAttribute("href", dataStr);
  downloadAnchor.setAttribute("download", `chart_${chartId}_data.json`);
  document.body.appendChild(downloadAnchor);
  downloadAnchor.click();
  downloadAnchor.remove();
}

// DOWNLOAD TRIGGER
function downloadFile(type) {
  const projId = currentProjectId || sessionStorage.getItem("current_project_id");
  if (!projId) return;
  
  const endpoint = `/api/project/${projId}/download/${type}`;
  window.open(`${getApiUrl()}${endpoint}`, "_blank");
}

// REPORTS INITIALIZER
async function initReportPreview() {
  if (reportInitialized) return;
  reportInitialized = true;

  document.getElementById("report-ref-id").innerText = currentProjectId;
  
  setupReportScrollspy();

  try {
    const res = await fetch(`${getApiUrl()}/api/project/${currentProjectId}`);
    if (!res.ok) return;
    const project = await res.json();
    
    const reportHtml = renderMarkdownToHtml(project.executive_report);
    document.getElementById("report-markdown-body").innerHTML = reportHtml;
  } catch (err) {
    document.getElementById("report-markdown-body").innerHTML = `<div class="alert alert-danger bg-transparent text-danger border-0">Error compiling report view.</div>`;
  }
}

function setupReportScrollspy() {
  const sheet = document.getElementById("report-sheet");
  if (!sheet) return;
  
  window.addEventListener("scroll", () => {
    const sections = ["cover", "sec-executive-summary", "sec-dataset-overview", "sec-data-quality-findings", "sec-key-insights", "sec-dashboard-highlights", "sec-recommendations", "sec-conclusion"];
    let currentActive = "cover";
    
    sections.forEach(sec => {
      const el = document.getElementById(sec);
      if (el) {
        const rect = el.getBoundingClientRect();
        if (rect.top <= 180) {
          currentActive = sec;
        }
      }
    });

    const tocMap = {
      "cover": "toc-cover",
      "sec-executive-summary": "toc-exec-summary",
      "sec-dataset-overview": "toc-dataset-overview",
      "sec-data-quality-findings": "toc-quality-findings",
      "sec-key-insights": "toc-key-insights",
      "sec-dashboard-highlights": "toc-dashboard-highlights",
      "sec-recommendations": "toc-recommendations",
      "sec-conclusion": "toc-conclusion"
    };

    const activeTOCId = tocMap[currentActive];
    document.querySelectorAll(".toc-item").forEach(item => {
      item.classList.remove("active");
      if (item.id === activeTOCId) {
        item.classList.add("active");
      }
    });
  });
}

function renderMarkdownToHtml(md) {
  if (!md) return "<p>Formulating report draft...</p>";
  
  let html = md;
  
  html = html.replace(/##\s+Executive Summary/g, '<h2 id="sec-executive-summary">Executive Summary</h2>');
  html = html.replace(/##\s+Dataset Overview/g, '<h2 id="sec-dataset-overview">Dataset Overview</h2>');
  html = html.replace(/##\s+Data Quality Findings/g, '<h2 id="sec-data-quality-findings">Data Quality Findings</h2>');
  html = html.replace(/##\s+Key Insights/g, '<h2 id="sec-key-insights">Key Insights</h2>');
  html = html.replace(/##\s+Dashboard Highlights/g, '<h2 id="sec-dashboard-highlights">Dashboard Highlights</h2>');
  html = html.replace(/##\s+Recommendations/g, '<h2 id="sec-recommendations">Recommendations</h2>');
  html = html.replace(/##\s+Conclusion/g, '<h2 id="sec-conclusion">Conclusion</h2>');
  
  html = html.replace(/^#\s+(.+)$/gm, '<h2 class="mt-4 mb-3 text-white border-bottom pb-2">$1</h2>');
  html = html.replace(/^##\s+(.+)$/gm, '<h2 class="mt-4 mb-3 text-white border-bottom pb-2">$1</h2>');
  html = html.replace(/^###\s+(.+)$/gm, '<h3 class="mt-3 text-white">$1</h3>');
  
  html = html.replace(/^\*\s+(.+)$/gm, '<ul><li>$1</li></ul>');
  html = html.replace(/^-\s+(.+)$/gm, '<ul><li>$1</li></ul>');
  html = html.replace(/<\/ul>\s*<ul>/g, "");
  
  html = html.replace(/^(?!<h|<ul|<li|<p)(.+)$/gm, '<p>$1</p>');
  
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong style="color: var(--text-main);">$1</strong>');
  
  return html;
}

/// AGENT LOGIC REGISTRY & POPUP TRIGGER
const AGENT_REGISTRY = {
  ceo: {
    name: "Amaldev K M",
    id: "EXBI-CEO-001",
    department: "Leadership",
    role: "Founder & CEO",
    experience: "Founder & CEO",
    avatar: "Image/avatar_amaldev.png",
    agent_type: "Human",
    current_role: "Leading product vision, strategy, and innovation for EXBI",
    skills: [
      "Data Science & Analytics",
      "Business Intelligence",
      "AI Product Development",
      "Dashboard Design",
      "Business Strategy"
    ],
    education: [
      "MBA (Finance & Marketing)",
      "B.Com Computer Applications",
      "Diploma in Data Science"
    ],
    role_desc: "Leading product vision, strategy, and innovation for EXBI.",
    vision: "Making data-driven decision-making simple, intelligent, and accessible through AI."
  },
  dataset_intelligence: {
    name: "Victor Vance",
    id: "EXBI-DI-001",
    department: "Data Engineering",
    role: "Lead Ingestion & Profiling Engineer",
    experience: "12+ Years Equivalent Industry Expertise",
    avatar: "Image/avatar_victor.png",
    agent_type: "AI",
    current_role: "Dataset Intelligence Agent (Phase 1 Ingestion & Discovery)",
    skills: ["Schema Validation", "Statistical Profiling", "Semantic Dimension Mapping"],
    responsibilities: [
      "Performs initial format validation of uploaded data structures",
      "Measures missing value densities and identifies columns profile",
      "Performs dynamic relationship discovery (Date/Categorical -> Numerical)"
    ],
    capabilities: [
      "Dynamic CSV/XLSX Schema Parsing",
      "Card-based Metadata Profiling",
      "Outlier Range Discovery"
    ],
    deliverables: [
      "Technical Profile Schema Blueprint",
      "Auto-categorized Columns Mapping",
      "Guided Analysis Configuration Setup"
    ]
  },
  business_analyst: {
    name: "Michael Reed",
    id: "EXBI-BA-001",
    department: "Business Analysis",
    role: "Senior Business Analyst",
    experience: "20+ Years Equivalent Industry Expertise",
    avatar: "Image/avatar_gary.png",
    agent_type: "AI",
    current_role: "Business Analyst Agent (Phase 2 Business Logic Design)",
    skills: ["KPI Design", "Strategic Analysis", "Business Intelligence", "Executive Reporting"],
    responsibilities: [
      "Understand user requirements and business objectives",
      "Identify opportunities and define success indicators",
      "Generate strategic recommendations based on dataset insights"
    ],
    capabilities: [
      "Revenue Analysis",
      "Customer Analysis",
      "Operational Analysis",
      "Market Analysis"
    ],
    deliverables: [
      "Business Insights Summary Document",
      "Executive Strategic Recommendations",
      "Targeted KPI Framework Definition"
    ]
  },
  data_quality: {
    name: "Quinn Vance",
    id: "EXBI-DQ-001",
    department: "Data Quality & Cleansing",
    role: "Principal Data Quality Engineer",
    experience: "10+ Years Equivalent Industry Expertise",
    avatar: "Image/avatar_quinn.png",
    agent_type: "AI",
    current_role: "Data Quality Agent (Phase 2 Cleaning & Standardization)",
    skills: ["Data Cleansing", "Median Imputation", "Z-Score Outlier Removal"],
    responsibilities: [
      "Detects and cleans duplicate record fields",
      "Imputes empty numerical coordinates using calculated medians",
      "Trims logical outlier outliers from metric calculations"
    ],
    capabilities: [
      "Format Case Standardization",
      "Anomaly Threshold Detection",
      "Logical Outlier Trimming"
    ],
    deliverables: [
      "Cleaned Dataset Ingestion Tables",
      "Cleansing Scorecards & Metric Reports",
      "Governance Sign-off Certificates"
    ]
  },
  visualization: {
    name: "Regina Chen",
    id: "EXBI-VIZ-001",
    department: "Data Visualization",
    role: "Senior Visualization Architect",
    experience: "8+ Years Equivalent Industry Expertise",
    avatar: "Image/avatar_regina.png",
    agent_type: "AI",
    current_role: "Visualization Agent (Phase 2 Interactive Dashboard Rendering)",
    skills: ["Chart.js Options Configuration", "Responsive Grid Layouts", "Aesthetic Design Systems"],
    responsibilities: [
      "Compiles structured Chart.js option datasets",
      "Aligns charts with visual guidelines matrix (Line, Bar, Pie)",
      "Applies premium responsive color theme structures"
    ],
    capabilities: [
      "Grouped Bar Charting",
      "Multi-Trend Line Graphs",
      "Donut Segment Slices Formatting"
    ],
    deliverables: [
      "Interactive Consultation Dashboard View",
      "Clean UI Graph Components",
      "Audience-Customized Layout Specs"
    ]
  },
  reporting: {
    name: "David Kim",
    id: "EXBI-RP-001",
    department: "Document Systems",
    role: "Executive Reporting Analyst",
    experience: "14+ Years Equivalent Industry Expertise",
    avatar: "Image/avatar_dave.png",
    agent_type: "AI",
    current_role: "Reporting Agent (Phase 2 Executive Summary Compile)",
    skills: ["Technical Business Writing", "Document Formatting", "Report Compilation"],
    responsibilities: [
      "Compiles final markdown-based executive strategy papers",
      "Orchestrates PDF, Word, PowerPoint and Excel file compilation",
      "Structures summary overviews and recommendations roadmaps"
    ],
    capabilities: [
      "Multi-format Export Pipelines",
      "High-grade Executive Writing Templates",
      "Structured Strategy Layout Compilation"
    ],
    deliverables: [
      "Word consulting documents (.docx)",
      "Slide deck presentation files (.pptx)",
      "Multi-tab spreadsheet workbooks (.xlsx)"
    ]
  }
};

function showAgentDetails(key) {
  const agent = AGENT_REGISTRY[key];
  if (!agent) return;
  
  document.getElementById("agent-modal-title").innerText = `${agent.name} - Resume`;
  document.getElementById("agent-modal-name").innerText = agent.name;
  document.getElementById("agent-modal-role").innerText = agent.role;
  document.getElementById("agent-modal-id").innerText = agent.id;
  
  const typeEl = document.getElementById("agent-modal-type");
  if (typeEl) typeEl.innerText = agent.agent_type || "AI";
  
  const deptEl = document.getElementById("agent-modal-dept");
  if (deptEl) deptEl.innerText = agent.department;
  const expEl = document.getElementById("agent-modal-exp");
  if (expEl) expEl.innerText = agent.experience;
  const currentRoleEl = document.getElementById("agent-modal-current-role");
  if (currentRoleEl) currentRoleEl.innerText = agent.current_role;
  
  const avatarImg = document.getElementById("agent-modal-avatar");
  if (avatarImg) {
    avatarImg.src = agent.avatar || "Image/favicon.png";
  }
  
  function populateList(elementId, items) {
    const list = document.getElementById(elementId);
    if (!list) return;
    list.innerHTML = "";
    if (items && items.length > 0) {
      items.forEach(item => {
        const li = document.createElement("li");
        li.className = "mb-1";
        li.innerText = item;
        list.appendChild(li);
      });
    }
  }
  
  const hSkills = document.getElementById("agent-modal-h-skills");
  const hResp = document.getElementById("agent-modal-h-resp");
  const hCap = document.getElementById("agent-modal-h-cap");
  const hDeliv = document.getElementById("agent-modal-h-deliv");
  
  if (key === "ceo") {
    if (hSkills) hSkills.innerText = "Core Skills";
    if (hResp) hResp.innerText = "Education";
    if (hCap) hCap.innerText = "Role";
    if (hDeliv) hDeliv.innerText = "Vision";
    
    populateList("agent-modal-skills", agent.skills);
    populateList("agent-modal-responsibilities", agent.education);
    populateList("agent-modal-capabilities", [agent.role_desc]);
    populateList("agent-modal-deliverables", [agent.vision]);
  } else {
    if (hSkills) hSkills.innerText = "Core Skills";
    if (hResp) hResp.innerText = "Responsibilities";
    if (hCap) hCap.innerText = "Capabilities";
    if (hDeliv) hDeliv.innerText = "Example Deliverables";
    
    populateList("agent-modal-skills", agent.skills);
    populateList("agent-modal-responsibilities", agent.responsibilities);
    populateList("agent-modal-capabilities", agent.capabilities);
    populateList("agent-modal-deliverables", agent.deliverables);
  }
  
  const modal = new bootstrap.Modal(document.getElementById("agentDetailsModal"));
  modal.show();
}
