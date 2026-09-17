const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
let studio = null;
let appState = {};
let models = [];
let tools = {};
const FLOW = ["welcome", "model", "context", "output", "review", "environment", "cell1", "cell2", "connect", "agents", "ready", "monitor"];
const METER = ["model", "environment", "connect", "agents"];
const GROUPS = { welcome:"model", context:"model", output:"model", review:"model", cell1:"environment", cell2:"environment", ready:"agents" };
const AGENTS = { codex: { name: "Codex", icon: "ph-terminal-window", desc: "Responses API" }, claude: { name: "Claude Code", icon: "ph-brackets-curly", desc: "Anthropic Messages" }, opencode: { name: "OpenCode", icon: "ph-code-block", desc: "OpenAI-compatible" }, zcode: { name: "ZCode", icon: "ph-lightning", desc: "Custom provider" } };

function escapeHtml(value = "") { return String(value).replace(/[&<>'"]/g, (char) => ({ "&":"&amp;", "<":"&lt;", ">":"&gt;", "'":"&#39;", '"':"&quot;" }[char])); }
function formatTokens(value) { const n = Number(value || 0); return !Number.isFinite(n) ? "0" : n >= 1024 && n % 1024 === 0 ? `${n / 1024}K` : n.toLocaleString("pt-BR"); }
function formatBytes(value) { const n = Number(value || 0); return n ? `${(n / 1e9).toFixed(1)} GB` : "tamanho remoto"; }
function invoke(name, ...args) { if (studio && typeof studio[name] === "function") { studio[name](...args); return true; } return false; }
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
  box.innerHTML = models.map((model) => `<article class="model-card ${model.key === appState.model ? "active" : ""}" data-model="${escapeHtml(model.key)}" tabindex="0" role="button" aria-pressed="${model.key === appState.model}"><span class="check">${model.key === appState.model ? "✓" : ""}</span><span class="kicker">${escapeHtml(model.quant)}</span><h3>${escapeHtml(model.name)}</h3><p>${escapeHtml(model.description)}</p><div class="model-meta"><span>${formatBytes(model.size_bytes)}</span><span>VRAM ${escapeHtml(model.min_vram_gb || "—")} GB</span><span>${escapeHtml(model.revision || "main")}</span><span>SHA ${escapeHtml(String(model.sha256 || "").slice(0, 8))}</span></div></article>`).join("");
  $$("[data-model]").forEach((el) => { const choose = () => { appState.model = el.dataset.model; invoke("selectModel", el.dataset.model); if (!studio) { const model = selectedModel(); appState.context = model.context; appState.output = model.output; } renderState(); }; el.onclick = choose; el.onkeydown = (event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); choose(); } }; });
}

function syncPreset(key) { const value = Number(appState[key] || 0); $(`[data-preset-group="${key}"]`)?.querySelectorAll("button").forEach((button) => button.classList.toggle("active", Number(button.dataset.value) === value)); }
function renderRuntime() {
  ["context", "output", "parallel", "reasoning_budget", "temperature", "mtp_tokens", "top_k", "top_p", "min_p"].forEach((key) => { const el = $(`#${key}`); if (el && document.activeElement !== el) el.value = appState[key] ?? ""; });
  $("#backend").value = appState.backend || "official-layer";
  $("#contextDisplay").textContent = formatTokens(appState.context); $("#outputDisplay").textContent = formatTokens(appState.output); $("#summaryParallel").textContent = appState.parallel || 1;
  const auto = appState.parallel_auto !== false; $("#automaticSlots").classList.toggle("is-on", auto); $("#automaticSlots").setAttribute("aria-pressed", String(auto)); $("#slotDescription").textContent = auto ? "Definido automaticamente para este preset." : "Ajuste manual ativo."; $("#parallel").hidden = auto;
  syncPreset("context"); syncPreset("output");
  $("#reviewModel").textContent = selectedModel().name || "—"; $("#reviewContext").textContent = formatTokens(appState.context); $("#reviewOutput").textContent = formatTokens(appState.output);
  const warning = $("#memoryWarning"); const total = Number(appState.context || 0) * Number(appState.parallel || 1);
  if (total > 32768 || Number(appState.output) >= Number(appState.context)) { warning.hidden = false; warning.innerHTML = `<span class="notice-icon">!</span><p><b>Revise orçamento (${formatTokens(total)} total).</b> Resposta precisa caber no contexto junto com prompt. Contexto alto pode exceder VRAM.</p>`; } else warning.hidden = true;
  document.querySelectorAll('[data-next="environment"]').forEach(button => button.disabled = Number(appState.output) >= Number(appState.context));
  $("#mtpField").hidden = !Boolean(selectedModel().supports_mtp || selectedModel().mtp);
}

function renderTools() {
  const connected = Boolean(appState.connectionVerified && appState.agentsAvailable);
  const quickOnly = appState.connectionVerified && !appState.agentsAvailable;
  const installed = Object.values(tools).filter((tool) => tool.installed).length;
  const configured = Object.values(tools).filter((tool) => tool.configured).length;
  $("#agentConnectionStatus").classList.toggle("online", Boolean(appState.connectionVerified));
  $("#agentConnectionStatus").innerHTML = `<i></i> ${quickOnly ? "API online · sem SSE" : connected ? "Gateway conectado" : "Gateway offline"}`;
  $("#agentSummaryTitle").textContent = connected ? `${installed} ferramenta${installed === 1 ? "" : "s"} encontrada${installed === 1 ? "" : "s"}` : quickOnly ? "Túnel sem suporte a streaming" : "Conecte API primeiro";
  $("#agentSummaryText").textContent = connected ? `${configured} pronta${configured === 1 ? "" : "s"} para abrir. Configuração cria backup antes de alterar arquivos.` : quickOnly ? "Gere notebook com túnel nomeado para liberar agentes." : "URL e chave liberam configuração automática.";
  $("#agentGrid").innerHTML = Object.entries(AGENTS).map(([key, agent]) => { const tool = tools[key] || {}; const state = !tool.installed ? "missing" : tool.configured ? "ready" : "installed"; const status = state === "ready" ? "Pronto" : state === "installed" ? "Detectado" : "Não encontrado"; const button = !tool.installed ? "Não instalado" : connected ? "Abrir" : "Conecte API"; return `<article class="agent-card ${state}"><div class="agent-card-top"><div class="agent-icon"><i class="ph ${agent.icon}"></i></div><span class="agent-state"><i></i>${status}</span></div><div class="agent-info"><h3>${agent.name}</h3><p>${agent.desc}</p><code class="agent-path" title="${escapeHtml(tool.path || "")}">${escapeHtml(tool.path || (tool.installed ? "Instalação local detectada" : "Executável não localizado"))}</code></div><div class="agent-actions">${tool.configured ? `<button class="text-button" data-disconnect="${key}">Desconectar</button>` : ""}<button class="button ${tool.installed && connected ? "primary" : "secondary"}" data-launch="${key}" ${connected && tool.installed ? "" : "disabled"}>${button}${connected && tool.installed ? " <span>↗</span>" : ""}</button></div></article>`; }).join("");
  $$("[data-config]").forEach((button) => button.onclick = () => invoke("configureTool", button.dataset.config)); $$("[data-disconnect]").forEach((button) => button.onclick = () => invoke("disconnectTool", button.dataset.disconnect)); $$("[data-launch]").forEach((button) => button.onclick = () => invoke("launch", button.dataset.launch)); $("#configureAll").disabled = !connected || !installed;
}

function setMetrics(metrics) { $("#connectionFeedback").textContent = metrics.message || "API não conectada"; $("#connectionFeedback").className = `connection-feedback ${metrics.online ? "success" : "error"}`; const online = Boolean(metrics.online); const tps = Number(metrics.tps || 0); const preview = !studio; $("#globalStatus").classList.toggle("online", online); $("#globalStatus span").textContent = online ? "online" : "offline"; $("#metricOnline").textContent = online ? "Online" : "Offline"; $("#metricMessage").textContent = metrics.message || (online ? "Health check confirmado" : "API não conectada"); $("#metricTps").textContent = tps.toLocaleString("pt-BR", { maximumFractionDigits: 1 }); $("#metricTokens").textContent = Number(metrics.tokens || 0).toLocaleString("pt-BR"); $("#metricPulse").classList.toggle("online", online); $("#metricPulse").innerHTML = `<i></i> ${online ? "Sinal ativo" : "Sem sinal"}`; $(".gateway-state-icon i").className = online ? "ph ph-cloud-check" : "ph ph-cloud-slash"; $("#metricChecked").textContent = preview ? "Prévia local" : `Verificado ${new Date().toLocaleTimeString("pt-BR", { hour:"2-digit", minute:"2-digit" })}`; $("#metricTpsBar").style.width = `${Math.min(100, Math.max(0, tps / 40 * 100))}%`; }
function refreshCode() { if (!studio) return; studio.code("github", (code) => { $("#githubCode").textContent = code || ""; }); studio.code("install", (code) => { $("#installCode").textContent = code || ""; }); studio.code("runtime", (code) => { $("#runtimeCode").textContent = code || ""; }); }
function renderState() {
  $("#tunnel_mode").value = appState.tunnel_mode || "quick";
  if (document.activeElement !== $("#tunnel_url")) $("#tunnel_url").value = appState.tunnel_url || "";
  $("#tunnelUrlField").hidden = appState.tunnel_mode !== "named";
  $("#tunnelHelp").textContent = appState.tunnel_mode === "named" ? "Configure hostname para http://localhost:8000 no Cloudflare. Token será solicitado, oculto, no notebook. Não cole token aqui." : "Túnel rápido dispensa conta, mas não suporta SSE. Para agentes, escolha túnel nomeado.";
  $("#connectApi").disabled = Boolean(appState.connectionBusy);
  $("#connectApi").textContent = appState.connectionBusy ? "Verificando conexão…" : "Testar e conectar →";
  $("#testApi").disabled = Boolean(appState.connectionBusy);
  if (appState.connectionBusy) $("#connectionFeedback").textContent = "Verificando saúde e modelo. Você pode continuar navegando.";
  renderModels(); renderRuntime(); renderTools(); if (document.activeElement !== $("#baseUrl")) $("#baseUrl").value = appState.base_url || ""; $("#metricWatch").textContent = appState.sessionWatch ? "Ativo" : "Inativo"; $("#metricCheckMode").textContent = appState.sessionWatch ? "Automático" : "Manual"; $("#metricContext").textContent = Number(appState.serverContext || 0).toLocaleString("pt-BR"); }
function patch(payload) { if (payload.state) { const before = appState.stage; appState = { ...appState, ...payload.state }; renderState(); refreshCode(); if (appState.stage && appState.stage !== before && FLOW.includes(appState.stage)) showScreen(appState.stage); } if (payload.tools) { tools = payload.tools; renderTools(); } }
function collectOptions() { const out = {}; ["context", "output", "parallel", "reasoning_budget", "temperature", "mtp_tokens", "top_k", "top_p", "min_p", "backend", "tunnel_mode", "tunnel_url"].forEach((key) => { const el = $(`#${key}`); if (el) out[key] = el.value; }); return out; }
function pushOptions(overrides = {}) { invoke("updateOptions", JSON.stringify({ ...collectOptions(), ...overrides })); }

function wireUI() {
  $$("[data-nav]").forEach((button) => button.onclick = () => showScreen(button.dataset.nav)); $$("[data-next]").forEach((button) => button.onclick = () => { const next = button.dataset.next; invoke("setSetupStage", next === "monitor" ? "ready" : next); showScreen(next); });
  ["context", "output"].forEach((key) => $(`[data-preset-group="${key}"]`)?.querySelectorAll("button").forEach((button) => button.onclick = () => { const value = Number(button.dataset.value); appState[key] = value; $(`#${key}`).value = value; syncPreset(key); renderRuntime(); pushOptions({ [key]: value }); }));
  ["context", "output", "parallel", "reasoning_budget", "temperature", "mtp_tokens", "top_k", "top_p", "min_p", "backend", "tunnel_mode", "tunnel_url"].forEach((key) => { const el = $(`#${key}`); el.onchange = () => { appState[key] = ["backend", "tunnel_mode", "tunnel_url"].includes(key) ? el.value : Number(el.value); if (key === "parallel") invoke("setAutomaticSlots", false); renderRuntime(); pushOptions({ [key]: el.value }); renderState(); }; });
  $("#automaticSlots").onclick = () => { const enabled = appState.parallel_auto === false; appState.parallel_auto = enabled; invoke("setAutomaticSlots", enabled); renderRuntime(); };
  ["#openKaggle", "#openKaggle2"].forEach((id) => $(id).onclick = () => { if (invoke("openKaggle")) $("#kaggleHint").classList.add("show"); else toast("Abra kaggle.com/code/new no navegador."); }); $("#hideKaggle").onclick = () => { invoke("hideKaggle"); $("#kaggleHint").classList.remove("show"); };
  function copyCell(kind, id) {
    if (!studio) { toast("Cópia disponível no aplicativo desktop.", false); return; }
    studio.copy(kind, (ok) => {
      if (ok) { $(id).textContent = "Copiado ✓"; toast(kind === "github" ? "Célula GitHub copiada. Cole no Kaggle e execute." : kind === "install" ? "Copiado. Execute no Kaggle e aguarde concluir." : "Copiado. Pegue BASE URL e API KEY no output."); }
    });
  }
  $("#copyGitHub").onclick = () => copyCell("github", "#copyGitHub");
  $("#copyCell1").onclick = () => copyCell("install", "#copyCell1");
  $("#copyCell2").onclick = () => copyCell("runtime", "#copyCell2");
  $("#exportNotebook").onclick = () => { if (!invoke("exportNotebook")) toast("Exportação disponível no aplicativo desktop.", false); };
  $$("[data-copy='smoke']").forEach((button) => button.onclick = () => invoke("copy", "smoke")); $("#connectApi").onclick = () => {
    if (!$("#baseUrl").value.trim() || !$("#apiKey").value.trim()) { $("#connectionFeedback").textContent = "Preencha URL e chave."; $("#connectionFeedback").className = "connection-feedback error"; return; }
    if (!invoke("connectApi", $("#baseUrl").value, $("#apiKey").value)) { $("#connectionFeedback").textContent = "Conexão disponível no aplicativo desktop (run.bat)."; return; }
    $("#connectApi").disabled = true;
  }; $("#toggleKey").onclick = () => { const input = $("#apiKey"); input.type = input.type === "password" ? "text" : "password"; $("#toggleKey").setAttribute("aria-label", input.type === "password" ? "Mostrar API key" : "Ocultar API key"); }; $("#configureAll").onclick = () => invoke("configureAll"); $("#refreshTools").onclick = () => studio?.bootstrap((raw) => { tools = JSON.parse(raw).tools || {}; renderTools(); }); $("#testApi").onclick = () => invoke("testApi");
}

function installPreviewData() {
  models = [{ key:"gemopus",name:"Gemopus 4 26B A4B",quant:"Q4_K_M",description:"MoE compacto para coding e tarefas gerais.",context:16384,output:8192 },{ key:"velum",name:"VELUM Coder",quant:"auto Q4/IQ4",description:"Preset para código e ciclos longos.",context:16384,output:8192 },{ key:"qwen",name:"Qwen3.8 27B Aggressive",quant:"Q4_K_P",description:"Modelo denso para coding e tool use.",context:16384,output:8192 }];
  appState = { model:"gemopus",context:16384,output:8192,parallel:2,parallel_auto:true,reasoning_budget:3072,temperature:.6,mtp_tokens:2,top_k:40,top_p:.95,min_p:.05,backend:"official-layer",serverContext:32768,base_url:"",hasApiKey:false,sessionWatch:false }; tools = {}; $("#previewNotice").hidden = false; renderState(); showScreen("model"); $("#installCode").textContent = "# Código real disponível no aplicativo desktop."; $("#runtimeCode").textContent = "# Código real disponível no aplicativo desktop."; setMetrics({ online:false,tps:0,tokens:0,message:"Preview da interface" });
}

function init() {
  wireUI(); if (typeof QWebChannel === "undefined" || typeof qt === "undefined") { installPreviewData(); return; }
  new QWebChannel(qt.webChannelTransport, (channel) => { studio = channel.objects.studio; studio.toast.connect((message, ok) => toast(message, ok)); studio.stateChanged.connect((raw) => { try { patch(JSON.parse(raw)); } catch (_) {} }); studio.metricsChanged.connect((raw) => { try { setMetrics(JSON.parse(raw)); } catch (_) {} }); studio.bootstrap((raw) => { const data = JSON.parse(raw); appState = data.state || {}; models = data.models || []; tools = data.tools || {}; renderState(); refreshCode(); showScreen(FLOW.includes(appState.resumeStage) ? appState.resumeStage : "welcome"); studio.metrics((metrics) => setMetrics(JSON.parse(metrics))); }); });
}
document.addEventListener("DOMContentLoaded", () => {
  if (typeof qt !== "undefined" && typeof QWebChannel === "undefined") {
    const script = document.createElement("script");
    script.src = "qrc:///qtwebchannel/qwebchannel.js";
    script.onload = init;
    script.onerror = () => { installPreviewData(); toast("Bridge Qt indisponível. Reinicie aplicativo.", false); };
    document.head.appendChild(script);
  } else init();
});
