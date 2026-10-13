
from sternario.routines_concatenated_spreadsheet import DataProcessor
from sternario.routines_folder_creator import (
    main as create_simulation_folders,
)
from sternario.routines_solubility_spreadsheet import SolubilityProcessor
from sternario.routines_playmol import main as process_playmol
from sternario.routines_coeffs_creator import (
    main as create_lammps_coefficients,
)
from sternario.settings import load_settings


def main():
    """Main function responsible for managing the application menu."""

    settings = load_settings()

    data_processor = DataProcessor(settings)
    solubility_processor = SolubilityProcessor(settings)

    while True:
        print("\n" + "=" * 50)
        print("         TERNARY MIXTURE DATA PROCESSOR")
        print("=" * 50)

        print("\n--- Data Processing ---")
        print("1. Load input file")
        print("2. Read and unify data")
        print("3. Prepare output dataset")
        print("4. Save output dataset")

        print("\n--- Solubility Processing ---")
        print("5. Load solubility input")
        print("6. Generate solubility points")
        print("7. Prepare solubility dataset")
        print("8. Save solubility dataset")

        print("\n--- Simulation Preparation ---")
        print("9. Create simulation folders")
        print("10. Calculate stoichiometry and execute Playmol")
        print("11. Generate LAMMPS coefficients")

        print("\n--- Complete Workflow ---")
        print("12. Execute all workflows sequentially")

        print("\n--- Exit Menu ---")
        print("0. Exit")

        option = input("\nSelect an option: ").strip()

        try:
            if option == "1":
                data_processor.load_input_workbook()
                print("\nInput file loaded successfully.")

            elif option == "2":
                data_processor.read_input_workbook()
                print("\nInput data read successfully.")

            elif option == "3":
                data_processor.prepare_output_dataset()
                print("\nOutput dataset prepared successfully.")

            elif option == "4":
                data_processor.save_output_workbook()
                print("\nOutput dataset saved successfully.")

            elif option == "5":
                solubility_processor.load_input_dataset()
                print("\nSolubility input file loaded successfully.")

            elif option == "6":
                solubility_processor.generate_solubility_points()
                print("\nSolubility points generated successfully.")

            elif option == "7":
                solubility_processor.prepare_output_dataset()
                print("\nSolubility dataset prepared successfully.")

            elif option == "8":
                solubility_processor.save_output_workbook()
                print("\nSolubility dataset saved successfully.")

            elif option == "9":
                print("\nStarting simulation folder creation...")

                create_simulation_folders()

                print("\nSimulation folder creation routine finished.")

            elif option == "10":
                print("\nStarting stoichiometry calculations and Playmol...")

                process_playmol()

                print("\nStoichiometry and Playmol routine finished.")

            elif option == "11":
                print("\nStarting LAMMPS coefficient generation...")

                create_lammps_coefficients()

                print("\nLAMMPS coefficient generation routine finished.")

            elif option == "12":
                print("\nStarting complete workflow...")

                # Process the original data
                data_processor.execute()

                # Generate the solubility dataset
                solubility_processor.execute()

                # Create simulation directories
                create_simulation_folders()

                # Calculate ionic stoichiometry and execute Playmol
                process_playmol()

                # Generate LAMMPS force-field coefficients
                create_lammps_coefficients()

                print("\nAll workflows finished successfully.")

            elif option == "0":
                print("\nProgram closed.")
                break

            else:
                print("\nInvalid option. Please select a valid option.")

        except FileNotFoundError as error:
            print(f"\nFile not found: {error}")

        except ValueError as error:
            print(f"\nInvalid data or configuration: {error}")

        except Exception as error:
            print(f"\nAn unexpected error occurred: {error}")


if __name__ == "__main__":
    main()