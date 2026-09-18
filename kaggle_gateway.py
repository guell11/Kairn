from __future__ import annotations

import json
import os
import time
import uuid
import asyncio
import contextlib
from typing import Any

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse

BACKEND_URL = os.getenv("KAGGLE_BACKEND_URL", "http://127.0.0.1:8081").rstrip("/")
API_KEY = os.getenv("KAGGLE_STUDIO_API_KEY", "")
MODEL_ID = os.getenv("KAGGLE_MODEL_ID", "kaggle-model")
SYSTEM_PROMPT = os.getenv("KAGGLE_AGENT_SYSTEM_PROMPT", "").strip()
MAX_OUTPUT = int(os.getenv("KAGGLE_MAX_OUTPUT", "8192"))
REASONING_BUDGET = int(os.getenv("KAGGLE_REASONING_BUDGET", "3072"))
BACKEND_FAMILY = os.getenv("KAGGLE_BACKEND_FAMILY", "official-layer")
GPU_NAMES = [name.strip() for name in os.getenv("KAGGLE_GPU_NAMES", "").split("|") if name.strip()]
SPLIT_MODE = os.getenv("KAGGLE_SPLIT_MODE", "graph")
CONTEXT_SIZE = int(os.getenv("KAGGLE_CONTEXT_SIZE", "0") or 0)
SLOTS = int(os.getenv("KAGGLE_SLOTS", "0") or 0)
STARTED_AT = time.time()
STREAM_BATCH_SECONDS = min(10.0, max(0.25, float(os.getenv("KAGGLE_STREAM_BATCH_SECONDS", "4"))))
STREAM_BATCH_BYTES = min(1024 * 1024, max(16 * 1024, int(os.getenv("KAGGLE_STREAM_BATCH_BYTES", str(256 * 1024)))))
STREAM_TEST_DELAY = min(10.0, max(1.0, float(os.getenv("KAGGLE_STREAM_TEST_DELAY", "4"))))

app = FastAPI(title="Kaggle Studio Universal Gateway", version="4.0")
client = httpx.AsyncClient(
    timeout=httpx.Timeout(900.0, connect=20.0),
    limits=httpx.Limits(max_connections=256, max_keepalive_connections=64),
)


async def batched_stream(source, interval=STREAM_BATCH_SECONDS, max_bytes=STREAM_BATCH_BYTES):
    """Batch one continuous upstream stream, preserving every protocol byte."""
    if interval <= 0 or max_bytes < 1:
        raise ValueError("Batch interval and buffer size must be positive")
    iterator = source.__aiter__()
    pending = bytearray()
    deadline = None
    task = asyncio.create_task(iterator.__anext__())
    try:
        while True:
            if pending and deadline is None:
                deadline = asyncio.get_running_loop().time() + interval
            timeout = max(0.0, deadline - asyncio.get_running_loop().time()) if deadline is not None else None
            if pending and timeout == 0:
                yield bytes(pending)
                pending.clear()
                deadline = None
                continue
            done, _ = await asyncio.wait({task}, timeout=timeout)
            if not done:
                yield bytes(pending); pending.clear(); deadline = None
                continue
            try:
                chunk = task.result()
            except StopAsyncIteration:
                if pending:
                    yield bytes(pending)
                return
            except Exception:
                if pending:
                    yield bytes(pending)
                    pending.clear()
                raise
            if chunk:
                view = memoryview(chunk)
                offset = 0
                while offset < len(view):
                    length = min(max_bytes - len(pending), len(view) - offset)
                    pending.extend(view[offset:offset + length])
                    offset += length
                    if len(pending) == max_bytes:
                        yield bytes(pending)
                        pending.clear()
                        deadline = None
            task = asyncio.create_task(iterator.__anext__())
    except asyncio.CancelledError:
        raise
    finally:
        if not task.done():
            task.cancel()
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await task
        if hasattr(iterator, "aclose"):
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await iterator.aclose()


def _error(message: str, status: int, error_type: str = "gateway_error") -> JSONResponse:
    return JSONResponse(
        {"error": {"message": message, "type": error_type}}, status_code=status
    )


def _authorized(request: Request) -> bool:
    if not API_KEY:
        return False
    bearer = request.headers.get("authorization", "")
    xkey = request.headers.get("x-api-key", "")
    return bearer == f"Bearer {API_KEY}" or xkey == API_KEY


def _merge_system(existing: Any) -> Any:
    if not SYSTEM_PROMPT:
        return existing
    if not existing:
        return SYSTEM_PROMPT
    if isinstance(existing, str):
        return SYSTEM_PROMPT + "\n\n" + existing
    if isinstance(existing, list):
        return [{"type": "text", "text": SYSTEM_PROMPT}, *existing]
    return existing


def _bounded_int(value: Any, default: int, ceiling: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(1, min(parsed, ceiling))


def _normalize(payload: dict, path: str) -> dict:
    data = dict(payload)
    data["model"] = MODEL_ID

    if path.endswith("chat/completions"):
        messages = list(data.get("messages") or [])
        if SYSTEM_PROMPT:
            if messages and isinstance(messages[0], dict) and messages[0].get("role") == "system":
                messages[0] = dict(
                    messages[0], content=_merge_system(messages[0].get("content"))
                )
            else:
                messages.insert(0, {"role": "system", "content": SYSTEM_PROMPT})
        data["messages"] = messages
        data["max_tokens"] = _bounded_int(data.get("max_tokens"), MAX_OUTPUT, MAX_OUTPUT)
        data.setdefault("reasoning_budget", REASONING_BUDGET)

    elif path.endswith("responses"):
        data["instructions"] = _merge_system(data.get("instructions"))
        data["max_output_tokens"] = _bounded_int(
            data.get("max_output_tokens"), MAX_OUTPUT, MAX_OUTPUT
        )

    elif path.endswith("messages"):
        data["system"] = _merge_system(data.get("system"))
        data["max_tokens"] = _bounded_int(data.get("max_tokens"), MAX_OUTPUT, MAX_OUTPUT)

    return data


def _anthropic_to_openai(payload: dict) -> dict:
    messages = []
    system = _merge_system(payload.get("system"))
    if system:
        messages.append({"role": "system", "content": system})
    for source in payload.get("messages") or []:
        role = source.get("role", "user")
        content = source.get("content", "")
        if isinstance(content, str):
            messages.append({"role": role, "content": content})
            continue
        text, tool_calls = [], []
        for block in content or []:
            kind = block.get("type")
            if kind == "text":
                text.append(block.get("text", ""))
            elif kind == "tool_use":
                tool_calls.append({
                    "id": block.get("id") or "toolu_" + uuid.uuid4().hex,
                    "type": "function",
                    "function": {
                        "name": block.get("name", "tool"),
                        "arguments": json.dumps(block.get("input") or {}, ensure_ascii=False),
                    },
                })
            elif kind == "tool_result":
                value = block.get("content", "")
                if not isinstance(value, str):
                    value = json.dumps(value, ensure_ascii=False)
                messages.append({"role": "tool", "tool_call_id": block.get("tool_use_id", ""), "content": value})
        item = {"role": role, "content": "\n".join(text) or None}
        if tool_calls:
            item["tool_calls"] = tool_calls
        if item["content"] is not None or tool_calls:
            messages.append(item)
    tools = []
    for tool in payload.get("tools") or []:
        tools.append({"type": "function", "function": {
            "name": tool.get("name", "tool"),
            "description": tool.get("description", ""),
            "parameters": tool.get("input_schema") or {"type": "object", "properties": {}},
        }})
    result = {
        "model": MODEL_ID,
        "messages": messages,
        "max_tokens": _bounded_int(payload.get("max_tokens"), MAX_OUTPUT, MAX_OUTPUT),
        "stream": bool(payload.get("stream")),
    }
    for key in ("temperature", "top_p", "stop_sequences"):
        if key in payload:
            result["stop" if key == "stop_sequences" else key] = payload[key]
    if tools:
        result["tools"] = tools
    return result


def _openai_to_anthropic(payload: dict) -> dict:
    choice = (payload.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    blocks = []
    if message.get("content"):
        blocks.append({"type": "text", "text": message["content"]})
    for call in message.get("tool_calls") or []:
        function = call.get("function") or {}
        try:
            arguments = json.loads(function.get("arguments") or "{}")
        except json.JSONDecodeError:
            arguments = {"raw": function.get("arguments", "")}
        blocks.append({"type": "tool_use", "id": call.get("id") or "toolu_" + uuid.uuid4().hex,
                       "name": function.get("name", "tool"), "input": arguments})
    usage = payload.get("usage") or {}
    finish = choice.get("finish_reason")
    return {
        "id": payload.get("id") or "msg_" + uuid.uuid4().hex,
        "type": "message", "role": "assistant", "model": MODEL_ID,
        "content": blocks,
        "stop_reason": "tool_use" if finish == "tool_calls" else ("max_tokens" if finish == "length" else "end_turn"),
        "stop_sequence": None,
        "usage": {"input_tokens": usage.get("prompt_tokens", 0), "output_tokens": usage.get("completion_tokens", 0)},
    }


@app.on_event("shutdown")
async def _shutdown() -> None:
    await client.aclose()


@app.get("/")
async def root() -> dict:
    return {
        "name": "Kaggle Studio",
        "model": MODEL_ID,
        "protocols": ["openai-chat", "openai-responses", "anthropic-messages"],
    }


@app.get("/health")
async def health(request: Request):
    if not _authorized(request):
        return _error("Invalid API key", 401, "authentication_error")
    try:
        response = await client.get(BACKEND_URL + "/health", timeout=4)
    except httpx.HTTPError as exc:
        return JSONResponse(
            {"status": "offline", "error": str(exc)[:160], "model": MODEL_ID},
            status_code=503,
        )
    status = "ok" if response.is_success else "degraded"
    upstream: Any = None
    try:
        upstream = response.json()
    except (ValueError, TypeError):
        upstream = None
    return JSONResponse(
        {
            "status": status,
            "heartbeat": int(time.time()),
            "uptime_seconds": int(time.time() - STARTED_AT),
            "model": MODEL_ID,
            "backend": BACKEND_FAMILY,
            "backend_status": response.status_code,
            "backend_health": upstream,
            "gpus": GPU_NAMES,
            "gpu_count": len(GPU_NAMES),
            "split": SPLIT_MODE,
            "context": CONTEXT_SIZE,
            "slots": SLOTS,
            "max_output": MAX_OUTPUT,
            "stream_batch_seconds": STREAM_BATCH_SECONDS,
        },
        status_code=200 if response.is_success else 503,
    )


@app.get("/v1/models")
async def models(request: Request):
    if not _authorized(request):
        return _error("Unauthorized", 401, "authentication_error")
    return {
        "object": "list",
        "data": [{"id": MODEL_ID, "object": "model", "owned_by": "kaggle-studio"}],
    }


@app.get("/v1/stream-test")
async def stream_test(request: Request):
    """Deterministic SSE cadence check. No model inference involved."""
    if not _authorized(request):
        return _error("Unauthorized", 401, "authentication_error")

    async def events():
        yield b"event: stream_test\ndata: {\"seq\":1}\n\n"
        await asyncio.sleep(STREAM_TEST_DELAY)
        yield b"event: stream_test\ndata: {\"seq\":2,\"done\":true}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream", headers={"cache-control": "no-cache, no-transform", "x-accel-buffering": "no"})


@app.get("/metrics")
async def metrics(request: Request):
    if not _authorized(request):
        return Response("unauthorized", status_code=401)
    try:
        response = await client.get(BACKEND_URL + "/metrics", timeout=8)
    except httpx.HTTPError as exc:
        return Response(f"upstream unavailable: {str(exc)[:120]}", status_code=503)
    return Response(
        response.content,
        status_code=response.status_code,
        media_type=response.headers.get("content-type", "text/plain"),
    )


@app.api_route("/v1/{route:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy(route: str, request: Request):
    if not _authorized(request):
        return _error("Invalid API key", 401, "authentication_error")

    body = await request.body()
    payload = None
    if body:
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            pass

    anthropic = route == "messages" and BACKEND_FAMILY == "ik_llama"
    path = "v1/chat/completions" if anthropic else "v1/" + route
    if isinstance(payload, dict):
        payload = _anthropic_to_openai(payload) if anthropic else _normalize(payload, path)
        body = json.dumps(payload, ensure_ascii=False).encode()

    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower()
        not in {"host", "authorization", "x-api-key", "content-length", "connection"}
    }
    if body:
        headers["content-type"] = request.headers.get("content-type", "application/json")
    headers["accept-encoding"] = "identity"

    upstream = client.build_request(
        request.method,
        f"{BACKEND_URL}/{path}",
        content=body,
        headers=headers,
        params=request.query_params,
    )
    try:
        response = await client.send(upstream, stream=True)
    except httpx.HTTPError as exc:
        return _error(f"Upstream unavailable: {str(exc)[:160]}", 502)

    content_type = response.headers.get("content-type", "")
    wants_stream = response.is_success and ("text/event-stream" in content_type or (
        isinstance(payload, dict) and payload.get("stream")
    ))

    if wants_stream:
        if anthropic:
            async def anthropic_chunks():
                message_id = "msg_" + uuid.uuid4().hex
                def sse(name, value):
                    return ("event: " + name + "\ndata: " + json.dumps(value, ensure_ascii=False) + "\n\n").encode()
                yield sse("message_start", {"type":"message_start","message":{"id":message_id,"type":"message","role":"assistant","model":MODEL_ID,"content":[],"stop_reason":None,"stop_sequence":None,"usage":{"input_tokens":0,"output_tokens":0}}})
                text_index, text_started = 0, False
                tool_states = {}
                next_index = 1
                buffer = b""
                try:
                    async for raw in batched_stream(response.aiter_raw()):
                        emitted = []
                        buffer += raw
                        while b"\n\n" in buffer:
                            frame, buffer = buffer.split(b"\n\n", 1)
                            data = b"".join(line[5:].strip() for line in frame.splitlines() if line.startswith(b"data:"))
                            if not data or data == b"[DONE]":
                                continue
                            try:
                                event = json.loads(data)
                            except json.JSONDecodeError:
                                continue
                            choice = (event.get("choices") or [{}])[0]
                            delta = choice.get("delta") or {}
                            text = delta.get("content")
                            if text:
                                if not text_started:
                                    text_started = True
                                    emitted.append(sse("content_block_start", {"type":"content_block_start","index":text_index,"content_block":{"type":"text","text":""}}))
                                emitted.append(sse("content_block_delta", {"type":"content_block_delta","index":text_index,"delta":{"type":"text_delta","text":text}}))
                            for call in delta.get("tool_calls") or []:
                                source_index = int(call.get("index", 0))
                                function = call.get("function") or {}
                                state = tool_states.get(source_index)
                                if state is None:
                                    state = {"index": next_index, "id": call.get("id") or "toolu_" + uuid.uuid4().hex,
                                             "name": function.get("name") or "tool"}
                                    next_index += 1
                                    tool_states[source_index] = state
                                    emitted.append(sse("content_block_start", {"type":"content_block_start","index":state["index"],
                                              "content_block":{"type":"tool_use","id":state["id"],"name":state["name"],"input":{}}}))
                                arguments = function.get("arguments")
                                if arguments:
                                    emitted.append(sse("content_block_delta", {"type":"content_block_delta","index":state["index"],
                                              "delta":{"type":"input_json_delta","partial_json":arguments}}))
                            if choice.get("finish_reason"):
                                if text_started:
                                    emitted.append(sse("content_block_stop", {"type":"content_block_stop","index":text_index}))
                                for state in tool_states.values():
                                    emitted.append(sse("content_block_stop", {"type":"content_block_stop","index":state["index"]}))
                                reason = "tool_use" if choice["finish_reason"] == "tool_calls" else ("max_tokens" if choice["finish_reason"] == "length" else "end_turn")
                                emitted.append(sse("message_delta", {"type":"message_delta","delta":{"stop_reason":reason,"stop_sequence":None},"usage":{"output_tokens":0}}))
                        if emitted:
                            yield b"".join(emitted)
                    yield sse("message_stop", {"type":"message_stop"})
                finally:
                    await response.aclose()
            return StreamingResponse(anthropic_chunks(), status_code=response.status_code, media_type="text/event-stream", headers={"cache-control": "no-cache, no-transform", "x-accel-buffering": "no"})
        async def chunks():
            try:
                async for chunk in batched_stream(response.aiter_raw()):
                    yield chunk
            finally:
                await response.aclose()

        return StreamingResponse(
            chunks(),
            status_code=response.status_code,
            media_type=content_type or "text/event-stream",
            headers={"cache-control": "no-cache, no-transform", "x-accel-buffering": "no"},
        )

    content = await response.aread()
    await response.aclose()
    if anthropic and response.is_success:
        try:
            return JSONResponse(_openai_to_anthropic(json.loads(content)), status_code=response.status_code)
        except (json.JSONDecodeError, TypeError):
            return _error("Resposta inválida do backend", 502)
    return Response(
        content,
        status_code=response.status_code,
        media_type=content_type or "application/json",
    )


# Compatibility aliases for clients which accept a host URL but append no /v1.
@app.api_route("/chat/completions", methods=["POST"])
async def chat_completions_alias(request: Request):
    return await proxy("chat/completions", request)


@app.api_route("/responses", methods=["POST"])
async def responses_alias(request: Request):
    return await proxy("responses", request)


@app.api_route("/messages", methods=["POST"])
async def messages_alias(request: Request):
    return await proxy("messages", request)
