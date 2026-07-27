import os

import pandas as pd


class DataProcessor:
    """
    Class responsible for reading and preparing the input workbook.

    Current workflow
    ----------------
    1. Open input workbook.
    2. Read README sheet.
    3. Concatenate all data sheets.
    4. Filter temperatures between 5 and 95 °C.
    """

    def __init__(self, settings):

        self.settings = settings

        self.input_workbook = None

        self.readme_df = None
        self.input_df = None

    def load_input_file(self):
        """
        Open the Excel workbook.
        """

        input_file = os.path.join(
            self.settings.input_path,
            self.settings.input_file
        )

        print("=" * 60)
        print("Opening input workbook")
        print("=" * 60)
        print(input_file)

        self.input_workbook = pd.ExcelFile(input_file)

        print("Workbook successfully loaded.\n")

    def read_input_data(self):
        """
        Read README separately and concatenate all remaining sheets.
        """

        if self.input_workbook is None:
            raise RuntimeError(
                "Input workbook has not been loaded."
            )

        print("=" * 60)
        print("Reading workbook")
        print("=" * 60)

        # ----------------------------------------------------------
        # README
        # ----------------------------------------------------------

        print("Reading README sheet...")

        self.readme_df = pd.read_excel(
            self.input_workbook,
            sheet_name="README"
        )

        # ----------------------------------------------------------
        # Data sheets
        # ----------------------------------------------------------

        dataframes = []

        for sheet_name in self.input_workbook.sheet_names:

            if sheet_name == "README":
                continue

            print(f"Reading sheet: {sheet_name}")

            df = pd.read_excel(
                self.input_workbook,
                sheet_name=sheet_name
            )

            # First row contains the actual headers
            columns = df.iloc[0].values

            df = df.iloc[1:].copy()

            df.columns = columns

            # Remove first empty column if necessary
            if (
                pd.isna(df.columns[0])
                or str(df.columns[0]).startswith("Unnamed")
            ):
                df = df.iloc[:, 1:]

            dataframes.append(df)

        print("\nConcatenating sheets...")

        self.input_df = pd.concat(
            dataframes,
            ignore_index=True
        )

        # ----------------------------------------------------------
        # Temperature filter
        # ----------------------------------------------------------

        self.input_df["Temperature"] = pd.to_numeric(
            self.input_df["Temperature"],
            errors="coerce"
        )

        self.input_df = self.input_df[
            (self.input_df["Temperature"] >= 5)
            &
            (self.input_df["Temperature"] <= 95)
        ].copy()

        print("Temperature filter applied.")
        print()

        print(f"Rows    : {len(self.input_df)}")
        print(f"Columns : {len(self.input_df.columns)}")
        print()