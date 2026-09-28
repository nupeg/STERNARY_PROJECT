import sys

from sternario.settings import load_settings
from sternario.rotines_concatenated_spreadsheet import DataProcessor
from sternario.rotines_solubility_spreadsheet import SolubilityProcessor


def show_menu():
    """
    Display the main application menu.
    """

    print("\n==========================================")
    print("      STERNARIO - DATA PROCESSOR")
    print("==========================================")

    print("\n--- Concatenated Dataset ---")
    print("1. Carregar arquivo de entrada")
    print("2. Ler e unificar dados")
    print("3. Preparar dataset de saída")
    print("4. Salvar dataset de saída")

    print("\n--- Solubility Dataset ---")
    print("5. Carregar dataset de solubilidade")
    print("6. Gerar pontos de solubilidade")
    print("7. Preparar dataset de solubilidade")
    print("8. Salvar planilha de solubilidade")

    print("\n--- Complete Workflow ---")
    print("9. Executar todas as tarefas")

    print("\n0. Encerrar programa")


def main():
    """
    Main application entry point.
    """

    try:
        settings = load_settings()

        data_processor = DataProcessor(settings)
        solubility_processor = SolubilityProcessor(settings)

        while True:

            show_menu()

            option = input("\nEscolha uma opção: ").strip()

            # --------------------------------------------------
            # Concatenated dataset
            # --------------------------------------------------

            if option == "1":

                data_processor.load_input_workbook()

                print("\nArquivo de entrada carregado com sucesso.")

            elif option == "2":

                data_processor.read_input_workbook()

                print("\nDados lidos e unificados com sucesso.")

            elif option == "3":

                data_processor.prepare_output_dataset()

                print("\nDataset de saída preparado com sucesso.")

            elif option == "4":

                data_processor.save_output_workbook()

                print("\nDataset de saída salvo com sucesso.")

            # --------------------------------------------------
            # Solubility dataset
            # --------------------------------------------------

            elif option == "5":

                solubility_processor.load_input_dataset()

                print("\nDataset de entrada da solubilidade carregado com sucesso.")

            elif option == "6":

                solubility_processor.generate_solubility_points()

                print("\nPontos de solubilidade gerados com sucesso.")

            elif option == "7":

                solubility_processor.prepare_output_dataset()

                print("\nDataset de solubilidade preparado com sucesso.")

            elif option == "8":

                solubility_processor.save_output_workbook()

                print("\nPlanilha de solubilidade salva com sucesso.")

            # --------------------------------------------------
            # Complete workflow
            # --------------------------------------------------

            elif option == "9":

                print("\nExecutando todas as tarefas...")

                data_processor.execute()
                solubility_processor.execute()

                print("\nTodas as tarefas foram executadas com sucesso.")

            # --------------------------------------------------
            # Exit
            # --------------------------------------------------

            elif option == "0":

                print("\nPrograma encerrado.")

                break

            else:

                print("\nOpção inválida. Escolha uma opção do menu.")

    except FileNotFoundError as error:

        print(
            f"\nErro de arquivo: {error}",
            file=sys.stderr,
        )

    except Exception as error:

        print(
            f"\nOcorreu um erro inesperado: {error}",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()