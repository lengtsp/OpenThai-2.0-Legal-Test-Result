#!/usr/bin/env python3
"""Import clean section-level NCB Act text files into a local Open WebUI KB.

The script targets the no-auth, loopback-only lab configuration in this
directory. It authenticates through Open WebUI's normal session endpoint,
processes every uploaded Markdown file synchronously, and then performs one
batch ingest into the Knowledge Base collection.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import requests


DEFAULT_NAME = "พ.ร.บ. ข้อมูลเครดิต — iApp structural v2"
DEFAULT_DESCRIPTION = (
    "iApp-compatible structural chunks: หนึ่งมาตราต่อไฟล์ใน <law> scaffold "
    "พร้อม page-anchored provenance สำหรับ NCB, compliance และ internal audit"
)


def api(session: requests.Session, method: str, url: str, **kwargs):
    response = session.request(method, url, timeout=1_800, **kwargs)
    if not response.ok:
        raise RuntimeError(
            f"{method} {url} failed: HTTP {response.status_code}: "
            f"{response.text[:1_000]}"
        )
    if not response.content:
        return None
    return response.json()


def signin(session: requests.Session, base_url: str) -> dict:
    result = api(
        session,
        "POST",
        f"{base_url}/api/v1/auths/signin",
        json={"email": "admin@localhost", "password": "admin"},
    )
    token = result.get("token")
    if token:
        session.headers["Authorization"] = f"Bearer {token}"
    return result


def find_or_create_knowledge(
    session: requests.Session,
    base_url: str,
    name: str,
    description: str,
) -> dict:
    page = 1
    seen = 0
    while True:
        result = api(
            session,
            "GET",
            f"{base_url}/api/v1/knowledge/",
            params={"page": page},
        )
        items = result.get("items", [])
        for item in items:
            if item.get("name") == name:
                return item
        seen += len(items)
        if not items or seen >= result.get("total", 0):
            break
        page += 1

    return api(
        session,
        "POST",
        f"{base_url}/api/v1/knowledge/create",
        json={"name": name, "description": description, "access_grants": []},
    )


def existing_filenames(session: requests.Session, base_url: str, kb_id: str) -> set[str]:
    names: set[str] = set()
    page = 1
    seen = 0
    while True:
        result = api(
            session,
            "GET",
            f"{base_url}/api/v1/knowledge/{kb_id}/files",
            params={"page": page},
        )
        items = result.get("items", [])
        names.update(item.get("filename") or item.get("name") for item in items)
        seen += len(items)
        if not items or seen >= result.get("total", 0):
            break
        page += 1
    names.discard(None)
    return names


def reusable_files(session: requests.Session, base_url: str) -> dict[str, dict]:
    """Return the newest already-processed upload for each filename."""
    result: dict[str, dict] = {}
    page = 1
    seen = 0
    while True:
        response = api(
            session,
            "GET",
            f"{base_url}/api/v1/files/",
            params={"page": page, "content": "false"},
        )
        items = response.get("items", [])
        for item in items:
            if (item.get("data") or {}).get("status") == "completed":
                result.setdefault(item["filename"], item)
        seen += len(items)
        if not items or seen >= response.get("total", 0):
            break
        page += 1
    return result


def upload_processed(
    session: requests.Session,
    base_url: str,
    files: list[Path],
    metadata_by_name: dict[str, dict],
) -> list[dict]:
    uploaded: list[dict] = []
    for index, path in enumerate(files, start=1):
        metadata = {
            "source": "Credit Info Act update 1-6.pdf",
            "structural_chunk": True,
            "original_filename": path.name,
            **metadata_by_name.get(path.name, {}),
        }
        for attempt in range(2):
            try:
                with path.open("rb") as handle:
                    result = api(
                        session,
                        "POST",
                        f"{base_url}/api/v1/files/",
                        params={"process": "true", "process_in_background": "false"},
                        files={"file": (path.name, handle, "text/plain")},
                        data={"metadata": json.dumps(metadata, ensure_ascii=False)},
                    )
                break
            except RuntimeError as exc:
                if attempt == 0 and "HTTP 401" in str(exc):
                    signin(session, base_url)
                    print("session refreshed after HTTP 401", flush=True)
                    continue
                raise
        uploaded.append(result)
        print(f"uploaded {index:02d}/{len(files)} {path.name}", flush=True)
    return uploaded


def batch_add(
    session: requests.Session,
    base_url: str,
    kb_id: str,
    uploaded: list[dict],
) -> dict:
    payload = [{"file_id": item["id"]} for item in uploaded]
    started = time.perf_counter()
    result = api(
        session,
        "POST",
        f"{base_url}/api/v1/knowledge/{kb_id}/files/batch/add",
        json=payload,
    )
    print(f"batch indexing completed in {time.perf_counter() - started:.2f}s")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:3000")
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("data/credit_info_act/openwebui_knowledge_v2"),
    )
    parser.add_argument("--name", default=DEFAULT_NAME)
    parser.add_argument("--description", default=DEFAULT_DESCRIPTION)
    args = parser.parse_args()

    files = sorted(args.input_dir.glob("credit-info-act-section-*.txt"))
    if not files:
        parser.error(f"no section text files found under {args.input_dir}")
    manifest_path = args.input_dir / "manifest.json"
    if not manifest_path.is_file():
        parser.error(f"missing manifest: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    metadata_by_name = {
        item["filename"]: {
            "law_name": item["law_name"],
            "section": item["section"],
            "section_heading": item["section_heading"],
            "structural_topic": item["topic"],
            "page_start": item["page_start"],
            "page_end": item["page_end"],
            "source_url": item["source_url"],
            "content_sha256": item["content_sha256"],
        }
        for item in manifest["files"]
    }

    session = requests.Session()
    user = signin(session, args.base_url.rstrip("/"))
    print(f"signed in as {user.get('email')} ({user.get('role')})")

    kb = find_or_create_knowledge(
        session,
        args.base_url.rstrip("/"),
        args.name,
        args.description,
    )
    print(f"knowledge id={kb['id']} name={kb['name']}")

    present = existing_filenames(
        session,
        args.base_url.rstrip("/"),
        kb["id"],
    )
    missing = [path for path in files if path.name not in present]
    print(f"files total={len(files)} present={len(present)} missing={len(missing)}")

    if missing:
        reusable = reusable_files(session, args.base_url.rstrip("/"))
        resumed = [reusable[path.name] for path in missing if path.name in reusable]
        to_upload = [path for path in missing if path.name not in reusable]
        print(f"reusable={len(resumed)} new_uploads={len(to_upload)}")
        uploaded = resumed + upload_processed(
            session,
            args.base_url.rstrip("/"),
            to_upload,
            metadata_by_name,
        )
        batch_add(
            session,
            args.base_url.rstrip("/"),
            kb["id"],
            uploaded,
        )

    final = api(
        session,
        "GET",
        f"{args.base_url.rstrip('/')}/api/v1/knowledge/{kb['id']}/files",
        params={"page": 1},
    )
    print(
        json.dumps(
            {
                "knowledge_id": kb["id"],
                "knowledge_name": kb["name"],
                "file_count": final.get("total"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (requests.RequestException, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
