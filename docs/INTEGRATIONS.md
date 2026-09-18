# Integrações locais

Depois de Conectar, o Studio exige probe real de streaming e configura automaticamente cada cliente instalado no `PATH`. Repetir a configuração atualiza URL, modelo, contexto e limites; não baixa pesos nem altera o cache do modelo.

Cada arquivo existente recebe backup com sufixo `.kaggle-studio-YYYYMMDD-HHMMSS.bak`. JSON/JSONC inválido interrompe a configuração antes de sobrescrever o arquivo.

## Codex CLI

O Studio grava o provider em `~/.codex/config.toml` e o perfil em `~/.codex/kaggle-studio.config.toml`. O perfil é aberto com `codex --profile kaggle-studio`. A autenticação usa `model_providers.<id>.auth.command`, formato suportado pela Codex CLI atual; o comando imprime o token sem colocá-lo no TOML.

O token fica em `~/.codex/.kaggle-studio-token`, com permissões restritas, e o leitor gerenciado fica em `~/.codex/kaggle-studio-token.py`. A configuração usa Responses API (`wire_api = "responses"`).

## Claude Code

O Studio atualiza `~/.claude/settings.json`, aliases de modelo e `ANTHROPIC_BASE_URL`. Para funcionar em um terminal novo, `apiKeyHelper` executa `~/.claude/kaggle-studio-api-key.py`, que lê `~/.claude/.kaggle-studio-claude-token`. Isso usa o helper de credencial suportado pelo Claude Code e evita depender de variáveis exportadas pelo Studio. Token permanece em arquivo protegido.

## OpenCode

O provider OpenAI-compatible fica em `~/.config/opencode/opencode.jsonc` (ou `opencode.json` se esse arquivo já existir). O campo `options.apiKey` usa `{file:~/.kaggle-studio-opencode-token}`, referência de arquivo suportada pelo OpenCode. O token é protegido e o modelo principal e pequeno apontam para o mesmo modelo configurado.

## ZCode

Quando o executável `zcode` ou `zcodex` existe, o Studio atualiza os arquivos v2 e CLI em `~/.zcode/`. A chave fica somente no provider do Desktop; o CLI recebe `ZCODE_API_KEY` no ambiente do processo lançado pelo Studio.

## Verificação

Use `Integrações` depois de conectar o gateway. O resultado mostra cada ferramenta instalada, configurada ou ausente. O túnel precisa passar o probe de cadência SSE; URL Quick Tunnel só é aceita se o probe real funcionar. Para verificar manualmente:

```text
codex --profile kaggle-studio --help
opencode --help
claude --help
```

Esses comandos não fazem requisição de modelo.
