import csv
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"

REQUIRED_COLUMNS = {
    "timestamp",
    "station",
    "rainfall_mm",
}


def validate_rainfall_file(file_path: Path) -> None:
    with file_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        if reader.fieldnames is None:
            raise ValueError("CSV file has no header.")

        columns = {column.strip() for column in reader.fieldnames}

        missing = REQUIRED_COLUMNS - columns

        if missing:
            raise ValueError(
                f"Missing required columns: {sorted(missing)}"
            )

        row_count = sum(1 for _ in reader)

    print(f"Validated: {file_path.name}")
    print(f"Rows: {row_count}")
    print("Required columns: OK")


def main() -> None:
    csv_files = sorted(RAW_DIR.glob("*.csv"))

    if not csv_files:
        print("No rainfall CSV files found in data/raw.")
        print("Waiting for an approved rainfall dataset.")
        return

    for file_path in csv_files:
        validate_rainfall_file(file_path)


if __name__ == "__main__":
    main()