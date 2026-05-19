from pathlib import Path

import pandas as pd


def find_project_root(start: Path) -> Path:
    """Find the project root from either the repo root or notebooks folder."""
    start = start.resolve()
    for candidate in [start, *start.parents]:
        if (candidate / "data" / "raw").exists():
            return candidate
    raise FileNotFoundError("Could not find data/raw from the current path.")


def print_section(title: str) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def inspect_excel_file(path: Path) -> None:
    print_section(f"Excel file: {path.name}")

    if path.stat().st_size == 0:
        print("WARNING: File is empty. Skipping workbook read.")
        return

    try:
        workbook = pd.ExcelFile(path)
    except Exception as exc:
        print(f"WARNING: Could not read workbook: {exc}")
        return

    print("Sheet names:")
    for sheet_name in workbook.sheet_names:
        print(f"- {sheet_name}")

    for sheet_name in workbook.sheet_names:
        print_section(f"{path.name} | Sheet: {sheet_name}")

        try:
            sheet = pd.read_excel(workbook, sheet_name=sheet_name)
        except Exception as exc:
            print(f"WARNING: Could not read sheet '{sheet_name}': {exc}")
            continue

        print("Column names:")
        if len(sheet.columns) == 0:
            print("(no columns found)")
        else:
            for column in sheet.columns:
                print(f"- {column}")

        print("\nFirst 20 rows:")
        if sheet.empty:
            print("(sheet is empty)")
        else:
            print(sheet.head(20).to_string(index=False))


def main() -> None:
    project_root = find_project_root(Path.cwd())
    raw_dir = project_root / "data" / "raw"

    print_section(f"Files in {raw_dir}")
    all_files = sorted(path for path in raw_dir.rglob("*") if path.is_file())

    if not all_files:
        print("No files found in data/raw.")
        return

    for path in all_files:
        relative_path = path.relative_to(raw_dir)
        print(f"- {relative_path} ({path.stat().st_size:,} bytes)")

    excel_files = [
        path
        for path in all_files
        if path.suffix.lower() in {".xls", ".xlsx", ".xlsm", ".xlsb"}
    ]

    if not excel_files:
        print("\nNo Excel files found in data/raw.")
        return

    for path in excel_files:
        inspect_excel_file(path)


if __name__ == "__main__":
    main()
