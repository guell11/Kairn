from __future__ import annotations

MODELS = {
    "gemopus": {
        "key": "gemopus", "name": "Gemopus 4 26B A4B", "quant": "Q4_K_M",
        "source": "https://huggingface.co/Jackrong/Gemopus-4-26B-A4B-it-GGUF/blob/main/Gemopus-4-26B-A4B-it-Preview-Q4_K_M.gguf",
        "gguf": "Gemopus-4-26B-A4B-it-Preview-Q4_K_M.gguf", "revision": "main",
        "size_bytes": 16796015488, "sha256": "2037b8c978db6c8b947d10e34a70f410dde6301919c6040624fdda50647f7940", "min_vram_gb": 24,
        "model_id": "gemopus-4-26b-a4b",
        "description": "MoE compacto para coding e tarefas gerais; bom encaixe em T4 ×2.",
        "description_en": "Compact MoE for coding and general tasks; a good fit for dual T4 GPUs.",
        "context": 16384, "output": 8192, "parallel": 4, "backend": "official-layer", "mtp": "", "supports_mtp": False,
    },
    "velum": {
        "key": "velum", "name": "VELUM Coder", "quant": "Q8_0",
        "source": "https://huggingface.co/guell00/VELUM-Coder/blob/main/VELUM-Coder-Q8_0.gguf", "model_id": "velum-coder",
        "gguf": "VELUM-Coder-Q8_0.gguf", "revision": "main",
        "size_bytes": 9527500960, "sha256": "aef1a38a52290b9b2d8ff31fb0b234c4799b221183e038ab77fac8cfcb3ec6f3", "min_vram_gb": 12,
        "description": "Preset focado em código, tool use e ciclos longos de edição.",
        "description_en": "Preset focused on code, tool use, and long editing cycles.",
        "context": 16384, "output": 8192, "parallel": 4, "backend": "official-layer", "mtp": "", "supports_mtp": False,
    },
    "qwen": {
        "key": "qwen", "name": "Qwen3.8 27B Aggressive", "quant": "Q4_K_P",
        "source": "https://huggingface.co/HauhauCS/Qwen3.8-27B-Uncensored-HauhauCS-Aggressive-MTP-GGUF/blob/main/Qwen3.8-27B-Uncensored-HauhauCS-Aggressive-Q4_K_P.gguf",
        "gguf": "Qwen3.8-27B-Uncensored-HauhauCS-Aggressive-Q4_K_P.gguf", "revision": "main",
        "size_bytes": 17923393664, "sha256": "ba36dc3c2b2ff5e0aa5d71092a8894546996a6a119ae391803dda07cdc08516d", "min_vram_gb": 24,
        "model_id": "qwen3.8-27b-aggressive",
        "description": "Modelo denso com boa disciplina de ferramentas; preset denso otimizado para coding e tool use.",
        "description_en": "Dense model with strong tool discipline; optimized for coding and tool use.",
        "context": 16384, "output": 8192, "parallel": 4, "backend": "official-layer", "mtp": "", "supports_mtp": False,
    },
    "bonsai-abliterated": {
        "key": "bonsai-abliterated", "name": "Ternary Bonsai 2 27B Abliterated", "quant": "PTQ1_0",
        "source": "https://huggingface.co/BoldingBuilds/Ternary-Bonsai-2-27B-Abliterated-PTQ1_0-GGUF/blob/95ff0409db450bcd705d1d0c6d8aaeffd58de6cd/Ternary-Bonsai-2-27B-Abliterated-PTQ1_0.gguf",
        "gguf": "Ternary-Bonsai-2-27B-Abliterated-PTQ1_0.gguf", "revision": "95ff0409db450bcd705d1d0c6d8aaeffd58de6cd",
        "size_bytes": 5946648928, "sha256": "94dd53cbad55db5a515f245887c9f0317484502a451ccc0424c7d7788b52900a", "min_vram_gb": 8,
        "model_id": "ternary-bonsai-2-27b-abliterated-ptq1_0",
        "description": "Bonsai 2 ternário PTQ1_0; exige fork PrismML llama.cpp.",
        "description_en": "Ternary Bonsai 2 PTQ1_0; requires the PrismML llama.cpp fork.",
        "context": 16384, "output": 8192, "parallel": 1, "backend": "prism-ml", "required_backend": "prism-ml",
        "backend_repo": "https://github.com/PrismML-Eng/llama.cpp", "backend_ref": "1a07bfa5f4144274c8f1c9963821dd9d9a51854b",
        "mtp": "", "supports_mtp": False,
    },
}

def public_catalog() -> list[dict]:
    return [dict(v) for v in MODELS.values()]
