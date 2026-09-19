"""Linux CUDA validation and Kairn's optional wackMall prebuilt installer."""
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import tarfile
import urllib.error
import urllib.request
from pathlib import Path

WACKMALL_COMMIT = "6aa17e3a3d25104a9c786abb76e920d32faaae10"
WACKMALL_RELEASE = "wackmall-main-b30-6aa17e3-cuda12.4-t4"
WACKMALL_ASSET = "llama-wackmall-linux-cuda12.4-sm75.tar.gz"


def cuda_device_ids(text):
    # Only entries from --list-devices; CUDA compilation banners aren't proof.
    return sorted(set(re.findall(r"^\s*(CUDA\d+)\s*:", text, re.M)))


def require_cuda_devices(server, minimum=2):
    probe = subprocess.run([str(server), "--list-devices"], cwd=Path(server).parent,
                           capture_output=True, text=True, timeout=60)
    output = (probe.stdout or "") + "\n" + (probe.stderr or "")
    devices = cuda_device_ids(output)
    if probe.returncode or len(devices) < minimum:
        raise RuntimeError(
            f"CUDA indisponível no llama-server: {len(devices)}/{minimum} GPUs. "
            "Modelo não será baixado/carregado. Confira GPU T4 ×2, libggml-cuda.so, "
            "bibliotecas CUDA e driver. Diagnóstico:\n" + output[-8000:])
    print("CUDA validada:", ", ".join(devices), flush=True)
    return devices


def write_backend_launcher(directory, binary, library_dirs, loader=None):
    directory, binary = Path(directory), Path(binary)
    if not list(directory.glob("libggml-cuda.so*")):
        raise RuntimeError(f"Prebuilt Linux sem libggml-cuda.so: {directory}")
    library_path = ":".join(map(str, library_dirs))
    # With an explicit glibc loader, /proc/self/exe points to ld-linux. GGML also
    # searches cwd, so set it to the directory containing its dynamic plugins.
    lines = ["#!/bin/sh", "set -eu", "cd " + shlex.quote(str(directory))]
    if loader:
        command = [str(loader), "--library-path", library_path, str(binary)]
    else:
        lines.append("export LD_LIBRARY_PATH=" + shlex.quote(library_path) + '${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}')
        command = [str(binary)]
    lines.append("exec " + " ".join(map(shlex.quote, command)) + ' "$@"')
    launcher = directory / "llama-server"
    binary.chmod(binary.stat().st_mode | 0o111)
    launcher.write_text("\n".join(lines) + "\n", "utf-8")
    launcher.chmod(0o755)
    return launcher


def repair_official_launcher(directory):
    directory = Path(directory)
    binary = directory / "llama-server.bin"
    loaders = list((directory / "sysroot").rglob("ld-linux-x86-64.so.2"))
    if not binary.exists() or not loaders:
        return None
    loader = loaders[0]
    return write_backend_launcher(directory, binary, [directory, loader.parent,
        directory / "sysroot/usr/lib/x86_64-linux-gnu",
        Path("/usr/local/nvidia/lib64"), Path("/usr/lib/x86_64-linux-gnu")], loader)


def install_wackmall(root):
    directory = Path(root) / WACKMALL_RELEASE
    binary = directory / "llama-server.bin"
    if not binary.exists():
        api = f"https://api.github.com/repos/guell11/Kairn/releases/tags/{WACKMALL_RELEASE}"
        try:
            request = urllib.request.Request(api, headers={"User-Agent": "Kairn"})
            with urllib.request.urlopen(request, timeout=30) as response:
                release = json.load(response)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise RuntimeError("Prebuild wackMall Linux CUDA ainda não publicado no Kairn. "
                    "Execute workflow 'Build wackMall CUDA T4' no GitHub e tente novamente. "
                    "Release original main-b30-6aa17e3 só oferece CUDA para Windows. "
                    "Enquanto isso, selecione official-layer.") from exc
            raise
        asset = next((item for item in release.get("assets", []) if item["name"] == WACKMALL_ASSET), None)
        digest = (asset or {}).get("digest", "") or ""
        if not asset or not re.fullmatch(r"sha256:[a-f0-9]{64}", digest):
            raise RuntimeError("Release Kairn sem pacote Linux CUDA ou SHA-256 válido.")
        directory.mkdir(parents=True, exist_ok=True)
        archive = directory / (WACKMALL_ASSET + ".part")
        sha = hashlib.sha256()
        with urllib.request.urlopen(asset["browser_download_url"], timeout=120) as response, archive.open("wb") as out:
            for chunk in iter(lambda: response.read(8 * 1024 * 1024), b""):
                sha.update(chunk)
                out.write(chunk)
        if sha.hexdigest() != digest.removeprefix("sha256:"):
            archive.unlink(missing_ok=True)
            raise RuntimeError("SHA-256 inválido no prebuild wackMall.")
        with tarfile.open(archive, "r:gz") as bundle:
            bundle.extractall(directory, filter="data")
        archive.unlink()
    metadata = json.loads((directory / "build-info.json").read_text("utf-8"))
    if metadata.get("commit") != WACKMALL_COMMIT:
        raise RuntimeError("Prebuild wackMall não corresponde ao commit selecionado.")
    launcher = write_backend_launcher(directory, binary, [directory, Path("/usr/local/nvidia/lib64"), Path("/usr/lib/x86_64-linux-gnu")])
    require_cuda_devices(launcher)
    return launcher
