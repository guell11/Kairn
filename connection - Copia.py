"""Network checks run outside Qt's UI thread."""
from urllib.parse import urlsplit, urlunsplit
import json
import httpx
import time
import json
from localization import tr, normalize_language


def describe_probe(result, language="pt-BR"):
    """Render saved diagnostics in the current UI language without another request."""
    english = normalize_language(language) == "en"
    code = result.get("message_code", "healthy" if result.get("online") else "offline")
    messages = {
        "healthy": ("Saúde e modelo confirmados.", "Health and model confirmed."),
        "offline": ("API não conectada", "API not connected"),
        "missing": ("Preencha URL e chave para testar conexão.", "Enter URL and key to test the connection."),
        "auth": ("Chave recusada. Confira API key.", "Key rejected. Check the API key."),
        "http": (f"HTTP {result.get('http_status')}. Confira runtime e túnel no notebook.", f"HTTP {result.get('http_status')}. Check the runtime and tunnel in the notebook."),
        "failed": ("Conexão falhou. Confira URL, runtime ativo e logs no Kaggle.", "Connection failed. Check the URL, active runtime, and Kaggle logs."),
    }
    text = messages.get(code, messages["failed"])[english]
    if result.get("online"):
        if result.get("stream_verified"):
            text += " Streaming verificado." if not english else " Streaming verified."
        elif result.get("stream_checked"):
            text += (" Teste de streaming falhou; confira logs ou tente túnel nomeado." if not english else " Streaming test failed; check the logs or try a named tunnel.")
        else:
            text += " Execute teste de conexão para validar streaming." if not english else " Run the connection test to verify streaming."
        if result.get("metrics_unavailable"):
            text += " Telemetria indisponível." if not english else " Telemetry unavailable."
    return text


def _stream_works(client, base_url):
    # Parse SSE events, not HTTP packet boundaries. A fully buffered response
    # must not pass just because it was split into two network reads.
    received = {}
    started = time.monotonic()
    count = 0
    data_lines = []
    with client.stream("GET", base_url + "/stream-test", timeout=12) as response:
        if not response.is_success or "text/event-stream" not in response.headers.get("content-type", "").lower():
            return False
        for line in response.iter_lines():
            count += len(line)
            if count > 65536 or time.monotonic() - started > 15:
                return False
            if line.startswith("data:"):
                data_lines.append(line[5:].lstrip())
            elif not line and data_lines:
                try:
                    event = json.loads("\n".join(data_lines))
                except ValueError:
                    return False
                data_lines.clear()
                if not isinstance(event, dict):
                    return False
                seq = event.get("seq")
                if seq not in (1, 2) or seq in received:
                    return False
                received[seq] = time.monotonic()
                if seq == 2:
                    return bool(event.get("done") is True and 1 in received and received[2] - received[1] >= 1.0)
    return False


def normalize_url(value):
    value = value.strip()
    parts = urlsplit(value)
    if parts.scheme not in {"https", "http"} or not parts.hostname or parts.username or parts.password or parts.query or parts.fragment or any(c.isspace() for c in value):
        raise ValueError("Use URL HTTP(S), sem credenciais, query ou fragmento.")
    path = parts.path.rstrip("/")
    if not path.endswith("/v1"):
        path += "/v1"
    return urlunsplit((parts.scheme, parts.netloc, path, "", ""))


def probe_endpoint(base_url, api_key, language="pt-BR", verify_stream=False):
    language = normalize_language(language)
    result = {"online": False, "tps": 0, "tokens": 0, "agents_available": False,
              "stream_verified": False, "stream_checked": verify_stream, "message_code": "offline"}
    if not base_url or not api_key:
        result["message_code"] = "missing"
        return dict(result, message=describe_probe(result, language))
    headers = {"Authorization": f"Bearer {api_key}", "x-api-key": api_key}
    try:
        with httpx.Client(timeout=8, follow_redirects=True, headers=headers) as client:
            health = client.get(base_url.removesuffix("/v1") + "/health")
            health.raise_for_status()
            data = health.json()
            if data.get("status") not in {"ok", "healthy"}:
                raise ValueError("Server is not ready yet." if language == "en" else "Servidor ainda não está pronto.")
            response = client.get(base_url + "/models")
            response.raise_for_status()
            models = response.json().get("data") or []
            if not models or not models[0].get("id"):
                raise ValueError("API returned no available model." if language == "en" else "API respondeu sem modelo disponível.")
            result.update(online=True, model=models[0]["id"], message=("Health and model confirmed." if language == "en" else "Saúde e modelo confirmados."),
                          context=data.get("context"), slots=data.get("slots"), max_output=data.get("max_output"), agents_available=False,
                          stream_verified=False, message_code="healthy")
            if verify_stream:
                try:
                    verified = _stream_works(client, base_url)
                    result["stream_verified"] = verified
                    result["agents_available"] = verified
                    if not verified:
                        result["message"] += (" Streaming test failed; agents remain disabled." if language == "en" else " Teste de streaming falhou; agentes continuam desativados.")
                except (httpx.HTTPError, ValueError):
                    result["message"] += (" Streaming test failed; agents remain disabled." if language == "en" else " Teste de streaming falhou; agentes continuam desativados.")
            else:
                result["message"] += (" Run connection test to verify streaming." if language == "en" else " Execute o teste de conexão para validar streaming.")
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
                result["metrics_unavailable"] = True
                result["message"] += (" Telemetry unavailable." if language == "en" else " Telemetria indisponível.")
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        result.update(message_code="auth" if status in {401, 403} else "http", http_status=status)
        result["message"] = (("Key rejected. Check the API key." if language == "en" else "Chave recusada. Confira API key.") if status in {401, 403} else (f"HTTP {status}. Check the runtime and tunnel in the notebook." if language == "en" else f"HTTP {status}. Confira runtime e túnel no notebook."))
    except (httpx.HTTPError, ValueError, TypeError, AttributeError):
        result["message_code"] = "failed"
        result["message"] = "Connection failed. Check the URL, active runtime, and Kaggle logs." if language == "en" else "Conexão falhou. Confira URL, runtime ativo e logs no Kaggle."
    result["message"] = describe_probe(result, language)
    return result
