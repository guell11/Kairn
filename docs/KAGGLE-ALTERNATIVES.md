# Kaggle + llama.cpp: projetos prontos

Pesquisa em 17/09/2026. Comparação de código e documentação públicos; não representa benchmark nem execução em GPU Kaggle.

| Projeto | O que entrega | Quando usar |
|---|---|---|
| [Tahsine/kaggle-llm-server](https://github.com/Tahsine/kaggle-llm-server) | Notebooks separados para dataset do modelo, binários CUDA e servidor OpenAI; datasets públicos opcionais | Melhor encaixe encontrado para começar com notebook pronto. Avaliação por escopo, sem comprovação de estabilidade na sua conta. Seu Quick Tunnel também tem limitação de SSE. |
| [hoangkien1703/qwen36-q4km-kaggle](https://github.com/hoangkien1703/qwen36-q4km-kaggle) | Bootstrap reutilizável, notebook de chat Gradio e modelo Qwen em T4 ×2 | Alternativa orientada a chat; API externa de agentes exige revisar transporte. |
| [HyperFormia/llamacpp-t4-prebuilt](https://github.com/HyperFormia/llamacpp-t4-prebuilt) | Binários de variante Prism-ML para T4/Kaggle | Componente pronto, não aplicação completa; validar suporte ao GGUF escolhido. |
| [Muse-Glimmer / DFlash2 Kaggle](https://github.com/dangkhoa2016/Muse-Glimmer-30B-GGUF-DFlash2-Kaggle-GPU-T4x2) | Stack de inferência para modelo específico, decodificação especulativa e gateway autenticado | Referência para configuração específica; mais componentes para manter. |

## Decisão aplicada

Mantido `ggml-org/llama.cpp` oficial, release `b11009`, com os hashes dos arquivos CUDA 12.8 conferidos na [release oficial](https://github.com/ggml-org/llama.cpp/releases/tag/b11009). Não importamos executáveis comunitários ou substituímos o projeto inteiro sem validar compatibilidade.

O [servidor oficial nessa versão](https://github.com/ggml-org/llama.cpp/blob/b11009/tools/server/README.md) já oferece Chat Completions, Responses e Messages. Agora Messages passa direto para o backend oficial, preservando tools e streaming. Conversão legada continua apenas para `ik_llama`.

**Quick Tunnel não suporta SSE**, conforme [Cloudflare](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/do-more-with-tunnels/trycloudflare/). Resposta de `/health` não comprova streaming. Studio diferencia teste rápido de túnel nomeado e bloqueia configuração de agentes em URLs Quick Tunnel. Para agentes, configure hostname de túnel nomeado apontando para `http://localhost:8000`; informe token somente no notebook quando solicitado. Conta e domínio Cloudflare são necessários.

## Falhas corrigidas

- Venv não instalava `requests`, importado pelo runtime.
- Primeiro boot oficial herdava `graph`; somente caminho com cache definia split correto.
- `--parallel-tool-calls` era enviado sem suporte documentado nessa release.
- Ajustes de temperatura e amostragem não chegavam ao comando.
- Retry de memória existia somente para graph; agora também cobre layer/tensor.
- Processo que excedia espera de boot continuava vivo antes de retry.
- Runtime injetava pacotes no kernel; agora executa em subprocesso no venv.
- API Messages era convertida mesmo quando backend oferecia protocolo nativo.
- Erros JSON de chamadas com `stream=true` eram tratados como streams.
- Health check bloqueava thread da interface; métricas ausentes marcavam servidor saudável como offline.
- Cópia avançava fluxo mesmo sem confirmação do clipboard.

## Limites de validação

Testes locais cobrem geração e sintaxe das células, argumentos, reintentos, autenticação, repasse de Messages, erro em streaming e conexões simuladas. UI verificada no navegador. Download de GGUF, inicialização CUDA e integração ponta a ponta com agentes dependem de sessão Kaggle real. Não foram executados nesta revisão.
