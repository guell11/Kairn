"""Pure runtime helpers, also embedded in exported Kaggle cells."""


def llama_command(server, model, alias, context, slots, split, help_text,
                  temperature=0.6, top_k=40, top_p=0.95, min_p=0.05,
                  reasoning_budget=3072, speculation="auto", draft_tokens=4):
    import re
    flags = set(re.findall(r"--[a-z][a-z0-9-]*", help_text))
    command = [str(server), "--model", str(model), "--alias", alias,
               "--host", "127.0.0.1", "--port", "8081",
               "--ctx-size", str(context * slots), "--parallel", str(slots),
               "--split-mode", split, "--tensor-split", "1,1",
               "--n-gpu-layers", "999", "--batch-size", "512",
               "--ubatch-size", "128", "--jinja", "--metrics"]
    # Forks and upstream expose different optional flags. Never guess support.
    cache = "f16" if split == "tensor" else "q8_0"
    options = {"--cache-type-k": cache, "--cache-type-v": cache,
               "--temp": temperature, "--top-k": top_k, "--top-p": top_p,
               "--min-p": min_p, "--reasoning-budget": reasoning_budget}
    for flag, value in options.items():
        if flag in flags:
            command += [flag, str(value)]
    if "--flash-attn" in flags:
        command += ["--flash-attn", "on"] if split != "graph" else ["--flash-attn"]
    # Upstream llama.cpp n-gram speculation needs no second model. Enable only
    # when the compiled server advertises the exact options. Older forks
    # safely keep normal decoding. N-gram has its own draft-length parameter.
    advertised_ngram = "--spec-type" in flags and "ngram-simple" in (help_text or "")
    if speculation == "ngram" and not advertised_ngram:
        raise RuntimeError("Speculação ngram solicitada, mas llama-server não anuncia ngram-simple.")
    if speculation != "off" and not any(flag in command for flag in ("--model-draft", "--spec-type")):
        if advertised_ngram:
            command += ["--spec-type", "ngram-simple"]
            if "--spec-ngram-simple-size-m" in flags:
                command += ["--spec-ngram-simple-size-m", str(max(1, int(draft_tokens)))]
    return command


def retry_slots(slots):
    result = [max(1, int(slots))]
    while result[-1] > 1:
        result.append(max(1, result[-1] // 2))
    return result


def stop_process(process):
    import subprocess
    if process is not None and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)
