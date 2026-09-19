from __future__ import annotations

LANGUAGES = ("pt-BR", "en")

MESSAGES = {
    "pt-BR": {
        "unknown_model": "Modelo desconhecido",
        "invalid_config": "Configuração inválida",
        "invalid_stage": "Etapa de configuração inválida",
        "copied": "Copiado para a área de transferência",
        "save_notebook": "Salvar notebook Kaggle",
        "notebook_saved": "Notebook salvo. Importe no Kaggle e execute duas células.",
        "export_failed": "Falha ao exportar: {error}",
        "configured": "{count}/{total} integrações configuradas",
        "disconnected": "{count}/{total} integrações desconectadas",
        "invalid_navigation": "Destino de navegação inválido",
        "offline": "API não conectada",
        "wait_probe": "Aguarde teste de conexão terminar antes de fechar.",
        "connect_sse": "Conecte e valide streaming antes de configurar agentes.",
        "connect_kaggle": "Conecte a API do Kaggle primeiro",
        "not_found": "{tool} não encontrado no PATH; config foi gravado mesmo assim",
        "launched": "{tool} iniciado com o gateway Kaggle",
        "launch_failed": "Falha ao abrir {tool}: {error}",
        "diagnostic_failed": "Falha no diagnóstico. Confira URL e tente novamente.",
        "code_api": "# Conecte a API primeiro",
    },
    "en": {
        "unknown_model": "Unknown model",
        "invalid_config": "Invalid configuration",
        "invalid_stage": "Invalid setup stage",
        "copied": "Copied to clipboard",
        "save_notebook": "Save Kaggle notebook",
        "notebook_saved": "Notebook saved. Import it into Kaggle and run both cells.",
        "export_failed": "Export failed: {error}",
        "configured": "{count}/{total} integrations configured",
        "disconnected": "{count}/{total} integrations disconnected",
        "invalid_navigation": "Invalid navigation target",
        "offline": "API not connected",
        "wait_probe": "Wait for the connection test to finish before closing.",
        "connect_sse": "Connect and verify streaming before configuring agents.",
        "connect_kaggle": "Connect to the Kaggle API first",
        "not_found": "{tool} not found in PATH; config was still written",
        "launched": "{tool} started with the Kaggle gateway",
        "launch_failed": "Failed to open {tool}: {error}",
        "diagnostic_failed": "Diagnostics failed. Check the URL and try again.",
        "code_api": "# Connect the API first",
    },
}


def normalize_language(value: object) -> str:
    return value if value in LANGUAGES else "pt-BR"


def tr(language: object, key: str, **kwargs: object) -> str:
    language = normalize_language(language)
    template = MESSAGES[language].get(key, MESSAGES["pt-BR"].get(key, key))
    return template.format(**kwargs)


def localize_message(message: str, language: object) -> str:
    """Translate known integration messages while preserving paths/errors."""
    language = normalize_language(language)
    exact = {
        "Codex apontado para Responses API com profile-v2; token protegido é lido por auth.command.": "Codex configured for the Responses API with profile-v2; the protected token is read by auth.command.",
        "Claude Code configurado para /v1/messages; token protegido é lido por apiKeyHelper.": "Claude Code configured for /v1/messages; the protected token is read by apiKeyHelper.",
        "OpenCode recebeu provider OpenAI-compatible, modelo principal/lite e instruções AGENTS.md.": "OpenCode received an OpenAI-compatible provider, main/lite model, and AGENTS.md instructions.",
        "ZCode Desktop e app-server configurados. Desktop guarda chave em arquivo protegido; CLI recebe ZCODE_API_KEY no ambiente.": "ZCode Desktop and app-server configured. Desktop stores the key in a protected file; CLI receives ZCODE_API_KEY through the environment.",
        "Configuração Codex removida.": "Codex configuration removed.",
        "Configuração Claude removida.": "Claude configuration removed.",
        "Configuração OpenCode removida.": "OpenCode configuration removed.",
        "Configuração ZCode removida.": "ZCode configuration removed.",
    }
    if message in exact:
        return exact[message] if language == "en" else message
    if language == "en":
        if message.startswith("Falha ao configurar "):
            return message.replace("Falha ao configurar ", "Failed to configure ", 1)
        if message.startswith("Falha ao desconectar "):
            return message.replace("Falha ao desconectar ", "Failed to disconnect ", 1)
    return message
