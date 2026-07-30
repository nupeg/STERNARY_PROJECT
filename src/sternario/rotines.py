from pathlib import Path
import numpy as np
import pandas as pd


class DataProcessor:
    """
    Classe responsável por carregar, unificar, converter unidades físico-químicas
    e exportar os dados processados de misturas ternárias de sais.
    
    As massas molares são calculadas dinamicamente com base nas colunas
    'Salt 1 code' e 'Salt 2 code'.
    """

    # Massas atômicas dos elementos (g/mol) + Grupo SO4
    ATOMIC_MASSES = {
        "F": 18.9984,
        "Cl": 35.4530,
        "Br": 79.9040,
        "I": 126.9045,
        "Li": 6.9410,
        "Na": 22.9898,
        "K": 39.0983,
        "Rb": 85.4678,
        "Cs": 132.9055,
        "Mg": 24.3050,
        "Ca": 40.0780,
        "SO4": 96.0600,  # S (32.06) + 4 * O (15.999)
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

    def parse_salt_code(self, code):
        """
        Interpreta dinamicamente os códigos das colunas 'Salt X code'
        e calcula a massa molar (g/mol) do sal correspondente.
        
        Exemplos de entrada: 'Na_1_Cl_1', 'Ca_1_SO4_1', 'Na_2_SO_4', 'Li_2_SO4_1'
        """
        if not isinstance(code, str) or pd.isna(code):
            return np.nan

        parts = [p.strip() for p in str(code).split("_") if p.strip()]
        mw = 0.0
        i = 0

        while i < len(parts):
            elem = parts[i]

            # Trata variação em que o SO4 foi codificado como 'SO' e '4' separados
            if elem == "SO" and i + 1 < len(parts) and parts[i + 1] == "4":
                mw += self.ATOMIC_MASSES["SO4"]
                i += 2
                continue

            # Verifica se o elemento seguinte representa a quantidade
            if i + 1 < len(parts) and parts[i + 1].isdigit():
                qty = float(parts[i + 1])
                i += 2
            else:
                qty = 1.0
                i += 1

            if elem in self.ATOMIC_MASSES:
                mw += self.ATOMIC_MASSES[elem] * qty
            elif elem.isdigit():
                continue

        return mw if mw > 0 else np.nan

    def read_input_workbook(self):
        """
        Lê todas as abas de dados da planilha, limpa linhas/colunas nulas ou 'Unnamed',
        e concatena tudo em um único DataFrame com um único cabeçalho.
        """
        sheet_names = self.workbook.sheet_names

        # Tratamento e limpeza da aba README (removendo colunas/linhas vazias Unnamed)
        if "README" in sheet_names:
            readme_df = pd.read_excel(self.workbook, sheet_name="README")
            readme_df = readme_df.loc[:, ~readme_df.columns.str.contains("^Unnamed")].dropna(how="all")
            self.readme = readme_df

        data_sheets = [s for s in sheet_names if s.upper() != "README"]
        dataframes = []

        for sheet in data_sheets:
            # Lê definindo o cabeçalho na segunda linha (índice 1)
            df = pd.read_excel(self.workbook, sheet_name=sheet, header=1)

            # Remove colunas 'Unnamed' decorrentes da formatação
            df = df.loc[:, ~df.columns.str.contains("^Unnamed")].copy()

            # Força x1 e x2 para formato numérico e descarta linhas vazias
            df["x1"] = pd.to_numeric(df["x1"], errors="coerce")
            df["x2"] = pd.to_numeric(df["x2"], errors="coerce")
            df = df.dropna(subset=["x1", "x2"]).copy()

            dataframes.append(df)

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

        # 3. Cálculo dinâmico da Molalidade b1 e b2 (mol/kg de H2O) por interpretação do código
        b1_list, b2_list = [], []
        for _, row in df.iterrows():
            salt1_code = row.get("Salt 1 code")
            salt2_code = row.get("Salt 2 code")
            x1_val, x2_val = row["x1"], row["x2"]
            unit = str(row["x unit"]).strip().upper()

            # Cálculo dinâmico das massas molares (retorna np.nan em caso de erro/código ausente)
            mw1 = self.parse_salt_code(salt1_code)
            mw2 = self.parse_salt_code(salt2_code)

            # --- Regras de conversão baseadas nos códigos do README ---
            if unit == "SAT_SOL_WT%":
                # Gramas de soluto por 100g de solução total (mistura)
                mass_water = 100.0 - (x1_val + x2_val)
                b1 = (x1_val / mw1) / (mass_water / 1000.0) if mass_water > 0 else np.nan
                b2 = (x2_val / mw2) / (mass_water / 1000.0) if mass_water > 0 else np.nan

            elif unit in ["G_100G_MIX", "G_CM3_SOL"]:
                # Gramas de soluto por 100g (0.1 kg) de solvente H2O
                b1 = (x1_val / mw1) / 0.1
                b2 = (x2_val / mw2) / 0.1

            elif unit == "G_L_SOL":
                # Gramas de soluto por 1000g (1.0 kg) de solvente H2O
                b1 = x1_val / mw1
                b2 = x2_val / mw2

            elif unit == "GMOL_SOL":
                # Mols de soluto por kg de solvente H2O
                b1 = x1_val
                b2 = x2_val

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
        """Salva a planilha de saída limpa sem colunas Unnamed."""
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        with pd.ExcelWriter(self.output_path, engine="openpyxl") as writer:
            if self.readme is not None and not self.readme.empty:
                self.readme.to_excel(writer, sheet_name="README", index=False)
            self.output_dataset.to_excel(writer, sheet_name="Processed_Data", index=False)