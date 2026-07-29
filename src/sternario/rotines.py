from pathlib import Path
import numpy as np
import pandas as pd


class DataProcessor:
    """
    Classe responsável por carregar, unificar, converter unidades físico-químicas
    e exportar os dados processados de misturas ternárias de sais.
    """

    # Massas molares dos sais (g/mol)
    MOLAR_MASSES = {
        "NaCl": 58.44,
        "NaBr": 102.89,
        "KCl": 74.55,
        "KBr": 119.00,
        "KI": 166.00,
        "KF": 58.10,
        "K2SO4": 174.26,
        "NaI": 149.89,
        "Na2SO4": 142.04,
        "Li2SO4": 109.94,
        "LiCl": 42.39,
        "MgCl2": 95.21,
        "MgSO4": 120.36,
        "CaCl2": 110.98,
        "CaSO4": 136.14,
    }
    MW_H2O = 18.01528  # g/mol

    def __init__(self, settings):
        self.settings = settings
        self.input_path = Path(self.settings.get("INPUT_FILE"))
        self.output_path = Path(self.settings.get("OUTPUT_FILE"))

        self.workbook = None
        self.readme = None
        self.raw_dataset = None
        self.output_dataset = None

    def execute(self):
        """Executa a sequência do pipeline de dados."""
        self.load_input_workbook()
        self.read_input_workbook()
        self.prepare_output_dataset()
        self.save_output_workbook()

    def load_input_workbook(self):
        """Carrega a planilha de entrada."""
        if not self.input_path.exists():
            raise FileNotFoundError(f"Arquivo de entrada não encontrado: {self.input_path}")
        self.workbook = pd.ExcelFile(self.input_path)

    def read_input_workbook(self):
        """
        Lê todas as abas de dados da planilha, limpa linhas nulas/inválidas,
        e concatena tudo em um único DataFrame com um único cabeçalho.
        """
        sheet_names = self.workbook.sheet_names

        # Separa a aba README se ela existir no arquivo
        if "README" in sheet_names:
            self.readme = pd.read_excel(self.workbook, sheet_name="README")

        data_sheets = [s for s in sheet_names if s.upper() != "README"]
        dataframes = []

        for sheet in data_sheets:
            # Lê definindo o cabeçalho na linha de índice 1 (segunda linha da planilha)
            df = pd.read_excel(self.workbook, sheet_name=sheet, header=1)

            # Remove colunas genéricas 'Unnamed' (linhas vazias ou índices visuais)
            df = df.loc[:, ~df.columns.str.contains("^Unnamed")].copy()

            # Força x1 e x2 para formato numérico e descarta linhas sem dados
            df["x1"] = pd.to_numeric(df["x1"], errors="coerce")
            df["x2"] = pd.to_numeric(df["x2"], errors="coerce")
            df = df.dropna(subset=["x1", "x2"]).copy()

            dataframes.append(df)

        # Concatena mantendo um único cabeçalho padrão
        self.raw_dataset = pd.concat(dataframes, ignore_index=True)

    def prepare_output_dataset(self):
        """Realiza os cálculos de conversão e gera o dataset final formatado."""
        df = self.raw_dataset.copy()

        # 1. Conversão de Temperatura para Kelvin -> "T (K)"
        is_celsius = df["Temperature Unit"].astype(str).str.contains("Celsius", case=False, na=False)
        df["T (K)"] = np.where(is_celsius, df["Temperature"] + 273.15, df["Temperature"])

        # 2. Conversão de Pressão para atm -> "P (atm)"
        is_bar = df["Pressure Unit"].astype(str).str.contains("bar", case=False, na=False)
        df["P (atm)"] = np.where(is_bar, df["Pressure"] / 1.01325, df["Pressure"])

        # 3. Conversão das unidades de solubilidade para Molalidade b1 e b2 (mol/kg de H2O)
        b1_list, b2_list = [], []
        for _, row in df.iterrows():
            salt1, salt2 = row["Salt 1"], row["Salt 2"]
            x1_val, x2_val = row["x1"], row["x2"]
            unit = str(row["x unit"]).strip().upper()

            mw1 = self.MOLAR_MASSES.get(salt1, 58.44)
            mw2 = self.MOLAR_MASSES.get(salt2, 58.44)

            # --- Regras de conversão baseadas nos códigos do README ---
            if unit in ["G_100G_MIX", "SAT_SOL_WT%"]:
                # Gramas de soluto por 100g de mistura total (solução saturada)
                mass_water = 100.0 - (x1_val + x2_val)
                b1 = (x1_val / mw1) / (mass_water / 1000.0) if mass_water > 0 else np.nan
                b2 = (x2_val / mw2) / (mass_water / 1000.0) if mass_water > 0 else np.nan

            elif unit == "G_CM3_SOL":
                # Linke/Seidell: g soluto por 100 cm³ (0.1 kg) de solvente (H2O)
                b1 = (x1_val / mw1) / 0.1
                b2 = (x2_val / mw2) / 0.1

            elif unit == "G_L_SOL":
                # g soluto por Litro (1.0 kg) de solvente (H2O)
                b1 = x1_val / mw1
                b2 = x2_val / mw2

            elif unit == "GMOL_SOL":
                # mols de soluto por Litro (1.0 kg) de solvente (H2O)
                b1 = x1_val
                b2 = x2_val

            else:
                # Caso ocorra alguma unidade não cadastrada (Fallback)
                mass_water = 100.0 - (x1_val + x2_val)
                b1 = (x1_val / mw1) / (mass_water / 1000.0) if mass_water > 0 else np.nan
                b2 = (x2_val / mw2) / (mass_water / 1000.0) if mass_water > 0 else np.nan

            b1_list.append(b1)
            b2_list.append(b2)

        b1_array = np.array(b1_list)
        b2_array = np.array(b2_list)

        # 4. Cálculo das frações molares da mistura (x1, x2, xH2O)
        nH2O = 1000.0 / self.MW_H2O  # Mols de H2O em 1 kg (~55.5084 mol)
        n_total = b1_array + b2_array + nH2O

        df["x1"] = b1_array / n_total
        df["x2"] = b2_array / n_total
        df["xH2O"] = nH2O / n_total

        # 5. Molalidade total da mistura (b_total em mol/kg de H2O)
        df["b_total"] = b1_array + b2_array

        # 6. Seleção e ordenação das colunas de saída solicitadas
        output_columns = [
            "Salt 1",
            "Salt 2",
            "T (K)",
            "P (atm)",
            "x1",
            "x2",
            "xH2O",
            "b_total",
        ]
        self.output_dataset = df[output_columns].copy()

    def save_output_workbook(self):
        """Salva a planilha de saída e a aba README (se existir)."""
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        with pd.ExcelWriter(self.output_path, engine="openpyxl") as writer:
            if self.readme is not None:
                self.readme.to_excel(writer, sheet_name="README", index=False)
            self.output_dataset.to_excel(writer, sheet_name="Processed_Data", index=False)