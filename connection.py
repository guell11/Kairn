"""Network checks run outside Qt's UI thread."""
from urllib.parse import urlsplit, urlunsplit
import httpx


def normalize_url(value):
    value = value.strip()
    parts = urlsplit(value)
    if parts.scheme not in {"https", "http"} or not parts.hostname or parts.username or parts.password or parts.query or parts.fragment or any(c.isspace() for c in value):
        raise ValueError("Use URL HTTP(S), sem credenciais, query ou fragmento.")
    path = parts.path.rstrip("/")
    if not path.endswith("/v1"):
        path += "/v1"
    return urlunsplit((parts.scheme, parts.netloc, path, "", ""))


def probe_endpoint(base_url, api_key):
    result = {"online": False, "tps": 0, "tokens": 0}
    if not base_url or not api_key:
        return dict(result, message="Preencha URL e chave para testar conexão.")
    headers = {"Authorization": f"Bearer {api_key}", "x-api-key": api_key}
    try:
        with httpx.Client(timeout=8, follow_redirects=True, headers=headers) as client:
            health = client.get(base_url.removesuffix("/v1") + "/health")
            health.raise_for_status()
            data = health.json()
            if data.get("status") not in {"ok", "healthy"}:
                raise ValueError("Servidor ainda não está pronto.")
            response = client.get(base_url + "/models")
            response.raise_for_status()
            models = response.json().get("data") or []
            if not models or not models[0].get("id"):
                raise ValueError("API respondeu sem modelo disponível.")
            result.update(online=True, model=models[0]["id"], message="Saúde e modelo confirmados.",
                          context=data.get("context"), slots=data.get("slots"), agents_available=True)
            hostname = urlsplit(base_url).hostname
            if hostname == "trycloudflare.com" or hostname.endswith(".trycloudflare.com"):
                result["agents_available"] = False
                result["message"] += " Quick Tunnel não suporta SSE. Gere notebook com túnel nomeado para liberar agentes."
            try:
                metrics = client.get(base_url.removesuffix("/v1") + "/metrics")
                metrics.raise_for_status()
                import re
                def value(name):
                    match = re.search(r"^" + re.escape(name) + r"(?:\{[^}]*\})?\s+([0-9.eE+-]+)$", metrics.text, re.M)
                    return float(match.group(1)) if match else 0
                tokens = value("llamacpp:tokens_predicted_total")
                seconds = value("llamacpp:tokens_predicted_seconds_total")
                result.update(tokens=int(tokens), tps=round(value("llamacpp:predicted_tokens_seconds") or (tokens / seconds if seconds else 0), 1))
            except (httpx.HTTPError, ValueError):
                result["message"] += " Telemetria indisponível."
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        result["message"] = "Chave recusada. Confira API key." if status in {401, 403} else f"HTTP {status}. Confira runtime e túnel no notebook."
    except (httpx.HTTPError, ValueError, TypeError, AttributeError):
        result["message"] = "Conexão falhou. Confira URL, runtime ativo e logs no Kaggle."
    return result
