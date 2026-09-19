# Kairn / Kaggle Studio 4.2

Kaggle T4 ×2 → llama.cpp → API → agentes locais.

## Iniciar

Windows: `run.bat` ou `.\run.ps1`. Linux/macOS: `./run.sh`.

Windows verifica `pyvenv.cfg`, funcionamento do Python/pip e importação de Qt WebEngine/httpx. Ambiente `.venv` incompleto é preservado em `.kaggle-studio/venv-backup-*` e recriado automaticamente. `setup.bat` usa mesma recuperação, sem abrir interface. Requer Python 3.10+ instalado (recomendado 3.12).

Navegador Kaggle embutido usa perfil temporário. Login Google/Kaggle, cookies,
histórico, armazenamento local e tokens de sessão não entram no repositório.

## Fluxo novo

1. **Modelo e runtime:** escolha preset, contexto e saída na mesma tela. Automático limita concorrência inicial a até 2 slots.
2. **Iniciar no Kaggle:** clique **Copiar célula GitHub**, cole em notebook vazio e execute. Ative Internet e GPU T4 ×2. Célula busca código diretamente de `guell11/Kairn`, prepara dependências e inicia runtime. Não precisa upload de notebook.
3. **Conectar API:** cole Base URL e API key. Teste consulta saúde e modelo em segundo plano, sem congelar interface.
4. **Agentes locais:** configure ferramentas detectadas ou abra uma delas. Configuração só é liberada após conexão confirmada.

Célula pronta para copiar: [`kaggle/start.py`](kaggle/start.py). Requer projeto completo publicado no repositório público `guell11/Kairn`, branch `main` (ou altere `REF`). Launcher resolve SHA do commit, valida `runtime-manifest.json` e baixa todos os arquivos dessa mesma versão. O SHA antigo `786544ea` não contém Bonsai; publique o projeto atualizado antes de executar a célula. Modelo fica em `/kaggle/working/models`, fora da pasta do código, e é reutilizado após verificação.

Cópia não avança etapa. Notebook completo continua como alternativa antes da publicação:

```powershell
.venv/Scripts/python.exe scripts/export_notebook.py --model gemopus
```

Arquivo pronto: `notebooks/kaggle-studio.ipynb`. Gera chave nova quando executado; não contém credenciais da sessão local.

## Túnel e streaming

Quick Tunnel pode bufferizar SSE. O Studio mantém uma requisição aberta e envia bytes acumulados em lotes de aproximadamente 4 s. Health check não comprova streaming: o botão Conectar executa `/v1/stream-test` e só libera agentes quando a cadência chega corretamente. Cloudflare Quick Tunnel não tem suporte garantido; se o probe falhar, use túnel nomeado.

Para agentes, selecione **Cloudflare nomeado** e informe URL HTTPS. Configure hostname no Cloudflare apontando para `http://localhost:8000`. Notebook solicita token com entrada oculta; também aceita variável `TUNNEL_TOKEN`. Conta e domínio Cloudflare são necessários.

```powershell
.venv/Scripts/python.exe scripts/export_notebook.py --tunnel-url https://llm.seudominio.com
```

Nenhum túnel ou recurso remoto é criado pelo Studio automaticamente.

## Correção: “no backends are loaded”

Launcher com glibc privado executa `ld-linux`, alterando caminho percebido do executável. GGML procura plugins no diretório do executável e no diretório corrente. Agora launcher muda para pasta contendo `libggml-cuda.so` e plugins CPU antes de executar servidor. [Código upstream](https://github.com/ggml-org/llama.cpp/blob/b11009/ggml/src/ggml-backend-reg.cpp).

Cache antigo recebe launcher corrigido, sem apagar GGUF. `--help` sozinho não comprova CUDA: `--list-devices` precisa listar duas GPUs CUDA antes de baixar ou carregar modelo. Se validação falhar, diagnóstico aparece imediatamente. Contexto inicial recomendado: 16K; 128K pode exceder VRAM mesmo após correção de CUDA.

## llama-wackMall prebuilt

Release [main-b30-6aa17e3](https://github.com/miltos22/llama-wackMall/releases/tag/main-b30-6aa17e3) oferece CUDA para **Windows**, sem pacote Linux CUDA. Pacote Ubuntu x64 dessa release não deve ser confundido com CUDA.

Opção `wackmall` usa prebuild Linux específico do Kairn:

1. Publique projeto completo em `guell11/Kairn`, incluindo `.github/workflows/`.
2. Workflow **Build wackMall CUDA T4** executa no primeiro push de seus arquivos para `main`, ou manualmente via Actions.
3. Workflow compila commit fixo `6aa17e3a3d25104a9c786abb76e920d32faaae10`, Ubuntu 22.04, CUDA 12.4, T4 `sm_75`, e publica release `wackmall-main-b30-6aa17e3-cuda12.4-t4`.
4. Escolha backend wackMall no Studio ou `CONFIG['backend'] = 'wackmall'` na célula. Kaggle baixa pacote, valida SHA-256 publicado pelo GitHub e verifica GPUs.

Sem release publicada, opção informa passo necessário e não baixa binário Windows nem compila silenciosamente. Build e release estão preparados neste projeto, ainda não executados remotamente nesta revisão. Runtime oficial continua disponível enquanto isso.

## Runtime

- Padrão: llama.cpp oficial `b11009`, CUDA 12.8, **layer split** desde primeiro boot. Arquivos verificados com SHA-256 da release oficial.
- VELUM usa `Q8_0` por padrão (`9B`, ~9.5 GB); não é reduzido para IQ4.
- Bonsai usa `Ternary-Bonsai-2-27B-Abliterated-PTQ1_0.gguf` e exige fork PrismML fixado; não use backend oficial para esse modelo.
- Backend oficial fornece Chat Completions, Responses e Messages nativos. Gateway autentica e normaliza limites sem converter Messages desnecessariamente.
- Tensor split é experimental, com KV `f16`. Layer usa KV `q8_0`; consumo real varia por modelo.
- `ik_llama` é opção avançada, compilada localmente no Kaggle. Não há garantia de paridade com upstream.
- Flags opcionais são verificadas contra `llama-server --help`. Temperatura, Top K/P, Min P e orçamento de reasoning chegam ao comando quando suportados. Especulação `auto` ativa `ngram-simple` somente quando o binário anuncia essa flag; MTP/DFlash nativos exigem suporte real do backend e não são simulados.
- Falta de VRAM reduz slots. Processo anterior termina antes de retry. Outros erros são exibidos.
- Runtime roda no Python do venv. Interromper célula encerra grupo de processos, inclusive gateway e túnel.
- Sessão continua sujeita a limites do Kaggle. Heartbeat não evita encerramento pela plataforma.

Logs no Kaggle: `/kaggle/working/llama_server.log`, `fastapi_gateway.log`, `cloudflared.log`.

## Configurações locais

Backups são criados antes das mudanças. Estado do Studio não grava API key. Após conexão com streaming validado, configura automaticamente ferramentas instaladas. Codex, Claude Code e OpenCode usam arquivos de credencial protegidos persistentes; ZCode mantém chave no provider Desktop e injeta no processo CLI. Configurações anteriores são preservadas pelas integrações.

Alterar contexto, temperatura, saída ou sampling não baixa pesos novamente: o cache usa modelo, tamanho e SHA-256. O cache sobrevive a reinícios na mesma sessão em `/kaggle/working/models`; nova sessão Kaggle exige dataset, volume persistente ou novo download.

## Projetos prontos pesquisados

[Comparação de quatro alternativas e fontes](docs/KAGGLE-ALTERNATIVES.md). Melhor encaixe por escopo encontrado: [Tahsine/kaggle-llm-server](https://github.com/Tahsine/kaggle-llm-server). Pesquisa documental; nenhum desses projetos foi executado na sua conta.

## Validar

```powershell
.venv/Scripts/python.exe -m pip install -r requirements-dev.txt
.venv/Scripts/python.exe -m unittest discover -s tests -v
.venv/Scripts/python.exe scripts/doctor.py
node --check ui/app.js
```

Testes locais verificam comandos, notebooks, configurações, cache e respostas HTTP simuladas. Boot CUDA, download dos modelos e uso ponta a ponta dos agentes ainda precisam de execução real no Kaggle; nenhuma GPU T4 foi usada nesta validação.

## Estrutura

`main.py`: desktop e bridge Qt. `connection.py`: diagnóstico HTTP fora da interface. `runtime_builder.py`: células e notebook. `runtime_support.py`: argumentos e encerramento. `kaggle_gateway.py`: autenticação/proxy. `ui/`: interface. `scripts/export_notebook.py`: exportação via CLI.
