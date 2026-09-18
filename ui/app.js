const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
let studio = null;
let appState = {};
let models = [];
let tools = {};
const tr = (key, vars) => window.KairnI18n ? window.KairnI18n.t(key, vars) : key;
const locale = () => window.KairnI18n?.language || appState.language || "pt-BR";
const FLOW = ["welcome", "model", "context", "output", "review", "environment", "cell1", "cell2", "connect", "agents", "ready", "monitor"];
const METER = ["model", "environment", "connect", "agents"];
const GROUPS = { welcome:"model", context:"model", output:"model", review:"model", cell1:"environment", cell2:"environment", ready:"agents" };
const AGENTS = { codex: { name: "Codex", icon: "ph-terminal-window", desc: "Responses API" }, claude: { name: "Claude Code", icon: "ph-brackets-curly", desc: "Anthropic Messages" }, opencode: { name: "OpenCode", icon: "ph-code-block", desc: "OpenAI-compatible" }, zcode: { name: "ZCode", icon: "ph-lightning", desc: "Custom provider" } };

function escapeHtml(value = "") { return String(value).replace(/[&<>'"]/g, (char) => ({ "&":"&amp;", "<":"&lt;", ">":"&gt;", "'":"&#39;", '"':"&quot;" }[char])); }
function formatTokens(value) { const n = Number(value || 0); return !Number.isFinite(n) ? "0" : n >= 1024 && n % 1024 === 0 ? `${n / 1024}K` : n.toLocaleString(locale()); }
function formatBytes(value) { const n = Number(value || 0); return n ? `${(n / 1e9).toFixed(1)} GB` : (locale() === "en" ? "remote size" : "tamanho remoto"); }
function invoke(name, ...args) { if (studio && typeof studio[name] === "function") { studio[name](...args); return true; } return false; }
window.KairnInvokeLanguage = (language) => invoke("setLanguage", language);
function toast(message, ok = true) { const el = $("#toast"); el.textContent = message; el.className = `toast show ${ok ? "ok" : "bad"}`; clearTimeout(toast.timer); toast.timer = setTimeout(() => { el.className = "toast"; }, 3000); }
function selectedModel() { return models.find((model) => model.key === appState.model) || models[0] || {}; }

function showScreen(name) {
  name = GROUPS[name] || name;
  if (!FLOW.includes(name)) return;
  $$("[data-screen]").forEach((screen) => { const active = (GROUPS[screen.dataset.screen] || screen.dataset.screen) === name && !["welcome", "ready"].includes(screen.dataset.screen); screen.hidden = !active; screen.classList.toggle("active", active); });
  $$("[data-nav]").forEach((button) => button.classList.toggle("active", (GROUPS[button.dataset.nav] || button.dataset.nav) === name));
  window.scrollTo({top:0, behavior:"instant"});
  const meterIndex = Math.max(0, METER.indexOf(name));
  $$("[data-meter]").forEach((item, index) => { item.classList.toggle("active", index === meterIndex); item.classList.toggle("done", index < meterIndex); });
}

function renderModels() {
  const box = $("#modelGrid");
  box.innerHTML = models.map((model) => { const description = locale() === "en" ? (model.description_en || model.description || "") : (model.description || model.description_en || ""); return `<article class="model-card ${model.key === appState.model ? "active" : ""}" data-model="${escapeHtml(model.key)}" tabindex="0" role="button" aria-pressed="${model.key === appState.model}" aria-label="${escapeHtml(model.name)}"><span class="check">${model.key === appState.model ? "✓" : ""}</span><span class="kicker">${escapeHtml(model.quant)}</span><h3>${escapeHtml(model.name)}</h3><p>${escapeHtml(description)}</p><div class="model-meta"><span>${formatBytes(model.size_bytes)}</span><span>VRAM ${escapeHtml(model.min_vram_gb || "—")} GB</span><span>${escapeHtml(model.revision || "main")}</span><span>SHA ${escapeHtml(String(model.sha256 || "").slice(0, 8))}</span></div></article>`; }).join("");
  $$("[data-model]").forEach((el) => { const choose = () => { appState.model = el.dataset.model; invoke("selectModel", el.dataset.model); if (!studio) { const model = selectedModel(); appState.context = model.context; appState.output = model.output; } renderState(); }; el.onclick = choose; el.onkeydown = (event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); choose(); } }; });
}

function syncPreset(key) { const value = Number(appState[key] || 0); $(`[data-preset-group="${key}"]`)?.querySelectorAll("button").forEach((button) => button.classList.toggle("active", Number(button.dataset.value) === value)); }
function renderRuntime() {
  ["context", "output", "parallel", "reasoning_budget", "temperature", "mtp_tokens", "top_k", "top_p", "min_p", "speculation"].forEach((key) => { const el = $(`#${key}`); if (el && document.activeElement !== el) el.value = appState[key] ?? (key === "speculation" ? "auto" : ""); });
  const selected = selectedModel(); const requiredBackend = selected.required_backend || selected.backend;
  if (requiredBackend === "prism-ml" && !$("#backend option[value='prism-ml']")) { const option = document.createElement("option"); option.value = "prism-ml"; option.textContent = "PrismML llama.cpp · Bonsai PTQ1_0"; $("#backend").appendChild(option); }
  const locked = Boolean(selected.required_backend); if (locked && appState.backend !== requiredBackend) { appState.backend = requiredBackend; invoke("setBackend", requiredBackend); }
  $("#backend").value = appState.backend || "official-layer"; $("#backend").disabled = locked;
  if ($("#modelBackendNotice")) { $("#modelBackendNotice").innerHTML = locked ? `<b>${locale() === "en" ? "PrismML fork required." : "Fork PrismML obrigatório."}</b> ${locale() === "en" ? "This PTQ1_0 model compiles a custom llama.cpp backend." : "Este modelo PTQ1_0 compila backend llama.cpp customizado."}` : `<b>${locale() === "en" ? "CUDA prebuilt is the default." : "CUDA prebuilt é o padrão."}</b> ${locale() === "en" ? "Official llama.cpp with pinned version and checksum." : "llama.cpp oficial com versão e checksum fixos."}`; }
  $("#contextDisplay").textContent = formatTokens(appState.context); $("#outputDisplay").textContent = formatTokens(appState.output); $("#summaryParallel").textContent = appState.parallel || 1;
  const auto = appState.parallel_auto !== false; $("#automaticSlots").classList.toggle("is-on", auto); $("#automaticSlots").setAttribute("aria-pressed", String(auto)); $("#slotDescription").textContent = auto ? tr("autoPreset") : tr("manualSlots"); $("#parallel").hidden = auto;
  syncPreset("context"); syncPreset("output");
  $("#reviewModel").textContent = selectedModel().name || "—"; $("#reviewContext").textContent = formatTokens(appState.context); $("#reviewOutput").textContent = formatTokens(appState.output);
  const warning = $("#memoryWarning"); const total = Number(appState.context || 0) * Number(appState.parallel || 1);
  if (total > 32768 || Number(appState.output) >= Number(appState.context)) { warning.hidden = false; warning.innerHTML = `<span class="notice-icon">!</span><p><b>${tr("reviewBudget", { total: formatTokens(total) })}</b> ${tr("budgetHint")}</p>`; } else warning.hidden = true;
  document.querySelectorAll('[data-next="environment"]').forEach(button => button.disabled = Number(appState.output) >= Number(appState.context));
  $("#mtpField").hidden = !Boolean(selectedModel().supports_mtp || selectedModel().mtp);
  $("#cacheNote").textContent = tr("cacheNote");
}

function renderTools() {
  const connected = Boolean(appState.connectionVerified && appState.agentsAvailable);
  const quickOnly = appState.connectionVerified && !appState.agentsAvailable;
  const results = Array.isArray(appState.configurationResults) ? appState.configurationResults : [];
  const resultFor = (key) => results.find((result) => String(result.tool || result.key || "").toLowerCase() === key.toLowerCase());
  const installed = Object.values(tools).filter((tool) => tool.installed).length;
  const configured = Object.entries(tools).filter(([key, tool]) => tool.configured && resultFor(key)?.ok !== false).length;
  const failed = results.filter((result) => result.ok === false).length;
  $("#agentConnectionStatus").classList.toggle("online", Boolean(appState.connectionVerified));
  $("#agentConnectionStatus").innerHTML = `<i></i> ${quickOnly ? tr("quickAgents") : connected ? (locale() === "en" ? "Gateway connected" : "Gateway conectado") : (locale() === "en" ? "Gateway offline" : "Gateway offline")}`;
  $("#agentSummaryTitle").textContent = failed ? tr("configFailed") : connected ? tr("found", { n: installed, plural: installed === 1 ? "" : locale() === "en" ? "s" : "s" }) : quickOnly ? tr("quickAgents") : tr("connectFirst");
  $("#agentSummaryText").textContent = failed ? `${failed} ${locale() === "en" ? "configuration(s) failed. Retry failed agents." : "configuração(ões) falharam. Tente novamente."}` : connected ? tr("readyToOpen", { n: configured, plural: configured === 1 ? "" : "s" }) : quickOnly ? tr("namedRequired") : tr("autoConfig");
  $("#agentGrid").innerHTML = Object.entries(AGENTS).map(([key, agent]) => { const tool = tools[key] || {}; const state = !tool.installed ? "missing" : tool.configured ? "ready" : "installed"; const status = state === "ready" ? tr("ready") : state === "installed" ? tr("detected") : tr("missing"); const button = !tool.installed ? tr("notInstalled") : connected ? tr("open") : tr("connectFirst"); const description = tr("agents." + key); return `<article class="agent-card ${state}"><div class="agent-card-top"><div class="agent-icon"><i class="ph ${agent.icon}"></i></div><span class="agent-state"><i></i>${status}</span></div><div class="agent-info"><h3>${agent.name}</h3><p>${description}</p><code class="agent-path" title="${escapeHtml(tool.path || "")}">${escapeHtml(tool.path || (tool.installed ? tr("localInstall") : tr("executableMissing")))}</code></div><div class="agent-actions">${tool.configured ? `<button class="text-button" data-disconnect="${key}">${tr("disconnect")}</button>` : ""}<button class="button ${tool.installed && connected ? "primary" : "secondary"}" data-launch="${key}" ${connected && tool.installed ? "" : "disabled"}>${button}${connected && tool.installed ? " <span>↗</span>" : ""}</button></div></article>`; }).join("");
  results.forEach((result) => { const key = String(result.tool || result.key || ""); const card = [...document.querySelectorAll(".agent-card")].find((el) => el.querySelector("h3")?.textContent.toLowerCase().replace(/\s+/g, "") === key.toLowerCase().replace(/\s+/g, "")); if (!card) return; if (result.ok === false) { card.classList.add("failed"); const state = card.querySelector(".agent-state"); if (state) state.innerHTML = `<i></i>${tr("failed")}`; const actions = card.querySelector(".agent-actions"); if (actions) actions.insertAdjacentHTML("afterbegin", `<button class="text-button" data-retry="${escapeHtml(key)}">${tr("retry")}</button>`); } const info = card.querySelector(".agent-info"); if (info && !info.querySelector(".agent-result")) info.insertAdjacentHTML("afterbegin", `<p class="agent-result ${result.ok === false ? "error" : "success"}">${escapeHtml(result.message || (result.ok === false ? tr("configFailed") : tr("configSuccess")))}${result.backup ? ` · ${tr("backup")}: ${escapeHtml(result.backup)}` : ""}</p>`); });
  $$("[data-config]").forEach((button) => button.onclick = () => invoke("configureTool", button.dataset.config)); $$("[data-disconnect]").forEach((button) => button.onclick = () => invoke("disconnectTool", button.dataset.disconnect)); $$("[data-launch]").forEach((button) => button.onclick = () => invoke("launch", button.dataset.launch)); $("#configureAll").disabled = !connected || !installed;
}

function setMetrics(metrics) { $("#connectionFeedback").textContent = metrics.message || tr("apiDown"); $("#connectionFeedback").className = `connection-feedback ${metrics.online ? "success" : "error"}`; const online = Boolean(metrics.online); const tps = Number(metrics.tps || 0); const preview = !studio; $("#globalStatus").classList.toggle("online", online); $("#globalStatus span").textContent = online ? tr("online") : tr("offline"); $("#metricOnline").textContent = online ? "Online" : "Offline"; $("#metricMessage").textContent = metrics.message || (online ? tr("health") : tr("apiDown")); $("#metricTps").textContent = tps.toLocaleString(locale(), { maximumFractionDigits: 1 }); $("#metricTokens").textContent = Number(metrics.tokens || 0).toLocaleString(locale()); $("#metricPulse").classList.toggle("online", online); $("#metricPulse").innerHTML = `<i></i> ${online ? tr("activeSignal") : tr("noSignal")}`; $(".gateway-state-icon i").className = online ? "ph ph-cloud-check" : "ph ph-cloud-slash"; $("#metricChecked").textContent = preview ? tr("localPreview") : `${tr("checked")} ${new Date().toLocaleTimeString(locale(), { hour:"2-digit", minute:"2-digit" })}`; $("#metricTpsBar").style.width = `${Math.min(100, Math.max(0, tps / 40 * 100))}%`; }
function refreshCode() { if (!studio) return; studio.code("github", (code) => { $("#githubCode").textContent = code || ""; }); studio.code("install", (code) => { $("#installCode").textContent = code || ""; }); studio.code("runtime", (code) => { $("#runtimeCode").textContent = code || ""; }); }
function renderState() {
  $("#tunnel_mode").value = appState.tunnel_mode || "quick";
  if (document.activeElement !== $("#tunnel_url")) $("#tunnel_url").value = appState.tunnel_url || "";
  $("#tunnelUrlField").hidden = appState.tunnel_mode !== "named";
  $("#tunnelHelp").textContent = appState.tunnel_mode === "named" ? tr("tunnelNamed") : tr("tunnelQuick");
  $("#connectApi").disabled = Boolean(appState.connectionBusy);
  $("#connectApi").textContent = appState.connectionBusy ? (locale() === "en" ? "Checking connection…" : "Verificando conexão…") : (locale() === "en" ? "Test and connect →" : "Testar e conectar →");
  $("#testApi").disabled = Boolean(appState.connectionBusy);
  if (appState.connectionBusy) $("#connectionFeedback").textContent = tr("checking");
  renderModels(); renderRuntime(); renderTools(); if (document.activeElement !== $("#baseUrl")) $("#baseUrl").value = appState.base_url || ""; $("#metricWatch").textContent = appState.sessionWatch ? "Ativo" : "Inativo"; $("#metricCheckMode").textContent = appState.sessionWatch ? "Automático" : "Manual"; $("#metricContext").textContent = Number(appState.serverContext || 0).toLocaleString("pt-BR"); }
function patch(payload) { if (payload.state) { const before = appState.stage; appState = { ...appState, ...payload.state }; renderState(); refreshCode(); if (appState.stage && appState.stage !== before && FLOW.includes(appState.stage)) showScreen(appState.stage); } if (payload.tools) { tools = payload.tools; renderTools(); } }
function collectOptions() { const out = {}; ["context", "output", "parallel", "reasoning_budget", "temperature", "mtp_tokens", "top_k", "top_p", "min_p", "speculation", "backend", "tunnel_mode", "tunnel_url"].forEach((key) => { const el = $(`#${key}`); if (el) out[key] = el.value; }); return out; }
function pushOptions(overrides = {}) { invoke("updateOptions", JSON.stringify({ ...collectOptions(), ...overrides })); }

function wireUI() {
  $$("[data-nav]").forEach((button) => button.onclick = () => showScreen(button.dataset.nav)); $$("[data-next]").forEach((button) => button.onclick = () => { const next = button.dataset.next; invoke("setSetupStage", next === "monitor" ? "ready" : next); showScreen(next); });
  ["context", "output"].forEach((key) => $(`[data-preset-group="${key}"]`)?.querySelectorAll("button").forEach((button) => button.onclick = () => { const value = Number(button.dataset.value); appState[key] = value; $(`#${key}`).value = value; syncPreset(key); renderRuntime(); pushOptions({ [key]: value }); }));
  ["context", "output", "parallel", "reasoning_budget", "temperature", "mtp_tokens", "top_k", "top_p", "min_p", "speculation", "backend", "tunnel_mode", "tunnel_url"].forEach((key) => { const el = $(`#${key}`); el.onchange = () => { appState[key] = ["backend", "tunnel_mode", "tunnel_url", "speculation"].includes(key) ? el.value : Number(el.value); if (key === "parallel") invoke("setAutomaticSlots", false); renderRuntime(); pushOptions({ [key]: el.value }); renderState(); }; });
  $("#automaticSlots").onclick = () => { const enabled = appState.parallel_auto === false; appState.parallel_auto = enabled; invoke("setAutomaticSlots", enabled); renderRuntime(); };
  ["#openKaggle", "#openKaggle2"].forEach((id) => $(id).onclick = () => { if (invoke("openKaggle")) $("#kaggleHint").classList.add("show"); else toast(tr("noKaggle")); }); $("#hideKaggle").onclick = () => { invoke("hideKaggle"); $("#kaggleHint").classList.remove("show"); };
  function copyCell(kind, id) {
    if (!studio) { toast(tr("copyDesktop"), false); return; }
    studio.copy(kind, (ok) => {
      if (ok) { $(id).textContent = tr("copied"); toast(kind === "github" ? tr("copyGithub") : kind === "install" ? tr("copyInstall") : tr("copyRuntime")); }
    });
  }
  $("#copyGitHub").onclick = () => copyCell("github", "#copyGitHub");
  $("#copyCell1").onclick = () => copyCell("install", "#copyCell1");
  $("#copyCell2").onclick = () => copyCell("runtime", "#copyCell2");
  $("#exportNotebook").onclick = () => { if (!invoke("exportNotebook")) toast(tr("exportDesktop"), false); };
  $$("[data-copy='smoke']").forEach((button) => button.onclick = () => invoke("copy", "smoke")); $("#connectApi").onclick = () => {
    if (!$("#baseUrl").value.trim() || !$("#apiKey").value.trim()) { $("#connectionFeedback").textContent = tr("fillUrl"); $("#connectionFeedback").className = "connection-feedback error"; return; }
    if (!invoke("connectApi", $("#baseUrl").value, $("#apiKey").value)) { $("#connectionFeedback").textContent = tr("desktopConnection"); return; }
    $("#connectApi").disabled = true;
  }; $("#toggleKey").onclick = () => { const input = $("#apiKey"); input.type = input.type === "password" ? "text" : "password"; $("#toggleKey").setAttribute("aria-label", input.type === "password" ? (locale() === "en" ? "Show API key" : "Mostrar API key") : (locale() === "en" ? "Hide API key" : "Ocultar API key")); }; $("#configureAll").onclick = () => invoke("configureAll"); $("#refreshTools").onclick = () => studio?.bootstrap((raw) => { tools = JSON.parse(raw).tools || {}; renderTools(); }); $("#testApi").onclick = () => invoke("testApi");
}

function installPreviewData() {
  models = [{ key:"gemopus",name:"Gemopus 4 26B A4B",quant:"Q4_K_M",description:"MoE compacto para coding e tarefas gerais.",description_en:"Compact MoE for coding and general tasks.",context:16384,output:8192 },{ key:"velum",name:"VELUM Coder",quant:"Q8_0",description:"Modelo 9B preservado em Q8 para código e ciclos longos.",description_en:"9B model kept at Q8 for code and long work cycles.",context:16384,output:8192 },{ key:"bonsai-abliterated",name:"Bonsai Abliterated",quant:"PTQ1_0",required_backend:"prism-ml",description:"Modelo PrismML com backend obrigatório.",description_en:"PrismML model with a required backend.",context:16384,output:8192 },{ key:"qwen",name:"Qwen3.8 27B Aggressive",quant:"Q4_K_P",description:"Modelo denso para coding e tool use.",description_en:"Dense model for coding and tool use.",context:16384,output:8192 }];
  appState = { model:"gemopus",context:16384,output:8192,parallel:2,parallel_auto:true,reasoning_budget:3072,temperature:.6,mtp_tokens:2,speculation:"auto",top_k:40,top_p:.95,min_p:.05,backend:"official-layer",serverContext:32768,base_url:"",hasApiKey:false,sessionWatch:false }; tools = {}; $("#previewNotice").hidden = false; renderState(); showScreen("model"); $("#installCode").textContent = "# Código real disponível no aplicativo desktop."; $("#runtimeCode").textContent = "# Código real disponível no aplicativo desktop."; setMetrics({ online:false,tps:0,tokens:0,message:"Preview da interface" });
}

function init() {
  wireUI(); if (typeof QWebChannel === "undefined" || typeof qt === "undefined") { installPreviewData(); return; }
  new QWebChannel(qt.webChannelTransport, (channel) => { studio = channel.objects.studio; studio.toast.connect((message, ok) => toast(message, ok)); studio.stateChanged.connect((raw) => { try { patch(JSON.parse(raw)); } catch (_) {} }); studio.metricsChanged.connect((raw) => { try { setMetrics(JSON.parse(raw)); } catch (_) {} }); studio.bootstrap((raw) => { const data = JSON.parse(raw); appState = data.state || {}; models = data.models || []; tools = data.tools || {}; renderState(); refreshCode(); showScreen(FLOW.includes(appState.resumeStage) ? appState.resumeStage : "welcome"); studio.metrics((metrics) => setMetrics(JSON.parse(metrics))); }); });
}
window.addEventListener("languageChanged", () => { if (appState && Object.keys(appState).length) { renderModels(); renderRuntime(); renderTools(); setMetrics({ online: Boolean(appState.connectionVerified), tps: appState.tps || 0, tokens: appState.tokens || 0, message: appState.connectionMessage || "" }); } });
document.addEventListener("DOMContentLoaded", () => {
  if (typeof qt !== "undefined" && typeof QWebChannel === "undefined") {
    const script = document.createElement("script");
    script.src = "qrc:///qtwebchannel/qwebchannel.js";
    script.onload = init;
    script.onerror = () => { installPreviewData(); toast("Bridge Qt indisponível. Reinicie aplicativo.", false); };
    document.head.appendChild(script);
  } else init();
});
