# Segurança

## Credenciais

O arquivo `.kaggle-studio/state.json` contém apenas preferências e Base URL. A API key **não** é gravada no estado do Studio.

Cada cliente, porém, tem um contrato diferente:

- **Codex:** o bearer fica em `~/.codex/.kaggle-studio-token` com permissão `0600` quando suportada. `config.toml` contém somente `auth.command`, que lê esse arquivo.
- **Claude Code:** o token não é escrito em `settings.json`; é injetado no ambiente do processo aberto pelo Studio.
- **OpenCode:** a config contém `{env:KAGGLE_STUDIO_API_KEY}` e a chave é injetada no ambiente.
- **ZCode:** o Desktop precisa de `options.apiKey` em `~/.zcode/v2/config.json`; esse arquivo é restringido a `0600`. O config do CLI em `~/.zcode/cli/config.json` não duplica a chave e usa `ZCODE_API_KEY` do ambiente.

Nunca publique esses arquivos sensíveis em repositórios, tickets ou logs.

## Backups

Antes de modificar uma configuração existente, `integrations.py` cria um backup timestampado ao lado do arquivo quando o conteúdo realmente muda. Backups podem conter segredos anteriores do próprio cliente; revise-os antes de compartilhá-los.

## Gateway público

O túnel Cloudflare do Kaggle é publicamente alcançável. O gateway exige uma chave via `Authorization: Bearer` ou `x-api-key` em health, models, metrics e rotas de inferência. Use a chave aleatória gerada pelo Studio e não a reutilize em outros serviços.

## Sessão Kaggle

A célula principal pode permanecer executando um heartbeat autenticado enquanto os processos estão saudáveis. Isso não simula usuário, não remove quotas/limites do Kaggle e não transforma o notebook em hosting permanente.

## Relato

Não inclua Base URLs ainda ativas, chaves, arquivos de token, configs ZCode ou logs com conteúdo privado ao abrir um issue público.
