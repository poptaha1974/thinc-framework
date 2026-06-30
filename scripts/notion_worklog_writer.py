#!/usr/bin/env python3
"""Write a daily work log entry to Notion safely."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any


DEFAULT_ITEMS = [
    "Configured GitHub agent secrets for integrations",
    "Added NOTION_TOKEN, META_ACCESS_TOKEN, and SLACK_BOT_TOKEN to repository secrets",
    "Created and configured THINC Agent in Slack",
    "Added Slack bot scopes and installed the app to the workspace",
    "Ran a GitHub Copilot cloud agent task successfully",
    "Created and reviewed a PR for a Slack connectivity test script",
]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write today's completed work to Notion using env credentials."
    )
    parser.add_argument(
        "--item",
        action="append",
        default=[],
        help="Completed-work item. Repeat for multiple items.",
    )
    parser.add_argument(
        "--title-prefix",
        default="Daily Work Log",
        help="Title prefix used for database entries.",
    )
    return parser.parse_args()


def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _notion_request(
    token: str,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        url=f"https://api.notion.com/v1{path}",
        data=data,
        method=method,
        headers={
            "Authorization": "Bearer " + token,
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            body = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            data = json.loads(body)
            code = data.get("code") or "http_error"
            message = data.get("message") or str(exc)
        except json.JSONDecodeError:
            code = "http_error"
            message = str(exc)
        raise RuntimeError(f"Notion API error [{code}]: {message}") from None
    except Exception as exc:
        raise RuntimeError(f"Request failed: {type(exc).__name__}") from None

    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Invalid JSON response from Notion API") from exc


def _worklog_blocks(log_date: str, items: list[str]) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = [
        {
            "object": "block",
            "type": "heading_2",
            "heading_2": {"rich_text": [{"type": "text", "text": {"content": log_date}}]},
        }
    ]
    for item in items:
        blocks.append(
            {
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": item}}]
                },
            }
        )
    return blocks


def _detect_database_title_property(token: str, database_id: str) -> str:
    database = _notion_request(token, "GET", f"/databases/{database_id}")
    for name, details in database.get("properties", {}).items():
        if details.get("type") == "title":
            return name
    raise RuntimeError("Could not detect the title property for the Notion database.")


def _append_to_page(token: str, page_id: str, blocks: list[dict[str, Any]]) -> str:
    payload = {"children": blocks}
    response = _notion_request(token, "PATCH", f"/blocks/{page_id}/children", payload)
    if not response.get("results"):
        raise RuntimeError("Notion append did not return created blocks.")
    return page_id


def _create_database_page(
    token: str,
    database_id: str,
    title_prefix: str,
    log_date: str,
    blocks: list[dict[str, Any]],
) -> str:
    title_property = _detect_database_title_property(token, database_id)
    payload = {
        "parent": {"database_id": database_id},
        "properties": {
            title_property: {
                "title": [{"type": "text", "text": {"content": f"{title_prefix} - {log_date}"}}]
            }
        },
        "children": blocks,
    }
    response = _notion_request(token, "POST", "/pages", payload)
    page_id = response.get("id")
    if not page_id:
        raise RuntimeError("Notion page creation did not return a page id.")
    return page_id


def main() -> int:
    args = _parse_args()
    token = _require_env("NOTION_TOKEN")
    notion_page_id = os.getenv("NOTION_PAGE_ID", "").strip()
    notion_database_id = os.getenv("NOTION_DATABASE_ID", "").strip()

    if not notion_page_id and not notion_database_id:
        raise RuntimeError(
            "Set NOTION_PAGE_ID or NOTION_DATABASE_ID (one is required)."
        )

    log_date = dt.date.today().isoformat()
    items = [value.strip() for value in args.item if value.strip()] or DEFAULT_ITEMS
    blocks = _worklog_blocks(log_date, items)

    if notion_database_id:
        page_id = _create_database_page(
            token=token,
            database_id=notion_database_id,
            title_prefix=args.title_prefix,
            log_date=log_date,
            blocks=blocks,
        )
        target = "database"
    else:
        page_id = _append_to_page(token=token, page_id=notion_page_id, blocks=blocks)
        target = "page"

    print(
        json.dumps(
            {"ok": True, "target": target, "page_id": page_id, "items_logged": len(items)}
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as error:
        print(json.dumps({"ok": False, "error": str(error)}))
        raise SystemExit(1)
