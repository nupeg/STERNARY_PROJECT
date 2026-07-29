import numpy as np
import pandas as pd
from pathlib import Path


class DataProcessor:
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
        self.load_input_workbook()
        self.read_input_workbook()
        self.prepare_output_dataset()
        self.save_output_workbook()

    def load_input_workbook(self):
        if not self.input_path.exists():
            raise FileNotFoundError(f"Arquivo de entrada não encontrado: {self.input_path}")
        self.workbook = pd.ExcelFile(self.input_path)

    def read_input_workbook(self):
        sheet_names = self.workbook.sheet_names

        # Separa README se existir
        if "README" in sheet_names:
            self.readme = pd.read_excel(self.workbook, sheet_name="README")

        data_sheets = [s for s in sheet_names if s.upper() != "README"]
        dataframes = []

        for sheet in data_sheets:
            # Lê com o cabeçalho correto na linha index 1 (segunda linha)
            df = pd.read_excel(self.workbook, sheet_name=sheet, header=1)

            # Remove colunas 'Unnamed' decorrentes de formatação da planilha original
            df = df.loc[:, ~df.columns.str.contains("^Unnamed")].copy()

            # Garante que x1 e x2 são numéricos e descarta linhas inválidas/em branco
            df["x1"] = pd.to_numeric(df["x1"], errors="coerce")
            df["x2"] = pd.to_numeric(df["x2"], errors="coerce")
            df = df.dropna(subset=["x1", "x2"]).copy()

            dataframes.append(df)

        # Concatena todas as abas criando uma única tabela com 1 único cabeçalho
        self.raw_dataset = pd.concat(dataframes, ignore_index=True)

    def prepare_output_dataset(self):
        df = self.raw_dataset.copy()

        # 1. Conversão de Temperatura para Kelvin -> "T (K)"
        is_celsius = df["Temperature Unit"].astype(str).str.contains("Celsius", case=False, na=False)
        df["T (K)"] = np.where(is_celsius, df["Temperature"] + 273.15, df["Temperature"])

        # 2. Conversão de Pressão para atm -> "P (atm)"
        is_bar = df["Pressure Unit"].astype(str).str.contains("bar", case=False, na=False)
        df["P (atm)"] = np.where(is_bar, df["Pressure"] / 1.01325, df["Pressure"])

        # 3. Cálculo das Molalidades b1 e b2 (mols / kg de H2O) com base nas unidades do README
        b1_list, b2_list = [], []
        for _, row in df.iterrows():
            salt1, salt2 = row["Salt 1"], row["Salt 2"]
            x1_val, x2_val = row["x1"], row["x2"]
            unit = str(row["x unit"]).strip().upper()

            mw1 = self.MOLAR_MASSES.get(salt1, 58.44)
            mw2 = self.MOLAR_MASSES.get(salt2, 58.44)

            # Para G_100G_MIX ou SAT_SOL_WT%: g soluto por 100g de solução
            if unit in ["G_100G_MIX", "SAT_SOL_WT%"]:
                mass_water = 100.0 - (x1_val + x2_val)
                b1 = (x1_val / mw1) / (mass_water / 1000.0) if mass_water > 0 else np.nan
                b2 = (x2_val / mw2) / (mass_water / 1000.0) if mass_water > 0 else np.nan
            else:
                # Caso padrão para g soluto / 100g mistura
                mass_water = 100.0 - (x1_val + x2_val)
                b1 = (x1_val / mw1) / (mass_water / 1000.0) if mass_water > 0 else np.nan
                b2 = (x2_val / mw2) / (mass_water / 1000.0) if mass_water > 0 else np.nan

            b1_list.append(b1)
            b2_list.append(b2)

        b1_array = np.array(b1_list)
        b2_array = np.array(b2_list)

        # 4. Cálculo das frações molares da mistura (x1, x2, xH2O)
        nH2O = 1000.0 / self.MW_H2O  # mols de H2O em 1 kg (~55.508 mol)
        n_total = b1_array + b2_array + nH2O

        df["x1"] = b1_array / n_total
        df["x2"] = b2_array / n_total
        df["xH2O"] = nH2O / n_total

        # 5. Cálculo da molalidade total (b_total em mol/kg de H2O)
        df["b_total (mol/kg)"] = b1_array + b2_array

        # 6. Formatação final na sequência exata solicitada
        output_columns = [
            "Salt 1",
            "Salt 2",
            "T (K)",
            "P (atm)",
            "x1",
            "x2",
            "xH2O",
            "b_total (mol/kg)",
        ]
        self.output_dataset = df[output_columns].copy()

    def save_output_workbook(self):
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        with pd.ExcelWriter(self.output_path, engine="openpyxl") as writer:
            if self.readme is not None:
                self.readme.to_excel(writer, sheet_name="README", index=False)
            self.output_dataset.to_excel(writer, sheet_name="Processed_Data", index=False)