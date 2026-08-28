import csv
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

OUTPUT_FILE = PROCESSED_DIR / "rainfall_normalized.csv"


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

            for row in reader:
                rows.append(
                    {
                        "timestamp": row["timestamp"].strip(),
                        "station": row["station"].strip(),
                        "rainfall_mm": row["rainfall_mm"].strip(),
                    }
                )

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