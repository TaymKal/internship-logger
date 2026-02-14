import os
from datetime import datetime, timezone
from typing import Tuple

import requests


from app.core.config import NOTION_API_KEY, NOTION_DATABASE_ID, NOTION_STATUS_DEFAULT


class NotionError(Exception):
    """Raised when Notion API operations fail."""


def create_notion_page(title: str, body: str) -> Tuple[str, str]:
    """
    Create a new page in the configured Notion database.

    Database is expected to have:
    - Name (title)
    - Date (date)
    - Status (select or status)
    """
    if not NOTION_API_KEY:
        raise NotionError("NOTION_API_KEY is not set.")
    if not NOTION_DATABASE_ID:
        raise NotionError("NOTION_DATABASE_ID is not set.")

    now = datetime.now(timezone.utc)
    full_title = title

    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }

    payload = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "Name": {
                "title": [
                    {
                        "text": {
                            "content": full_title,
                        }
                    }
                ]
            },
            "Date": {
                "date": {
                    "start": now.isoformat(),
                }
            },
            "Status": {
                # Works for either status or select properties, depending on your DB.
                "status": {"name": NOTION_STATUS_DEFAULT},
            },
        },
        "children": [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": body},
                        }
                    ]
                },
            }
        ],
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
    except requests.RequestException as exc:
        raise NotionError(f"Failed to reach Notion API: {exc}") from exc

    if resp.status_code != 200:
        raise NotionError(
            f"Notion API error {resp.status_code}: {resp.text[:500]}"
        )

    data = resp.json()
    page_id = data.get("id", "")
    page_url = data.get("url", "")
    return page_id, page_url

