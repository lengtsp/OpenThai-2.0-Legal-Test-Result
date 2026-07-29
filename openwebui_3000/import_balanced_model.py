#!/usr/bin/env python3
"""Import and refresh the validated OpenThai Legal 12k model preset."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import requests

from import_ncb_knowledge import api, signin


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:3000")
    parser.add_argument(
        "--preset",
        type=Path,
        default=Path(__file__).with_name("openthai_audit_balanced_model.json"),
    )
    args = parser.parse_args()
    base_url = args.base_url.rstrip("/")
    model = json.loads(args.preset.read_text(encoding="utf-8"))
    session = requests.Session()
    signin(session, base_url)
    api(
        session,
        "POST",
        f"{base_url}/api/v1/models/import",
        json={"models": [model]},
    )
    models = api(session, "GET", f"{base_url}/api/models").get("data", [])
    installed = next((item for item in models if item.get("id") == model["id"]), None)
    if not installed:
        raise RuntimeError(f"Imported model is not discoverable: {model['id']}")
    print(f"Installed: {model['name']} ({model['id']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
