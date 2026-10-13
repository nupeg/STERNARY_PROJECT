import importlib.util
import math
import re
import subprocess
from pathlib import Path

from sternario.settings import load_settings


# ----------------------------------------------------------
# SYSTEM CONSTANTS
# ----------------------------------------------------------

NUMERO_MOLECULAS_AGUA = 555
MASSA_MOLAR_AGUA = 18.015
MASSA_TOTAL_AGUA = NUMERO_MOLECULAS_AGUA * MASSA_MOLAR_AGUA / 1000

dicionario_ions = {}


# ----------------------------------------------------------
# LOAD ION DICTIONARY
# ----------------------------------------------------------

def load_ion_dictionary(settings):
    """Loads the ion dictionary from the configured input directory."""

    dictionary_path = Path(settings.input_path) / settings.dicionario_file

    if not dictionary_path.is_file():
        raise FileNotFoundError(
            f"Ion dictionary not found: {dictionary_path}"
        )

    spec = importlib.util.spec_from_file_location(
        "dicionario_ions",
        dictionary_path
    )

    if spec is None or spec.loader is None:
        raise ImportError(
            f"Could not load the ion dictionary: {dictionary_path}"
        )

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if not hasattr(module, "dicionario_ions"):
        raise AttributeError(
            "The dictionary file does not contain 'dicionario_ions'."
        )

    dictionary = module.dicionario_ions

    if not isinstance(dictionary, dict):
        raise TypeError("'dicionario_ions' must be a dictionary.")

    return dictionary


# ----------------------------------------------------------
# INTERPRET CHEMICAL FORMULAS
# ----------------------------------------------------------

def interpretar_formula_quimica(formula):
    ions = {}

    grupos_parenteses = re.findall(r"\(([^\)]+)\)(\d*)", formula)

    for grupo, quantidade in grupos_parenteses:
        quantidade = int(quantidade) if quantidade else 1

        sub_ions = interpretar_formula_quimica(grupo)

        for ion, contagem in sub_ions.items():
            ions[ion] = ions.get(ion, 0) + contagem * quantidade

    formula_limpa = re.sub(r"\([^\)]+\)\d*", "", formula)

    ions_poliatomicos = [
        ion for ion in dicionario_ions.keys()
        if len(ion) > 1
    ]

    ions_poliatomicos.sort(key=lambda ion: -len(ion))

    for ion in ions_poliatomicos:
        padrao = re.escape(ion) + r"(\d*)"
        matches = re.findall(padrao, formula_limpa)

        for quantidade in matches:
            quantidade = int(quantidade) if quantidade else 1
            ions[ion] = ions.get(ion, 0) + quantidade

        formula_limpa = re.sub(padrao, "", formula_limpa)

    padrao_mono = r"([A-Z][a-z]?)(\d*)"
    matches = re.findall(padrao_mono, formula_limpa)

    for ion, quantidade in matches:
        if ion == "":
            continue

        quantidade = int(quantidade) if quantidade else 1
        ions[ion] = ions.get(ion, 0) + quantidade

    return ions


# ----------------------------------------------------------
# CALCULATE NUMBER OF MOLES
# ----------------------------------------------------------

def calcular_numero_mols_sais(
    molalidade_total,
    fracao_molal_sal1,
    fracao_molal_sal2
):
    molalidade_sal1 = molalidade_total * fracao_molal_sal1
    molalidade_sal2 = molalidade_total * fracao_molal_sal2

    numero_mols_sal1 = molalidade_sal1 * MASSA_TOTAL_AGUA
    numero_mols_sal2 = molalidade_sal2 * MASSA_TOTAL_AGUA

    return numero_mols_sal1, numero_mols_sal2


# ----------------------------------------------------------
# CALCULATE IONIC STOICHIOMETRY
# ----------------------------------------------------------

def calcular_estequiometria_ionica(
    sal1,
    sal2,
    molalidade_total,
    fracao_molal_sal1,
    fracao_molal_sal2
):
    numero_mols_sal1, numero_mols_sal2 = calcular_numero_mols_sais(
        molalidade_total,
        fracao_molal_sal1,
        fracao_molal_sal2
    )

    ions_sal1 = interpretar_formula_quimica(sal1)
    ions_sal2 = interpretar_formula_quimica(sal2)

    for ion in list(ions_sal1.keys()) + list(ions_sal2.keys()):
        if ion not in dicionario_ions:
            raise ValueError(
                f"Ion '{ion}' not found in the ion dictionary."
            )

    quantidade_ions_sal1 = {
        ion: quantidade * numero_mols_sal1
        for ion, quantidade in ions_sal1.items()
    }

    quantidade_ions_sal2 = {
        ion: quantidade * numero_mols_sal2
        for ion, quantidade in ions_sal2.items()
    }

    total_ions = {}

    for ions in (quantidade_ions_sal1, quantidade_ions_sal2):
        for ion, quantidade in ions.items():
            total_ions[ion] = total_ions.get(ion, 0) + quantidade

    total_ions_arredondado = {
        ion: math.ceil(quantidade)
        for ion, quantidade in total_ions.items()
    }

    return total_ions_arredondado


# ----------------------------------------------------------
# EXTRACT INFORMATION FROM SIMULATION FOLDER NAME
# ----------------------------------------------------------

def extrair_informacoes_pasta(nome_pasta):
    padroes = {
        "sal1": r"S1_(.*?)_S2",
        "sal2": r"S2_(.*?)_M",
        "molalidade": r"M_([\d.]+)",
        "x1": r"X1_([\d.]+)",
        "x2": r"X2_([\d.]+)"
    }

    valores = {}

    for chave, padrao in padroes.items():
        resultado = re.search(padrao, nome_pasta)

        if resultado is None:
            raise ValueError(
                f"Could not extract '{chave}' from folder '{nome_pasta}'."
            )

        valores[chave] = resultado.group(1)

    sal1 = valores["sal1"]
    sal2 = valores["sal2"]
    molalidade_total = float(valores["molalidade"])
    fracao_molal_sal1 = float(valores["x1"])
    fracao_molal_sal2 = float(valores["x2"])

    return (
        sal1,
        sal2,
        molalidade_total,
        fracao_molal_sal1,
        fracao_molal_sal2
    )


# ----------------------------------------------------------
# WRITE PLAYMOL INPUT FILE
# ----------------------------------------------------------

def escrever_arquivo_playmol(caminho_pasta, quantidade_ions):
    caminho_pasta = Path(caminho_pasta)
    caminho_arquivo = caminho_pasta / "setup.playmol"

    includes = ["include H2O.mol"]
    nomes_ions = sorted(quantidade_ions.keys())

    for ion in nomes_ions:
        includes.append(f"include {ion}.mol")

    linha_packmol = f"packmol retry 0.95 pack 1 {NUMERO_MOLECULAS_AGUA} "

    for idx, ion in enumerate(nomes_ions, start=2):
        linha_packmol += f"pack {idx} {quantidade_ions[ion]} "

    conteudo = (
        "\n".join(includes)
        + "\nimproper search\n"
        + "box lengths 40 40 40\n"
        + linha_packmol + "\n"
        + "packmol action execute\n"
        + "write lammps start_box.lmp\n"
        + "write xyz start_box.xyz\n"
    )

    caminho_arquivo.write_text(conteudo, encoding="utf-8")

    return caminho_arquivo


# ----------------------------------------------------------
# EXECUTE PLAYMOL THROUGH WSL
# ----------------------------------------------------------

def executar_playmol_em_pasta(caminho_pasta, playmol_executable_folder):
    """
    Executes Playmol through WSL in the simulation directory.
    Writes standard output and errors to separate log files.
    """

    caminho_pasta = Path(caminho_pasta)
    arquivo_setup = caminho_pasta / "setup.playmol"

    if not arquivo_setup.is_file():
        print(f"Playmol skipped: setup.playmol not found in {caminho_pasta}")
        return False

    comando = [
        "wsl",
        playmol_executable_folder,
        "setup.playmol"
    ]

    log_saida = caminho_pasta / "playmol_output.log"
    log_erro = caminho_pasta / "playmol_error.log"

    print(f"\nExecuting Playmol in: {caminho_pasta}")

    try:
        with (
            log_saida.open("w", encoding="utf-8") as saida,
            log_erro.open("w", encoding="utf-8") as erro
        ):
            resultado = subprocess.run(
                comando,
                cwd=str(caminho_pasta),
                stdout=saida,
                stderr=erro,
                check=False
            )

        if resultado.returncode == 0:
            print(f"Playmol completed successfully: {caminho_pasta.name}")
            return True

        print(
            f"Playmol failed: {caminho_pasta.name}. "
            f"Check {log_erro}"
        )
        return False

    except Exception as erro_execucao:
        with log_erro.open("a", encoding="utf-8") as erro:
            erro.write(f"\nExecution exception: {erro_execucao}\n")

        print(
            f"Could not execute Playmol in {caminho_pasta.name}: "
            f"{erro_execucao}"
        )
        return False


# ----------------------------------------------------------
# PROCESS ALL SIMULATION FOLDERS
# ----------------------------------------------------------

def processar_todas_as_pastas(
    caminho_base,
    playmol_folder,
    ignorar_se_arquivo_existir=False
):
    caminho_base = Path(caminho_base)

    if not caminho_base.is_dir():
        raise NotADirectoryError(
            f"Simulation directory not found: {caminho_base}"
        )

    pastas = sorted(
        pasta for pasta in caminho_base.iterdir()
        if pasta.is_dir() and pasta.name.lower() != "logs"
    )

    print(f"Simulation directory: {caminho_base}")
    print(f"Subfolders found: {len(pastas)}")

    sucessos_estequiometria = 0
    sucessos_playmol = 0
    falhas_estequiometria = 0
    falhas_playmol = 0
    ignoradas = 0

    for caminho_pasta in pastas:
        pasta = caminho_pasta.name
        caminho_setup = caminho_pasta / "setup.playmol"

        if ignorar_se_arquivo_existir and caminho_setup.exists():
            print(f"Skipping existing setup.playmol: {pasta}")
            ignoradas += 1
            continue

        print(f"\nProcessing: {pasta}")

        try:
            sal1, sal2, molalidade_total, x1, x2 = (
                extrair_informacoes_pasta(pasta)
            )

            estequiometria_ionica = calcular_estequiometria_ionica(
                sal1,
                sal2,
                molalidade_total,
                x1,
                x2
            )

            escrever_arquivo_playmol(
                caminho_pasta,
                estequiometria_ionica
            )

            sucessos_estequiometria += 1
            print(f"setup.playmol created: {pasta}")

        except Exception as erro:
            falhas_estequiometria += 1
            print(
                f"Stoichiometry or setup generation failed "
                f"for {pasta}: {erro}"
            )
            continue

        # Run Playmol only after successful setup generation.
        if executar_playmol_em_pasta(caminho_pasta, playmol_folder):
            sucessos_playmol += 1
        else:
            falhas_playmol += 1

    print("\n" + "=" * 55)
    print("STOICHIOMETRY AND PLAYMOL SUMMARY")
    print("=" * 55)
    print(f"Folders found: {len(pastas)}")
    print(f"Setups generated: {sucessos_estequiometria}")
    print(f"Stoichiometry/setup failures: {falhas_estequiometria}")
    print(f"Playmol successes: {sucessos_playmol}")
    print(f"Playmol failures: {falhas_playmol}")
    print(f"Folders skipped: {ignoradas}")
    print("=" * 55)


# ----------------------------------------------------------
# MAIN ROUTINE
# ----------------------------------------------------------

def main():
    global dicionario_ions

    settings = load_settings()

    dicionario_ions = load_ion_dictionary(settings)

    caminho_base = Path(settings.simulation_folder)
    playmol_folder = settings.playmol_executable_folder

    ignorar_existentes = False

    processar_todas_as_pastas(
        caminho_base=caminho_base,
        playmol_folder=playmol_folder,
        ignorar_se_arquivo_existir=ignorar_existentes
    )


if __name__ == "__main__":
    main()