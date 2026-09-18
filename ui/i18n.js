(function () {
  const dictionaries = {
    'pt-BR': {
      language: 'Idioma', online: 'online', offline: 'offline',
      copied: 'Copiado ✓', openKaggle: 'Abrir Kaggle ↗', continue: 'Continuar →',
      preview: 'Prévia visual. Execute run.bat para gerar célula GitHub e conectar agentes locais.',
      desktopOnly: 'Disponível no aplicativo desktop.', copyDesktop: 'Cópia disponível no aplicativo desktop.',
      noKaggle: 'Abra kaggle.com/code/new no navegador.',
      waiting: 'Aguardando URL e chave.', fillUrl: 'Preencha URL e chave.',
      desktopConnection: 'Conexão disponível no aplicativo desktop (run.bat).',
      checking: 'Verificando saúde e modelo. Você pode continuar navegando.',
      apiDown: 'API não conectada', health: 'Health check confirmado', localPreview: 'Prévia local',
      noSignal: 'Sem sinal', activeSignal: 'Sinal ativo', notChecked: 'Ainda não verificado',
      manual: 'Manual', automatic: 'Automático', active: 'Ativo', inactive: 'Inativo',
      copyGithub: 'Célula GitHub copiada. Cole no Kaggle e execute.',
      copyInstall: 'Copiado. Execute no Kaggle e aguarde concluir.',
      copyRuntime: 'Copiado. Pegue BASE URL e API KEY no output.',
      exportDesktop: 'Exportação disponível no aplicativo desktop.',
      tunnelQuick: 'Túnel rápido pode entregar resposta em lotes. A conexão testa streaming antes de liberar agentes.',
      tunnelNamed: 'Configure hostname para http://localhost:8000 no Cloudflare. Token será solicitado, oculto, no notebook. Não cole token aqui.',
      autoPreset: 'Definido automaticamente para este preset.', manualSlots: 'Ajuste manual ativo.',
      reviewBudget: 'Revise orçamento ({total} total).', budgetHint: 'Resposta precisa caber no contexto junto com prompt. Contexto alto pode exceder VRAM.',
      quickAgents: 'Streaming em lotes de 4 s', connectFirst: 'Conecte API primeiro', cacheNote: 'Alterar parâmetros reutiliza o modelo nesta sessão.', speculationAuto: 'Automático · método n-gram suportado', speculationOff: 'Desativado', speculationNgram: 'N-gram · fallback local',
      streamBatch: 'Tokens enviados em lotes de até 4 s.', checked: 'Verificado', cloudflarePlaceholder: 'https://llm.seudominio.com', baseUrlPlaceholder: 'https://…trycloudflare.com/v1', apiKeyPlaceholder: 'ks_…',
      found: '{n} ferramenta{plural} encontrada{plural}', readyToOpen: '{n} pronta{plural} para abrir. Configuração cria backup antes de alterar arquivos.',
      namedRequired: 'Gere notebook com túnel nomeado para liberar agentes.', autoConfig: 'URL e chave liberam configuração automática.',
      ready: 'Pronto', detected: 'Detectado', missing: 'Não encontrado', failed: 'Falhou', notInstalled: 'Não instalado', open: 'Abrir', disconnect: 'Desconectar', retry: 'Tentar novamente', configSuccess: 'Configuração concluída', configFailed: 'Configuração falhou', backup: 'Backup salvo',
      localInstall: 'Instalação local detectada', executableMissing: 'Executável não localizado',
      agents: { codex: 'Respostas API', claude: 'Mensagens Anthropic', opencode: 'Compatível com OpenAI', zcode: 'Provedor personalizado' }
    },
    en: {
      language: 'Language', online: 'online', offline: 'offline',
      copied: 'Copied ✓', openKaggle: 'Open Kaggle ↗', continue: 'Continue →',
      preview: 'Visual preview. Run run.bat to generate the GitHub cell and connect local agents.',
      desktopOnly: 'Available in the desktop app.', copyDesktop: 'Copy is available in the desktop app.',
      noKaggle: 'Open kaggle.com/code/new in your browser.',
      waiting: 'Waiting for URL and key.', fillUrl: 'Enter URL and key.',
      desktopConnection: 'Connection is available in the desktop app (run.bat).',
      checking: 'Checking health and model. You can keep browsing.',
      apiDown: 'API not connected', health: 'Health check confirmed', localPreview: 'Local preview',
      noSignal: 'No signal', activeSignal: 'Active signal', notChecked: 'Not checked yet',
      manual: 'Manual', automatic: 'Automatic', active: 'Active', inactive: 'Inactive',
      copyGithub: 'GitHub cell copied. Paste it into Kaggle and run it.',
      copyInstall: 'Copied. Run it in Kaggle and wait for completion.',
      copyRuntime: 'Copied. Get BASE URL and API KEY from the output.',
      exportDesktop: 'Export is available in the desktop app.',
      tunnelQuick: 'Quick tunnel can deliver batched output. The connection tests streaming before enabling agents.',
      tunnelNamed: 'Configure the hostname for http://localhost:8000 in Cloudflare. The token is requested privately in the notebook. Do not paste it here.',
      autoPreset: 'Automatically set for this preset.', manualSlots: 'Manual adjustment enabled.',
      reviewBudget: 'Review budget ({total} total).', budgetHint: 'The response must fit the context alongside the prompt. High context may exceed VRAM.',
      quickAgents: 'Streaming in 4 s batches', connectFirst: 'Connect API first', cacheNote: 'Changing parameters reuses the model within this session.', speculationAuto: 'Automatic · supported n-gram method', speculationOff: 'Off', speculationNgram: 'N-gram · local fallback',
      streamBatch: 'Tokens are sent in batches of up to 4 s.', checked: 'Checked', cloudflarePlaceholder: 'https://llm.example.com', baseUrlPlaceholder: 'https://…trycloudflare.com/v1', apiKeyPlaceholder: 'ks_…',
      found: '{n} tool{plural} found', readyToOpen: '{n} ready to open. Configuration backs up files before changing them.',
      namedRequired: 'Generate a notebook with a named tunnel to enable agents.', autoConfig: 'URL and key enable automatic configuration.',
      ready: 'Ready', detected: 'Detected', missing: 'Not found', failed: 'Failed', notInstalled: 'Not installed', open: 'Open', disconnect: 'Disconnect', retry: 'Retry', configSuccess: 'Configuration complete', configFailed: 'Configuration failed', backup: 'Backup saved',
      localInstall: 'Local installation detected', executableMissing: 'Executable not found',
      agents: { codex: 'Responses API', claude: 'Anthropic Messages', opencode: 'OpenAI-compatible', zcode: 'Custom provider' }
    }
  };
  const staticTranslations = {
    'pt-BR': {
      '.sidebar-brand small':'GPU remota. Controle local.','.rail-button[data-nav=model] span':'Modelo e runtime','.rail-button[data-nav=environment] span':'Iniciar no Kaggle','.rail-button[data-nav=connect] span':'Conectar API','.rail-button[data-nav=agents] span':'Agentes locais','.rail-button[data-nav=monitor] span':'Monitor',
      '.wordmark strong':'Seu workspace de inferência','#openKaggle':'Abrir Kaggle ↗','.preview-banner':'Prévia visual. Execute run.bat para gerar célula GitHub e conectar agentes locais.',
      '[data-screen=welcome] .eyebrow':'KAGGLE GPU → AGENTES LOCAIS','[data-screen=model] .eyebrow':'01 — MODELO','[data-screen=context] .eyebrow':'02 — CONTEXTO','[data-screen=output] .eyebrow':'03 — SAÍDA','[data-screen=review] .eyebrow':'04 — REVISÃO','[data-screen=environment] .eyebrow':'02 / EXECUTAR','[data-screen=cell1] .eyebrow':'CÉLULA 1 / PREPARAR','[data-screen=cell2] .eyebrow':'CÉLULA 2 / INICIAR','[data-screen=connect] .eyebrow':'03 / CONECTAR','[data-screen=agents] .eyebrow':'04 / AGENTES','[data-screen=ready] .eyebrow':'PRONTO','[data-screen=monitor] .eyebrow':'MONITOR','[data-screen=welcome] h1':'Modelo no Kaggle.<br>Agente no PC.','[data-screen=welcome] .hero-copy p:not(.eyebrow)':'Configure runtime e abra Codex, Claude Code, OpenCode ou ZCode em um clique.','[data-screen=welcome] figcaption':'Mais poder<br>para suas<br>ideias','[data-screen=welcome] .notice-guide strong':'Antes de começar','[data-screen=welcome] .notice-guide p':'Abra Kaggle, ative Internet e selecione 2 × T4.','[data-screen=welcome] [data-next=model]':'Escolher modelo →',
      '[data-screen=model] h2':'Seu modelo, sua GPU.','[data-screen=model] .screen-heading p:last-child':'Escolha modelo. Ajustes recomendados já estão preenchidos.','[data-screen=model] .notice.compact p':'CUDA prebuilt é o padrão. llama.cpp oficial com versão e checksum fixos.','[data-screen=model] [data-next=context]':'Continuar →',
      '[data-screen=context] h2':'Quanto cada agente pode enxergar?','[data-screen=context] .screen-heading p:last-child':'Contexto usa VRAM em cada slot. Comece com 16K.','label[for=context]':'Contexto por geração','[data-screen=context] [data-next=output]':'Continuar →',
      '[data-screen=output] h2':'Quanto o modelo pode responder?','[data-screen=output] .screen-heading p:last-child':'8K serve para mudanças grandes sem exagerar memória.','label[for=output]':'Saída máxima','[data-screen=output] [data-next=review]':'Revisar configuração →',
      '[data-screen=review] h2':'Pronto para iniciar.','[data-screen=review] .screen-heading p:last-child':'Comece com até 2 slots. Falta de VRAM reduz slots automaticamente.','.slots-row strong':'Slots simultâneos','#automaticSlots span':'Auto','.review-banner span:nth-of-type(1)':'Modelo','.review-banner span:nth-of-type(2)':'Contexto','.review-banner span:nth-of-type(3)':'Saída','[data-screen=review] .advanced-options summary':'Backend e opções avançadas','[data-screen=review] [data-next=environment]':'Gerar célula GitHub →',
      '[data-screen=environment] h2':'Uma célula. Direto do GitHub.','[data-screen=environment] .screen-heading p:last-child':'Abra Kaggle, ative Internet e selecione GPU T4 ×2. Cole célula abaixo. Ela busca arquivos do Kairn, prepara ambiente e inicia API.','#copyGitHub':'Copiar célula GitHub','#openKaggle2':'Abrir Kaggle ↗','.code-card summary':'Ver célula GitHub','.tunnel-card p':'Túnel rápido pode entregar resposta em lotes. A conexão testa streaming antes de liberar agentes.','[data-screen=environment] [data-next=connect]':'Já tenho URL e chave →','[data-screen=environment] .advanced-options summary':'Alternativa offline: exportar notebook completo','#exportNotebook':'Salvar notebook (opcional)',
      '[data-screen=connect] h2':'Traga sua API para cá.','[data-screen=connect] .screen-heading p:last-child':'Cole dados do notebook. Verificaremos saúde e modelo antes de liberar agentes.','label[for=baseUrl]':'Base URL','label[for=apiKey]':'API key','#connectApi':'Testar e conectar →','[data-copy=smoke]':'Copiar smoke test',
      '[data-screen=agents] h2':'Seu agente. Um clique.','[data-screen=agents] .screen-heading p:last-child':'Detectamos ferramentas locais. Conexão validada libera configuração dos agentes.','#refreshTools':' Atualizar','#configureAll':'Configurar todos disponíveis →',
      '[data-screen=ready] h2':'Gateway conectado.','[data-screen=ready] p:not(.eyebrow)':'Agentes instalados já podem usar modelo no Kaggle.','[data-screen=ready] [data-next=monitor]':'Abrir monitor →','[data-screen=monitor] h2':'Runtime em tempo real.','[data-screen=monitor] .screen-heading p:last-child':'Saúde, velocidade e uso. Só telemetria confirmada.','#testApi':' Testar agora'
    },
    en: {
      '.sidebar-brand small':'Remote GPU. Local control.','.rail-button[data-nav=model] span':'Model and runtime','.rail-button[data-nav=environment] span':'Start in Kaggle','.rail-button[data-nav=connect] span':'Connect API','.rail-button[data-nav=agents] span':'Local agents','.rail-button[data-nav=monitor] span':'Monitor',
      '.wordmark strong':'Your inference workspace','#openKaggle':'Open Kaggle ↗','.preview-banner':'Visual preview. Run run.bat to generate the GitHub cell and connect local agents.',
      '[data-screen=welcome] .eyebrow':'KAGGLE GPU → LOCAL AGENTS','[data-screen=model] .eyebrow':'01 — MODEL','[data-screen=context] .eyebrow':'02 — CONTEXT','[data-screen=output] .eyebrow':'03 — OUTPUT','[data-screen=review] .eyebrow':'04 — REVIEW','[data-screen=environment] .eyebrow':'02 / RUN','[data-screen=cell1] .eyebrow':'CELL 1 / PREPARE','[data-screen=cell2] .eyebrow':'CELL 2 / START','[data-screen=connect] .eyebrow':'03 / CONNECT','[data-screen=agents] .eyebrow':'04 / AGENTS','[data-screen=ready] .eyebrow':'READY','[data-screen=monitor] .eyebrow':'MONITOR','[data-screen=welcome] h1':'Model in Kaggle.<br>Agent on your PC.','[data-screen=welcome] .hero-copy p:not(.eyebrow)':'Configure the runtime and open Codex, Claude Code, OpenCode, or ZCode in one click.','[data-screen=welcome] figcaption':'More power<br>for your<br>ideas','[data-screen=welcome] .notice-guide strong':'Before you start','[data-screen=welcome] .notice-guide p':'Open Kaggle, enable Internet, and select 2 × T4.','[data-screen=welcome] [data-next=model]':'Choose model →',
      '[data-screen=model] h2':'Your model, your GPU.','[data-screen=model] .screen-heading p:last-child':'Choose a model. Recommended settings are already filled in.','[data-screen=model] .notice.compact p':'CUDA prebuilt is the default. Official llama.cpp with pinned version and checksum.','[data-screen=model] [data-next=context]':'Continue →',
      '[data-screen=context] h2':'How much can each agent see?','[data-screen=context] .screen-heading p:last-child':'Context uses VRAM in every slot. Start with 16K.','label[for=context]':'Context per generation','[data-screen=context] [data-next=output]':'Continue →',
      '[data-screen=output] h2':'How much can the model answer?','[data-screen=output] .screen-heading p:last-child':'8K handles large changes without overusing memory.','label[for=output]':'Maximum output','[data-screen=output] [data-next=review]':'Review settings →',
      '[data-screen=review] h2':'Ready to start.','[data-screen=review] .screen-heading p:last-child':'Start with up to 2 slots. Low VRAM reduces slots automatically.','.slots-row strong':'Concurrent slots','#automaticSlots span':'Auto','.review-banner span:nth-of-type(1)':'Model','.review-banner span:nth-of-type(2)':'Context','.review-banner span:nth-of-type(3)':'Output','[data-screen=review] .advanced-options summary':'Backend and advanced options','[data-screen=review] [data-next=environment]':'Generate GitHub cell →',
      '[data-screen=environment] h2':'One cell. Straight from GitHub.','[data-screen=environment] .screen-heading p:last-child':'Open Kaggle, enable Internet, and select GPU T4 ×2. Paste the cell below. It fetches Kairn files, prepares the environment, and starts the API.','#copyGitHub':'Copy GitHub cell','#openKaggle2':'Open Kaggle ↗','.code-card summary':'View GitHub cell','.tunnel-card p':'Quick tunnel can deliver batched output. The connection tests streaming before enabling agents.','[data-screen=environment] [data-next=connect]':'I have URL and key →','[data-screen=environment] .advanced-options summary':'Offline alternative: export complete notebook','#exportNotebook':'Save notebook (optional)',
      '[data-screen=connect] h2':'Bring your API here.','[data-screen=connect] .screen-heading p:last-child':'Paste notebook details. We will check health and model before enabling agents.','label[for=baseUrl]':'Base URL','label[for=apiKey]':'API key','#connectApi':'Test and connect →','[data-copy=smoke]':'Copy smoke test',
      '[data-screen=agents] h2':'Your agent. One click.','[data-screen=agents] .screen-heading p:last-child':'We detected local tools. A validated connection enables agent configuration.','#refreshTools':' Refresh','#configureAll':'Configure all available →',
      '[data-screen=ready] h2':'Gateway connected.','[data-screen=ready] p:not(.eyebrow)':'Installed agents can now use the Kaggle model.','[data-screen=ready] [data-next=monitor]':'Open monitor →','[data-screen=monitor] h2':'Runtime in real time.','[data-screen=monitor] .screen-heading p:last-child':'Health, speed, and usage. Confirmed telemetry only.','#testApi':' Test now'
    }
  };
  let language = (() => { try { return localStorage.getItem('kairn-language') || 'pt-BR'; } catch (_) { return 'pt-BR'; } })();
  function dict() { return dictionaries[language] || dictionaries['pt-BR']; }
  function t(key, vars = {}) { let value = key.split('.').reduce((node, part) => node && node[part], dict()) ?? key; return String(value).replace(/\{(\w+)\}/g, (_, name) => vars[name] ?? ''); }
  function apply() {
    document.documentElement.lang = language;
    const map = staticTranslations[language];
    Object.keys(map).forEach((selector) => document.querySelectorAll(selector).forEach((el) => {
      const value = map[selector];
      // Keep child controls/icons and their listeners intact when translating buttons.
      if (el.matches('button') && el.children.length) {
        const textNode = [...el.childNodes].find((node) => node.nodeType === Node.TEXT_NODE);
        if (textNode) textNode.nodeValue = ` ${value.replace(/\s*→\s*$/, '')} `;
        else el.insertBefore(document.createTextNode(` ${value.replace(/\s*→\s*$/, '')} `), el.firstChild);
        return;
      }
      // Interactive descendants must never be replaced by a translation pass.
      if (el.querySelector('input,select,button,textarea')) return;
      el.innerHTML = value;
    }));
    const controls = language === 'en' ? {
      '#tunnel_mode option[value="quick"]': 'Quick tunnel · 4 s batches',
      '#tunnel_mode option[value="named"]': 'Named Cloudflare · agents and streaming',
      '#tunnelUrlField span': 'Public URL configured in Cloudflare',
      '#speculation option[value="auto"]': 'Automatic · supported n-gram method', '#speculation option[value="off"]': 'Off', '#speculation option[value="ngram"]': 'N-gram · local fallback', '#cacheNote': 'Changing parameters reuses the model within this session.',
      '[data-screen=environment] .tunnel-card > .form-field > span': 'How to expose the API',
      '[data-screen=connect] .result-example code:first-child': 'BASE URL → https://…trycloudflare.com/v1',
      '[data-screen=connect] .result-example code:last-child': 'API KEY → ks_…',
      '[data-screen=connect] .notice.compact p': 'API key is saved only in a protected local credential file after connection.',
      '#kaggleHint span': 'Kaggle opened beside this window', '#hideKaggle': 'Close panel'
    } : {
      '#tunnel_mode option[value="quick"]': 'Túnel rápido · lotes de 4 s',
      '#tunnel_mode option[value="named"]': 'Cloudflare nomeado · agentes e streaming',
      '#tunnelUrlField span': 'URL pública configurada no Cloudflare',
      '#speculation option[value="auto"]': 'Automático · método n-gram suportado', '#speculation option[value="off"]': 'Desativado', '#speculation option[value="ngram"]': 'N-gram · fallback local', '#cacheNote': 'Alterar parâmetros reutiliza o modelo nesta sessão.',
      '[data-screen=environment] .tunnel-card > .form-field > span': 'Como expor API',
      '[data-screen=connect] .result-example code:first-child': 'BASE URL → https://…trycloudflare.com/v1',
      '[data-screen=connect] .result-example code:last-child': 'API KEY → ks_…',
      '[data-screen=connect] .notice.compact p': 'API key é salva somente em arquivo local protegido após conexão.',
      '#kaggleHint span': 'Kaggle aberto ao lado', '#hideKaggle': 'Fechar painel'
    };
    Object.entries(controls).forEach(([selector, value]) => document.querySelectorAll(selector).forEach((el) => { if (el.matches('button') && el.children.length) { const node = [...el.childNodes].find((n) => n.nodeType === Node.TEXT_NODE); if (node) node.nodeValue = ` ${value} `; else el.insertBefore(document.createTextNode(` ${value} `), el.firstChild); } else el.textContent = value; }));
    const attrs = language === 'en' ? {
      'body': { 'aria-label': 'Kaggle Studio' }, '.app-sidebar': { 'aria-label': 'Studio navigation' }, '.studio-panel': { 'aria-label': 'Kaggle Studio setup assistant' }, '.step-meter': { 'aria-label': 'Current step' },
      '#context': { 'aria-label': 'Custom context' }, '#output': { 'aria-label': 'Custom output' }, '#parallel': { 'aria-label': 'Concurrent slots' }, '#toggleKey': { 'aria-label': 'Show API key' },
      '[data-screen=environment] .footnote': { 'textContent': 'Source: guell11/Kairn · main branch. Requires published project.' }
    } : {
      'body': { 'aria-label': 'Kaggle Studio' }, '.app-sidebar': { 'aria-label': 'Navegação do Studio' }, '.studio-panel': { 'aria-label': 'Assistente de configuração Kaggle Studio' }, '.step-meter': { 'aria-label': 'Etapa atual' },
      '#context': { 'aria-label': 'Contexto customizado' }, '#output': { 'aria-label': 'Saída customizada' }, '#parallel': { 'aria-label': 'Slots simultâneos' }, '#toggleKey': { 'aria-label': 'Mostrar API key' },
      '[data-screen=environment] .footnote': { 'textContent': 'Fonte: guell11/Kairn · branch main. Requer projeto publicado.' }
    };
    Object.entries(attrs).forEach(([selector, values]) => document.querySelectorAll(selector).forEach((el) => Object.entries(values).forEach(([key, value]) => key === 'textContent' ? (el.textContent = value) : el.setAttribute(key, value))));
    const labels = language === 'en' ? { '#languageSelect': 'Language', '#speculation': 'Speculative decoding', '#mtp_tokens': 'Draft tokens' } : { '#languageSelect': 'Idioma', '#speculation': 'Decodificação especulativa', '#mtp_tokens': 'Tokens de rascunho' };
    Object.entries(labels).forEach(([selector, value]) => { const el = document.querySelector(`label[for="${selector.slice(1)}"]`); if (el) el.firstChild.textContent = value; });
    document.querySelectorAll('[data-i18n-placeholder]').forEach((el) => { el.placeholder = t(el.dataset.i18nPlaceholder); });
    const select = document.querySelector('#languageSelect'); if (select) { select.value = language; select.setAttribute('aria-label', language === 'en' ? 'Language' : 'Idioma'); }
    window.dispatchEvent(new CustomEvent('languageChanged', { detail: language }));
  }
  function normalizeLanguage(value) { return value === 'en' || value === 'pt-BR' ? value : 'pt-BR'; }
  language = normalizeLanguage(language);
  window.KairnI18n = { t, get language() { return language; }, get dictionaries() { return dictionaries; }, get staticTranslations() { return staticTranslations; }, setLanguage(next, notify = true) { language = normalizeLanguage(next); try { localStorage.setItem('kairn-language', language); } catch (_) {} apply(); if (notify && window.KairnInvokeLanguage) window.KairnInvokeLanguage(language); }, apply };
  document.addEventListener('DOMContentLoaded', () => { const select = document.querySelector('#languageSelect'); if (select) select.addEventListener('change', () => window.KairnI18n.setLanguage(select.value)); apply(); });
})();
