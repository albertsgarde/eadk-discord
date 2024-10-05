import json
import os
from pathlib import Path

if __name__ == "__main__":
    database_path_option: str | None = os.getenv("DATABASE_PATH")
    if database_path_option is None:
        raise ValueError("DATABASE_PATH is not set in environment variables")
    else:
        database_path: Path = Path(database_path_option)

    db_dict = json.loads(database_path.read_text())
    for event in db_dict["history"]:
        event_data = event["event"]
        if "desk_index" in event_data and "date" in event_data:
            event_data["start_date"] = event_data["date"]
            event_data["end_date"] = event_data["date"]
            del event_data["date"]
    database_path.write_text(json.dumps(db_dict))
