from sternario.settings import load_settings
from sternario.rotines import DataProcessor


def main():

    settings = load_settings()

    processor = DataProcessor(settings)

    processor.load_input_file()

    processor.read_input_data()

    print("=" * 60)
    print("README PREVIEW")
    print("=" * 60)
    print(processor.readme_df.head())

    print()

    print("=" * 60)
    print("INPUT DATA PREVIEW")
    print("=" * 60)
    print(processor.input_df.head())

    print()

    print("=" * 60)
    print("Program finished successfully.")
    print("=" * 60)


if __name__ == "__main__":
    main()