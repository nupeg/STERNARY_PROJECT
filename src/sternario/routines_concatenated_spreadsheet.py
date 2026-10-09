from pathlib import Path

import numpy as np
import pandas as pd


class DataProcessor:
    """
    Class responsible for loading, processing, converting, and exporting
    physicochemical data for ternary salt mixtures.

    Molar masses are calculated dynamically from the
    'Salt 1 code' and 'Salt 2 code' columns.
    """

    # Atomic masses (g/mol), including the sulfate group.
    ATOMIC_MASSES = {
        "F": 18.9984,
        "Cl": 35.4530,
        "Br": 79.9040,
        "I": 126.9045,
        "Li": 6.9410,
        "Na": 22.9898,
        "K": 39.0983,
        "Rb": 85.4678,
        "Cs": 132.9055,
        "Mg": 24.3050,
        "Ca": 40.0780,
        "SO4": 96.0600,
    }

    MW_H2O = 18.01528  # g/mol

    BAR_TO_ATM = 0.9869232667

    def __init__(self, settings):
        self.settings = settings

        self.input_path = (
            Path(self.settings["input_path"])
            / self.settings["input_file"]
        )

        self.output_path = (
            Path(self.settings["output_path"])
            / self.settings["output_file"]
        )

        self.workbook = None
        self.readme = None
        self.raw_dataset = None
        self.output_dataset = None

    def execute(self):
        """Execute the complete data-processing pipeline."""
        self.load_input_workbook()
        self.read_input_workbook()
        self.prepare_output_dataset()
        self.save_output_workbook()

    def load_input_workbook(self):
        """Load the input Excel workbook."""
        if not self.input_path.is_file():
            raise FileNotFoundError(
                f"Input file not found: {self.input_path}"
            )

        self.workbook = pd.ExcelFile(self.input_path)

    def parse_salt_code(self, code):
        """
        Calculate the molar mass of a salt from its component code.

        Examples:
            Na_1_Cl_1
            Ca_1_SO4_1
            Na_2_SO_4
            Li_2_SO4_1
        """
        if not isinstance(code, str) or pd.isna(code):
            return np.nan

        parts = [
            part.strip()
            for part in str(code).split("_")
            if part.strip()
        ]

        molar_mass = 0.0
        i = 0

        while i < len(parts):
            element = parts[i]

            # Treat SO_4 as a single sulfate group.
            if (
                element == "SO"
                and i + 1 < len(parts)
                and parts[i + 1] == "4"
            ):
                molar_mass += self.ATOMIC_MASSES["SO4"]
                i += 2
                continue

            # Read the stoichiometric coefficient when available.
            if i + 1 < len(parts) and parts[i + 1].isdigit():
                quantity = float(parts[i + 1])
                i += 2
            else:
                quantity = 1.0
                i += 1

            if element in self.ATOMIC_MASSES:
                molar_mass += (
                    self.ATOMIC_MASSES[element] * quantity
                )

        return molar_mass if molar_mass > 0 else np.nan

    def read_input_workbook(self):
        """
        Read all data sheets, remove empty and unnamed columns,
        and concatenate the data into a single DataFrame.
        """
        if self.workbook is None:
            raise ValueError(
                "The input workbook has not been loaded. "
                "Run load_input_workbook() first."
            )

        sheet_names = self.workbook.sheet_names

        # Read and clean the README sheet when available.
        if "README" in sheet_names:
            readme_df = pd.read_excel(
                self.workbook,
                sheet_name="README",
            )

            readme_df = readme_df.loc[
                :,
                ~readme_df.columns.astype(str).str.contains(
                    "^Unnamed",
                    case=False,
                    na=False,
                ),
            ].dropna(how="all")

            self.readme = readme_df

        data_sheets = [
            sheet
            for sheet in sheet_names
            if sheet.upper() != "README"
        ]

        dataframes = []

        for sheet in data_sheets:
            # The data header is located on the second row.
            df = pd.read_excel(
                self.workbook,
                sheet_name=sheet,
                header=1,
            )

            # Remove unnamed columns.
            df = df.loc[
                :,
                ~df.columns.astype(str).str.contains(
                    "^Unnamed",
                    case=False,
                    na=False,
                ),
            ].copy()

            # Convert composition values to numeric.
            df["x1"] = pd.to_numeric(
                df["x1"],
                errors="coerce",
            )

            df["x2"] = pd.to_numeric(
                df["x2"],
                errors="coerce",
            )

            # Discard rows without valid composition values.
            df = df.dropna(subset=["x1", "x2"]).copy()

            dataframes.append(df)

        if not dataframes:
            raise ValueError(
                "No valid data sheets were found in the workbook."
            )

        self.raw_dataset = pd.concat(
            dataframes,
            ignore_index=True,
        )

    def prepare_output_dataset(self):
        """Convert units, calculate molalities, and prepare output data."""
        if self.raw_dataset is None:
            raise ValueError(
                "Input data have not been read. "
                "Run read_input_workbook() first."
            )

        df = self.raw_dataset.copy()

        # 1. Convert temperature to Kelvin.
        temperature = pd.to_numeric(
            df["Temperature"],
            errors="coerce",
        )

        temperature_unit = (
            df["Temperature Unit"]
            .astype(str)
            .str.strip()
            .str.casefold()
        )

        is_celsius = temperature_unit.str.contains(
            "celsius",
            na=False,
        )

        df["T (K)"] = np.where(
            is_celsius,
            temperature + 273.15,
            temperature,
        )

        # 2. Convert pressure to atm when necessary.
        pressure = pd.to_numeric(
            df["Pressure"],
            errors="coerce",
        )

        pressure_unit = (
            df["Pressure Unit"]
            .astype(str)
            .str.strip()
            .str.casefold()
        )

        is_atm = pressure_unit.eq("atm")
        is_bar = pressure_unit.eq("bar")

        invalid_units = ~(is_atm | is_bar)

        if invalid_units.any():
            units = (
                df.loc[invalid_units, "Pressure Unit"]
                .drop_duplicates()
                .tolist()
            )

            raise ValueError(
                f"Unsupported pressure units: {units}. "
                "Only 'atm' and 'bar' are accepted."
            )

        # Initialize the output pressure column.
        df["P (atm)"] = np.nan

        # Preserve values already expressed in atm.
        df.loc[is_atm, "P (atm)"] = pressure.loc[is_atm]

        # Convert bar to atm.
        df.loc[is_bar, "P (atm)"] = (
            pressure.loc[is_bar] * self.BAR_TO_ATM
        )

        if df["P (atm)"].isna().any():
            raise ValueError(
                "Some pressure values are missing or non-numeric."
            )

        # 3. Calculate the molalities b1 and b2.
        b1_list = []
        b2_list = []

        for _, row in df.iterrows():
            salt1_code = row.get("Salt 1 code")
            salt2_code = row.get("Salt 2 code")

            x1_value = row["x1"]
            x2_value = row["x2"]
            unit = str(row["x unit"]).strip()

            # Calculate the molar masses.
            mw1 = self.parse_salt_code(salt1_code)
            mw2 = self.parse_salt_code(salt2_code)

            if pd.isna(mw1) or pd.isna(mw2):
                raise ValueError(
                    "Could not calculate the molar mass for "
                    f"salt codes: {salt1_code}, {salt2_code}."
                )

            # Saturated solution weight percentage.
            if unit == "SAT_SOL_WT%":
                mass_water_g = (
                    100.0 - (x1_value + x2_value)
                )

                if mass_water_g <= 0:
                    raise ValueError(
                        "Water mass must be positive. "
                        f"Salt 1: {salt1_code}; "
                        f"Salt 2: {salt2_code}; "
                        f"water mass: {mass_water_g} g."
                    )

                mass_water_kg = mass_water_g / 1000.0

                b1 = (
                    x1_value / mw1
                ) / mass_water_kg

                b2 = (
                    x2_value / mw2
                ) / mass_water_kg

            # Grams of solute per 100 g of mixture.
            elif unit == "G_100G_MIX":
                mass_water_g = (
                    100.0 - (x1_value + x2_value)
                )

                if mass_water_g <= 0:
                    raise ValueError(
                        "Water mass must be positive. "
                        f"Salt 1: {salt1_code}; "
                        f"Salt 2: {salt2_code}; "
                        f"water mass: {mass_water_g} g."
                    )

                mass_water_kg = mass_water_g / 1000.0

                b1 = (
                    x1_value / mw1
                ) / mass_water_kg

                b2 = (
                    x2_value / mw2
                ) / mass_water_kg

            # Grams of solute per 100 g of water.
            elif unit == "G_100G_H2O":
                mass_water_kg = 0.1

                b1 = (
                    x1_value / mw1
                ) / mass_water_kg

                b2 = (
                    x2_value / mw2
                ) / mass_water_kg

            # Units for which molality conversion is not implemented.
            elif unit in [
                "G_CM3_SOL",
                "G_L_SOL",
                "GMOL_SOL",
            ]:
                b1 = np.nan
                b2 = np.nan

            else:
                raise ValueError(
                    f"Unrecognized composition unit: {unit}"
                )

            b1_list.append(b1)
            b2_list.append(b2)

        # 4. Calculate total molality.
        df["b1"] = np.array(b1_list, dtype=float)
        df["b2"] = np.array(b2_list, dtype=float)

        df["b_total"] = df["b1"] + df["b2"]

        # 5. Remove rows with unavailable molalities.
        df = df.dropna(
            subset=["b1", "b2"]
        ).copy()

        # Remove binary-like cases with zero salt molality.
        df = df[
            (df["b1"] != 0.0)
            & (df["b2"] != 0.0)
        ].copy()

        # 6. Validate the processed numerical values.
        invalid_rows = df[
            (df["b1"] <= 0)
            | (df["b2"] <= 0)
            | (df["b_total"] <= 0)
            | (df["T (K)"] <= 0)
            | (df["P (atm)"] <= 0)
        ]

        if not invalid_rows.empty:
            raise ValueError(
                f"Found {len(invalid_rows)} rows with invalid "
                "molality, temperature, or pressure values."
            )

        # 7. Select and order the output columns.
        output_columns = [
            "Salt 1",
            "Salt 2",
            "Salt 1 code",
            "Salt 2 code",
            "T (K)",
            "P (atm)",
            "b1",
            "b2",
            "b_total",
            "Ref",
        ]

        missing_columns = [
            column
            for column in output_columns
            if column not in df.columns
        ]

        if missing_columns:
            raise ValueError(
                "Missing columns required for output: "
                + ", ".join(missing_columns)
            )

        self.output_dataset = df[output_columns].copy()

    def save_output_workbook(self):
        """Save the processed dataset to the output workbook."""
        if self.output_dataset is None:
            raise ValueError(
                "The output dataset has not been prepared. "
                "Run prepare_output_dataset() first."
            )

        self.output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with pd.ExcelWriter(
            self.output_path,
            engine="openpyxl",
        ) as writer:
            if self.readme is not None and not self.readme.empty:
                self.readme.to_excel(
                    writer,
                    sheet_name="README",
                    index=False,
                )

            self.output_dataset.to_excel(
                writer,
                sheet_name="Processed_Data",
                index=False,
            )