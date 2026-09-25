from pathlib import Path

import pandas as pd
import numpy as np

def calculate_b2_points(
    b2,
    reduction_factor=0.90,
    initial_n=8,
    minimum_step=1.0,
):
    """
    Generate b2 sampling points starting from the 90% safety limit.

    The sampling step is calculated from the reduced b2 value.
    The number of intervals starts at initial_n and is reduced
    until the minimum step tolerance is satisfied.

    If no valid step is possible, only the 90% safety value
    is returned.
    """

    b2_safe = b2 * reduction_factor

    for n in range(initial_n, 0, -1):

        step = b2_safe / n

        if step >= minimum_step:
            return [
                round(b2_safe - i * step, 2)
                for i in range(n)
            ]

    return [round(b2_safe, 2)]

def generate_solubility_dataset(input_file, output_file):
    """
    Generate the solubility dataset from the processed Linke data.

    The original b2 values are used only as reference limits.
    Generated points start at 90% of the original b2 value
    and decrease according to the sampling rule defined in
    calculate_b2_points().
    """

    input_dataset = pd.read_excel(input_file)


    generated_rows = []

    for _, row in input_dataset.iterrows():

        b2_reference = row["b2"]

        b2_points = calculate_b2_points(b2_reference)

        for b2 in b2_points:

            generated_rows.append(
                {
                    "Salt 1": row["Salt 1"],
                    "Salt 2": row["Salt 2"],
                    "T (K)": row["T (K)"],
                    "P (atm)": row["P (atm)"],
                    "b1": row["b1"],
                    "b2": b2,
                }
            )

    generated_dataset = pd.DataFrame(generated_rows)

    generated_dataset = generated_dataset.sort_values(
        by=[
            "Salt 1",
            "Salt 2",
            "T (K)",
            "P (atm)",
            "b1",
            "b2",
        ],
        ascending=[
            True,
            True,
            True,
            True,
            True,
            True,
        ],
    )

    generated_dataset = generated_dataset.reset_index(drop=True)

    generated_dataset.to_excel(
        output_file,
        index=False,
    )

    return generated_dataset

if __name__ == "__main__":

    from sternario.settings import load_settings

    settings = load_settings()

    input_file = (
        Path(settings.output_path)
        / settings.output_file
    )

    output_file = (
        Path(settings.output_path)
        / settings.solubility_file
    )

    dataset = generate_solubility_dataset(
        input_file=input_file,
        output_file=output_file,
    )

    print("\nGenerated dataset:")
    print(dataset.head(20))

    print("\nDataset shape:")
    print(dataset.shape)

    print(f"\nOutput file:")
    print(output_file)