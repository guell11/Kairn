from __future__ import annotations

import base64
import json
import re
import secrets
import textwrap
from pathlib import Path

from agent_prompt import AGENT_SYSTEM_PROMPT


IK_LLAMA_COMMIT = "06e20d7ece47d78bcebaf6efec47bc291b7d3135"
CLOUDFLARED_VERSION = "2026.9.1"
CLOUDFLARED_SHA256 = "03f1f25d1cc93b9ad6c60569d44060bc4f17ed97075760ed8cfca4b12dcd68cc"
LLAMA_PREBUILT_TAG = "b11009"
LLAMA_PREBUILT_SHA256 = "f0fdb09b03d1e6be2f9a6933613f9d5c398cc53d2a96f86515a5de93334f020e"
LLAMA_CUDART_SHA256 = "7633219ca9deca050e913b53a8bf19dfa35233672c30f30a4ae5c4eb67a3c737"


class RuntimeBuilder:
    def __init__(self, root: Path):
        self.root = root

    def github_cell(self, model: dict, state) -> str:
        config = {key: value for key, value in state.public().items()
                  if key not in {"base_url", "stage"}}
        config["model"] = model["key"]
        return '''# Kaggle: Internet ON, GPU T4 x2. Execute somente esta célula.
import json, runpy, urllib.request, urllib.error
from pathlib import Path

REPOSITORY = "guell11/Kairn"
REF = "main"  # Pode ser tag ou SHA de versão publicada.
CONFIG = ''' + repr(config) + '''

try:
    request = urllib.request.Request(
        f"https://api.github.com/repos/{REPOSITORY}/commits/{REF}",
        headers={"User-Agent": "Kairn-Kaggle"})
    with urllib.request.urlopen(request, timeout=30) as response:
        commit = json.load(response)["sha"]
    url = f"https://raw.githubusercontent.com/{REPOSITORY}/{commit}/kaggle/bootstrap.py"
    with urllib.request.urlopen(url, timeout=60) as response:
        source = response.read()
except urllib.error.HTTPError as error:
    raise RuntimeError(f"Kairn indisponível no GitHub (HTTP {error.code}). Publique projeto completo e confira REF.") from error

compile(source, "bootstrap.py", "exec")
folder = Path("/kaggle/working/.kairn") / commit
folder.mkdir(parents=True, exist_ok=True)
bootstrap = folder / "bootstrap.py"
bootstrap.write_bytes(source)
runpy.run_path(str(bootstrap), run_name="__main__", init_globals={
    "CONFIG": CONFIG, "KAIRN_REPOSITORY": REPOSITORY, "KAIRN_COMMIT": commit})
'''

    def install_cell(self) -> str:
        return '''import os, shutil, subprocess, sys, venv
from pathlib import Path

RUNTIME_VENV = Path("/kaggle/working/.kaggle-runtime-venv")
RUNTIME_PYTHON = RUNTIME_VENV / "bin" / "python"
CLEAN_ENV = os.environ.copy()
CLEAN_ENV.pop("PYTHONPATH", None)
CLEAN_ENV.pop("PYTHONHOME", None)
CLEAN_ENV["PYTHONNOUSERSITE"] = "1"

def runtime_python_ok():
    return RUNTIME_PYTHON.exists() and subprocess.run(
        [str(RUNTIME_PYTHON), "-c", "import sys; print(sys.prefix)"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        env=CLEAN_ENV,
    ).returncode == 0

if not runtime_python_ok():
    print("Criando venv isolado sem ensurepip:", RUNTIME_VENV)
    if RUNTIME_VENV.exists():
        shutil.rmtree(RUNTIME_VENV)
    venv.EnvBuilder(with_pip=False, clear=False, symlinks=False).create(RUNTIME_VENV)

# --python instala NO venv alvo. Ambiente Python global não é alterado.
install = [
    sys.executable, "-m", "pip", "--python", str(RUNTIME_PYTHON),
    "install", "--no-cache-dir", "-q",
    "--upgrade-strategy", "only-if-needed",
    "huggingface_hub", "hf_xet", "fastapi", "uvicorn", "httpx", "requests", "tqdm", "uvloop", "httptools",
]
result = subprocess.run(install, env=CLEAN_ENV)
if result.returncode:
    # Compatibilidade com pip antigo: bootstrap direto dentro do venv.
    get_pip = Path("/kaggle/working/get-pip.py")
    subprocess.check_call([
        sys.executable, "-c",
        "import urllib.request; urllib.request.urlretrieve('https://bootstrap.pypa.io/get-pip.py', r'%s')" % get_pip,
    ], env=CLEAN_ENV)
    subprocess.check_call([str(RUNTIME_PYTHON), str(get_pip), "--no-cache-dir", "-q"], env=CLEAN_ENV)
    get_pip.unlink(missing_ok=True)
    subprocess.check_call([str(RUNTIME_PYTHON), "-m", "pip", *install[5:]], env=CLEAN_ENV)

subprocess.check_call([str(RUNTIME_PYTHON), "-c", "import fastapi,httpx,huggingface_hub,uvicorn,requests"], env=CLEAN_ENV)
print("Venv runtime pronto:", RUNTIME_PYTHON)
'''

    @staticmethod
    def _between(source: str, start: str, end: str, replacement: str) -> str:
        first = source.index(start)
        last = source.index(end, first)
        return source[:first] + replacement.rstrip() + "\n\n" + source[last:]

    @staticmethod
    def _once(source: str, old: str, new: str) -> str:
        if old not in source:
            raise RuntimeError(f"Runtime template changed; missing {old[:40]!r}")
        return source.replace(old, new, 1)

    def _patch_runtime(self, source: str) -> str:
        source = '''# RuntimeBuilder managed prelude: private venv, no global notebook packages.
import os as _runtime_os
import sys as _runtime_sys
import hashlib as _runtime_hashlib
import lzma as _runtime_lzma
import shlex as _runtime_shlex
import shutil as _runtime_shutil
import tarfile as _runtime_tarfile
import urllib.request as _runtime_urllib
from pathlib import Path as _RuntimePath
RUNTIME_VENV = _RuntimePath("/kaggle/working/.kaggle-runtime-venv")
RUNTIME_PYTHON = RUNTIME_VENV / "bin" / "python"
RUNTIME_ENV = _runtime_os.environ.copy()
RUNTIME_ENV.pop("PYTHONPATH", None)
RUNTIME_ENV.pop("PYTHONHOME", None)
RUNTIME_ENV["PYTHONNOUSERSITE"] = "1"
RUNTIME_SITE_PACKAGES = RUNTIME_VENV / "lib" / f"python{_runtime_sys.version_info.major}.{_runtime_sys.version_info.minor}" / "site-packages"
if not RUNTIME_PYTHON.exists() or not RUNTIME_SITE_PACKAGES.exists():
    raise RuntimeError("Venv runtime ausente. Execute primeiro a célula de instalação.")
_runtime_sys.path.insert(0, str(RUNTIME_SITE_PACKAGES))
IK_LLAMA_COMMIT = "06e20d7ece47d78bcebaf6efec47bc291b7d3135"
CLOUDFLARED_VERSION = "2026.9.1"
CLOUDFLARED_SHA256 = "03f1f25d1cc93b9ad6c60569d44060bc4f17ed97075760ed8cfca4b12dcd68cc"
LLAMA_PREBUILT_TAG = "b11009"
LLAMA_PREBUILT_SHA256 = "f0fdb09b03d1e6be2f9a6933613f9d5c398cc53d2a96f86515a5de93334f020e"
LLAMA_CUDART_SHA256 = "7633219ca9deca050e913b53a8bf19dfa35233672c30f30a4ae5c4eb67a3c737"
\n''' + source
        source = self._once(source, "import os\n", "import os\nimport hashlib\nimport ctypes.util\n")
        source = source.replace("sys.executable,", "str(RUNTIME_PYTHON),")
        source = self._once(
            source,
            "    stdout=gateway_log,\n\n    stderr=subprocess.STDOUT,",
            "    env={**RUNTIME_ENV, **{key: value for key, value in os.environ.items() if key.startswith('KAGGLE_')}},\n\n    stdout=gateway_log,\n\n    stderr=subprocess.STDOUT,",
        )

        compiler = '''# =====================================================================
# COMPILAR BACKEND DE INFERÊNCIA
# =====================================================================
backend = BACKEND_FAMILY if BACKEND_FAMILY != "auto" else "official-layer"
if backend not in {"ik_llama", "official-layer", "official-tensor"}:
    raise ValueError(f"Backend inválido: {backend}")

def cuda_architectures():
    try:
        raw = subprocess.check_output(["nvidia-smi", "--query-gpu=compute_cap", "--format=csv,noheader"], text=True)
        values = sorted({line.strip().replace(".", "") for line in raw.splitlines() if line.strip()})
        if values and all(value.isdigit() for value in values):
            return ";".join(value + "-real" for value in values)
    except Exception:
        pass
    print("⚠️ compute_cap indisponível; fallback T4 sm_75")
    return "75-real"

def cuda_driver_present():
    paths = ["/usr/lib/x86_64-linux-gnu/libcuda.so", "/usr/local/nvidia/lib64/libcuda.so", "/usr/lib/wsl/lib/libcuda.so"]
    return bool(ctypes.util.find_library("cuda") or any(Path(path).exists() for path in paths))

GPU_ARCHITECTURES = cuda_architectures()
CUDA_DRIVER_PRESENT = cuda_driver_present()
if backend == "ik_llama":
    repo_url, SPLIT_MODE = "https://github.com/ikawrakow/ik_llama.cpp", "graph"
    cmake_extra = [
        "-DGGML_IQK_FA_ALL_QUANTS=OFF",
        "-DGGML_CUDA_FA_ALL_QUANTS=OFF",
        "-DLLAMA_BUILD_TESTS=OFF",
        "-DLLAMA_BUILD_EXAMPLES=ON",
        "-DLLAMA_CURL=OFF",
        "-DBUILD_SHARED_LIBS=OFF",
    ]
else:
    repo_url = "https://github.com/ggml-org/llama.cpp"
    SPLIT_MODE = "tensor" if backend == "official-tensor" else "layer"
    cmake_extra = ["-DGGML_CUDA_NCCL=ON"]
    if backend == "official-tensor":
        KV_CACHE_K = KV_CACHE_V = "f16"
source_dir, build_dir = ROOT / "inference_backend", ROOT / "inference_backend" / "build"
print(f"🔨 backend={backend} CUDA arch={GPU_ARCHITECTURES} driver={CUDA_DRIVER_PRESENT}")
reuse_checkout = False
if source_dir.exists() and (source_dir / ".git").exists():
    try:
        current_commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=source_dir, text=True
        ).strip()
        reuse_checkout = backend == "ik_llama" and current_commit == IK_LLAMA_COMMIT
    except Exception:
        pass
if reuse_checkout:
    print("♻️ Build parcial encontrado; retomando sem recompilar objetos prontos")
elif backend == "ik_llama":
    shutil.rmtree(source_dir, ignore_errors=True)
    run(["git", "clone", "--filter=blob:none", repo_url, str(source_dir)])
    run(["git", "checkout", "--detach", IK_LLAMA_COMMIT], cwd=source_dir)
else:
    shutil.rmtree(source_dir, ignore_errors=True)
    run(["git", "clone", "--depth", "1", repo_url, str(source_dir)])
generator = ["-G", "Ninja"] if shutil.which("ninja") and not (build_dir / "CMakeCache.txt").exists() else []
cmake_cmd = ["cmake", *generator, "-S", str(source_dir), "-B", str(build_dir), "-DGGML_CUDA=ON", f"-DCMAKE_CUDA_ARCHITECTURES={GPU_ARCHITECTURES}", "-DCMAKE_BUILD_TYPE=Release", *cmake_extra]
if not CUDA_DRIVER_PRESENT:
    cmake_cmd.append("-DGGML_CUDA_NO_VMM=ON")
configure = subprocess.run(cmake_cmd, capture_output=True, text=True)
configure_log = (configure.stdout or "") + "\\n" + (configure.stderr or "")
if configure.returncode and "CUDA::cuda_driver" in configure_log and "-DGGML_CUDA_NO_VMM=ON" not in cmake_cmd:
    print("⚠️ CUDA::cuda_driver ausente; recompilando sem VMM")
    cmake_cmd.append("-DGGML_CUDA_NO_VMM=ON")
    configure = subprocess.run(cmake_cmd, capture_output=True, text=True)
    configure_log = (configure.stdout or "") + "\\n" + (configure.stderr or "")
if configure.returncode:
    raise RuntimeError("CMake falhou:\\n" + configure_log[-12000:])
run(["cmake", "--build", str(build_dir), "--config", "Release", "--target", "llama-server", "-j", str(min(os.cpu_count() or 4, 8))])
compiled_server = next((p for p in [build_dir / "bin" / "llama-server", build_dir / "bin" / "Release" / "llama-server"] if p.exists()), None)
if compiled_server is None:
    raise RuntimeError("llama-server não foi compilado.")
RUNTIME_SERVER = ROOT / "llama-server"
shutil.copy2(compiled_server, RUNTIME_SERVER)
RUNTIME_SERVER.chmod(RUNTIME_SERVER.stat().st_mode | stat.S_IEXEC)
(ROOT / "llama-server.build-id").write_text(f"{backend}|{IK_LLAMA_COMMIT if backend == 'ik_llama' else 'upstream'}")
probe = subprocess.run([str(RUNTIME_SERVER), "--help"], capture_output=True, text=True, timeout=30)
if probe.returncode != 0:
    raise RuntimeError("llama-server falhou --help:\\n" + (probe.stderr or probe.stdout)[-4000:])
shutil.rmtree(source_dir, ignore_errors=True)
LLAMA_SERVER = RUNTIME_SERVER
print("✅ llama-server compilado e validado")
show_disk()'''
        prebuilt = '''# Download oficial verificado por SHA-256: sem compilação CUDA no Kaggle.
PREBUILT_DIR = ROOT / f"llama-prebuilt-{LLAMA_PREBUILT_TAG}"
PREBUILT_DIR.mkdir(parents=True, exist_ok=True)
_runtime_shutil.rmtree(ROOT / "inference_backend", ignore_errors=True)

def _file_sha256(path):
    digest = _runtime_hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()

def _download_verified(url, name, sha256):
    archive = ROOT / name
    if archive.exists():
        if _file_sha256(archive) == sha256:
            return archive
        archive.unlink()
    partial = Path(str(archive) + ".part")
    offset = partial.stat().st_size if partial.exists() else 0
    headers = {"Range": f"bytes={offset}-"} if offset else {}
    headers["User-Agent"] = "Kaggle-Studio/4"
    request = _runtime_urllib.Request(url, headers=headers)
    with _runtime_urllib.urlopen(request, timeout=60) as response:
        resumed = offset and getattr(response, "status", 200) == 206
        mode = "ab" if resumed else "wb"
        with open(partial, mode) as handle:
            _runtime_shutil.copyfileobj(response, handle, length=8 * 1024 * 1024)
    if _file_sha256(partial) != sha256:
        raise RuntimeError(f"SHA-256 inválido no prebuilt: {name}")
    partial.replace(archive)
    return archive

def _prebuilt_download(name, sha256):
    url = f"https://github.com/ggml-org/llama.cpp/releases/download/{LLAMA_PREBUILT_TAG}/{name}"
    return _download_verified(url, name, sha256)

binary_name = f"llama-{LLAMA_PREBUILT_TAG}-bin-ubuntu-cuda-12.8-x64.tar.gz"
cudart_name = f"cudart-llama-{LLAMA_PREBUILT_TAG}-bin-ubuntu-cuda-12.8-x64.tar.gz"
print("⬇️ Baixando llama-server CUDA oficial (~760 MB); zero build local")
archives = [
    _prebuilt_download(binary_name, LLAMA_PREBUILT_SHA256),
    _prebuilt_download(cudart_name, LLAMA_CUDART_SHA256),
]
extract_dir = ROOT / f".extract-{LLAMA_PREBUILT_TAG}"
_runtime_shutil.rmtree(extract_dir, ignore_errors=True)
extract_dir.mkdir(parents=True)
for archive in archives:
    with _runtime_tarfile.open(archive, "r:gz") as bundle:
        bundle.extractall(extract_dir, filter="data")
server_source = next(extract_dir.rglob("llama-server"), None)
if server_source is None:
    raise RuntimeError("Prebuilt oficial não contém llama-server")
for source in [server_source, *extract_dir.rglob("*.so*")]:
    if source.is_file():
        target = "llama-server.bin" if source == server_source else source.name
        _runtime_shutil.copy2(source, PREBUILT_DIR / target)

# Kaggle usa glibc antiga; runtime Noble fica privado, sem apt/install global.
sysroot = PREBUILT_DIR / "sysroot"
packages_url = "https://archive.ubuntu.com/ubuntu/dists/noble/main/binary-amd64/Packages.xz"
packages_raw = _runtime_urllib.urlopen(
    _runtime_urllib.Request(packages_url, headers={"User-Agent": "Kaggle-Studio/4"}),
    timeout=60,
).read()
packages_text = _runtime_lzma.decompress(packages_raw).decode("utf-8")
records = {}
for paragraph in packages_text.split("\\n\\n"):
    fields = {}
    for line in paragraph.splitlines():
        if ": " in line:
            key, value = line.split(": ", 1)
            fields[key] = value
    if fields.get("Package") in {"libc6", "libstdc++6", "libgcc-s1"}:
        records[fields["Package"]] = fields
if set(records) != {"libc6", "libstdc++6", "libgcc-s1"}:
    raise RuntimeError("Metadados do runtime glibc incompletos")
debs = []
for package in ("libc6", "libstdc++6", "libgcc-s1"):
    record = records[package]
    filename = Path(record["Filename"]).name
    deb = _download_verified(
        "https://archive.ubuntu.com/ubuntu/" + record["Filename"],
        filename,
        record["SHA256"],
    )
    debs.append(deb)
    subprocess.check_call(["dpkg-deb", "-x", str(deb), str(sysroot)])

loader = next(sysroot.rglob("ld-linux-x86-64.so.2"), None)
real_server = PREBUILT_DIR / "llama-server.bin"
if loader is None or not real_server.exists():
    raise RuntimeError("Runtime glibc privado incompleto")
library_dirs = [
    PREBUILT_DIR,
    loader.parent,
    sysroot / "usr/lib/x86_64-linux-gnu",
    Path("/usr/local/nvidia/lib64"),
    Path("/usr/lib/x86_64-linux-gnu"),
]
library_path = ":".join(str(path) for path in library_dirs)
RUNTIME_SERVER = PREBUILT_DIR / "llama-server"
RUNTIME_SERVER = write_backend_launcher(PREBUILT_DIR, real_server, library_dirs, loader)
require_cuda_devices(RUNTIME_SERVER)
BUILD_ID.write_text(expected_build_id)
for archive in archives:
    archive.unlink(missing_ok=True)
for deb in debs:
    deb.unlink(missing_ok=True)
_runtime_shutil.rmtree(extract_dir, ignore_errors=True)
LLAMA_SERVER = RUNTIME_SERVER
print("✅ llama-server CUDA prebuilt validado")'''

        compiler = '''# =====================================================================
# BACKEND COMPILADO — reutiliza binário validado na mesma sessão Kaggle.
# =====================================================================
backend = BACKEND_FAMILY if BACKEND_FAMILY != "auto" else "official-layer"
RUNTIME_SERVER = ROOT / (f"llama-prebuilt-{LLAMA_PREBUILT_TAG}/llama-server" if backend.startswith("official-") else "llama-server")
BUILD_ID = ROOT / "llama-server.build-id"
expected_build_id = f"{backend}|{IK_LLAMA_COMMIT if backend == 'ik_llama' else LLAMA_PREBUILT_TAG}"
if backend.startswith("official-") and RUNTIME_SERVER.exists():
    # Repair previous launcher in place; keep verified GGUF and CUDA archives.
    repair_official_launcher(RUNTIME_SERVER.parent)
cached_server_ok = RUNTIME_SERVER.exists() and BUILD_ID.exists() and BUILD_ID.read_text() == expected_build_id
if cached_server_ok:
    probe = subprocess.run([str(RUNTIME_SERVER), "--help"], env=_runtime_os.environ, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
    cached_server_ok = probe.returncode == 0
if cached_server_ok:
    LLAMA_SERVER = RUNTIME_SERVER
    SPLIT_MODE = "graph" if backend == "ik_llama" else ("tensor" if backend == "official-tensor" else "layer")
    print("♻️ llama-server validado; build ignorado")
elif backend == "wackmall":
    LLAMA_SERVER = install_wackmall(ROOT)
elif backend.startswith("official-"):
''' + textwrap.indent(prebuilt, "    ") + '''
else:
''' + textwrap.indent(compiler, "    ")
        compiler = (self.root / "prebuilt_support.py").read_text("utf-8") + "\n" + compiler + "\nrequire_cuda_devices(LLAMA_SERVER)\n"
        source = self._between(source, "# =====================================================================\n# COMPILAR BACKEND DE INFERÊNCIA", "# =====================================================================\n# HUGGING FACE", compiler)

        # Preserve .part files. Direct downloader below resumes them atomically.
        source = source.replace('name.endswith(".part")\n            or\n            ', "False\n            or\n            ")
        source = self._once(source, "size = remote_file_size(\n        repo,\n        selected,\n        revision,\n    )", "metadata = remote_file_metadata(repo, selected, revision)\n    size = metadata['size']")
        source = self._once(source, '"size": size,\n    }', '"size": size,\n        "sha256": metadata.get("sha256"),\n    }')
        metadata = '''# =====================================================================
# INFO REMOTA DO ARQUIVO
# =====================================================================
def remote_file_metadata(repo, filename, revision):
    info = HfApi(token=HF_TOKEN_REAL).model_info(repo_id=repo, revision=revision, files_metadata=True, token=HF_TOKEN_REAL)
    for sibling in info.siblings:
        if sibling.rfilename == filename:
            lfs = getattr(sibling, "lfs", None) or {}
            size = getattr(sibling, "size", None) or lfs.get("size")
            return {"size": int(size) if size is not None else None, "sha256": lfs.get("sha256")}
    raise RuntimeError(f"Arquivo remoto não encontrado: {filename}")'''
        source = self._between(source, "# =====================================================================\n# INFO REMOTA DO ARQUIVO", "# =====================================================================\n# ESCOLHER GGUF", metadata)
        downloader = '''# =====================================================================
# DOWNLOAD DIRETO — Range resume, sem cache duplicado, size + SHA-256.
# =====================================================================
def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()

def direct_download(info):
    if info is None:
        return None
    repo, filename, revision = info["repo"], info["filename"], info["revision"]
    expected_size, expected_hash = info.get("size"), info.get("sha256")
    folder = MODELS_DIR / repo.replace("/", "__")
    folder.mkdir(parents=True, exist_ok=True)
    destination = folder / Path(filename).name
    partial = Path(str(destination) + ".part")
    def valid(path):
        return (expected_size is None or path.stat().st_size == expected_size) and (not expected_hash or _sha256(path).lower() == expected_hash.lower())
    if destination.exists():
        if valid(destination):
            print("♻️ Modelo verificado:", destination.name)
            return destination
        destination.unlink()
    offset = partial.stat().st_size if partial.exists() else 0
    margin = int(MIN_FREE_AFTER_DOWNLOAD_GB * 1024**3)
    remaining = max(0, (expected_size or 0) - offset)
    if expected_size and disk_free() < remaining + margin:
        raise RuntimeError(f"Espaço insuficiente; parcial preservado. Faltam {human_bytes(remaining + margin - disk_free())}")
    url = "https://huggingface.co/" + repo + "/resolve/" + revision + "/" + quote(filename, safe="/") + "?download=true"
    headers = {"Authorization": "Bearer " + HF_TOKEN_REAL} if HF_TOKEN_REAL else {}
    if offset:
        headers["Range"] = f"bytes={offset}-"
        print(f"⬇️ Retomando {destination.name} em {human_bytes(offset)}")
    with requests.get(url, headers=headers, stream=True, allow_redirects=True, timeout=120) as response:
        if offset and response.status_code != 206:
            print("⚠️ Range recusado; reiniciando parcial")
            offset = 0
        response.raise_for_status()
        total = expected_size or int(response.headers.get("content-length", 0) or 0) + offset
        with open(partial, "ab" if offset else "wb") as handle, tqdm(total=total or None, initial=offset, unit="B", unit_scale=True, unit_divisor=1024, desc=destination.name) as bar:
            for chunk in response.iter_content(16 * 1024 * 1024):
                if chunk:
                    handle.write(chunk); bar.update(len(chunk))
    if not valid(partial):
        if expected_size is not None and partial.stat().st_size != expected_size:
            raise RuntimeError("Download incompleto; parcial preservado para retomar.")
        partial.unlink(missing_ok=True)
        raise RuntimeError("SHA-256 inválido; parcial removido.")
    partial.replace(destination)
    print("✅ Download validado:", destination)
    return destination'''
        source = self._between(source, "# =====================================================================\n# DOWNLOAD DIRETO", "# =====================================================================\n# SELECIONAR MODELOS", downloader)

        server = '''# fallback automático para layer split foi removido: graph só reduz slots após OOM.
# =====================================================================
# LLAMA SERVER — graph T4 x2 retries 4 -> 2 -> 1 only after a CUDA OOM.
# =====================================================================
for pattern in ["kaggle_universal_gateway", "cloudflared.*tunnel", str(LLAMA_SERVER)]:
    subprocess.run(["pkill", "-f", pattern], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(2)

backend_url = f"http://127.0.0.1:{LLAMA_PORT}"
LLAMA_LOG = ROOT / "llama_server.log"
def make_llama_command(slots):
    command = [str(LLAMA_SERVER), "--model", str(model_path), "--alias", MODEL_REFERENCE,
               "--host", "127.0.0.1", "--port", str(LLAMA_PORT),
               "--ctx-size", str(CONTEXT_PER_GENERATION * slots), "--parallel", str(slots),
               "--cont-batching", "--split-mode", SPLIT_MODE, "--tensor-split", TENSOR_SPLIT,
               "--n-gpu-layers", str(GPU_LAYERS), "--batch-size", str(BATCH_SIZE),
               "--ubatch-size", str(UBATCH_SIZE), "--threads", str(CPU_THREADS),
               "--threads-batch", str(CPU_BATCH_THREADS), "--cache-type-k", KV_CACHE_K,
               "--cache-type-v", KV_CACHE_V, "--jinja", "--parallel-tool-calls", "--metrics",
               "--reasoning", "auto", "--reasoning-budget", "-1"]
    if FLASH_ATTENTION: command += ["--flash-attn", "on"]
    if mtp_path:
        command += ["--model-draft", str(mtp_path), "--ctx-size-draft", str(CONTEXT_PER_GENERATION * slots),
                    "--spec-type", f"mtp:n_max={MTP_TOKENS},p_min={MTP_P_MIN},heads={MTP_HEADS}"]
    return command

def startup_oom(log_text):
    text = log_text.lower()
    return any(token in text for token in ["out of memory", "cuda error 2", "cuda malloc", "failed to allocate"])

slot_attempts = [MAX_CONCURRENT_GENERATIONS]
if SPLIT_MODE == "graph" and len(gpu_lines) == 2:
    while slot_attempts[-1] > 1:
        slot_attempts.append(max(1, slot_attempts[-1] // 2))
llama_process = None
backend_ready = False
for attempt, slots in enumerate(slot_attempts):
    print(f"🚀 Iniciando {backend}: graph={SPLIT_MODE} slots={slots} ctx={CONTEXT_PER_GENERATION * slots}")
    with open(LLAMA_LOG, "a" if attempt else "w", buffering=1) as llama_log:
        llama_log.write(f"\\n=== startup slots={slots} ===\\n")
        llama_process = subprocess.Popen(make_llama_command(slots), stdout=llama_log, stderr=subprocess.STDOUT)
        for _ in range(300):
            if llama_process.poll() is not None: break
            try:
                if httpx.get(backend_url + "/health", timeout=2).status_code == 200:
                    backend_ready = True; break
            except Exception:
                pass
            time.sleep(1)
    if backend_ready:
        MAX_CONCURRENT_GENERATIONS = slots
        SERVER_CONTEXT = CONTEXT_PER_GENERATION * slots
        break
    tail = LLAMA_LOG.read_text(errors="ignore")[-20000:]
    if attempt + 1 < len(slot_attempts) and startup_oom(tail):
        print(f"⚠️ OOM confirmado; reduzindo slots {slots} -> {slot_attempts[attempt + 1]}")
        continue
    raise RuntimeError(f"❌ {backend} não iniciou (slots={slots}).\\n" + tail)
if not backend_ready:
    raise RuntimeError("llama-server não iniciou.")
print(f"✅ {backend} online · slots={MAX_CONCURRENT_GENERATIONS} · ctx={SERVER_CONTEXT}")'''
        # Only the final runtime server section is replaced. Gateway routes stay unchanged.
        server_start = source.index("# =====================================================================\n# LLAMA SERVER", source.index("# MATAR PROCESSOS ANTIGOS"))
        server_end = source.index("# =====================================================================\n# UNIVERSAL API GATEWAY", server_start)
        source = source[:server_start] + server.rstrip() + "\n\n" + source[server_end:]

        cloudflared = '''# =====================================================================
# CLOUDFLARED
# =====================================================================
public_url = gateway_url
if USE_CLOUDFLARE:
    CLOUDFLARED = ROOT / "cloudflared"
    def cloudflared_valid(path): return path.exists() and _sha256(path).lower() == CLOUDFLARED_SHA256
    if not cloudflared_valid(CLOUDFLARED):
        CLOUDFLARED.unlink(missing_ok=True)
        partial = Path(str(CLOUDFLARED) + ".part")
        partial.unlink(missing_ok=True)
        url = f"https://github.com/cloudflare/cloudflared/releases/download/{CLOUDFLARED_VERSION}/cloudflared-linux-amd64"
        print(f"☁️ cloudflared {CLOUDFLARED_VERSION}, checksum fixo")
        with requests.get(url, stream=True, timeout=120) as response, open(partial, "wb") as handle:
            response.raise_for_status()
            for chunk in response.iter_content(1024 * 1024):
                if chunk: handle.write(chunk)
        if not cloudflared_valid(partial):
            partial.unlink(missing_ok=True); raise RuntimeError("Checksum cloudflared inválido.")
        partial.replace(CLOUDFLARED)
    CLOUDFLARED.chmod(CLOUDFLARED.stat().st_mode | stat.S_IEXEC)
    CF_LOG = ROOT / "cloudflared.log"; cf_log = open(CF_LOG, "w", buffering=1)
    cloudflare_process = subprocess.Popen([str(CLOUDFLARED), "tunnel", "--no-autoupdate", "--url", gateway_url], stdout=cf_log, stderr=subprocess.STDOUT)
    pattern = re.compile(r"https://[a-zA-Z0-9-]+\\.trycloudflare\\.com"); public_url = None
    for _ in range(120):
        match = pattern.search(CF_LOG.read_text(errors="ignore") if CF_LOG.exists() else "")
        if match: public_url = match.group(0); break
        if cloudflare_process.poll() is not None: break
        time.sleep(1)
    if not public_url: raise RuntimeError("Cloudflare Tunnel não iniciou:\\n" + CF_LOG.read_text(errors="ignore")[-10000:])'''
        source = self._between(source, "# =====================================================================\n# CLOUDFLARED", "# =====================================================================\n# TESTE FINAL", cloudflared)
        source = self._once(
            source,
            '"KAGGLE_REASONING_BUDGET": str(DEFAULT_REASONING_BUDGET),\n})',
            '"KAGGLE_REASONING_BUDGET": str(DEFAULT_REASONING_BUDGET),\n'
            '    "KAGGLE_BACKEND_FAMILY": str(backend),\n'
            '    "KAGGLE_GPU_NAMES": " | ".join(gpu_lines),\n'
            '    "KAGGLE_SPLIT_MODE": str(SPLIT_MODE),\n'
            '    "KAGGLE_CONTEXT_SIZE": str(SERVER_CONTEXT),\n'
            '    "KAGGLE_SLOTS": str(MAX_CONCURRENT_GENERATIONS),\n'
            '})',
        )
        source = source.replace(
            "heartbeat.raise_for_status()",
            "heartbeat.raise_for_status()\n"
            "                backend_health = httpx.get(backend_url + '/health', timeout=8)\n"
            "                backend_health.raise_for_status()\n"
            "                compatibility = httpx.get(gateway_url + '/v1/models', headers=AUTH_HEADERS, timeout=8)\n"
            "                compatibility.raise_for_status()",
        )
        # Keep the notebook kernel clean: run all imports in the private Python.
        source = source.replace('if SPLIT_MODE == "graph" and len(gpu_lines) == 2:', 'if len(gpu_lines) == 2:')
        start = source.index("def make_llama_command(slots):")
        end = source.index("def startup_oom", start)
        helpers = (self.root / "runtime_support.py").read_text("utf-8")
        source = source[:start] + helpers + '''
server_help = subprocess.check_output([str(LLAMA_SERVER), "--help"], text=True, stderr=subprocess.STDOUT)
def make_llama_command(slots):
    return llama_command(LLAMA_SERVER, model_path, MODEL_REFERENCE,
        CONTEXT_PER_GENERATION, slots, SPLIT_MODE, server_help,
        DEFAULT_TEMPERATURE, DEFAULT_TOP_K, DEFAULT_TOP_P, DEFAULT_MIN_P,
        DEFAULT_REASONING_BUDGET)

''' + source[end:]
        source = source.replace('slot_attempts = [MAX_CONCURRENT_GENERATIONS]\nif len(gpu_lines) == 2:\n    while slot_attempts[-1] > 1:\n        slot_attempts.append(max(1, slot_attempts[-1] // 2))', 'slot_attempts = retry_slots(MAX_CONCURRENT_GENERATIONS)')
        source = source.replace('    tail = LLAMA_LOG.read_text', '    stop_process(llama_process)\n    tail = LLAMA_LOG.read_text')
        source = source.replace('open(LLAMA_LOG, "a" if attempt else "w", buffering=1)', 'open(LLAMA_LOG, "w", buffering=1)')
        source = source.replace('for pattern in ["kaggle_universal_gateway", "cloudflared.*tunnel", str(LLAMA_SERVER)]:', 'for pattern in [str(ROOT / "kaggle_universal_gateway.py"), str(ROOT / "cloudflared") + " tunnel", str(LLAMA_SERVER)]:')
        source = source.replace('from IPython.display import display, Markdown', 'def Markdown(text): return text\ndef display(text): print(text)')
        source = source.replace('lfs.get("size")', '(lfs.get("size") if isinstance(lfs, dict) else getattr(lfs, "size", None))')
        source = source.replace('lfs.get("sha256")', '(lfs.get("sha256") if isinstance(lfs, dict) else getattr(lfs, "sha256", None))')
        old_start = source.index('# MATAR PROCESSOS ANTIGOS')
        old_end = source.index('# fallback automático', old_start)
        source = source[:old_start] + '# Processos anteriores são encerrados pelo supervisor da célula.\n' + source[old_end:]
        # Set split mode before both cached and fresh prebuilt paths.
        source = source.replace('BUILD_ID = ROOT / "llama-server.build-id"', 'SPLIT_MODE = "graph" if backend == "ik_llama" else ("tensor" if backend == "official-tensor" else "layer")\nBUILD_ID = ROOT / "llama-server.build-id"')
        source = source.replace('server_help = subprocess.check_output', 'KV_CACHE_K = KV_CACHE_V = "f16" if SPLIT_MODE == "tensor" else "q8_0"\nserver_help = subprocess.check_output')
        source = source.replace('"                    KAGGLE LLM API ONLINE"', '"KAGGLE LLM API ONLINE" if public_ready else "TÚNEL AINDA NÃO VALIDADO: confira URL e logs"')
        source = source.replace('cloudflare_process = subprocess.Popen([str(CLOUDFLARED), "tunnel", "--no-autoupdate", "--url", gateway_url], stdout=cf_log, stderr=subprocess.STDOUT)', '''named_tunnel = os.environ.get("KAGGLE_TUNNEL_MODE") == "named"
    tunnel_command = [str(CLOUDFLARED), "tunnel", "--no-autoupdate"]
    tunnel_command += ["run"] if named_tunnel else ["--url", gateway_url]
    cloudflare_process = subprocess.Popen(tunnel_command, stdout=cf_log, stderr=subprocess.STDOUT)
    if not named_tunnel:
        print("AVISO: Quick Tunnel não suporta SSE. Para agentes, configure túnel nomeado.")''')
        source = source.replace('    if not public_url: raise RuntimeError', '    if named_tunnel:\n        public_url = os.environ["KAGGLE_TUNNEL_URL"].rstrip("/").removesuffix("/v1")\n    if not public_url: raise RuntimeError')
        source = source.replace('    for _ in range(120):\n        match', '    for _ in range(0 if named_tunnel else 120):\n        match')
        return source

    def runtime_source(self, model: dict, state, api_key: str = "") -> str:
        if int(state.output) >= int(state.context):
            raise ValueError("Saída deve ser menor que contexto, reservando espaço para prompt.")
        key = api_key.strip() or ("ks_" + secrets.token_urlsafe(24))
        source = self._patch_runtime((self.root / "kaggle_runtime_template.py").read_text("utf-8"))
        gateway = base64.b64encode((self.root / "kaggle_gateway.py").read_bytes()).decode("ascii")
        values = {"MODEL": model["source"], "MTP": model.get("mtp", ""), "MODEL_REFERENCE": model["model_id"], "API_KEY": key, "CONTEXT_PER_GENERATION": int(state.context), "MAX_CONCURRENT_GENERATIONS": int(state.parallel), "MAX_OUTPUT_TOKENS": int(state.output), "MTP_TOKENS": int(state.mtp_tokens), "DEFAULT_REASONING_BUDGET": int(state.reasoning_budget), "DEFAULT_TEMPERATURE": float(state.temperature), "DEFAULT_TOP_K": int(state.top_k), "DEFAULT_TOP_P": float(state.top_p), "DEFAULT_MIN_P": float(state.min_p), "BACKEND_FAMILY": state.backend, "AGENT_SYSTEM_PROMPT": AGENT_SYSTEM_PROMPT, "UNIVERSAL_GATEWAY_B64": gateway}
        for name, value in values.items():
            source, count = re.subn(rf"^{re.escape(name)}\s*=\s*.*$", lambda _m, text=f"{name} = {value!r}": text, source, count=1, flags=re.M)
            if count != 1: raise RuntimeError(f"Runtime template is missing configurable field: {name}")
        return source

    def runtime_cell(self, model: dict, state, api_key: str) -> str:
        source = self.runtime_source(model, state, api_key)
        encoded = base64.b64encode(source.encode("utf-8")).decode("ascii")
        return '''# Executa runtime no venv, sem injetar pacotes no kernel Kaggle.
import base64, os, subprocess
from pathlib import Path
runtime_file = Path("/kaggle/working/kaggle_studio_runtime.py")
runtime_file.write_bytes(base64.b64decode(''' + repr(encoded) + '''))
runtime_file.chmod(0o600)
runtime_env = os.environ.copy()
runtime_env.pop("PYTHONPATH", None)
runtime_env.pop("PYTHONHOME", None)
runtime_env["PYTHONNOUSERSITE"] = "1"
runtime_env["KAGGLE_TUNNEL_MODE"] = ''' + repr(getattr(state, 'tunnel_mode', 'quick')) + '''
runtime_env["KAGGLE_TUNNEL_URL"] = ''' + repr(getattr(state, 'tunnel_url', '')) + '''
if runtime_env["KAGGLE_TUNNEL_MODE"] == "named":
    from getpass import getpass
    if not runtime_env["KAGGLE_TUNNEL_URL"].startswith("https://"):
        raise ValueError("Configure URL HTTPS do túnel nomeado no Studio.")
    runtime_env["TUNNEL_TOKEN"] = os.environ.get("TUNNEL_TOKEN") or getpass("Token do túnel Cloudflare (oculto): ")
runtime_python = Path("/kaggle/working/.kaggle-runtime-venv/bin/python")
if not runtime_python.exists():
    raise RuntimeError("Execute primeiro célula 1: preparação.")
process = subprocess.Popen([str(runtime_python), "-u", str(runtime_file)], env=runtime_env, start_new_session=True)
try:
    if process.wait():
        raise RuntimeError("Runtime falhou. Veja erro e logs acima.")
except KeyboardInterrupt:
    print("Runtime, gateway e túnel encerrados.")
finally:
    import signal
    try:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=15)
    except ProcessLookupError:
        pass
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait()
'''

    def notebook(self, model: dict, state) -> str:
        code = self.runtime_cell(model, state, "__RUNTIME_KEY__")
        # A reusable notebook creates its own key at execution time.
        encoded = re.search(r"b64decode\(('.*?')\)", code).group(1)
        import ast
        source = base64.b64decode(ast.literal_eval(encoded)).decode()
        source = source.replace("API_KEY = '__RUNTIME_KEY__'", "API_KEY = 'ks_' + __import__('secrets').token_urlsafe(24)")
        code = code.replace(encoded, repr(base64.b64encode(source.encode()).decode()))
        def cell(kind, text):
            result = {"cell_type": kind, "id": secrets.token_hex(4), "metadata": {}, "source": text.splitlines(True)}
            if kind == "code": result.update(execution_count=None, outputs=[])
            return result
        return json.dumps({"nbformat": 4, "nbformat_minor": 5,
            "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                         "language_info": {"name": "python"}},
            "cells": [cell("markdown", "# Kaggle Studio\nAtive Internet e GPU T4 ×2. Execute preparação, depois runtime.\nInterromper runtime encerra servidores. Túnel rápido serve para testes sem SSE; use túnel nomeado para agentes.\n"),
                      cell("code", self.install_cell()), cell("code", code)]}, ensure_ascii=False, indent=2)
