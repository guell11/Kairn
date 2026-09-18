"""Generate a ready-to-import notebook without opening the desktop app."""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from models_catalog import MODELS
from runtime_builder import RuntimeBuilder
from state_store import AppState


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", choices=MODELS, default="gemopus")
    parser.add_argument("--output", type=Path, default=ROOT / "notebooks" / "kaggle-studio.ipynb")
    parser.add_argument("--tunnel-url", default="", help="Hostname HTTPS de túnel Cloudflare nomeado")
    parser.add_argument("--language", choices=("pt-BR", "en"), default="pt-BR", help="Notebook instructions language")
    args = parser.parse_args()
    model = MODELS[args.model]
    state = AppState(model=args.model, language=args.language,
                     backend=model.get("required_backend", model["backend"]),
                     context=model["context"], output=model["output"],
                     parallel=min(2, model.get("parallel", 2)),
                     tunnel_mode="named" if args.tunnel_url else "quick", tunnel_url=args.tunnel_url)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(RuntimeBuilder(ROOT).notebook(MODELS[args.model], state), "utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
