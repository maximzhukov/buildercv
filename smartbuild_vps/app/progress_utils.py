import re


def parse_volume(value):
    normalized_value = re.sub(r"\s+", "", str(value)).replace(",", ".")
    match = re.search(r"[-+]?\d+(?:\.\d+)?", normalized_value)
    if not match:
        return 0.0
    return max(float(match.group()), 0.0)


def cumulative_progress(task_history, total_volume):
    if total_volume <= 0:
        return 0

    completed_volume = 0.0
    for entry in task_history.values():
        if "fact_vol" in entry:
            completed_volume += max(float(entry["fact_vol"]), 0.0)
        else:
            completed_volume += total_volume * max(float(entry.get("progress", 0)), 0.0) / 100

    return min(int(completed_volume / total_volume * 100), 100)


def latest_daily_progress(task_history):
    if not task_history:
        return 0
    latest_entry = task_history[max(task_history)]
    return max(float(latest_entry.get("progress", 0)), 0.0)