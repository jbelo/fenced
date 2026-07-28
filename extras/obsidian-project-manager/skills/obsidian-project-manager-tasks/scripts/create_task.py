#!/usr/bin/env python3
import argparse
import datetime as dt
import re
import secrets
from pathlib import Path


def slugify(value):
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = value.strip("-")
    return value or "task"


def yaml_scalar(value):
    if value is None:
        return '""'
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
    candidate = directory / f"{base}.md"
    idx = 2
    while candidate.exists():
        candidate = directory / f"{base}-{idx}.md"
        idx += 1
    return candidate


def make_id():
    alphabet = "abcdefghijklmnopqrstuvwxyz0123456789"
    return "".join(secrets.choice(alphabet) for _ in range(16))


def read_body(path):
    if not path:
        return ""
    return Path(path).read_text()


def main():
    parser = argparse.ArgumentParser(description="Create an Obsidian Project Manager task file")
    parser.add_argument("--dir", required=True, help="Directory where the task file should be created")
    parser.add_argument("--project-id", required=True, help="Project Manager project id from the pm-project file")
    parser.add_argument("--id", help="Explicit task id; defaults to a generated id")
    parser.add_argument("--title", required=True)
    parser.add_argument("--status", default="todo")
    parser.add_argument("--priority", default="medium")
    parser.add_argument("--progress", type=int, default=0)
    parser.add_argument("--assignee", action="append", default=[])
    parser.add_argument("--tag", action="append", default=[])
    parser.add_argument("--dependency", action="append", default=[])
    parser.add_argument("--due")
    parser.add_argument("--start")
    parser.add_argument("--body", help="Path to Markdown body content")
    args = parser.parse_args()

    directory = Path(args.dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = next_path(directory, args.title)
    task_id = args.id or make_id()

    lines = [
        "---",
        "pm-task: true",
        f"projectId: {yaml_scalar(args.project_id)}",
        "parentId: null",
        f"id: {yaml_scalar(task_id)}",
        f"title: {yaml_scalar(args.title)}",
        'type: "task"',
        f"status: {yaml_scalar(args.status)}",
        f"priority: {yaml_scalar(args.priority)}",
        f"progress: {args.progress}",
        f"assignees: {yaml_list(args.assignee)}",
        f"tags: {yaml_list(args.tag)}",
        "subtaskIds: []",
        f"dependencies: {yaml_list(args.dependency)}",
        f"createdAt: {yaml_scalar(dt.datetime.now(dt.timezone.utc).isoformat().replace('+00:00', 'Z'))}",
        f"updatedAt: {yaml_scalar(dt.datetime.now(dt.timezone.utc).isoformat().replace('+00:00', 'Z'))}",
    ]
    if args.start:
        lines.append(f"start: {yaml_scalar(args.start)}")
    if args.due:
        lines.append(f"due: {yaml_scalar(args.due)}")
    lines.extend(["---", ""])

    body = read_body(args.body).strip()
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
                "## Work Log",
                "",
            ]
        )

    path.write_text("\n".join(lines))
    print(path)


if __name__ == "__main__":
    main()
