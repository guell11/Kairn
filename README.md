<div align="center">

# KAIRN

### Turn free Kaggle GPUs into your local AI backend.

**2× NVIDIA T4 · llama.cpp · OpenAI-compatible API · Anthropic-compatible API · Local AI Agents**

<br>

[![Start Now](https://img.shields.io/badge/⚡_START_NOW-111111?style=for-the-badge)](#-quick-start)
[![How It Works](https://img.shields.io/badge/HOW_IT_WORKS-222222?style=for-the-badge)](#-how-it-works)
[![Agents](https://img.shields.io/badge/LOCAL_AGENTS-333333?style=for-the-badge)](#-local-agents)
[![Backends](https://img.shields.io/badge/BACKENDS-444444?style=for-the-badge)](#-backends)

<br>

**Kaggle → NVIDIA T4 ×2 → llama.cpp → Kairn → Your local tools**

<br>

https://github.com/user-attachments/assets/b56af5f6-3d62-4396-b36e-b2ca61e14109

<br>

<sub>
Run the model in Kaggle. Use it from your own machine.
</sub>

</div>

---

## What is Kairn?

Your GPU does not have to be inside your computer.

**Kairn turns a Kaggle notebook with 2× NVIDIA T4 GPUs into a remote AI inference backend that your local tools can use like a normal API.**

You configure everything locally, launch the runtime on Kaggle, connect the generated endpoint, and point your favorite AI tools at it.

No local CUDA setup.

No expensive GPU required.

No permanent server to deploy.

No infrastructure ceremony involving seventeen terminals and a blood offering to the dependency gods.

---

## ✦ Why Kairn?

Kaggle gives you the compute.

`llama.cpp` runs the model.

Kairn handles almost everything in between.

|                             |                                                 |
| --------------------------- | ----------------------------------------------- |
| ⚡ **2× NVIDIA T4**          | Multi-GPU inference                             |
| 🧠 **llama.cpp**            | CUDA-powered GGUF inference                     |
| 🔌 **OpenAI API**           | Chat Completions + Responses                    |
| 💬 **Anthropic API**        | Messages-compatible endpoint                    |
| 🌐 **Remote Gateway**       | Authentication + normalization                  |
| ♻️ **Model Cache**          | Reuse downloaded GGUF files                     |
| 🛡️ **Runtime Validation**  | CUDA and GPU checks before loading              |
| 🖥️ **Kairn Studio**        | Configure the runtime visually                  |
| 🤖 **Local Agents**         | Connect Codex, Claude Code, OpenCode and others |
| 🔐 **Credential Isolation** | Local credentials stay where they belong        |

---

# ⚡ Quick Start

## 01 · Launch Kairn

### Windows

```powershell
run.bat
```

or:

```powershell
.\run.ps1
```

### Linux / macOS

```bash
./run.sh
```

Kairn Studio opens locally.

---

## 02 · Configure your runtime

Choose:

```text
Model → Context → Output → Backend
```

Kairn prepares an initial configuration based on the available hardware and limits concurrency when necessary.

A good starting point for dual T4 sessions is:

```text
Context: 16K
Backend: llama.cpp
```

Larger contexts are possible, but VRAM remains governed by physics, which continues to ignore feature requests.

---

## 03 · Create the Kaggle runtime

Inside Kairn Studio, click:

> **Copy GitHub Cell**

Create a new empty Kaggle notebook.

Enable:

```text
Internet     ON
Accelerator  GPU T4 ×2
```

Paste the generated cell.

Run it.

That is the entire deployment process.

The Kaggle bootstrap performs roughly this sequence:

```text
GitHub repository
       │
       ▼
Resolve commit
       │
       ▼
Download Kairn
       │
       ▼
Prepare runtime
       │
       ▼
Validate CUDA
       │
       ▼
Download / reuse model
       │
       ▼
Start inference backend
       │
       ▼
Start Kairn API gateway
       │
       ▼
Expose remote endpoint
```

No notebook upload is required.

---

## 04 · Connect Kairn Studio

When the Kaggle runtime starts, it provides:

```text
Base URL
API Key
```

Paste them into Kairn Studio.

Kairn validates the connection and checks whether the model is ready without blocking the interface.

Once everything is healthy:

```text
● API Connected
● Model Ready
● Agents Unlocked
```

Your Kaggle GPUs are now available to local tools through a normal API endpoint.

---

# 🧭 How It Works

```text
┌─────────────────────────────────────┐
│            YOUR COMPUTER            │
│                                     │
│  Codex · Claude Code · OpenCode     │
│  Scripts · Apps · Custom Agents     │
└──────────────────┬──────────────────┘
                   │
                   │ OpenAI / Anthropic API
                   ▼
┌─────────────────────────────────────┐
│                KAIRN                │
│                                     │
│ Authentication · Gateway · Studio   │
│ API normalization · Agent config    │
└──────────────────┬──────────────────┘
                   │
                   │ HTTPS
                   ▼
┌─────────────────────────────────────┐
│                KAGGLE               │
│                                     │
│       NVIDIA T4      NVIDIA T4      │
│            ╲          ╱             │
│             llama.cpp               │
│                 │                   │
│          Kairn Gateway              │
└─────────────────────────────────────┘
```

The important part is simple:

**Your tools stay local.
The expensive inference happens on Kaggle.**

---

# 🤖 Local Agents

Kairn can connect local AI tools to the model running in your Kaggle session.

Examples include:

```text
Codex
Claude Code
OpenCode
OpenAI-compatible clients
Anthropic-compatible clients
Custom agents
Local scripts
```

Kairn can generate or update tool-specific configuration automatically.

Before changing an existing configuration, Kairn creates a backup whenever supported.

Studio does **not** persist your runtime API key in its regular state.

Tool-specific credentials remain isolated when required.

---

# 🔌 API Compatibility

Kairn exposes familiar API shapes so existing clients require little or no adaptation.

## OpenAI-compatible

Supported endpoints include:

```text
Chat Completions
Responses
```

Example:

```bash
curl "$KAIRN_BASE_URL/v1/chat/completions" \
  -H "Authorization: Bearer $KAIRN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "default",
    "messages": [
      {
        "role": "user",
        "content": "Explain why the sky is blue."
      }
    ]
  }'
```

---

## Anthropic-compatible

Kairn also supports a Messages-compatible API surface for clients expecting Anthropic-style requests.

```text
Messages
```

This makes it possible to connect tools built around either ecosystem without running separate inference servers.

---

# 🧠 Built for Dual T4

The default runtime is designed around Kaggle's dual NVIDIA T4 environment.

```text
llama.cpp b11009
CUDA 12.8

GPU 0 ─ NVIDIA T4
GPU 1 ─ NVIDIA T4

Strategy ─ layer split
KV cache ─ q8_0
```

Before downloading or loading the selected model, Kairn checks whether CUDA actually sees both GPUs.

```bash
llama-server --list-devices
```

Because discovering that CUDA is broken **after downloading 30 GB** is the kind of lesson nobody needs twice.

---

## Recommended starting context

```text
16K
```

Context size has a significant impact on memory usage.

A configuration such as:

```text
128K
```

may exceed available VRAM depending on:

* model size
* quantization
* KV cache type
* number of slots
* backend
* GPU split
* output configuration

If VRAM allocation fails, Kairn can reduce concurrency and retry after terminating the previous backend process.

---

# 🔥 Backends

Kairn supports multiple inference backends.

## llama.cpp

**Default · Recommended**

The standard runtime uses the pinned official `llama.cpp` build:

```text
b11009
```

with:

```text
CUDA 12.8
```

Supported features include:

* Chat Completions
* Responses
* Messages compatibility
* multi-GPU layer split
* configurable context
* configurable output size
* optional sampling flags
* reasoning budget when supported by the model
* GGUF model loading
* model cache reuse

For most users, this should be the first backend to try.

---

## wackMall

**Experimental · T4 optimized**

Kairn supports a dedicated Linux CUDA build targeting:

```text
Ubuntu 22.04
CUDA 12.4
NVIDIA Turing
sm_75
```

The repository contains the workflow needed to build the pinned wackMall revision and publish the expected runtime artifact:

```text
wackmall-main-b30-6aa17e3-cuda12.4-t4
```

If the required release is unavailable, Kairn reports that explicitly.

It does **not** quietly download a Windows binary into Linux and wait for reality to become more flexible.

---

## ik_llama

**Advanced · Experimental**

`ik_llama` can be compiled directly inside the Kaggle environment.

It is intended primarily for experimentation and specialized model support.

Upstream feature parity is not guaranteed.

---

# 🌎 Remote API

Kairn can expose the Kaggle runtime through Cloudflare Tunnel.

## Quick Tunnel

A Cloudflare Quick Tunnel can be useful for:

```text
basic API testing
temporary experiments
manual requests
short sessions
```

---

## Named Cloudflare Tunnel

For more reliable agent usage and streaming, use a **named Cloudflare Tunnel**.

Example:

```text
https://llm.yourdomain.com
             │
             │ Cloudflare Tunnel
             ▼
http://localhost:8000
```

Provide the tunnel token through the notebook prompt or environment configuration:

```bash
TUNNEL_TOKEN
```

Kairn does not automatically create Cloudflare accounts, domains, DNS records, tunnels, or other remote infrastructure.

It configures the runtime around resources you provide.

---

# 💾 Download Once. Reuse.

Models are stored outside the source checkout:

```text
/kaggle/working/models
```

This means updating the Kairn runtime does not automatically delete downloaded GGUF files.

Before reuse, cached model files are validated.

Typical lifecycle:

```text
First boot
   │
   ├── download model
   │
   └── store in /kaggle/working/models
              │
              ▼
Later boot
   │
   ├── locate cached model
   ├── validate file
   └── reuse it
```

Large model downloads are unpleasant enough once.

---

# 🖥️ Kairn Studio

Kairn Studio is the local configuration interface.

Use it to manage:

* model selection
* context length
* output length
* inference backend
* runtime settings
* remote connection
* API validation
* model readiness
* agent integrations
* generated Kaggle bootstrap cells

The networking checks run outside the UI thread so the interface stays responsive while remote services do what remote services traditionally do: take an unknowable amount of time to answer simple questions.

---

# 📓 Full Notebook Export

Prefer a complete `.ipynb` instead of the GitHub bootstrap cell?

Kairn can generate one.

On Windows:

```powershell
.venv/Scripts/python.exe scripts/export_notebook.py --model gemopus
```

Output:

```text
notebooks/kaggle-studio.ipynb
```

The exported notebook does not contain credentials from your local Studio session.

A fresh runtime API key is generated when the notebook starts.

---

# 🔐 Security

Kairn is designed so credentials do not have to become part of the repository or generated notebook.

Important behavior:

```text
Local Studio credentials
        │
        ├── not committed
        ├── not embedded into exported notebooks
        └── not stored as normal Studio state
```

Agent-specific credentials remain isolated where required.

A new API key is created for fresh runtime sessions.

As with any remotely exposed inference endpoint, treat the generated API key as a secret.

---

# 🔍 Logs

When CUDA, networking, Cloudflare, drivers, subprocesses, or the universe develop opinions, start here:

```text
/kaggle/working/llama_server.log
/kaggle/working/fastapi_gateway.log
/kaggle/working/cloudflared.log
```

These logs cover the main runtime services and are usually the fastest way to determine whether a problem comes from:

```text
CUDA
llama.cpp
model loading
gateway startup
networking
Cloudflare Tunnel
```

---

# 🧪 Development

Install development dependencies:

```powershell
.venv/Scripts/python.exe -m pip install -r requirements-dev.txt
```

Run the test suite:

```powershell
.venv/Scripts/python.exe -m unittest discover -s tests -v
```

Run diagnostics:

```powershell
.venv/Scripts/python.exe scripts/doctor.py
```

Validate the Studio JavaScript:

```bash
node --check ui/app.js
```

Local tests cover areas including:

* command generation
* notebook generation
* configuration handling
* runtime logic
* simulated HTTP responses
* validation behavior

Actual CUDA initialization, model downloads, multi-GPU inference and complete agent workflows require a real Kaggle GPU session.

Computers remain stubbornly unwilling to simulate two T4s merely because the unit tests asked politely.

---

# 🗂️ Architecture

```text
Kairn
│
├── main.py
│   └── Desktop application + Qt bridge
│
├── connection.py
│   └── Remote API diagnostics
│
├── runtime_builder.py
│   └── Kaggle cells + notebook generation
│
├── runtime_support.py
│   └── Runtime arguments + process management
│
├── kaggle_gateway.py
│   └── Authentication + API proxy
│
├── kaggle/
│   └── Kaggle runtime bootstrap
│
├── ui/
│   └── Kairn Studio
│
├── scripts/
│   └── Development + export utilities
│
├── tests/
│   └── Local test suite
│
└── notebooks/
    └── Generated notebooks
```

---

# 🧩 Runtime Flow

```text
LOCAL MACHINE
     │
     │ configure
     ▼
Kairn Studio
     │
     │ generates bootstrap
     ▼
Kaggle Notebook
     │
     ├── clone / download Kairn
     ├── validate CUDA
     ├── prepare backend
     ├── download / reuse GGUF
     ├── start inference
     ├── start API gateway
     └── start tunnel
              │
              ▼
        Remote Base URL
              │
              ▼
      Local AI clients
```

Kairn itself is not the model runtime.

It is the layer that makes the runtime usable.

---

# ❓ Common Questions

### Does inference run on my computer?

No.

Inference runs on the GPUs attached to the Kaggle notebook.

Your local machine runs Kairn Studio and whichever clients or agents you connect to the API.

---

### Do I need CUDA locally?

No.

CUDA is required inside the Kaggle runtime.

---

### Does Kairn provide GPUs?

No.

Kaggle provides the GPU environment.

Kairn configures and connects it.

---

### Does Kairn upload my local notebook?

Not when using the GitHub bootstrap flow.

Studio generates a small cell that retrieves the selected Kairn revision directly from GitHub.

---

### Can I use one T4?

The project is optimized around the dual-T4 Kaggle environment, although individual configurations and backends may support other layouts.

---

### Can I use 128K context?

Potentially.

Whether it fits depends on model size, quantization, KV cache configuration, slots and backend memory requirements.

Start with:

```text
16K
```

and increase from there.

---

### Can I use my own domain?

Yes.

A named Cloudflare Tunnel can expose the API through a hostname such as:

```text
https://llm.example.com
```

You provide the Cloudflare configuration and tunnel token.

---

### Are models downloaded every time?

Not necessarily.

Models stored in:

```text
/kaggle/working/models
```

can be reused while the Kaggle working environment remains available and the cached file passes validation.

---

# ⚠️ Project Status

Kairn connects several independently moving pieces:

```text
Kaggle
NVIDIA CUDA
llama.cpp
Cloudflare
model formats
agent APIs
```

Some behavior can therefore depend on external services and upstream changes.

Experimental backends may require specific pinned builds.

For the most predictable setup, use:

```text
Kaggle T4 ×2
+
llama.cpp
+
16K initial context
+
named Cloudflare Tunnel for agents
```

---

# 🤝 Contributing

Contributions are welcome.

Useful areas include:

* backend support
* model compatibility
* agent integrations
* runtime diagnostics
* Kaggle reliability
* UI improvements
* documentation
* tests

Before submitting changes, run:

```powershell
.venv/Scripts/python.exe -m unittest discover -s tests -v
.venv/Scripts/python.exe scripts/doctor.py
node --check ui/app.js
```

For runtime-specific changes, testing against an actual Kaggle dual-T4 session is strongly recommended.

---

# 📄 License

See the repository license for usage and distribution terms.

---

<div align="center">

## Stop buying hardware for experiments.

### Borrow the cloud's.

**Kaggle provides the GPUs.
llama.cpp runs the model.
Kairn connects everything.**

<br>

`2× NVIDIA T4` · `Local Agents` · `OpenAI API` · `Anthropic API` · `GGUF`

<br><br>

# KAIRN

**Your machine. Their GPUs.**

</div>
