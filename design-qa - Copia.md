# QA 4.3 — runtime e integrações

- Catálogo exibe VELUM em Q8_0 e Bonsai com backend PrismML obrigatório; configuração não permite backend incompatível.
- Célula única busca o commit inteiro no GitHub e valida manifesto/arquivos antes de executar. O catálogo antigo `786544ea` não contém Bonsai e deve ser substituído no repositório publicado.
- Alterar parâmetros de geração mantém o GGUF no cache compartilhado; novo download só ocorre em nova sessão sem armazenamento persistente.
- Conectar executa probe real de cadência SSE. Agentes só ficam disponíveis quando lotes chegam pela mesma requisição; Quick Tunnel não recebe garantia prévia.
- Codex, Claude Code e OpenCode recebem configuração automática apenas após probe aprovado, com tokens em arquivos protegidos persistentes.
- Especulação `auto` seleciona `ngram-simple` quando suportado pelo binário. Não há alegação de MTP/DFlash universal.
- 67 testes locais passam, incluindo transporte HTTP em lotes e contratos de runtime. Nenhuma execução real em GPU T4, Kaggle ou túnel Cloudflare foi feita.

# Atualização 4.2 — GitHub e CUDA

- Verificada etapa “Uma célula. Direto do GitHub.” com ação principal “Copiar célula GitHub”.
- Exportação de notebook agora recolhida como alternativa; células manuais saíram do fluxo principal.
- Seletor de backend contém wackMall com requisito de release Linux explícito.
- 40 testes locais passam; sintaxe Bash do workflow validada e flags CMake conferidas no commit upstream.
- Workflow não executado/publicado e nenhuma GPU T4 real utilizada nesta validação.

# UX 4.1 — verificação em 17/09/2026

Referência inicial: interface existente capturada no navegador; fluxo antigo tinha 12 telas, mascote dominante e avanço ao copiar células.

Resultado: quatro etapas e monitor; modelo/contexto/saída/revisão juntos; ambiente e duas células juntos; código recolhido; exportação de notebook; conexão com estado de teste e erro persistente.

Verificação visual: desktop 1440 × 1000 e viewport 390 × 844. Em 390 px, documento reportou 375 px de conteúdo, sem overflow horizontal. Preview deixa claro que bridge local exige aplicativo desktop.

Interações verificadas no navegador:
- Seleção de modelo permanece na configuração e atualiza resumo.
- Saída 32K com contexto 16K mostra aviso e desabilita continuar; voltar saída a 8K libera botão.
- Preparar notebook abre etapa com ambas as células e exportação.
- Túnel nomeado exibe campo de URL e instrução de token oculto no notebook.
- Copiar em preview mostra indisponibilidade e não avança etapa.
- Conexão vazia mostra erro inline.

Teste local de HTTP cobre Quick Tunnel saudável sem liberação de agentes, erro de autenticação, ausência de modelo e telemetria indisponível. Testes de runtime cobrem geração, parâmetros e notebook.

Limites: captura visual corresponde à SPA em preview; execução real de Qt, Kaggle CUDA, túnel e agentes não foi validada ponta a ponta.
