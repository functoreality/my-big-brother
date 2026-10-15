"""Common automation planning and completion, called by the executing Agent."""

import json
from datetime import date, datetime, timedelta
from pathlib import Path

from . import config, runner


def invocation_dates(settings, review_date, max_days):
    if review_date:
        date.fromisoformat(review_date)
        return [review_date]
    if type(max_days) is not int or not 1 <= max_days <= 31:
        raise ValueError("max_days must be from 1 to 31")
    latest = date.fromisoformat(runner.latest_closed_date(settings["day_start_hour"]))
    return [(latest - timedelta(days=offset)).isoformat() for offset in reversed(range(max_days))]


def launch_context(paths, launch_dir):
    directory = Path(launch_dir)
    if not directory.is_absolute():
        raise ValueError("launch-dir must be absolute")
    context = runner.read_object(directory / "context.json")
    if Path(context["config"]).resolve() != (paths.config / "config.json").resolve():
        raise ValueError("Automation context selects a different configuration")
    return directory, context


def begin(paths, settings, launch_dir, dates=None):
    """Plan this invocation after the Agent has read its task and local policy."""
    directory, context = launch_context(paths, launch_dir)
    if not context.get("date") and (context.get("snapshot_end") or context.get("allow_empty")):
        raise ValueError("snapshot-end and allow-empty require an explicit date")
    if context.get("snapshot_end"):
        runner.snapshot_window(context["date"], settings["day_start_hour"],
                               datetime.fromisoformat(context["snapshot_end"]))
    if dates is None:
        dates = invocation_dates(settings, context.get("date"), context.get("max_days"))
    else:
        for value in dates:
            if date.fromisoformat(value).isoformat() != value:
                raise ValueError("Automation dates must use YYYY-MM-DD")
        if dates != sorted(set(dates)):
            raise ValueError("Automation dates must be unique and oldest first")
    value = {**context, "dates": dates, "tickets_path": str(directory / "tickets.json"),
             "receipt_path": str(directory / "completion.json"),
             "receipt_example": {"invocation_id": context["invocation_id"],
                                 "results": [{"date": item, "status": "completed", "run_dir": "<run_dir>"}
                                             for item in dates]}}
    config.write_json(directory / "automation-context.json", value)
    return value


def validate_receipt(paths, settings, launch_dir, context):
    receipt = runner.read_object(launch_dir / "completion.json")
    tickets = json.loads((launch_dir / "tickets.json").read_text(encoding="utf-8"))
    results = receipt.get("results")
    if receipt.get("invocation_id") != context["invocation_id"]:
        raise ValueError("Automation receipt invocation mismatch")
    if not isinstance(tickets, list) or not isinstance(results, list):
        raise ValueError("Automation requires ticket and result arrays")
    expected = context["dates"]
    if (len(tickets) != len(expected) or len(results) != len(expected)
        or not all(isinstance(item, dict) for item in tickets + results)
        or [item.get("date") for item in tickets] != expected
        or [item.get("date") for item in results] != expected):
        raise ValueError("Automation receipt must cover exactly the requested dates, oldest first")
    for ticket, result in zip(tickets, results):
        review_date = result["date"]
        status = result.get("status")
        run_dir = result.get("run_dir")
        if status == "already-completed":
            if (ticket.get("status") != status or not runner.completed(paths, settings, review_date)
                or run_dir != runner.day_entry(paths, review_date).get("run_dir")):
                raise ValueError("Unverified already-completed automation result")
        elif status == "discarded":
            record = paths.layout.record(review_date)
            if (ticket.get("status") != status or run_dir is not None
                    or not record or record["disposition"] != "discarded"):
                raise ValueError("Unverified discarded automation result")
        elif status == "completed":
            entry = runner.day_entry(paths, review_date)
            if (ticket.get("status") not in {"prepared", "actions-pending", "completed"}
                or ticket.get("run_dir") != run_dir or entry.get("run_dir") != run_dir
                or entry.get("status") != "completed"):
                raise ValueError("Automation result is not a completed prepared review")
            review = runner.read_object(Path(run_dir) / "context.json")
            selected = config.load_profile(settings)
            expected_outputs = [item["final"] for item in runner.output_layout(
                settings, review_date, paths.state, selected)]
            if (review.get("date") != review_date or review.get("run_id") != entry.get("run_id")
                or entry.get("profile_digest") != (selected["digest"] if selected else None)
                or entry.get("review_configuration") != runner.review_configuration(paths, settings)
                or entry.get("results_root") != settings["results_root"]
                or entry.get("outputs") != expected_outputs
                or entry.get("window") != review.get("window")
                or not all(Path(name).is_file() for name in expected_outputs)):
                raise ValueError("Automation completion no longer matches this configuration")
            cutoff = context.get("snapshot_end")
            if cutoff is not None:
                requested = runner.snapshot_window(review_date, settings["day_start_hour"],
                                                    datetime.fromisoformat(cutoff))[1]
                if datetime.fromisoformat(entry["window"]["end"]) != requested:
                    raise ValueError("Automation completion snapshot mismatch")
            elif context["date"] is None and not entry.get("closed_day"):
                raise ValueError("Automation requires a closed day without an explicit snapshot")
        elif status == "empty":
            if ticket.get("status") != "empty" or ticket.get("run_dir") != run_dir or context["allow_empty"]:
                raise ValueError("Unverified empty automation result")
            directory = Path(run_dir).resolve()
            paths.layout.check_run(directory)
            manifest = runner.read_object(directory / "manifest.json")
            review = runner.read_object(directory / "context.json")
            enabled = {name for name, spec in settings["sources"].items() if spec.get("enabled", True)}
            if (manifest["window"]["date"] != review_date
                or set(manifest["sources"]) != enabled
                or review.get("review_configuration") != runner.review_configuration(paths, settings)
                or review.get("run_id") != directory.name
                or manifest.get("run_id") != directory.name
                or any(item["entries"] or (item["required"] and item["status"] == "unavailable")
                       for item in manifest["sources"].values())):
                raise ValueError("Empty result has evidence or blocked required input")
        else:
            raise ValueError(f"Automation did not complete {review_date}: {status}")
    return results


def complete(paths, settings, launch_dir):
    """Verify the current Agent's results without dispatching another Agent."""
    directory, request = launch_context(paths, launch_dir)
    context = runner.read_object(directory / "automation-context.json")
    if any(context.get(key) != value for key, value in request.items()):
        raise ValueError("Automation plan no longer matches its startup request")
    results = validate_receipt(paths, settings, directory, context)
    value = {"status": "completed", "invocation_id": context["invocation_id"],
             "launch_dir": str(directory), "results": results}
    config.write_json(directory / "automation-result.json", value)
    return value
