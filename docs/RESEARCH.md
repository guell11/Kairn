> Histórico de pesquisa anterior. Decisões atuais e limitações: [KAGGLE-ALTERNATIVES.md](KAGGLE-ALTERNATIVES.md).

# Notas técnicas e compatibilidade (setembro de 2026)

## OmniClaw

A base conceitual reaproveitada do `guell11/OmniClaw-GLM-Proxy-for-Claude-Code-Codex-OpenCode` é a configuração real e aditiva dos clientes, separada do proxy. O Kaggle Studio mantém um único endpoint público `/v1` e deixa cada cliente usar seu protocolo nativo, em vez de fingir que todas as CLIs falam exatamente a mesma coisa, uma fantasia que os formatos de configuração insistem em desmentir.

## Codex

O Codex atual aceita providers customizados em `~/.codex/config.toml`, usa `wire_api = "responses"` e suporta autenticação dinâmica por comando. O Studio grava o provider no `config.toml`, cria o profile-v2 em `~/.codex/kaggle-studio.config.toml`, guarda o bearer em `~/.codex/.kaggle-studio-token` com permissão `0600` quando disponível e configura `[model_providers.kaggle_studio.auth]` para lê-lo por `auth.command`. O bloco legado `[profiles.kaggle-studio]` é removido porque versões atuais do Codex o rejeitam quando `--profile` é usado. Assim o Codex continua funcionando quando aberto fora do Studio sem expor a chave dentro do TOML.

Há versões/clientes de terceiros com diferenças no encaminhamento de subagentes. O gateway não serializa requests e o runtime reserva múltiplos slots; portanto a infraestrutura aceita concorrência, mas não tenta mascarar bugs específicos do cliente.

## Claude Code

Gateways customizados são configuráveis via `ANTHROPIC_BASE_URL`. O Studio grava URL e aliases de modelo em `~/.claude/settings.json`, injeta o token somente no ambiente do processo lançado e mantém um bloco gerenciado em `~/.claude/CLAUDE.md` com instruções de agente.

## OpenCode

O provider customizado usa `@ai-sdk/openai-compatible`, `options.baseURL` e `{env:KAGGLE_STUDIO_API_KEY}`. O Studio também define `model`/`small_model`, limites de contexto/output e um bloco gerenciado em `AGENTS.md`. Um backup é criado antes de normalizar JSONC existente.

## ZCode

O ecossistema separa o config do desktop (`~/.zcode/v2/config.json`) do config consumido pelo app-server/CLI (`~/.zcode/cli/config.json`). O Studio escreve o provider nos dois e define `model.main`/`model.lite` no segundo. O Desktop recebe a chave no provider v2; o CLI mantém apenas `baseURL`/modelo e recebe `ZCODE_API_KEY` no ambiente, evitando duplicar o segredo.

## Multi-GPU em T4 ×2

### Padrão: ik_llama.cpp graph split

`ikawrakow/ik_llama.cpp` mantém suporte CUDA para Turing ou mais novo e oferece `split-mode graph`, que divide tensores e grafo entre GPUs. A documentação atual lista suporte a várias arquiteturas densas e MoE, incluindo Qwen3/3.5, Gemma4 e GLM4-MoE. Por isso o Studio usa esse caminho no modo **Auto**.

O fork `pt13762104/ik_llama.cpp` foi avaliado por manter patches para dispositivos TU11x e expor recursos semelhantes, incluindo graph split e Responses API. Ele não virou dependência padrão: o upstream do `ikawrakow` está mais ativo e já declara Turing como backend suportado. Menos forks em cadeia também significa menos maneiras criativas de compilar algo incompatível às duas da manhã.

Alguns modelos MLA/híbridos não suportam graph split; o próprio ik_llama pode cair para layer em arquiteturas não suportadas. Há também relato oficial de respostas incoerentes com graph split + offload parcial; nesse caso a recomendação do projeto é testar `-cuda graphs=0` ou usar layer split.

### Alternativa: llama.cpp

O upstream `ggml-org/llama.cpp` oferece `layer` como caminho conservador e `tensor`/NCCL como opção avançada. O tensor split atual exige Flash Attention e KV não quantizado em caminhos relevantes e ainda tem restrições por arquitetura. O Studio força KV `f16` nesse modo e, se o `llama-server` não subir, troca automaticamente para `layer` antes de abortar.

## Gateway universal

O `llama-server` atual já implementa OpenAI Chat Completions, OpenAI Responses e Anthropic Messages. O gateway Python deliberadamente não reimplementa esses protocolos: autentica, troca o alias de modelo, limita output, adiciona a camada curta de instruções e preserva streaming. Isso reduz conversões de payload e superfície de bugs.

## Prompt layer para modelos menores

A camada em `agent_prompt.py` segue uma estratégia curta e operacional: inspecionar antes de editar, usar ferramentas em vez de inventar resultados, dividir trabalho independente em subagentes, manter contexto enxuto, executar testes e declarar limitações observadas. O prompt é anexado ao campo nativo de cada protocolo sem apagar as instruções enviadas pelo cliente.

## Sessão Kaggle

O runtime deixa a célula principal realmente executando e faz `/health` autenticado a cada minuto, parando com erro visível se `llama-server`, gateway ou túnel morrerem. Isso substitui a ideia de gerar cliques/eventos falsos. O heartbeat não transforma uma sessão Kaggle em servidor permanente e não elimina limites de sessão/quota da plataforma.

## Referências

- OmniClaw: https://github.com/guell11/OmniClaw-GLM-Proxy-for-Claude-Code-Codex-OpenCode
- ik_llama.cpp: https://github.com/ikawrakow/ik_llama.cpp
- ik_llama parameters: https://github.com/ikawrakow/ik_llama.cpp/blob/main/docs/parameters.md
- TU11x fork avaliado: https://github.com/pt13762104/ik_llama.cpp
- llama.cpp: https://github.com/ggml-org/llama.cpp
- Codex: https://github.com/openai/codex
- OpenCode providers: https://opencode.ai/docs/providers/
- Claude Code: https://docs.anthropic.com/
