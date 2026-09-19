# Arquitetura

## Plano de dados

```text
Codex ───── Responses ─────┐
OpenCode ─ Chat/Responses ─┼─► Cloudflare URL ─► Kaggle Studio Gateway ─► llama-server
Claude ─── Anthropic ──────┤                                          ├─ GPU 0 T4
ZCode ──── OpenAI/Anthropic┘                                          └─ GPU 1 T4
```

O gateway não tenta reimplementar todo o protocolo de cada cliente. Os servidores atuais de `llama.cpp`/`ik_llama.cpp` já possuem rotas OpenAI e, nas versões atuais, Anthropic Messages. A camada Python fica pequena: autenticação, alias estável do modelo, limites de output, prompt de agente, proxy de streaming e métricas.

## Plano de controle

`main.py` mantém a chave apenas em memória, persiste preferências não-secretas em `.kaggle-studio/state.json`, gera o runtime com `RuntimeBuilder` e instala configurações locais com `integrations.py`.

A SPA em `ui/` conversa com Python exclusivamente por Qt WebChannel. O navegador Kaggle usa perfil temporário, sem persistir login, cookies, OAuth, histórico, armazenamento local ou tokens de sessão no projeto.

## Backends

`BACKEND_FAMILY` possui quatro valores de UI:

- `auto` → `ik_llama`
- `ik_llama` → `ikawrakow/ik_llama.cpp`, `split-mode graph`
- `official-layer` → `ggml-org/llama.cpp`, `split-mode layer`
- `official-tensor` → `ggml-org/llama.cpp`, `split-mode tensor`, NCCL e KV `f16`; se a inicialização falhar, tenta `layer` automaticamente

O runtime compila somente `llama-server`, copia o binário final para `/kaggle/working` e apaga checkout/objetos antes do download do GGUF para economizar disco.

## Segurança

- Base URL sem segredo é persistida; API key do Studio não é.
- Codex usa profile-v2 (`kaggle-studio.config.toml`) e `auth.command` apontando para um leitor de token local `0600`; OpenCode usa referência a variável de ambiente.
- Claude recebe token ao lançar pelo Studio.
- Backups são criados antes de alterar configs existentes.
- ZCode Desktop precisa do token em seu provider v2; o CLI recebe `ZCODE_API_KEY` via ambiente. Arquivos sensíveis recebem `0600` quando possível.
- O gateway valida `Authorization: Bearer` ou `x-api-key`.
- Não há automação de mouse/teclado. A célula do runtime fica ativa com health checks autenticados e continua sujeita aos limites do Kaggle.
