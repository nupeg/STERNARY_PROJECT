from pathlib import Path

import pandas as pd
import numpy as np

from sternario.auxiliar_solubility_spreadsheet import calculate_b2_points

class SolubilityProcessor:
    """
    Class responsible for generating and exporting the solubility dataset.
    """

    def __init__(self, settings):
        self.settings = settings

        # Input file: processed and concatenated Linke dataset
        self.input_path = (
            Path(self.settings.output_path)
            / self.settings.output_file
        )

        # Output file: generated solubility dataset
        self.output_path = (
            Path(self.settings.output_path)
            / self.settings.solubility_file
        )

        self.input_dataset = None
        self.generated_dataset = None
        self.output_dataset = None

    def execute(self):
        """
        Execute the complete solubility dataset workflow.
        """

        self.load_input_dataset()
        self.generate_solubility_points()
        self.prepare_output_dataset()
        self.save_output_workbook()

    def load_input_dataset(self):
        """
        Load the processed Linke dataset.
        """

        if not self.input_path.exists():
            raise FileNotFoundError(
                f"Input file not found: {self.input_path}"
            )

        self.input_dataset = pd.read_excel(self.input_path)

    def generate_solubility_points(self):
        """
        Generate b2 sampling points for each experimental row.

        The original b2 values are used only as reference limits.
        Generated points start at 90% of the original b2 value
        and decrease according to the sampling rule defined in
        calculate_b2_points() - see auxiliar_solubility_spreadsheet.py for the reference.
        """

        if self.input_dataset is None:
            raise ValueError(
                "Input dataset has not been loaded. "
                "Run load_input_dataset() first."
            )

        generated_rows = []

        for _, row in self.input_dataset.iterrows():

            b2_reference = row["b2"]

            b2_points = calculate_b2_points(b2_reference,
                                            reduction_factor=0.90,
                                            minimum_step=0.15
            )



            for b2 in b2_points:
                if b2 <= 0.01: 
                    continue
                if row["b1"] <= 0:
                    continue

                generated_rows.append(
                    {
                        "Salt 1": row["Salt 1"],
                        "Salt 2": row["Salt 2"],
                        "T (K)": row["T (K)"],
                        "P (MPa)": row["P (MPa)"],
                        "b1 (mol*kg-1)": row["b1"],
                        "b2 (mol*kg-1)": b2,
                    }
                )

        self.generated_dataset = pd.DataFrame(generated_rows)

    def prepare_output_dataset(self):
        """
        Sort and prepare the generated solubility dataset.
        """

        if self.generated_dataset is None:
            raise ValueError(
                "Solubility points have not been generated. "
                "Run generate_solubility_points() first."
            )


        self.output_dataset = self.generated_dataset.copy()

        self.output_dataset["b_total (mol*kg-1)"] = (
            self.output_dataset["b1 (mol*kg-1)"]
            + self.output_dataset["b2 (mol*kg-1)"]
        )

        self.output_dataset = self.output_dataset.round(
            {
                "b_total (mol*kg-1)": 3,
                "b1 (mol*kg-1)": 3,
                "b2 (mol*kg-1)": 3,
            }
        )


        self.output_dataset = self.output_dataset.sort_values(
            by=[
                "Salt 1",
                "Salt 2",
                "T (K)",
                "P (MPa)",
                "b1 (mol*kg-1)",
                "b2 (mol*kg-1)",
            ],
            ascending=[
                True,
                True,
                True,
                True,
                True,
                True,
            ],
        ).reset_index(drop=True)

    
    def save_output_workbook(self):
        """
        Save the prepared solubility dataset to an Excel file.
        """

        if self.output_dataset is None:
            raise ValueError(
                "Output dataset has not been prepared. "
                "Run prepare_output_dataset() first."
            )

        self.output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.output_dataset.to_excel(
            self.output_path,
            index=False,
        )



if __name__ == "__main__":

    from sternario.settings import load_settings

    settings = load_settings()

    processor = SolubilityProcessor(settings)

    processor.execute()



    print("\nOutput dataset:")
    print(processor.output_dataset.head(20))

    print("\nDataset columns:")
    print(processor.output_dataset.columns.tolist())

    print("\nDataset shape:")
    print(processor.output_dataset.shape)

    print("\nOutput file:")
    print(processor.output_path)