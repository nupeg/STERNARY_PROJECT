import sys
from sternario.rotines import DataProcessor
from sternario.settings import load_settings


def main():
    """
    Main application entry point.
    """
    print("==========================================")
    print("      STERNARIO - DATA PROCESSOR          ")
    print("==========================================")

    try:
        # 1. Carrega configurações e mapeamentos
        print("\n[1/3] Carregando configurações...")
        settings = load_settings()

        # 2. Instancia o processador
        print("[2/3] Inicializando rotinas de processamento...")
        processor = DataProcessor(settings)

        # 3. Executa o pipeline de dados
        print("[3/3] Executando pipeline...")
        processor.execute()

        print("\n✨ Processo finalizado com êxito!")

    except FileNotFoundError as fnf_err:
        print(f"\n❌ Erro de Arquivo: {fnf_err}", file=sys.stderr)
        sys.exit(1)
    except Exception as err:
        print(f"\n❌ Ocorreu um erro inesperado durante a execução: {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()