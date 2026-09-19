## 4.3 — 2026-09-18

- VELUM fixado em GGUF `Q8_0`; Bonsai Abliterated usa fork PrismML fixado e catálogo próprio.
- Célula GitHub valida `runtime-manifest.json` e SHA dos arquivos antes de iniciar; SHA antigo sem Bonsai falha com diagnóstico claro.
- Cache de pesos fica fora do checkout em `/kaggle/working/models` e reaproveita modelo ao mudar contexto, temperatura ou sampling.
- Gateway mantém uma requisição aberta e agrupa bytes SSE por aproximadamente 4 s; compatibilidade de túnel é liberada somente após probe de cadência.
- Auto configuração de Codex, Claude Code e OpenCode usa credenciais persistentes protegidas após conexão validada.
- Especulação automática usa `ngram-simple` somente quando anunciada pelo `llama-server`; MTP/DFlash não são simulados.
- Nenhuma GPU T4 ou boot Kaggle real foi executado nesta revisão.

## 4.2 — 2026-09-17

- Launcher CUDA muda para diretório dos plugins GGML, inclusive reparando cache anterior.
- Exige duas GPUs reais via --list-devices antes de download/carregamento de modelo.
- Célula única busca arquivos de guell11/Kairn no mesmo commit, preservando cache de modelos.
- Opção wackMall Linux prebuilt e workflow de build CUDA 12.4 / T4 para Kairn.
- Release original informada só contém prebuilds CUDA Windows; pacote Linux Kairn requer execução do workflow.

## 4.1 — 2026-09-17

- Setup em quatro etapas; configurações reunidas e exportação de notebook.
- Conexões verificadas em worker Qt, sem bloquear navegação.
- Corrigidos dependência requests, split inicial e flags do servidor; fallback do pip coberto por regressão.
- Runtime isolado em subprocesso; interrupção encerra processos filhos.
- Protocolo Messages nativo no backend oficial; erros HTTP preservados em pedidos com streaming.
- Túnel nomeado opcional e limitação SSE do Quick Tunnel explícita.
- Pesquisa de alternativas prontas documentada; validação GPU ainda pendente.

# Changelog

## 3.2.0
- Refeita a UX para layout com sidebar guiada e mascote assistente em tema claro.
- Fluxo do Kaggle ficou mais explícito: Settings → Internet ON → Accelerator 2× T4 / P100, depois célula 1 e célula 2.
- Adicionados presets claros de contexto e saída com guidance visual passo a passo.
- Integrada a imagem do mascote `penguin-guide.png` na UI.
- Célula de instalação do Kaggle agora instala apenas dependências ausentes, evitando upgrades agressivos do ambiente base.
- Bootstrap do CMake reforçado para criar `CUDA::cuda_driver` quando o target não vier pronto no ambiente Kaggle.


## 3.1.0

- Troca a UX para tema claro por padrão, com alternância opcional para tema escuro.
- Remove o hero gigante e coloca o setup operacional no topo da aplicação.
- Torna `ik_llama.cpp` o backend principal e padrão dos presets.
- Adiciona presets de contexto `8K/16K/32K/64K/128K` + custom.
- Adiciona presets de saída máxima `2K/4K/8K/16K/32K` + custom.
- Exibe plano de runtime com contexto total, slots e backend antes de gerar as células.
- Reescreve a etapa Kaggle como fluxo explícito de 3 passos, com código recolhido e CTAs grandes para copiar cada célula.
- Adiciona feedback visual "Copiado. Agora cole no Kaggle" e testes de contrato da UX.

## 3.0.0

- Reescreve as integrações de Codex, Claude Code, OpenCode e ZCode com schemas atuais.
- Codex passa a usar profile-v2 (`kaggle-studio.config.toml`) + `auth.command` + token separado `0600`, sem bearer no TOML.
- Corrige os health checks do runtime para enviarem autenticação ao próprio gateway.
- Adiciona heartbeat de célula ativo no Kaggle, sem mouse/teclado sintético.
- Adiciona fallback automático `llama.cpp tensor → layer` quando o servidor não inicia.
- Propaga limites reais de contexto/output para os providers locais.
- Adiciona validação defensiva do estado e erros de upstream 502/503 no gateway.
- Refina a UX com trilha de setup, caminhos de config, server context e assets SVG novos.
- Expande testes de idempotência, secrets, heartbeat e limites de estado.

## 2.0.0

- Substitui a navegação por múltiplos HTMLs por uma SPA responsiva com Qt WebChannel.
- Adiciona catálogo central de modelos e estado não-secreto persistente.
- Adiciona gateway universal com OpenAI Chat, OpenAI Responses e Anthropic Messages.
- Corrige Codex para `wire_api = "responses"` e cria profile `kaggle-studio`.
- Adiciona configuração preservativa/backup para Claude Code e OpenCode.
- Adiciona provider ZCode em configs Desktop e CLI/app-server.
- Adiciona backends `ik_llama graph`, `llama.cpp layer` e `llama.cpp tensor/NCCL`.
- Adiciona prompt layer para coding agents e slots concorrentes para subagentes.
- Adiciona telemetria `/metrics`, health watch e UI de status.
- Remove qualquer ideia de input sintético para contornar timeout do Kaggle.
- Adiciona testes, doctor e scripts de setup/execução para Windows, Linux e macOS.
