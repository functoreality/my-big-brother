"""Deliver optional local Markdown reminders without overwriting messages."""

import hashlib
import json
import re
import sys
from pathlib import Path


TASK = Path(__file__).resolve().parents[1] / "tasks" / "notifications" / "TASK.md"


def settings(config):
    value = config.get("notifications", {"enabled": False})
    inbox = Path(value.get("inbox") or Path(config["results_root"]) / "inbox")
    return {"enabled": value["enabled"],
            "inbox": str(inbox.resolve() if value["enabled"] else inbox)}


def policy(config):
    selected = settings(config)
    if not selected["enabled"]:
        return None
    fingerprint = hashlib.sha256(TASK.read_bytes() + Path(__file__).read_bytes()).hexdigest()
    return dict(selected, policy_sha256=fingerprint)


def read_object(path):
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Expected a JSON object: " + str(path))
    return value


def messages(action_dir):
    """Validate the complete plan before performing any delivery."""
    action_dir = Path(action_dir).resolve()
    context = read_object(action_dir / "context.json")
    plan = read_object(action_dir / "messages.json")
    if any(plan.get(key) != context[key] for key in ("run_id", "date")):
        raise ValueError("Message plan does not match this run")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", context["date"]):
        raise ValueError("Invalid notification date")
    inbox = Path(context["inbox"])
    if not inbox.is_absolute() or inbox.resolve() != inbox:
        raise ValueError("Inbox path changed since preparation")
    if context["write_paths"] != [context["inbox"]]:
        raise ValueError("Notifications require exactly the selected inbox")
    entries = plan.get("messages")
    if not isinstance(entries, list):
        raise ValueError("messages must be an array")
    seen = set()
    result = []
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"id", "content_file"}:
            raise ValueError("Each message requires id and content_file")
        identity = entry["id"]
        if not isinstance(identity, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,79}", identity):
            raise ValueError("Invalid message id")
        if identity in seen:
            raise ValueError("Duplicate message id")
        seen.add(identity)
        name = entry["content_file"]
        if not isinstance(name, str) or not name:
            raise ValueError("content_file must name a staged Markdown file")
        relative = Path(name)
        source = (action_dir / relative).resolve()
        if relative.is_absolute() or ".." in relative.parts or action_dir not in source.parents:
            raise ValueError("Message draft must stay inside the action directory")
        if source.suffix != ".md" or not source.is_file():
            raise ValueError("Message draft must be a Markdown file")
        content = source.read_bytes()
        if not content.decode("utf-8").strip():
            raise ValueError("Message draft must not be empty")
        target = inbox / (context["date"] + "--" + identity + ".md")
        if target.is_symlink() or (target.exists() and not target.is_file()):
            raise ValueError("Message target must be a regular file: " + str(target))
        if target.exists() and target.read_bytes() != content:
            raise ValueError("Existing message differs. Preserve it: " + str(target))
        result.append((target, content))
    return result


def deliver(action_dir, *, apply=False):
    planned = messages(action_dir)
    for target, content in planned:
        if apply:
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            try:
                with target.open("xb") as handle:
                    target.chmod(0o600)
                    handle.write(content)
            except FileExistsError:
                pass
        if target.is_symlink() or not target.is_file() or target.read_bytes() != content:
            raise ValueError("Message delivery is missing or differs: " + str(target))
    return [str(target) for target, _ in planned]


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in {"apply", "validate"}:
        raise ValueError("Usage: notifications.py apply|validate ACTION_DIRECTORY")
    delivered = deliver(sys.argv[2], apply=sys.argv[1] == "apply")
    print(json.dumps({"status": "completed", "messages": delivered}, ensure_ascii=False))


if __name__ == "__main__":
    main()
