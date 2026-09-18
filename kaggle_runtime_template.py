# =====================================================================
# CONFIGURAÇÃO
# =====================================================================

MODEL = "alztrk/Ornith-1.5-35B-A3B-Abliterated-GGUF"
MODEL_SIZE = None
MODEL_SHA256 = ""

# Repo ou link direto do MTP.
# "" = desativado
MTP = ""

MODEL_REFERENCE = "ornith-1.5-35b"

HF_TOKEN = ""


# =====================================================================
# SUBAGENTES / CONTEXTO
# =====================================================================

# Contexto disponível POR geração.
CONTEXT_PER_GENERATION = 16384

# agente principal + até 3 subagentes
MAX_CONCURRENT_GENERATIONS = 4

MAX_OUTPUT_TOKENS = 8192


# =====================================================================
# REASONING
# =====================================================================

DEFAULT_REASONING_BUDGET = 2048
DEFAULT_TEMPERATURE = 0.7
DEFAULT_TOP_K = 40
DEFAULT_TOP_P = 0.95
DEFAULT_MIN_P = 0.05


# =====================================================================
# MTP
# =====================================================================

MTP_TOKENS = 4
MTP_HEADS = 1
MTP_P_MIN = 0.0
# auto selects ngram speculation when this server advertises it; off disables it.
SPECULATION = "auto"


# =====================================================================
# GPU
# =====================================================================

SPLIT_MODE = "graph"
TENSOR_SPLIT = "1,1"
GPU_LAYERS = 999

FLASH_ATTENTION = True

# KV quantizado é importante com 4 slots.
KV_CACHE_K = "q4_0"
KV_CACHE_V = "q4_0"

BATCH_SIZE = 2048
UBATCH_SIZE = 512

CPU_THREADS = 4
CPU_BATCH_THREADS = 2


# =====================================================================
# API
# =====================================================================

API_KEY = ""

API_PORT = 8000
LLAMA_PORT = 8081

USE_CLOUDFLARE = True

# Mantém esta célula ativa com health checks reais. Não simula mouse/teclado
# e continua sujeito aos limites normais de sessão/quota do Kaggle.
KEEP_RUNTIME_CELL_ACTIVE = True
HEARTBEAT_SECONDS = 60

# Backend: auto | ik_llama | official-layer | official-tensor
BACKEND_FAMILY = "official-layer"
AGENT_SYSTEM_PROMPT = ""
UNIVERSAL_GATEWAY_B64 = ""


# =====================================================================
# DOWNLOAD
# =====================================================================

# Espaço que precisa continuar livre depois do download.
#
# Precisamos dele para:
# - ik_llama.cpp
# - compilação
# - logs
# - arquivos temporários
#
# Como compilaremos ANTES do modelo, 512 MiB já dá uma margem
# razoável para o runtime.

MIN_FREE_AFTER_DOWNLOAD_GB = 0.50


# Se ficou lixo de tentativa anterior, remove automaticamente.
CLEAN_INCOMPLETE_DOWNLOADS = True


# Preferência de quantização.
#
# IQ4 / imatrix primeiro.
# Q4_K_M depois.

QUANT_PRIORITY = [
    "IQ4_KT",
    "IQ4_KS_R4",
    "IQ4_KS",
    "IQ4_KSS",
    "IQ4_XS",
    "IQ4_NL",
    "Q4_K_M",
    "Q4_K_S",
    "Q4_0",
]


# =====================================================================
# FIM DAS CONFIGURAÇÕES
# =====================================================================


# =====================================================================
# IMPORTS
# =====================================================================

import os
import re
import base64
import sys
import stat
import time
import json
import shutil
import secrets
import subprocess

from pathlib import Path
from urllib.parse import urlparse, quote

import requests
import httpx

from tqdm.auto import tqdm
from huggingface_hub import HfApi

from IPython.display import display, Markdown


# =====================================================================
# DIRETÓRIOS
# =====================================================================

ROOT = Path("/kaggle/working")

IK_DIR = ROOT / "ik_llama.cpp"
BUILD_DIR = IK_DIR / "build"

LLAMA_SERVER = (
    BUILD_DIR
    / "bin"
    / "llama-server"
)

MODELS_DIR = ROOT / "models"

MODELS_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


SERVER_CONTEXT = (
    CONTEXT_PER_GENERATION
    * MAX_CONCURRENT_GENERATIONS
)


API_KEY = (
    API_KEY.strip()
    or
    "sk-kaggle-"
    + secrets.token_urlsafe(32)
)


AUTH_HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "x-api-key": API_KEY,
}


HF_TOKEN_REAL = (
    HF_TOKEN.strip()
    or
    os.environ.get(
        "HF_TOKEN",
        "",
    ).strip()
    or None
)


# =====================================================================
# HELPERS
# =====================================================================

def human_bytes(value):

    value = float(value)

    units = [
        "B",
        "KiB",
        "MiB",
        "GiB",
        "TiB",
    ]

    for unit in units:

        if value < 1024:
            return f"{value:.2f} {unit}"

        value /= 1024

    return f"{value:.2f} PiB"


def disk_free():

    return shutil.disk_usage(
        ROOT
    ).free


def disk_total():

    return shutil.disk_usage(
        ROOT
    ).total


def show_disk():

    usage = shutil.disk_usage(
        ROOT
    )

    print(
        "💾 Disco:",
        human_bytes(usage.free),
        "livres de",
        human_bytes(usage.total),
    )


def run(
    command,
    cwd=None,
    env=None,
):

    print()

    print(
        "▶",
        " ".join(
            map(str, command)
        )
    )

    subprocess.run(
        list(
            map(str, command)
        ),
        cwd=cwd,
        env=env,
        check=True,
    )


# =====================================================================
# LIMPAR CACHE VELHO
# =====================================================================

def cleanup_hf_cache():

    possible = [

        Path.home()
        / ".cache"
        / "huggingface"
        / "xet",

        Path.home()
        / ".cache"
        / "huggingface"
        / "hub",

        ROOT
        / ".cache"
        / "huggingface",
    ]

    reclaimed = 0

    for path in possible:

        if not path.exists():
            continue

        try:

            before = disk_free()

            shutil.rmtree(
                path,
                ignore_errors=True,
            )

            after = disk_free()

            reclaimed += max(
                0,
                after - before,
            )

        except Exception:
            pass

    return reclaimed


def cleanup_incomplete_models():

    if not MODELS_DIR.exists():
        return

    for path in (
        MODELS_DIR.rglob("*")
    ):

        if not path.is_file():
            continue

        name = path.name.lower()

        if (
            name.endswith(".part")
            or
            name.endswith(".incomplete")
            or
            name.endswith(".lock")
        ):

            try:

                print(
                    "🧹 Removendo incompleto:",
                    path.name,
                )

                path.unlink()

            except Exception:
                pass


# =====================================================================
# LIMPEZA DA TENTATIVA QUE FALHOU
# =====================================================================

if CLEAN_INCOMPLETE_DOWNLOADS:

    print(
        "🧹 Limpando downloads incompletos..."
    )

    cleanup_incomplete_models()

    reclaimed = cleanup_hf_cache()

    if reclaimed:

        print(
            "♻️ Recuperados:",
            human_bytes(reclaimed),
        )


show_disk()


# =====================================================================
# VERIFICAR GPU
# =====================================================================

try:

    gpu_info = subprocess.check_output(
        [
            "nvidia-smi",

            "--query-gpu="
            "name,memory.total,memory.free",

            "--format="
            "csv,noheader,nounits",
        ],
        text=True,
    ).strip()

except Exception:

    gpu_info = ""


gpu_lines = [

    line.strip()

    for line
    in gpu_info.splitlines()

    if line.strip()
]


if len(gpu_lines) < 2:

    raise RuntimeError(
        "\n"
        "Este preset espera 2 GPUs.\n"
        "No Kaggle selecione GPU T4 x2.\n"
    )


print()
print("🎮 GPUs encontradas:")

for index, gpu in enumerate(
    gpu_lines
):

    print(
        f"   GPU {index}: {gpu}"
    )


# =====================================================================
# COMPILAR BACKEND DE INFERÊNCIA
# =====================================================================
# ik_llama graph é o padrão por compatibilidade/performance em T4 x2.
# llama.cpp official tensor usa NCCL e continua experimental.

backend = BACKEND_FAMILY if BACKEND_FAMILY != "auto" else "ik_llama"
if backend not in {"ik_llama", "official-layer", "official-tensor"}:
    raise ValueError(f"Backend inválido: {backend}")

if backend == "ik_llama":
    repo_url = "https://github.com/ikawrakow/ik_llama.cpp"
    SPLIT_MODE = "graph"
    source_dir = ROOT / "inference_backend"
    cmake_extra = ["-DGGML_IQK_FA_ALL_QUANTS=ON"]
else:
    repo_url = "https://github.com/ggml-org/llama.cpp"
    SPLIT_MODE = "tensor" if backend == "official-tensor" else "layer"
    source_dir = ROOT / "inference_backend"
    cmake_extra = ["-DGGML_CUDA_NCCL=ON"]
    if backend == "official-tensor":
        # tensor split requer KV não quantizado no caminho atual do llama.cpp.
        KV_CACHE_K = "f16"
        KV_CACHE_V = "f16"

build_dir = source_dir / "build"
print()
print(f"🔨 Preparando backend: {backend}...")
if source_dir.exists():
    shutil.rmtree(source_dir, ignore_errors=True)
run(["git", "clone", "--depth", "1", repo_url, str(source_dir)])
(ROOT / "cuda_bootstrap.cmake").write_text(
    "\n".join([
        "find_package(CUDAToolkit REQUIRED)",
        "if(NOT TARGET CUDA::cuda_driver)",
        "  find_library(CUDA_DRIVER_LIBRARY NAMES cuda libcuda.so PATHS /usr/lib/x86_64-linux-gnu /usr/local/cuda/lib64/stubs /usr/local/nvidia/lib64 /usr/lib/wsl/lib)",
        "  if(CUDA_DRIVER_LIBRARY)",
        "    add_library(CUDA::cuda_driver UNKNOWN IMPORTED)",
        "    set_target_properties(CUDA::cuda_driver PROPERTIES IMPORTED_LOCATION \"${CUDA_DRIVER_LIBRARY}\")",
        "  endif()",
        "endif()",
        "find_library(RT_LIBRARY rt)",
        "if(RT_LIBRARY)",
        "  link_libraries(${RT_LIBRARY})",
        "endif()",
        "",
    ])
)
cmake_cmd = [
    "cmake", "-S", str(source_dir), "-B", str(build_dir),
    "-DCMAKE_PROJECT_TOP_LEVEL_INCLUDES=" + str(ROOT / "cuda_bootstrap.cmake"),
    "-DGGML_CUDA=ON", "-DCMAKE_CUDA_ARCHITECTURES=75", "-DCMAKE_BUILD_TYPE=Release",
    *cmake_extra,
]
run(cmake_cmd)
jobs = min(os.cpu_count() or 4, 8)
run(["cmake", "--build", str(build_dir), "--config", "Release", "--target", "llama-server", "-j", str(jobs)])
compiled_server = build_dir / "bin" / "llama-server"
if not compiled_server.exists():
    raise RuntimeError("llama-server não foi compilado.")
RUNTIME_SERVER = ROOT / "llama-server"
shutil.copy2(compiled_server, RUNTIME_SERVER)
RUNTIME_SERVER.chmod(RUNTIME_SERVER.stat().st_mode | stat.S_IEXEC)
shutil.rmtree(source_dir, ignore_errors=True)
LLAMA_SERVER = RUNTIME_SERVER
print(f"✅ Backend {backend} compilado · split-mode={SPLIT_MODE}")
show_disk()


# =====================================================================
# HUGGING FACE
# =====================================================================

def parse_hf_source(
    source
):

    source = source.strip()

    if not source:

        return (
            None,
            None,
            "main",
        )


    # usuario/repo

    if not source.startswith(
        "http"
    ):

        return (
            source.strip("/"),
            None,
            "main",
        )


    parsed = urlparse(
        source
    )


    if (
        "huggingface.co"
        not in parsed.netloc
    ):

        raise ValueError(
            "MODEL/MTP precisa ser "
            "um repo ou URL Hugging Face."
        )


    parts = [

        p

        for p
        in parsed.path.split("/")

        if p
    ]


    if len(parts) < 2:

        raise ValueError(
            "URL Hugging Face inválida."
        )


    repo = (
        parts[0]
        + "/"
        + parts[1]
    )


    filename = None
    revision = "main"


    if (
        len(parts) >= 5
        and
        parts[2]
        in (
            "resolve",
            "blob",
        )
    ):

        revision = parts[3]

        filename = "/".join(
            parts[4:]
        )


    return (
        repo,
        filename,
        revision,
    )


# =====================================================================
# SCORE DAS QUANTIZAÇÕES
# =====================================================================

def quant_score(
    filename,
    role,
):

    name = filename.upper()


    if not name.endswith(
        ".GGUF"
    ):

        return -10**9


    if "MMPROJ" in name:

        return -10**9


    score = 0


    for index, quant in enumerate(
        QUANT_PRIORITY
    ):

        if quant in name:

            score += (
                100000
                -
                index * 5000
            )

            break


    # Importance Matrix

    if "IMATRIX" in name:

        score += 30000


    if "IQ4" in name:

        score += 20000


    if "Q4" in name:

        score += 10000


    # Modelo principal não pode
    # selecionar MTP por acidente.

    if role == "model":

        if any(
            marker in name

            for marker in [
                "MTP",
                "DRAFT",
                "ASSISTANT",
                "NEXTN",
                "NEXT-N",
            ]
        ):

            score -= 500000


    # MTP

    else:

        for marker in [
            "MTP",
            "DRAFT",
            "ASSISTANT",
            "NEXTN",
            "NEXT-N",
        ]:

            if marker in name:

                score += 30000


    return score


# =====================================================================
# INFO REMOTA DO ARQUIVO
# =====================================================================

def remote_file_size(
    repo,
    filename,
    revision,
):

    api = HfApi(
        token=HF_TOKEN_REAL
    )


    info = api.model_info(
        repo_id=repo,
        revision=revision,
        files_metadata=True,
        token=HF_TOKEN_REAL,
    )


    for sibling in info.siblings:

        if (
            sibling.rfilename
            == filename
        ):

            size = getattr(
                sibling,
                "size",
                None,
            )

            if size is not None:

                return int(size)


    # Fallback HEAD

    url = (
        "https://huggingface.co/"
        + repo
        + "/resolve/"
        + revision
        + "/"
        + quote(
            filename,
            safe="/",
        )
    )


    headers = {}

    if HF_TOKEN_REAL:

        headers[
            "Authorization"
        ] = (
            "Bearer "
            + HF_TOKEN_REAL
        )


    response = requests.head(
        url,
        headers=headers,
        allow_redirects=True,
        timeout=30,
    )

    response.raise_for_status()


    size = response.headers.get(
        "content-length"
    )


    if size:

        return int(size)


    return None


# =====================================================================
# ESCOLHER GGUF
# =====================================================================

def choose_gguf(
    source,
    role,
):

    (
        repo,
        explicit_file,
        revision,
    ) = parse_hf_source(
        source
    )


    if not repo:

        return None


    api = HfApi(
        token=HF_TOKEN_REAL
    )


    print()
    print(
        f"🔎 Analisando {role}:",
        repo,
    )


    files = api.list_repo_files(
        repo_id=repo,
        revision=revision,
        token=HF_TOKEN_REAL,
    )


    if explicit_file:

        if explicit_file not in files:

            raise RuntimeError(
                "Arquivo não existe no repo:\n"
                + explicit_file
            )

        selected = explicit_file


    else:

        candidates = [

            file

            for file
            in files

            if file.lower().endswith(
                ".gguf"
            )
        ]


        if not candidates:

            raise RuntimeError(
                "Nenhum GGUF encontrado em "
                + repo
            )


        candidates.sort(
            key=lambda file:
                quant_score(
                    file,
                    role,
                ),
            reverse=True,
        )


        selected = candidates[0]


        if (
            quant_score(
                selected,
                role,
            )
            < 0
        ):

            raise RuntimeError(
                "Nenhum GGUF Q4 adequado "
                "foi encontrado."
            )


    size = remote_file_size(
        repo,
        selected,
        revision,
    )



    print(
        "✅ GGUF:",
        selected,
    )


    if size:

        print(
            "📦 Tamanho:",
            human_bytes(size),
        )


    return {
        "repo": repo,
        "filename": selected,
        "revision": revision,
        "size": size,
    }


# =====================================================================
# DOWNLOAD DIRETO
# =====================================================================
#
# NÃO usa hf_hub_download.
#
# Portanto:
#
# arquivo remoto
#       ↓
# arquivo.gguf.part
#       ↓
# arquivo.gguf
#
# Sem segunda cópia no cache.
# =====================================================================

def direct_download(
    info,
):

    if info is None:

        return None


    repo = info[
        "repo"
    ]

    filename = info[
        "filename"
    ]

    revision = info[
        "revision"
    ]

    expected_size = info["size"]


    repo_dir = (
        MODELS_DIR
        /
        repo.replace(
            "/",
            "__",
        )
    )


    repo_dir.mkdir(
        parents=True,
        exist_ok=True,
    )


    destination = (
        repo_dir
        /
        Path(filename).name
    )


    partial = Path(
        str(destination)
        + ".part"
    )


    # ---------------------------------------------------------
    # JÁ EXISTE?
    # ---------------------------------------------------------

    if destination.exists():

        actual = (
            destination.stat().st_size
        )


        if expected_size is None or destination.stat().st_size == expected_size:

            print()
            print(
                "♻️ Modelo já existe:"
            )

            print(
                destination
            )

            return destination


        print("🧹 Arquivo existente está incompleto.")

        destination.unlink()


    # ---------------------------------------------------------
    # REMOVER PART ANTIGO
    # ---------------------------------------------------------

    if partial.exists():

        print(
            "🧹 Removendo download "
            "parcial anterior:",
            partial.name,
        )

        partial.unlink()


    # ---------------------------------------------------------
    # CHECAR ESPAÇO ANTES
    # ---------------------------------------------------------

    free = disk_free()


    margin = int(
        MIN_FREE_AFTER_DOWNLOAD_GB
        * 1024**3
    )


    if expected_size:

        required = (
            expected_size
            + margin
        )


        print()
        print(
            "💾 Espaço livre:",
            human_bytes(free),
        )

        print(
            "📦 Modelo:",
            human_bytes(
                expected_size
            ),
        )

        print(
            "🛟 Margem:",
            human_bytes(
                margin
            ),
        )


        if free < required:

            missing = (
                required
                - free
            )


            raise RuntimeError(
                "\n\n"
                "❌ ESPAÇO INSUFICIENTE\n"
                "\n"
                f"Modelo: {human_bytes(expected_size)}\n"
                f"Livre:  {human_bytes(free)}\n"
                f"Margem: {human_bytes(margin)}\n"
                f"Falta:  {human_bytes(missing)}\n"
                "\n"
                "O download NÃO foi iniciado.\n"
                "\n"
                "Escolha uma quantização menor "
                "ou libere espaço.\n"
            )


    # ---------------------------------------------------------
    # URL
    # ---------------------------------------------------------

    url = (
        "https://huggingface.co/"
        + repo
        + "/resolve/"
        + revision
        + "/"
        + quote(
            filename,
            safe="/",
        )
        + "?download=true"
    )


    headers = {}


    if HF_TOKEN_REAL:

        headers[
            "Authorization"
        ] = (
            "Bearer "
            + HF_TOKEN_REAL
        )


    print()
    print(
        "⬇️ Baixando diretamente..."
    )


    with requests.get(
        url,
        headers=headers,
        stream=True,
        allow_redirects=True,
        timeout=120,
    ) as response:

        response.raise_for_status()


        total = expected_size


        if total is None:

            content_length = (
                response.headers.get(
                    "content-length"
                )
            )

            if content_length:

                total = int(
                    content_length
                )


        with open(
            partial,
            "wb",
        ) as file:

            with tqdm(
                total=total,
                unit="B",
                unit_scale=True,
                unit_divisor=1024,
                desc=destination.name,
            ) as bar:

                for chunk in (
                    response.iter_content(
                        chunk_size=
                        16 * 1024 * 1024
                    )
                ):

                    if not chunk:
                        continue


                    file.write(
                        chunk
                    )

                    bar.update(
                        len(chunk)
                    )


    # ---------------------------------------------------------
    # VALIDAR
    # ---------------------------------------------------------

    actual_size = (
        partial.stat().st_size
    )


    if (
        expected_size
        and
        actual_size
        != expected_size
    ):

        partial.unlink(
            missing_ok=True
        )

        raise RuntimeError(
            "\nDownload incompleto.\n"
            f"Esperado: {human_bytes(expected_size)}\n"
            f"Recebido: {human_bytes(actual_size)}"
        )


    # rename é atômico no mesmo filesystem

    partial.replace(
        destination
    )


    print()
    print(
        "✅ Download concluído:"
    )

    print(
        destination
    )

    show_disk()


    return destination


# =====================================================================
# SELECIONAR MODELOS
# =====================================================================

model_info = choose_gguf(
    MODEL,
    "model",
)


mtp_info = None

if MTP.strip():

    mtp_info = choose_gguf(
        MTP,
        "mtp",
    )


# =====================================================================
# CHECAR ESPAÇO DOS DOIS JUNTOS
# =====================================================================

required_download = 0


if (
    model_info
    and
    model_info["size"]
):

    required_download += (
        model_info["size"]
    )


if (
    mtp_info
    and
    mtp_info["size"]
):

    required_download += (
        mtp_info["size"]
    )


margin = int(
    MIN_FREE_AFTER_DOWNLOAD_GB
    * 1024**3
)


if (
    required_download
    and
    disk_free()
    <
    required_download + margin
):

    raise RuntimeError(
        "\n"
        "❌ Modelo + MTP não cabem no disco.\n\n"
        f"Downloads: {human_bytes(required_download)}\n"
        f"Livre:     {human_bytes(disk_free())}\n"
        f"Margem:    {human_bytes(margin)}\n"
    )


# =====================================================================
# BAIXAR
# =====================================================================

model_path = direct_download(
    model_info
)


mtp_path = None

if mtp_info:

    mtp_path = direct_download(
        mtp_info
    )


selected_model_file = (
    model_info["filename"]
)

selected_mtp_file = (
    mtp_info["filename"]
    if mtp_info
    else None
)


# =====================================================================
# MATAR PROCESSOS ANTIGOS
# =====================================================================

for pattern in [

    "kaggle_universal_gateway",

    "cloudflared.*tunnel",

    str(
        LLAMA_SERVER
    ),

]:

    subprocess.run(
        [
            "pkill",
            "-f",
            pattern,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


time.sleep(2)


# =====================================================================
# LLAMA SERVER
# =====================================================================

llama_cmd = [

    str(
        LLAMA_SERVER
    ),

    "--model",
    str(
        model_path
    ),

    "--alias",
    MODEL_REFERENCE,

    "--host",
    "127.0.0.1",

    "--port",
    str(
        LLAMA_PORT
    ),

    "--ctx-size",
    str(
        SERVER_CONTEXT
    ),

    "--parallel",
    str(
        MAX_CONCURRENT_GENERATIONS
    ),

    "--cont-batching",

    "--split-mode",
    SPLIT_MODE,

    "--tensor-split",
    TENSOR_SPLIT,

    "--n-gpu-layers",
    str(
        GPU_LAYERS
    ),

    "--batch-size",
    str(
        BATCH_SIZE
    ),

    "--ubatch-size",
    str(
        UBATCH_SIZE
    ),

    "--threads",
    str(
        CPU_THREADS
    ),

    "--threads-batch",
    str(
        CPU_BATCH_THREADS
    ),

    "--cache-type-k",
    KV_CACHE_K,

    "--cache-type-v",
    KV_CACHE_V,

    "--jinja",

    "--parallel-tool-calls",

    "--metrics",

    "--reasoning",
    "auto",

    "--reasoning-budget",
    "-1",
]


if FLASH_ATTENTION:

    llama_cmd += [
        "--flash-attn",
        "on",
    ]


# =====================================================================
# MTP
# =====================================================================

if mtp_path:

    llama_cmd += [

        "--model-draft",
        str(
            mtp_path
        ),

        "--ctx-size-draft",
        str(
            SERVER_CONTEXT
        ),

        "--spec-type",

        (
            "mtp:"
            f"n_max={MTP_TOKENS},"
            f"p_min={MTP_P_MIN},"
            f"heads={MTP_HEADS}"
        ),
    ]


# =====================================================================
# LOG BACKEND
# =====================================================================

LLAMA_LOG = (
    ROOT
    /
    "llama_server.log"
)


llama_log = open(
    LLAMA_LOG,
    "w",
    buffering=1,
)


print()
print(
    f"🚀 Iniciando {backend}..."
)


llama_process = subprocess.Popen(

    llama_cmd,

    stdout=llama_log,

    stderr=subprocess.STDOUT,
)


# =====================================================================
# ESPERAR BACKEND
# =====================================================================

backend_url = (
    f"http://127.0.0.1:"
    f"{LLAMA_PORT}"
)


backend_ready = False


for _ in range(300):

    if (
        llama_process.poll()
        is not None
    ):

        break


    try:

        response = httpx.get(
            backend_url
            + "/health",

            timeout=2,
        )


        if (
            response.status_code
            == 200
        ):

            backend_ready = True

            break


    except Exception:

        pass


    time.sleep(1)


if not backend_ready and backend == "official-tensor":

    print(
        "⚠️ tensor split não iniciou; tentando fallback automático para layer split..."
    )

    try:
        llama_process.terminate()
        llama_process.wait(timeout=5)
    except Exception:
        pass

    def _set_cli_arg(command, flag, value):
        try:
            index = command.index(flag)
            command[index + 1] = str(value)
        except ValueError:
            command.extend([flag, str(value)])

    SPLIT_MODE = "layer"
    KV_CACHE_K = "q4_0"
    KV_CACHE_V = "q4_0"
    _set_cli_arg(llama_cmd, "--split-mode", SPLIT_MODE)
    _set_cli_arg(llama_cmd, "--cache-type-k", KV_CACHE_K)
    _set_cli_arg(llama_cmd, "--cache-type-v", KV_CACHE_V)

    llama_log.close()
    llama_log = open(LLAMA_LOG, "a", buffering=1)
    llama_log.write("\n\n=== fallback: official-layer ===\n")
    llama_process = subprocess.Popen(
        llama_cmd,
        stdout=llama_log,
        stderr=subprocess.STDOUT,
    )

    for _ in range(300):
        if llama_process.poll() is not None:
            break
        try:
            response = httpx.get(backend_url + "/health", timeout=2)
            if response.status_code == 200:
                backend_ready = True
                backend = "official-layer (fallback)"
                break
        except Exception:
            pass
        time.sleep(1)


if not backend_ready:

    llama_log.flush()


    log_tail = (
        LLAMA_LOG.read_text(
            errors="ignore"
        )[-20000:]
    )


    raise RuntimeError(
        "\n"
        f"❌ {backend} não iniciou.\n\n"
        + log_tail
    )


print(
    f"✅ {backend} online."
)


# =====================================================================
# UNIVERSAL API GATEWAY
# =====================================================================
# O gateway só autentica, normaliza o modelo/prompt e encaminha streaming.
# Chat Completions, Responses e Anthropic Messages ficam no llama-server.

gateway_path = ROOT / "kaggle_universal_gateway.py"
if not UNIVERSAL_GATEWAY_B64:
    raise RuntimeError("Gateway embutido ausente. Gere novamente o comando no Kaggle Studio.")
gateway_path.write_bytes(base64.b64decode(UNIVERSAL_GATEWAY_B64))

os.environ.update({
    "KAGGLE_BACKEND_URL": backend_url,
    "KAGGLE_STUDIO_API_KEY": API_KEY,
    "KAGGLE_MODEL_ID": MODEL_REFERENCE,
    "KAGGLE_AGENT_SYSTEM_PROMPT": AGENT_SYSTEM_PROMPT,
    "KAGGLE_MAX_OUTPUT": str(MAX_OUTPUT_TOKENS),
    "KAGGLE_REASONING_BUDGET": str(DEFAULT_REASONING_BUDGET),
})


# =====================================================================
# UVICORN
# =====================================================================

GATEWAY_LOG = (
    ROOT
    /
    "fastapi_gateway.log"
)


gateway_log = open(
    GATEWAY_LOG,
    "w",
    buffering=1,
)


print(
    "⚡ Iniciando FastAPI..."
)


gateway_process = subprocess.Popen(

    [
        sys.executable,

        "-m",
        "uvicorn",

        "kaggle_universal_gateway:app",

        "--app-dir",
        str(ROOT),

        "--host",
        "127.0.0.1",

        "--port",
        str(API_PORT),

        "--workers",
        "1",

        "--loop",
        "uvloop",

        "--http",
        "httptools",

        "--backlog",
        "256",

        "--limit-concurrency",
        "256",

        "--no-access-log",
    ],

    stdout=gateway_log,

    stderr=subprocess.STDOUT,
)


# =====================================================================
# ESPERAR FASTAPI
# =====================================================================

gateway_url = (
    f"http://127.0.0.1:"
    f"{API_PORT}"
)


gateway_ready = False


for _ in range(60):

    try:

        response = httpx.get(
            gateway_url
            + "/health",

            headers=AUTH_HEADERS,
            timeout=2,
        )


        if (
            response.status_code
            == 200
        ):

            gateway_ready = True

            break


    except Exception:

        pass


    time.sleep(1)


if not gateway_ready:

    gateway_log.flush()


    raise RuntimeError(
        "\n"
        "❌ FastAPI não iniciou.\n\n"
        +
        GATEWAY_LOG.read_text(
            errors="ignore"
        )[-10000:]
    )


print(
    "✅ FastAPI online."
)


# =====================================================================
# CLOUDFLARED
# =====================================================================

public_url = (
    gateway_url
)


if USE_CLOUDFLARE:

    CLOUDFLARED = (
        ROOT
        /
        "cloudflared"
    )


    if not CLOUDFLARED.exists():

        print(
            "☁️ Baixando cloudflared..."
        )


        cloudflared_url = (
            "https://github.com/"
            "cloudflare/cloudflared/"
            "releases/latest/download/"
            "cloudflared-linux-amd64"
        )


        response = requests.get(
            cloudflared_url,
            stream=True,
            allow_redirects=True,
            timeout=120,
        )


        response.raise_for_status()


        with open(
            CLOUDFLARED,
            "wb",
        ) as file:

            for chunk in (
                response.iter_content(
                    1024 * 1024
                )
            ):

                if chunk:

                    file.write(
                        chunk
                    )


        CLOUDFLARED.chmod(
            CLOUDFLARED.stat().st_mode
            |
            stat.S_IEXEC
        )


    CF_LOG = (
        ROOT
        /
        "cloudflared.log"
    )


    cf_log = open(
        CF_LOG,
        "w",
        buffering=1,
    )


    print(
        "🌐 Criando Cloudflare Tunnel..."
    )


    cloudflare_process = (
        subprocess.Popen(

            [
                str(
                    CLOUDFLARED
                ),

                "tunnel",

                "--no-autoupdate",

                "--url",
                gateway_url,
            ],

            stdout=cf_log,

            stderr=subprocess.STDOUT,
        )
    )


    pattern = re.compile(
        r"https://"
        r"[a-zA-Z0-9-]+"
        r"\.trycloudflare\.com"
    )


    public_url = None


    for _ in range(120):

        try:

            text = (
                CF_LOG.read_text(
                    errors="ignore"
                )
            )

        except Exception:

            text = ""


        match = pattern.search(
            text
        )


        if match:

            public_url = (
                match.group(0)
            )

            break


        if (
            cloudflare_process.poll()
            is not None
        ):

            break


        time.sleep(1)


    if not public_url:

        raise RuntimeError(
            "\n"
            "❌ Cloudflare Tunnel não iniciou.\n\n"
            +
            CF_LOG.read_text(
                errors="ignore"
            )[-10000:]
        )


# =====================================================================
# TESTE FINAL
# =====================================================================

public_ready = False


for _ in range(30):

    try:

        response = httpx.get(
            public_url
            + "/health",

            headers=AUTH_HEADERS,
            timeout=10,
            follow_redirects=True,
        )


        if (
            response.status_code
            == 200
        ):

            public_ready = True

            break


    except Exception:

        pass


    time.sleep(1)


# =====================================================================
# DASHBOARD
# =====================================================================

status = (
    "🟢 ONLINE"
    if public_ready
    else
    "🟡 TUNNEL CRIADO"
)


mtp_display = (
    selected_mtp_file
    if selected_mtp_file
    else
    "Desativado"
)


dashboard = f'''
# 🚀 Kaggle LLM API

| Configuração | Valor |
|---|---|
| **Status** | {status} |
| **Base URL** | `{public_url}/v1` |
| **API Key** | `{API_KEY}` |
| **Model Reference** | `{MODEL_REFERENCE}` |
| **GGUF** | `{selected_model_file}` |
| **MTP** | `{mtp_display}` |
| **Gerações simultâneas** | `{MAX_CONCURRENT_GENERATIONS}` |
| **Contexto / geração** | `{CONTEXT_PER_GENERATION:,} tokens` |
| **Contexto servidor** | `{SERVER_CONTEXT:,} tokens` |
| **Max output** | `{MAX_OUTPUT_TOKENS:,} tokens` |
| **Reasoning default** | `{DEFAULT_REASONING_BUDGET:,} tokens` |
| **KV Cache** | `{KV_CACHE_K} / {KV_CACHE_V}` |
| **Multi-GPU** | `{SPLIT_MODE} / {TENSOR_SPLIT}` |

### OpenAI client

**Base URL**

`{public_url}/v1`

**API Key**

`{API_KEY}`

**Model**

`{MODEL_REFERENCE}`
'''


display(
    Markdown(
        dashboard
    )
)


print()
print(
    "=" * 72
)

print(
    "                    KAGGLE LLM API ONLINE"
)

print(
    "=" * 72
)

print()

print(
    f"BASE URL : {public_url}/v1"
)

print(
    f"API KEY  : {API_KEY}"
)

print(
    f"MODEL    : {MODEL_REFERENCE}"
)

print()

print(
    "PARALLEL :",
    MAX_CONCURRENT_GENERATIONS,
)

print(
    "CONTEXT  :",
    f"{CONTEXT_PER_GENERATION:,}",
    "tokens / geração",
)

print(
    "GGUF     :",
    selected_model_file,
)

print()

print(
    "=" * 72
)

# =====================================================================
# ACTIVE-CELL HEARTBEAT
# =====================================================================
# O notebook fica realmente executando esta célula enquanto o runtime estiver
# saudável. Isso evita depender de cliques falsos e também torna uma queda
# visível imediatamente. Interrompa a célula para encerrar o monitoramento.

if KEEP_RUNTIME_CELL_ACTIVE:

    print()
    print(
        "💓 Monitor ativo: health check real a cada",
        HEARTBEAT_SECONDS,
        "s. Interrompa a célula para parar."
    )

    heartbeat_count = 0

    try:

        while True:

            dead = []

            if llama_process.poll() is not None:
                dead.append("llama-server")

            if gateway_process.poll() is not None:
                dead.append("gateway")

            if USE_CLOUDFLARE and cloudflare_process.poll() is not None:
                dead.append("cloudflared")

            if dead:
                raise RuntimeError(
                    "Processo(s) encerrado(s): " + ", ".join(dead)
                )

            try:
                heartbeat = httpx.get(
                    gateway_url + "/health",
                    headers=AUTH_HEADERS,
                    timeout=8,
                )
                heartbeat.raise_for_status()
            except Exception as exc:
                print(f"⚠️ heartbeat falhou: {exc}")

            heartbeat_count += 1
            if heartbeat_count % 5 == 0:
                print(
                    time.strftime("[%H:%M:%S]"),
                    "runtime saudável ·",
                    f"{heartbeat_count * HEARTBEAT_SECONDS // 60} min monitorados",
                )

            time.sleep(max(15, int(HEARTBEAT_SECONDS)))

    except KeyboardInterrupt:
        print("\n⏹️ Monitor interrompido. Os processos continuam enquanto a sessão Kaggle existir.")
