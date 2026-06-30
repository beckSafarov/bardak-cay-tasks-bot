import json
from pathlib import Path


def get_trunc_text(text: str, max_length: int = 100) -> str:
    """Truncate text to the given number of characters, adding ellipsis if necessary."""
    if len(text) > max_length:
        return text[: max_length - 2] + ".."
    return text


def get_labels():
    # 1. Get the absolute path of the directory this current file (index.py) is in
    current_dir = Path(__file__).resolve().parent

    # 2. Navigate up one level to the project root, then down into 'data/labels.json'
    json_path = current_dir.parent / "data" / "labels.json"

    # 3. Open and load the JSON data
    with open(json_path, "r", encoding="utf-8") as file:
        labels = json.load(file)

    return labels
