#!/usr/bin/env python3
import argparse
import datetime as dt
import re
from pathlib import Path


def slugify(value):
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = value.strip("-")
    return value or "ticket"


def yaml_scalar(value):
    escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def yaml_list(values):
    if not values:
        return "[]"
    return "[" + ", ".join(yaml_scalar(v) for v in values) + "]"


def next_path(directory, title):
    date = dt.date.today().isoformat()
    slug = slugify(title)
    base = f"{date}-{slug}"
    path = directory / f"{base}.md"
    idx = 2
    while path.exists():
        path = directory / f"{base}-{idx}.md"
        idx += 1
    return path


def read_body(path):
    if not path:
        return None
    return Path(path).read_text().strip()


def main():
    parser = argparse.ArgumentParser(description="Create an Obsidian Dataview/Tasks ticket file")
    parser.add_argument("--dir", required=True, help="Directory where the ticket should be created")
    parser.add_argument("--title", required=True)
    parser.add_argument("--status", default="ready")
    parser.add_argument("--priority", default="medium")
    parser.add_argument("--assignee", default="")
    parser.add_argument("--story", default="")
    parser.add_argument("--tag", action="append", default=[])
    parser.add_argument("--body", help="Path to Markdown body content")
    args = parser.parse_args()

    directory = Path(args.dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = next_path(directory, args.title)
    today = dt.date.today().isoformat()

    tags = args.tag or ["task"]
    lines = [
        "---",
        "ticket: true",
        f"title: {yaml_scalar(args.title)}",
        f"status: {yaml_scalar(args.status)}",
        f"assignee: {yaml_scalar(args.assignee)}",
        f"priority: {yaml_scalar(args.priority)}",
        f"story: {yaml_scalar(args.story)}",
        f"updated: {today}",
        f"tags: {yaml_list(tags)}",
        "---",
        "",
    ]

    body = read_body(args.body)
    if body:
        lines.append(body)
        lines.append("")
    else:
        lines.extend(
            [
                f"# {args.title}",
                "",
                "## Goal",
                "",
                "## Acceptance Criteria",
                "",
                "- [ ] Define acceptance criteria #task",
                "",
                "## Work Log",
                "",
            ]
        )

    path.write_text("\n".join(lines))
    print(path)


if __name__ == "__main__":
    main()
