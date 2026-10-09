
import json
import os
import pandas as pd


def load_settings(settings_file="settings.json"):
    """Load settings from the JSON configuration file."""
    if not os.path.exists(settings_file):
        raise FileNotFoundError(
            f"Configuration file '{settings_file}' not found."
        )

    with open(settings_file, "r", encoding="utf-8") as file:
        return json.load(file)


def build_folder_name(row):
    """Build the simulation folder name using spreadsheet data.

    Calculate normalized molality fractions x1 and x2 from b1 and b2.
    The original spreadsheet values remain unchanged.
    """
    s1 = str(row["Salt 1"]).strip()
    s2 = str(row["Salt 2"]).strip()

    # Read the original values from the spreadsheet
    b_total = str(row["b_total (mol*kg-1)"]).strip()
    b1 = float(row["b1 (mol*kg-1)"])
    b2 = float(row["b2 (mol*kg-1)"])
    temp = str(row["T (K)"]).strip()
    pres = str(row["P (MPa)"]).strip()

    # Calculate normalized molality fractions
    total_molality = b1 + b2

    if total_molality <= 0:
        raise ValueError(
            "The sum of b1 and b2 must be greater than zero."
        )

    x1 = round(b1 / total_molality, 2)
    x2 = round(1.00 - x1, 2)

    # Format fractions with exactly two decimal places
    x1_text = f"{x1:.2f}"
    x2_text = f"{x2:.2f}"

    # Build the folder name
    folder_name = (
        f"S1_{s1}_S2_{s2}_M_{b_total}"
        f"_X1_{x1_text}_X2_{x2_text}"
        f"_T_{temp}_P_{pres}"
    )

    return folder_name


def main():
    # 1. Load settings from settings.json
    settings = load_settings("settings.json")

    output_path = settings["output_path"]
    solubility_file = settings["solubility_file"]
    simulation_folder = settings["simulation_folder"]

    # Build the complete input file path
    full_excel_path = os.path.join(output_path, solubility_file)

    if not os.path.exists(full_excel_path):
        raise FileNotFoundError(
            f"Spreadsheet not found at: {full_excel_path}"
        )

    # 2. Read the spreadsheet
    print(f"Reading data from: {full_excel_path}...")
    df = pd.read_excel(full_excel_path, dtype=str)

    # 3. Ensure the destination directory exists
    os.makedirs(simulation_folder, exist_ok=True)
    print(f"Output directory: {simulation_folder}\n")

    # 4. Create one folder for each spreadsheet row
    created_count = 0

    for idx, row in df.iterrows():
        try:
            folder_name = build_folder_name(row)
            folder_path = os.path.join(
                simulation_folder,
                folder_name,
            )

            os.makedirs(folder_path, exist_ok=True)
            created_count += 1

            print(f"[{created_count}] Folder generated: {folder_name}")

        except Exception as error:
            print(
                f"Error processing spreadsheet row {idx + 2}: {error}"
            )

    print(
        f"\nProcessing completed! Total of {created_count} folders "
        f"created in: {simulation_folder}"
    )


if __name__ == "__main__":
    main()