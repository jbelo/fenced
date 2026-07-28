#!/usr/bin/env python3
import argparse
from pathlib import Path


DASHBOARD = """# Ticket Dashboard

## Doing

```dataview
TABLE assignee, priority, updated
FROM ""
WHERE ticket = true AND status = "doing"
SORT updated DESC
```

## Blocked

```dataview
TABLE assignee, priority, updated
FROM ""
WHERE ticket = true AND status = "blocked"
SORT updated DESC
```

## Ready

```dataview
TABLE assignee, priority, updated
FROM ""
WHERE ticket = true AND status = "ready"
SORT priority DESC, updated DESC
```

## Review

```dataview
TABLE assignee, priority, updated
FROM ""
WHERE ticket = true AND status = "review"
SORT updated DESC
```

## Open Action Items

```tasks
not done
tag includes #task
group by filename
sort by due
```

## Blocked Action Items

```tasks
not done
tag includes #blocked
group by filename
```

## Done Recently

```tasks
done
done after 7 days ago
group by filename
```
"""


def main():
    parser = argparse.ArgumentParser(description="Write an Obsidian Dataview/Tasks dashboard note")
    parser.add_argument("--path", required=True)
    parser.add_argument("--force", action="store_true", help="Overwrite an existing dashboard")
    args = parser.parse_args()

    path = Path(args.path)
    if path.exists() and not args.force:
        raise SystemExit(f"refusing to overwrite existing file: {path}; pass --force")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(DASHBOARD)
    print(path)


if __name__ == "__main__":
    main()
