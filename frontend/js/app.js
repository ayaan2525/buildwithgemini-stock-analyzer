/**
 * Frontend Application for Stock Pulse Analyzer
 */

// Application State
let currentRunData = null;
let selectedDomain = "AI";
let selectedRatingFilter = "ALL"; // ALL, BUY, CAUTIOUS
let isPollingStatus = false;

// DOM Elements
const rankingsContainer = document.getElementById("rankingsContainer");
const summaryText = document.getElementById("summaryText");
const statusLabel = document.getElementById("statusLabel");
const statusDot = document.getElementById("statusDot");
const lastUpdatedLabel = document.getElementById("lastUpdatedLabel");
const historySelect = document.getElementById("historySelect");
const triggerScanBtn = document.getElementById("triggerScanBtn");
const scanIcon = document.getElementById("scanIcon");
const scanText = document.getElementById("scanText");
const domainTabs = document.querySelectorAll(".domain-tab");
const ratingFilterBtns = document.querySelectorAll(".rating-filter");

// Chat Drawer Elements
const chatDrawer = document.getElementById("chatDrawer");
const drawerBackdrop = document.getElementById("drawerBackdrop");
const openChatBtn = document.getElementById("openChatBtn");
const closeChatBtn = document.getElementById("closeChatBtn");
const chatForm = document.getElementById("chatForm");
const chatInput = document.getElementById("chatInput");
const chatMessages = document.getElementById("chatMessages");
const quickPrompts = document.querySelectorAll(".quick-prompt");

// Initialize application
document.addEventListener("DOMContentLoaded", () => {
  try { lucide.createIcons(); } catch (e) {}
  try { setupEventListeners(); } catch (e) { console.error("Setup listeners error:", e); }
  loadLatestAnalysis();
  loadHistoryList();
  checkScanStatus();
  refreshPortfolioBadge();
  if (window.location.search.includes("chat=open") || window.location.hash === "#chat") {
    setTimeout(openDrawer, 300);
  }
});

function setupEventListeners() {
  // Domain tab clicks
  domainTabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      domainTabs.forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");
      selectedDomain = tab.getAttribute("data-domain");
      renderRankings();
    });
  });

  // Rating filter clicks (All 10, 5 Buys, 5 Cautious)
  ratingFilterBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      ratingFilterBtns.forEach((b) => {
        b.classList.remove("active", "bg-slate-800", "text-white");
        b.classList.add("text-slate-400");
      });
      btn.classList.add("active", "bg-slate-800", "text-white");
      btn.classList.remove("text-slate-400");
      selectedRatingFilter = btn.getAttribute("data-rating");
      renderRankings();
    });
  });

  // History selector
  if (historySelect) {
    historySelect.addEventListener("change", (e) => {
      const val = e.target.value;
      if (val === "latest") {
        loadLatestAnalysis();
      } else {
        loadRunById(parseInt(val, 10));
      }
    });
  }

  // Trigger scan button
  if (triggerScanBtn) {
    triggerScanBtn.addEventListener("click", () => {
      triggerNewScan();
    });
  }

  // Chat Drawer toggle
  if (openChatBtn) openChatBtn.addEventListener("click", openDrawer);
  if (closeChatBtn) closeChatBtn.addEventListener("click", closeDrawer);
  if (drawerBackdrop) drawerBackdrop.addEventListener("click", closeDrawer);

  // Portfolio Memory Button click
  const portfolioMemoryBtn = document.getElementById("portfolioMemoryBtn");
  if (portfolioMemoryBtn) {
    portfolioMemoryBtn.addEventListener("click", () => {
      openDrawer();
      sendMessage("Show my portfolio");
    });
  }

  // Chat form submit
  if (chatForm) {
    chatForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const text = chatInput ? chatInput.value.trim() : "";
      if (!text) return;
      sendMessage(text);
      if (chatInput) chatInput.value = "";
    });
  }

  // Quick prompts
  document.querySelectorAll(".quick-prompt").forEach((btn) => {
    btn.addEventListener("click", () => {
      const q = btn.textContent.trim();
      sendMessage(q);
    });
  });
}

function openDrawer() {
  chatDrawer.classList.remove("translate-x-full");
  drawerBackdrop.classList.remove("hidden");
}

function closeDrawer() {
  chatDrawer.classList.add("translate-x-full");
  drawerBackdrop.classList.add("hidden");
}

async function loadLatestAnalysis() {
  try {
    if (statusLabel) statusLabel.textContent = "Loading...";
    const res = await fetch("/api/analysis/latest");
    const data = await res.json();

    if (data.status === "empty") {
      if (summaryText) summaryText.textContent = "No analysis completed yet. Click 'Scan Latest News' to start.";
      if (statusLabel) statusLabel.textContent = "Awaiting First Scan";
      return;
    }

    currentRunData = data;
    updateUIWithRun(data);
  } catch (err) {
    console.error("Failed to load latest analysis:", err);
    if (statusLabel) statusLabel.textContent = "Connection Error";
  }
}

async function loadRunById(runId) {
  try {
    if (statusLabel) statusLabel.textContent = `Loading Run #${runId}...`;
    const res = await fetch(`/api/analysis/run/${runId}`);
    const data = await res.json();
    currentRunData = data;
    updateUIWithRun(data);
  } catch (err) {
    console.error("Failed to load run:", err);
  }
}

async function loadHistoryList() {
  try {
    const res = await fetch("/api/analysis/history?limit=20");
    const runs = await res.json();
    if (historySelect) {
      historySelect.innerHTML = `<option value="latest">Latest Snapshot</option>`;

      runs.forEach((r) => {
        const date = new Date(r.timestamp);
        const formatted = date.toLocaleDateString("en-US", {
          month: "short",
          day: "numeric",
          hour: "2-digit",
          minute: "2-digit"
        });
        const opt = document.createElement("option");
        opt.value = r.id;
        opt.textContent = `Run #${r.id} (${formatted})`;
        historySelect.appendChild(opt);
      });
    }
  } catch (err) {
    console.error("Failed to fetch history runs:", err);
  }
}

function updateUIWithRun(data) {
  if (statusLabel) statusLabel.textContent = "Active";
  if (statusDot) statusDot.className = "w-2 h-2 rounded-full bg-emerald-500 animate-pulse";

  if (lastUpdatedLabel) {
    if (data.timestamp) {
      const d = new Date(data.timestamp);
      lastUpdatedLabel.textContent = `Scanned ${d.toLocaleDateString()} ${d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
    } else {
      lastUpdatedLabel.textContent = "Live";
    }
  }

  if (summaryText) {
    summaryText.textContent = data.summary || "7-Day analysis completed across AI, Chips, and Energy.";
  }
  renderDominoChain(data.domino_chain);
  renderRankings();
}

function renderDominoChain(domino) {
  const stepsContainer = document.getElementById("dominoSteps");
  const takeawayLabel = document.getElementById("dominoTakeaway");
  if (!stepsContainer) return;

  if (!domino || !domino.steps) {
    stepsContainer.innerHTML = "";
    return;
  }

  if (takeawayLabel && domino.takeaway) {
    takeawayLabel.textContent = domino.takeaway;
  }

  stepsContainer.innerHTML = domino.steps.map((step, idx) => {
    return `
      <div class="relative p-3 rounded-lg bg-slate-950/70 border border-indigo-500/20 hover:border-indigo-500/40 transition">
        <div class="flex items-center space-x-2 text-indigo-400 text-xs font-bold mb-1">
          <span class="w-5 h-5 rounded-md bg-indigo-500/20 flex items-center justify-center text-[11px]">${idx + 1}</span>
          <span>${escapeHtml(step.domain)}</span>
        </div>
        <div class="text-xs font-semibold text-white tracking-tight">${escapeHtml(step.lead)}</div>
        <p class="text-[11px] text-slate-400 mt-1 leading-snug">${escapeHtml(step.description)}</p>
      </div>
    `;
  }).join("");
}

window.toggleDominoChain = function() {
  const el = document.getElementById("dominoCollapse");
  const chevron = document.getElementById("dominoChevron");
  if (!el) return;
  const isHidden = el.classList.contains("hidden");
  if (isHidden) {
    el.classList.remove("hidden");
    if (chevron) chevron.classList.add("rotate-180");
  } else {
    el.classList.add("hidden");
    if (chevron) chevron.classList.remove("rotate-180");
  }
};

function renderRankings() {
  rankingsContainer.innerHTML = "";
  if (!currentRunData || !currentRunData.domains) {
    rankingsContainer.innerHTML = `<div class="text-center py-12 text-slate-500">No ranking data available.</div>`;
    return;
  }

  const domainKeys = selectedDomain === "ALL" ? ["AI", "Chips", "Energy"] : [selectedDomain];

  domainKeys.forEach((domKey) => {
    const domData = currentRunData.domains[domKey];
    if (!domData) return;

    const domainSection = document.createElement("section");
    domainSection.className = "space-y-3";

    const domainTitles = {
      AI: { label: "Artificial Intelligence & Cloud Ecosystem", icon: "cpu" },
      Chips: { label: "Semiconductors & Foundry Fabrication", icon: "zap" },
      Energy: { label: "Energy, Nuclear & Power for Data Centers", icon: "battery-charging" }
    };

    const info = domainTitles[domKey] || { label: domKey, icon: "layers" };

    const showBuy = selectedRatingFilter === "ALL" || selectedRatingFilter === "BUY";
    const showCautious = selectedRatingFilter === "ALL" || selectedRatingFilter === "CAUTIOUS";

    let contentHtml = "";

    if (showBuy && showCautious) {
      // Split 2 Columns
      contentHtml = `
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <!-- Buy Column -->
          <div class="space-y-3">
            <div class="flex items-center justify-between px-1">
              <div class="flex items-center space-x-1.5">
                <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
                <h3 class="text-xs font-bold uppercase tracking-wider text-emerald-400">Top 5 Positive (Buy)</h3>
              </div>
              <span class="text-[10px] text-emerald-500/80 font-medium">Growth Catalysts</span>
            </div>
            <div class="space-y-2.5" id="buy-container-${domKey}"></div>
          </div>

          <!-- Cautious Column -->
          <div class="space-y-3">
            <div class="flex items-center justify-between px-1">
              <div class="flex items-center space-x-1.5">
                <span class="w-2 h-2 rounded-full bg-rose-500"></span>
                <h3 class="text-xs font-bold uppercase tracking-wider text-rose-400">Top 5 Cautious (Not to Buy)</h3>
              </div>
              <span class="text-[10px] text-rose-500/80 font-medium">Headwinds & Multiple Risk</span>
            </div>
            <div class="space-y-2.5" id="cautious-container-${domKey}"></div>
          </div>
        </div>
      `;
    } else if (showBuy) {
      // Only Buy picks in responsive grid
      contentHtml = `
        <div class="flex items-center justify-between px-1">
          <div class="flex items-center space-x-1.5">
            <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
            <h3 class="text-xs font-bold uppercase tracking-wider text-emerald-400">Top 5 Positive Ratings (Buy)</h3>
          </div>
          <span class="text-xs text-slate-400 font-mono">5 High-Conviction Picks</span>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3" id="buy-container-${domKey}"></div>
      `;
    } else {
      // Only Cautious picks in responsive grid
      contentHtml = `
        <div class="flex items-center justify-between px-1">
          <div class="flex items-center space-x-1.5">
            <span class="w-2 h-2 rounded-full bg-rose-500"></span>
            <h3 class="text-xs font-bold uppercase tracking-wider text-rose-400">Top 5 Cautionary Alerts (Not to Buy)</h3>
          </div>
          <span class="text-xs text-slate-400 font-mono">5 Downside Risk Alerts</span>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3" id="cautious-container-${domKey}"></div>
      `;
    }

    domainSection.innerHTML = `
      <div class="flex items-center justify-between border-b border-slate-800 pb-2">
        <div class="flex items-center space-x-2">
          <div class="p-1.5 rounded-lg bg-slate-800 text-slate-300">
            <i data-lucide="${info.icon}" class="w-4 h-4"></i>
          </div>
          <h2 class="text-sm font-bold text-white tracking-tight">${info.label}</h2>
        </div>
        <span class="text-[11px] px-2 py-0.5 rounded bg-slate-800 text-slate-400 font-mono">
          ${(domData.buy || []).length + (domData.cautious || []).length} Stocks Scanned
        </span>
      </div>
      ${contentHtml}
    `;

    rankingsContainer.appendChild(domainSection);

    // Populate Buy picks
    if (showBuy) {
      const buyContainer = document.getElementById(`buy-container-${domKey}`);
      if (buyContainer) {
        (domData.buy || []).slice(0, 5).forEach((stock) => {
          buyContainer.appendChild(createStockCard(stock, "BUY"));
        });
      }
    }

    // Populate Cautious picks
    if (showCautious) {
      const cautiousContainer = document.getElementById(`cautious-container-${domKey}`);
      if (cautiousContainer) {
        (domData.cautious || []).slice(0, 5).forEach((stock) => {
          cautiousContainer.appendChild(createStockCard(stock, "CAUTIOUS"));
        });
      }
    }
  });

  lucide.createIcons();
}

function createStockCard(stock, rating) {
  const isBuy = rating === "BUY";
  const card = document.createElement("div");

  const borderClass = isBuy
    ? "border-slate-800 hover:border-emerald-500/40 bg-slate-900/60 hover:bg-slate-900"
    : "border-slate-800 hover:border-rose-500/40 bg-slate-900/60 hover:bg-slate-900";

  const badgeClass = isBuy
    ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
    : "bg-rose-500/10 text-rose-400 border border-rose-500/30";

  const rankBadge = isBuy
    ? "bg-emerald-950 text-emerald-400 border border-emerald-500/30"
    : "bg-rose-950 text-rose-400 border border-rose-500/30";

  const changeVal = stock.weekly_change_pct !== null ? stock.weekly_change_pct : 0.0;
  const changeColor = changeVal >= 0 ? "text-emerald-400" : "text-rose-400";
  const changeBg = changeVal >= 0 ? "bg-emerald-500/10" : "bg-rose-500/10";
  const changeSign = changeVal >= 0 ? "+" : "";

  const priceFormatted = stock.current_price ? `$${stock.current_price.toFixed(2)}` : "—";

  // Beginner risk badge
  const risk = stock.beginner_risk || {
    badge: isBuy ? "🟢 Core Anchor" : "🔴 High Volatility",
    desc: "Check position size."
  };

  const bullArg = stock.bull_case || (stock.catalysts && stock.catalysts[0]) || "Market momentum setup.";
  const bearArg = stock.bear_case || (stock.risks && stock.risks[0]) || "Multiple & sector volatility.";

  card.className = `p-3.5 rounded-xl border ${borderClass} transition-all duration-150 shadow-sm hover:shadow-md flex flex-col justify-between space-y-2.5`;
  card.innerHTML = `
    <div>
      <div class="flex items-start justify-between gap-2">
        <div class="flex items-center space-x-2">
          <span class="w-5 h-5 rounded flex items-center justify-center text-[10px] font-bold ${rankBadge}">
            #${stock.rank}
          </span>
          <div>
            <div class="flex items-center space-x-1.5">
              <span class="text-sm font-bold text-white tracking-wide">${stock.ticker}</span>
              <span class="text-[10px] font-semibold px-1.5 py-0.2 rounded ${badgeClass}">${rating}</span>
              <span class="text-[9px] font-medium px-1.5 py-0.2 rounded bg-slate-800 text-slate-300 border border-slate-700/60">${escapeHtml(risk.badge || '🟢 Core')}</span>
            </div>
            <p class="text-[11px] text-slate-400 truncate max-w-[190px] sm:max-w-[240px]">${escapeHtml(stock.company_name)}</p>
          </div>
        </div>

        <div class="text-right shrink-0">
          <div class="text-xs font-mono font-bold text-slate-100">${priceFormatted}</div>
          <div class="text-[10px] font-mono px-1.5 py-0.5 rounded ${changeBg} ${changeColor} font-semibold inline-block mt-0.5">
            ${changeSign}${changeVal.toFixed(1)}% 7d
          </div>
        </div>
      </div>

      <!-- Courtroom Debate: Clean Bull & Bear rows -->
      <div class="mt-2.5 space-y-1.5">
        <div class="flex items-start space-x-1.5 text-xs">
          <span class="px-1.5 py-0.2 rounded text-[9px] font-bold uppercase tracking-wider bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 shrink-0 mt-0.5">🐂 Bull</span>
          <p class="text-[11px] text-slate-300 leading-snug line-clamp-2">${escapeHtml(bullArg)}</p>
        </div>

        <div class="flex items-start space-x-1.5 text-xs">
          <span class="px-1.5 py-0.2 rounded text-[9px] font-bold uppercase tracking-wider bg-rose-500/10 text-rose-400 border border-rose-500/20 shrink-0 mt-0.5">🐻 Bear</span>
          <p class="text-[11px] text-slate-400 leading-snug line-clamp-2">${escapeHtml(bearArg)}</p>
        </div>
      </div>
    </div>

    <!-- Quick Ask link -->
    <div class="pt-2 border-t border-slate-800/80 flex items-center justify-between text-[11px]">
      <span class="text-slate-500 text-[10px]">Sentiment Score: <strong class="${changeColor}">${stock.sentiment_score ? stock.sentiment_score.toFixed(1) : '0.0'}</strong></span>
      <button onclick="askAboutStock('${stock.ticker}', '${stock.company_name}')" class="text-indigo-400 hover:text-indigo-300 flex items-center space-x-1 font-medium transition text-[11px]">
        <span>Deep Dive</span>
        <i data-lucide="arrow-right" class="w-3 h-3"></i>
      </button>
    </div>
  `;

  return card;
}

window.askAboutStock = function(ticker, company) {
  openDrawer();
  sendMessage(`Give me the Bull vs Bear case, recent news drivers, and beginner safety advice for ${ticker} (${company}).`);
};

window.askAboutDomino = function() {
  openDrawer();
  sendMessage("Explain the supply chain ripple effect from AI software to Chip hardware and Energy power grids.");
};

async function triggerNewScan() {
  try {
    triggerScanBtn.disabled = true;
    scanIcon.classList.add("animate-spin");
    scanText.textContent = "Scanning 7d News...";
    if (statusLabel) statusLabel.textContent = "Ingesting Google News & quotes...";
    if (statusDot) statusDot.className = "w-2 h-2 rounded-full bg-amber-500 animate-ping";

    const res = await fetch("/api/analysis/trigger", { method: "POST" });
    const data = await res.json();

    pollScanStatus();
  } catch (err) {
    console.error("Failed to trigger scan:", err);
    triggerScanBtn.disabled = false;
    scanIcon.classList.remove("animate-spin");
    scanText.textContent = "Scan Latest News";
  }
}

function pollScanStatus() {
  if (isPollingStatus) return;
  isPollingStatus = true;

  const interval = setInterval(async () => {
    try {
      const res = await fetch("/api/analysis/status");
      const status = await res.json();

      if (!status.is_running) {
        clearInterval(interval);
        isPollingStatus = false;
        triggerScanBtn.disabled = false;
        scanIcon.classList.remove("animate-spin");
        scanText.textContent = "Scan Latest News";
        await loadLatestAnalysis();
        await loadHistoryList();
      } else {
        if (statusLabel) statusLabel.textContent = status.progress || "Scanning...";
      }
    } catch (err) {
      clearInterval(interval);
      isPollingStatus = false;
      triggerScanBtn.disabled = false;
      scanIcon.classList.remove("animate-spin");
      scanText.textContent = "Scan Latest News";
    }
  }, 2000);
}

async function checkScanStatus() {
  try {
    const res = await fetch("/api/analysis/status");
    const status = await res.json();
    if (status.is_running) {
      triggerScanBtn.disabled = true;
      scanIcon.classList.add("animate-spin");
      scanText.textContent = "Scanning...";
      pollScanStatus();
    }
  } catch (e) {}
}

async function sendMessage(text) {
  appendUserMessage(text);
  const loadingId = appendLoadingMessage();

  try {
    const res = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: text })
    });
    const data = await res.json();
    removeLoadingMessage(loadingId);
    appendAssistantMessage(data.answer);
    refreshPortfolioBadge();
  } catch (err) {
    removeLoadingMessage(loadingId);
    appendAssistantMessage("⚠️ Sorry, unable to fetch an answer right now. Please verify server connection.");
  }
}

function appendUserMessage(text) {
  const div = document.createElement("div");
  div.className = "flex items-start justify-end space-x-2";
  div.innerHTML = `
    <div class="bg-emerald-600 text-white rounded-2xl rounded-tr-sm p-3 text-xs leading-relaxed max-w-[85%] shadow-sm">
      ${escapeHtml(text)}
    </div>
  `;
  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function appendAssistantMessage(markdownContent) {
  const div = document.createElement("div");
  div.className = "flex items-start space-x-3";
  div.innerHTML = `
    <div class="w-7 h-7 rounded bg-emerald-500/20 text-emerald-400 flex items-center justify-center shrink-0 mt-0.5">
      <i data-lucide="bot" class="w-4 h-4"></i>
    </div>
    <div class="bg-slate-800/90 rounded-2xl rounded-tl-sm p-3 text-xs leading-relaxed text-slate-200 border border-slate-700/60 shadow-sm max-w-[88%] markdown-body">
      ${marked.parse(markdownContent)}
    </div>
  `;
  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  lucide.createIcons();
}

function appendLoadingMessage() {
  const id = "loading-" + Date.now();
  const div = document.createElement("div");
  div.id = id;
  div.className = "flex items-start space-x-3";
  div.innerHTML = `
    <div class="w-7 h-7 rounded bg-emerald-500/20 text-emerald-400 flex items-center justify-center shrink-0 mt-0.5">
      <i data-lucide="bot" class="w-4 h-4"></i>
    </div>
    <div class="bg-slate-800/70 rounded-2xl rounded-tl-sm px-4 py-2 text-xs text-slate-400 border border-slate-700/50 flex items-center space-x-2">
      <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping"></span>
      <span>Analyzing news & ratings...</span>
    </div>
  `;
  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  lucide.createIcons();
  return id;
}

function removeLoadingMessage(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

function escapeHtml(str) {
  if (!str) return "";
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

async function refreshPortfolioBadge() {
  try {
    const res = await fetch("/api/portfolio");
    const data = await res.json();
    const count = data.portfolio ? data.portfolio.length : 0;
    const badge = document.getElementById("portfolioCountBadge");
    if (badge) {
      badge.textContent = count;
      if (count > 0) {
        badge.classList.remove("text-indigo-300", "bg-indigo-500/20");
        badge.classList.add("text-emerald-300", "bg-emerald-500/20");
      } else {
        badge.classList.remove("text-emerald-300", "bg-emerald-500/20");
        badge.classList.add("text-indigo-300", "bg-indigo-500/20");
      }
    }
  } catch (e) {}
}
