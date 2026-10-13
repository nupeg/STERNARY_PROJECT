import json
import re
import shutil
from pathlib import Path

import pandas as pd


def load_settings(settings_file="settings.json"):
    """Load settings from the JSON configuration file."""
    config_path = Path(settings_file)

    if not config_path.is_file():
        raise FileNotFoundError(
            f"Configuration file not found: {config_path}"
        )

    with config_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def build_folder_name(row):
    """Build the simulation folder name using spreadsheet data."""
    salt1 = str(row["Salt 1"]).strip()
    salt2 = str(row["Salt 2"]).strip()

    b_total = str(row["b_total (mol*kg-1)"]).strip()
    b1 = float(row["b1 (mol*kg-1)"])
    b2 = float(row["b2 (mol*kg-1)"])

    temperature = str(row["T (K)"]).strip()
    pressure = str(row["P (atm)"]).strip()

    total_molality = b1 + b2

    if total_molality <= 0:
        raise ValueError(
            "The sum of b1 and b2 must be greater than zero."
        )

    x1 = round(b1 / total_molality, 2)
    x2 = round(1.00 - x1, 2)

    return (
        f"S1_{salt1}_S2_{salt2}_M_{b_total}"
        f"_X1_{x1:.2f}_X2_{x2:.2f}"
        f"_T_{temperature}_P_{pressure}"
    )


def extract_components(*salt_codes):
    """Extract unique atom or molecular-group names from salt codes."""
    components = []
    seen = set()

    for salt_code in salt_codes:
        if pd.isna(salt_code):
            continue

        code = str(salt_code).strip()

        # Treat sulfate as a single component.
        code = re.sub(
            r"(?<![A-Za-z0-9])SO_4(?![A-Za-z0-9])",
            "SO4",
            code,
        )

        # Extract component names while ignoring stoichiometric numbers.
        for token in code.split("_"):
            if not token:
                continue

            if token[0].isupper() and token not in seen:
                components.append(token)
                seen.add(token)

    return components


def find_component_file(molecules_folder, component_name):
    """Find a component file by its name, regardless of its extension."""
    source_folder = Path(molecules_folder)

    matches = [
        path
        for path in source_folder.iterdir()
        if path.is_file()
        and path.stem.casefold() == component_name.casefold()
    ]

    if not matches:
        raise FileNotFoundError(
            f"No file found for component '{component_name}' "
            f"in '{source_folder}'."
        )

    if len(matches) > 1:
        filenames = ", ".join(
            sorted(path.name for path in matches)
        )

        raise ValueError(
            f"Multiple files found for component '{component_name}': "
            f"{filenames}. Keep only one file for this component."
        )

    return matches[0]


def copy_required_molecules(
    molecules_folder,
    destination_folder,
    salt1_code,
    salt2_code,
):
    """Copy water and all unique component files required by a mixture."""
    molecules_path = Path(molecules_folder)
    destination_path = Path(destination_folder)

    if not molecules_path.is_dir():
        raise FileNotFoundError(
            f"Molecules directory not found: {molecules_path}"
        )

    # Water is always required.
    components = ["H2O"]
    seen = {"h2o"}

    for component in extract_components(salt1_code, salt2_code):
        if component.casefold() not in seen:
            components.append(component)
            seen.add(component.casefold())

    # Resolve all source files before copying.
    source_files = [
        find_component_file(molecules_path, component)
        for component in components
    ]

    destination_path.mkdir(parents=True, exist_ok=True)

    copied_files = []

    for source_file in source_files:
        destination_file = destination_path / source_file.name

        shutil.copy2(source_file, destination_file)
        copied_files.append(source_file.name)

    return copied_files


def validate_lammps_script(lammps_script_folder):
    """Validate the exact filename and extension of density.in."""
    source_folder = Path(lammps_script_folder)

    if not source_folder.is_dir():
        raise FileNotFoundError(
            f"LAMMPS script directory not found: {source_folder}"
        )

    # Check the actual directory entry to enforce the exact filename.
    exact_matches = [
        path
        for path in source_folder.iterdir()
        if path.is_file() and path.name == "density.in"
    ]

    if len(exact_matches) == 1:
        return exact_matches[0]

    alternative_files = [
        path.name
        for path in source_folder.iterdir()
        if path.is_file()
        and path.stem.casefold() == "density"
    ]

    if alternative_files:
        found_names = ", ".join(sorted(alternative_files))

        raise ValueError(
            "Invalid LAMMPS script filename or extension. "
            "The required file must be named exactly 'density.in'. "
            f"Found: {found_names}"
        )

    raise FileNotFoundError(
        f"Required file 'density.in' was not found in: {source_folder}"
    )


def copy_lammps_script(lammps_script_path, destination_folder):
    """Copy the validated density.in template into a simulation folder."""
    source_file = Path(lammps_script_path)
    destination_path = Path(destination_folder)

    if not source_file.is_file() or source_file.name != "density.in":
        raise ValueError(
            "Only a valid file named exactly 'density.in' can be copied."
        )

    destination_path.mkdir(parents=True, exist_ok=True)

    destination_file = destination_path / "density.in"

    shutil.copy2(source_file, destination_file)

    return destination_file


def update_lammps_script(density_file, folder_name):
    """Update temperature and pressure in the copied density.in file."""
    density_path = Path(density_file)

    if not density_path.is_file():
        raise FileNotFoundError(
            f"Copied LAMMPS script not found: {density_path}"
        )

    # Extract temperature and pressure from the folder name.
    temperature_match = re.search(
        r"_T_(.+?)_P_",
        folder_name,
    )
    pressure_match = re.search(
        r"_P_(.+)$",
        folder_name,
    )

    if temperature_match is None or pressure_match is None:
        raise ValueError(
            "Could not extract temperature and pressure "
            f"from folder name: {folder_name}"
        )

    temperature = temperature_match.group(1)
    pressure = pressure_match.group(1)

    # Read only the copied script.
    content = density_path.read_text(encoding="utf-8")

    # Replace the temperature placeholder.
    content, temperature_count = re.subn(
        r"(?m)^(\s*variable\s+T\s+equal\s+)\{TEMPERATURE\}(\s*)$",
        lambda match: (
            f"{match.group(1)}{temperature}{match.group(2)}"
        ),
        content,
    )

    # Replace the pressure placeholder.
    content, pressure_count = re.subn(
        r"(?m)^(\s*variable\s+P\s+equal\s+)\{PRESSURE\}(\s*)$",
        lambda match: (
            f"{match.group(1)}{pressure}{match.group(2)}"
        ),
        content,
    )

    # Validate the expected template lines before saving.
    if temperature_count != 1 or pressure_count != 1:
        raise ValueError(
            f"Unexpected template format in {density_path}. "
            "Expected exactly one temperature placeholder and one "
            "pressure placeholder. "
            f"Found: T={temperature_count}, P={pressure_count}."
        )

    # Modify only the copied file.
    density_path.write_text(content, encoding="utf-8")


def main():
    """Create simulation folders and prepare their required files."""
    settings = load_settings("settings.json")

    output_path = Path(settings["output_path"])
    solubility_file = settings["solubility_file"]
    simulation_folder = Path(settings["simulation_folder"])
    molecules_folder = Path(settings["molecules_folder"])
    lammps_script_folder = Path(settings["lammps_script_folder"])

    excel_path = output_path / solubility_file

    # Validate the input spreadsheet.
    if not excel_path.is_file():
        raise FileNotFoundError(
            f"Solubility spreadsheet not found: {excel_path}"
        )

    # Validate the molecules directory.
    if not molecules_folder.is_dir():
        raise FileNotFoundError(
            f"Molecules directory not found: {molecules_folder}"
        )

    # Validate the LAMMPS template before creating simulation folders.
    try:
        lammps_script_path = validate_lammps_script(
            lammps_script_folder
        )
    except (FileNotFoundError, ValueError) as error:
        print(f"\n[FATAL ERROR] {error}")
        print("Processing stopped. No simulation rows were processed.")
        raise SystemExit(1) from error

    print(f"Reading spreadsheet: {excel_path}")
    print(f"Simulation directory: {simulation_folder}")
    print(f"Molecules directory: {molecules_folder}")
    print(f"LAMMPS template: {lammps_script_path}\n")

    # Read the spreadsheet without modifying the original.
    dataset = pd.read_excel(excel_path, dtype=str)

    required_columns = [
        "Salt 1",
        "Salt 2",
        "Salt 1 code",
        "Salt 2 code",
        "b_total (mol*kg-1)",
        "b1 (mol*kg-1)",
        "b2 (mol*kg-1)",
        "T (K)",
        "P (atm)",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in dataset.columns
    ]

    if missing_columns:
        raise ValueError(
            "Missing spreadsheet columns: "
            + ", ".join(missing_columns)
        )

    simulation_folder.mkdir(parents=True, exist_ok=True)

    successful_count = 0
    failed_count = 0

    for index, row in dataset.iterrows():
        try:
            # Create the simulation folder.
            folder_name = build_folder_name(row)
            folder_path = simulation_folder / folder_name
            folder_path.mkdir(parents=True, exist_ok=True)

            # Copy the required molecule files.
            copied_molecules = copy_required_molecules(
                molecules_folder=molecules_folder,
                destination_folder=folder_path,
                salt1_code=row["Salt 1 code"],
                salt2_code=row["Salt 2 code"],
            )

            # Copy the LAMMPS template into the simulation folder.
            copied_script = copy_lammps_script(
                lammps_script_path=lammps_script_path,
                destination_folder=folder_path,
            )

            # Update only the copied script.
            update_lammps_script(
                density_file=copied_script,
                folder_name=folder_name,
            )

            successful_count += 1

            print(f"[SUCCESS] {folder_name}")
            print(
                f"          Molecules: "
                f"{', '.join(copied_molecules)}"
            )
            print("          LAMMPS script: density.in")

        except Exception as error:
            failed_count += 1
            excel_row = index + 2

            print(
                f"[ERROR] Spreadsheet row {excel_row}: {error}"
            )

    print("\nProcessing completed.")
    print(f"Successfully processed: {successful_count}")
    print(f"Failed rows: {failed_count}")
    print(f"Simulation directory: {simulation_folder}")


if __name__ == "__main__":
    main()