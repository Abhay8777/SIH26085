import csv
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

OUTPUT_FILE = PROCESSED_DIR / "rainfall_normalized.csv"

REQUIRED_COLUMNS = {"timestamp", "station", "rainfall_mm"}


def normalize_rainfall() -> None:
    csv_files = sorted(RAW_DIR.glob("*.csv"))

    if not csv_files:
        print("No rainfall CSV files found in data/raw.")
        print("Normalization skipped.")
        return

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    rows = []

    for file_path in csv_files:
        with file_path.open(
            "r",
            encoding="utf-8-sig",
            newline=""
        ) as file:
            reader = csv.DictReader(file)

            if not reader.fieldnames:
                print(f"Skipped {file_path.name}: missing header.")
                continue

            missing = REQUIRED_COLUMNS - set(reader.fieldnames)

            if missing:
                print(
                    f"Skipped {file_path.name}: "
                    f"missing columns {sorted(missing)}."
                )
                continue

            for row_number, row in enumerate(reader, start=2):
                try:
                    rainfall_mm = float(row["rainfall_mm"])

                    if rainfall_mm < 0:
                        raise ValueError("rainfall cannot be negative")

                    rows.append(
                        {
                            "timestamp": row["timestamp"].strip(),
                            "station": row["station"].strip(),
                            "rainfall_mm": rainfall_mm,
                        }
                    )

                except (TypeError, ValueError) as exc:
                    print(
                        f"Skipped {file_path.name} row {row_number}: {exc}"
                    )

    if not rows:
        print("No valid rainfall records found.")
        print("Normalization skipped.")
        return

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8",
        newline=""
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "timestamp",
                "station",
                "rainfall_mm",
            ],
        )

        writer.writeheader()
        writer.writerows(rows)

    print(f"Normalized {len(rows)} rainfall records.")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    normalize_rainfall()