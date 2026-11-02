"""Export the FastAPI OpenAPI document without starting an HTTP server."""

import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.main import app  # noqa: E402


def main() -> None:
    output = BACKEND_ROOT / "openapi.json"
    output.write_text(json.dumps(app.openapi(), indent=2) + "\n", encoding="utf-8")
    print(f"OpenAPI exportado a {output}")


if __name__ == "__main__":
    main()
