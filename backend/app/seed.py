"""Seed the demo inbox + memory. Run: ``python -m app.seed``."""
from __future__ import annotations

import json

from app.service import get_service


def main() -> None:
    result = get_service().seed_demo()
    print("Seeded Aide demo data:")
    print(json.dumps(result, indent=2))
    print("\nStart the API with:  uvicorn app.main:app --reload")


if __name__ == "__main__":
    main()
