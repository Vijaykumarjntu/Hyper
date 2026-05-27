"""
notion.py — Fetch a Notion page and extract clean plain text from all blocks.
"""

import os
from notion_client import AsyncClient
from dotenv import load_dotenv

load_dotenv()

_notion = AsyncClient(auth=os.getenv("NOTION_API_KEY"))


def _rich_text_to_str(rich_text: list) -> str:
    """Flatten a rich_text array into a plain string."""
    return "".join(rt.get("plain_text", "") for rt in rich_text)


def _block_to_text(block: dict) -> str:
    """Convert a single block to its text representation."""
    btype = block.get("type", "")
    data = block.get(btype, {})

    # Most content blocks carry a rich_text array
    rich = data.get("rich_text", [])
    text = _rich_text_to_str(rich)

    # Special handling
    if btype == "code":
        lang = data.get("language", "")
        return f"```{lang}\n{text}\n```"
    if btype in ("bulleted_list_item", "numbered_list_item"):
        return f"• {text}"
    if btype == "to_do":
        checked = "✓" if data.get("checked") else "☐"
        return f"{checked} {text}"
    if btype == "divider":
        return "---"
    if btype == "equation":
        return data.get("expression", "")
    if btype == "table_row":
        cells = [_rich_text_to_str(cell) for cell in data.get("cells", [])]
        return " | ".join(cells)

    return text  # heading_1/2/3, paragraph, toggle, quote, callout …


async def _fetch_all_blocks(block_id: str) -> list[str]:
    """Recursively fetch all block text, depth-first."""
    lines: list[str] = []
    cursor = None

    while True:
        resp = await _notion.blocks.children.list(
            block_id=block_id,
            start_cursor=cursor,
            page_size=100,
        )
        for block in resp.get("results", []):
            line = _block_to_text(block)
            if line.strip():
                lines.append(line)
            # Recurse into children (toggles, synced blocks, columns …)
            if block.get("has_children"):
                child_lines = await _fetch_all_blocks(block["id"])
                lines.extend(child_lines)

        if not resp.get("has_more"):
            break
        cursor = resp.get("next_cursor")

    return lines


async def extract_page_text(page_id: str) -> dict:
    """
    Returns:
        {
            "page_id": str,
            "title": str,
            "url": str,
            "last_edited": str,
            "text": str,          # full plain-text dump
        }
    """
    page = await _notion.pages.retrieve(page_id=page_id)

    # ── Title ─────────────────────────────────────────────────────────────────
    title = ""
    props = page.get("properties", {})
    for prop in props.values():
        if prop.get("type") == "title":
            title = _rich_text_to_str(prop["title"])
            break

    # ── Body text ─────────────────────────────────────────────────────────────
    lines = await _fetch_all_blocks(page_id)
    full_text = f"{title}\n\n" + "\n".join(lines) if title else "\n".join(lines)

    return {
        "page_id": page_id,
        "title": title,
        "url": page.get("url", ""),
        "last_edited": page.get("last_edited_time", ""),
        "text": full_text,
    }
