from __future__ import annotations

MODELS = {
    "gemopus": {
        "key": "gemopus", "name": "Gemopus 4 26B A4B", "quant": "Q4_K_M",
        "source": "https://huggingface.co/Jackrong/Gemopus-4-26B-A4B-it-GGUF/blob/main/Gemopus-4-26B-A4B-it-Preview-Q4_K_M.gguf",
        "gguf": "Gemopus-4-26B-A4B-it-Preview-Q4_K_M.gguf", "revision": "main",
        "size_bytes": 16796015488, "sha256": "2037b8c978db6c8b947d10e34a70f410dde6301919c6040624fdda50647f7940", "min_vram_gb": 24,
        "model_id": "gemopus-4-26b-a4b",
        "description": "MoE compacto para coding e tarefas gerais; bom encaixe em T4 ×2.",
        "context": 16384, "output": 8192, "parallel": 4, "backend": "official-layer", "mtp": "", "supports_mtp": False,
    },
    "velum": {
        "key": "velum", "name": "VELUM Coder", "quant": "auto Q4/IQ4",
        "source": "https://huggingface.co/guell00/VELUM-Coder/blob/main/VELUM-Coder-IQ4_XS.gguf", "model_id": "velum-coder",
        "gguf": "VELUM-Coder-IQ4_XS.gguf", "revision": "main",
        "size_bytes": 5196439968, "sha256": "29eb42aafaf7ef454c4c4c53707c1e0cb364c442dc6b8d3b638c9a0f9847b538", "min_vram_gb": 8,
        "description": "Preset focado em código, tool use e ciclos longos de edição.",
        "context": 16384, "output": 8192, "parallel": 4, "backend": "official-layer", "mtp": "", "supports_mtp": False,
    },
    "qwen": {
        "key": "qwen", "name": "Qwen3.8 27B Aggressive", "quant": "Q4_K_P",
        "source": "https://huggingface.co/HauhauCS/Qwen3.8-27B-Uncensored-HauhauCS-Aggressive-MTP-GGUF/blob/main/Qwen3.8-27B-Uncensored-HauhauCS-Aggressive-Q4_K_P.gguf",
        "gguf": "Qwen3.8-27B-Uncensored-HauhauCS-Aggressive-Q4_K_P.gguf", "revision": "main",
        "size_bytes": 17923393664, "sha256": "ba36dc3c2b2ff5e0aa5d71092a8894546996a6a119ae391803dda07cdc08516d", "min_vram_gb": 24,
        "model_id": "qwen3.8-27b-aggressive",
        "description": "Modelo denso com boa disciplina de ferramentas; preset denso otimizado para coding e tool use.",
        "context": 16384, "output": 8192, "parallel": 4, "backend": "official-layer", "mtp": "", "supports_mtp": False,
    },
}

def public_catalog() -> list[dict]:
    return [dict(v) for v in MODELS.values()]
