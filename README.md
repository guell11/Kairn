<div align="center">

<!-- HERO / LOGO -->



https://github.com/user-attachments/assets/b56af5f6-3d62-4396-b36e-b2ca61e14109



<br>

# Kairn

### Turn free Kaggle GPUs into your local AI backend.

**2× NVIDIA T4 · llama.cpp · OpenAI-compatible API · Local Agents**

<br>

<a href="#-quick-start">
  <img src="https://img.shields.io/badge/⚡_START_NOW-111111?style=for-the-badge" alt="Start">
</a>
<a href="#-how-it-works">
  <img src="https://img.shields.io/badge/HOW_IT_WORKS-222222?style=for-the-badge" alt="How it works">
</a>
<a href="#-agents">
  <img src="https://img.shields.io/badge/LOCAL_AGENTS-333333?style=for-the-badge" alt="Agents">
</a>

<br><br>

<img src="assets/kaggle.svg" height="26" alt="Kaggle">
&nbsp;&nbsp;→&nbsp;&nbsp;
<img src="assets/nvidia.svg" height="26" alt="NVIDIA">
&nbsp;&nbsp;→&nbsp;&nbsp;
<img src="assets/llamacpp.svg" height="26" alt="llama.cpp">
&nbsp;&nbsp;→&nbsp;&nbsp;
<img src="assets/kairn-mark.svg" height="26" alt="Kairn">
&nbsp;&nbsp;→&nbsp;&nbsp;
<strong>Your agents.</strong>

</div>

---

## Your GPU doesn't have to be in your computer.

Kairn turns a **Kaggle notebook with 2× NVIDIA T4 GPUs** into a remote inference backend that your local AI tools can use like a normal API.

No local CUDA setup.

No expensive GPU required.

No server deployment ritual involving seventeen terminals and a sacrifice to the dependency gods.

```text
┌─────────────────┐
│   YOUR MACHINE  │
│                 │
│ Codex · Claude  │
│ OpenCode · etc. │
└────────┬────────┘
         │
         │ OpenAI / Anthropic API
         ▼
┌─────────────────┐
│      KAIRN      │
│  Auth · Gateway │
└────────┬────────┘
         │
         ▼
┌──────────────────────────┐
│          KAGGLE          │
│                          │
│  NVIDIA T4  +  NVIDIA T4 │
│         llama.cpp        │
└──────────────────────────┘
```

---

# 🎬 See Kairn in action

<div align="center">


</div>

---

# ⚡ Quick Start

## 01 — Launch Kairn

<table>
<tr>
<td width="50%">

### Windows

```powershell
run.bat
```

or

```powershell
.\run.ps1
```

</td>
<td width="50%">

### Linux / macOS

```bash
./run.sh
```

</td>
</tr>
</table>

---

## 02 — Pick your model

<div align="center">
<img src="assets/studio-preview.webp" width="850" alt="Kairn Studio">
</div>

Choose your:

**Model → Context → Output → Backend**

Kairn prepares an initial configuration for the available GPUs and limits initial concurrency when necessary.

---

## 03 — Give Kaggle the heavy lifting

Click:

> **Copy GitHub Cell**

Create an empty Kaggle notebook and enable:

```text
Internet    ON
Accelerator GPU T4 ×2
```

Paste.

Run.

That's it.

The launcher:

```text
GitHub
   ↓
resolve commit
   ↓
download Kairn
   ↓
prepare runtime
   ↓
validate CUDA
   ↓
download / reuse model
   ↓
start llama.cpp
   ↓
start API
```

No notebook upload required.

---

## 04 — Connect

Copy the generated:

```text
Base URL
API Key
```

Paste them into Kairn Studio.

Connection and model checks happen in the background, so the UI doesn't freeze while networking does networking things.

Once validated:

```text
● API Connected
● Model Ready
● Agents Unlocked
```

---

# ✦ One notebook. Two GPUs. Your tools.

<div align="center">

<img src="assets/pipeline.svg" width="900" alt="Kairn pipeline">

</div>

Kairn handles the annoying middle layer between your local tools and Kaggle:

|                      |                                |
| -------------------- | ------------------------------ |
| ⚡ **2× T4**          | Multi-GPU inference            |
| 🧠 **llama.cpp**     | CUDA runtime                   |
| 🔌 **OpenAI API**    | Chat Completions + Responses   |
| 💬 **Anthropic API** | Messages                       |
| 🌐 **Gateway**       | Authentication + normalization |
| ♻️ **Model cache**   | Reuse downloaded GGUFs         |
| 🛡️ **Validation**   | CUDA and runtime checks        |
| 🖥️ **Studio**       | Configure everything visually  |

---

# 🤖 Agents

Connect local AI tools to the model running on Kaggle.

<div align="center">

<img src="assets/agents.svg" width="760" alt="Supported AI agents">

</div>

Kairn keeps existing configurations backed up before making changes.

API keys aren't stored in Studio state.

Tool-specific credentials remain isolated where required.

---

# 🧠 Built for dual T4

The default runtime uses:

```text
llama.cpp b11009
CUDA 12.8

GPU 0 ─ NVIDIA T4
GPU 1 ─ NVIDIA T4

Strategy ─ layer split
KV cache ─ q8_0
```

Before downloading or loading the model, Kairn verifies that CUDA actually sees both GPUs.

```bash
llama-server --list-devices
```

Because discovering that CUDA is broken **after downloading 30 GB** is an experience nobody needs twice.

### Recommended starting context

```text
16K
```

128K may exceed available VRAM depending on model and configuration.

If VRAM runs out, Kairn can reduce slots and retry after terminating the previous process.

---

# 🔥 Backends

### llama.cpp

**Default · Recommended**

Official `b11009` runtime with CUDA 12.8.

Supports:

* Chat Completions
* Responses
* Messages
* layer split
* optional sampling flags
* reasoning budget when supported

---

### wackMall

**Experimental · T4 optimized**

Kairn supports a dedicated Linux CUDA build targeting:

```text
Ubuntu 22.04
CUDA 12.4
Turing sm_75
```

The repository includes the workflow required to build the pinned wackMall commit and publish:

```text
wackmall-main-b30-6aa17e3-cuda12.4-t4
```

If the release isn't available, Kairn tells you.

It does **not** quietly download a Windows binary and hope physics changes its mind.

---

### ik_llama

Advanced experimental backend compiled inside Kaggle.

Useful for experimentation, without guaranteed upstream parity.

---

# 🌎 Remote API

For basic API testing, Kairn can work with a Cloudflare Quick Tunnel.

For full agent streaming, use a **named Cloudflare Tunnel**.

```text
https://llm.yourdomain.com
            │
            ▼
http://localhost:8000
```

Provide the tunnel token through the notebook prompt or:

```bash
TUNNEL_TOKEN
```

Kairn does not automatically create remote infrastructure or Cloudflare resources.

---

# 💾 Download once. Reuse.

Models live outside the source directory:

```text
/kaggle/working/models
```

That means runtime updates don't automatically destroy your downloaded GGUF.

Cached files are verified before reuse.

---

# 📓 Prefer a full notebook?

You can still export one:

```powershell
.venv/Scripts/python.exe scripts/export_notebook.py --model gemopus
```

Output:

```text
notebooks/kaggle-studio.ipynb
```

The notebook contains no local session credentials.

A fresh API key is generated when it runs.

---

# 🔍 Logs

When the universe decides today is the day CUDA develops opinions:

```text
/kaggle/working/llama_server.log
/kaggle/working/fastapi_gateway.log
/kaggle/working/cloudflared.log
```

---

# 🧪 Development

```powershell
.venv/Scripts/python.exe -m pip install -r requirements-dev.txt
.venv/Scripts/python.exe -m unittest discover -s tests -v
.venv/Scripts/python.exe scripts/doctor.py
node --check ui/app.js
```

Local tests cover commands, notebooks, configuration and simulated HTTP responses.

Actual CUDA boot, model downloads and end-to-end agent usage require a real Kaggle session.

---

# 🗂️ Architecture

```text
Kairn
│
├── main.py
│   └── Desktop + Qt bridge
│
├── connection.py
│   └── API diagnostics
│
├── runtime_builder.py
│   └── Kaggle cells + notebooks
│
├── runtime_support.py
│   └── Runtime arguments + processes
│
├── kaggle_gateway.py
│   └── Authentication + proxy
│
├── kaggle/
│   └── Kaggle bootstrap
│
├── ui/
│   └── Studio interface
│
└── scripts/
    └── Development utilities
```

---

<div align="center">

<img src="assets/kairn-footer.svg" width="700" alt="Kairn">

<br>

## Stop buying hardware for experiments.

### Borrow the cloud's.

**Kaggle provides the GPUs.
llama.cpp runs the model.
Kairn connects everything.**

<br>

`2× T4` · `Local Agents` · `OpenAI API` · `Anthropic API`

<br><br>

**KAIRN**

</div>
