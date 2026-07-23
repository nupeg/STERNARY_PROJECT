import os
import pandas as pd

# Dicionário de Massas Molares dos Sais envolvidos em kg/mol
MOLAR_MASSES_KG_MOL = {
    'CaCl2': 0.11098,
    'MgCl2': 0.09521,
    'NaCl': 0.05844,
    'KCl': 0.074551,
    'Na2SO4': 0.14204,
    'K2SO4': 0.17426,
    'MgSO4': 0.12036,
    'CaSO4': 0.13614,
    'Li2SO4': 0.10994,
    'LiCl': 0.04239,
    'NaBr': 0.10289,
    'KBr': 0.11900,
    'NaI': 0.14989,
    'KI': 0.16600,
    'KF': 0.05810,
}


def processar_e_concatenar_planilha(caminho_entrada: str, caminho_saida: str) -> pd.DataFrame:
    """
    1. Lê a aba README separadamente.
    2. Concatena todas as abas de dados de sais mantendo apenas um cabeçalho.
    3. Filtra mantendo apenas temperaturas entre 5°C e 95°C (inclusive).
    4. Salva o resultado preliminar concatenado no local especificado.
    5. Retorna o DataFrame concatenado e filtrado.
    """
    print(f"--> Carregando arquivo de entrada: {caminho_entrada}")
    xls = pd.ExcelFile(caminho_entrada)
    
    # 1. Isolando a aba README
    print("--> Processando aba README...")
    df_readme = pd.read_excel(xls, sheet_name='README')
    
    # 2. Concatenação das abas de sais
    print("--> Concatenando abas de dados...")
    data_frames = []
    
    for sheet_name in xls.sheet_names:
        if sheet_name == 'README':
            continue
        
        # Lê a aba de dados
        df = pd.read_excel(xls, sheet_name=sheet_name)
        
        # A linha 0 da planilha contém os nomes reais das colunas
        cols = df.iloc[0].values
        df_dados = df.iloc[1:].copy()
        df_dados.columns = cols
        
        # Descarta a primeira coluna vazia se existir
        if pd.isna(df_dados.columns[0]) or str(df_dados.columns[0]).startswith('Unnamed'):
            df_dados = df_dados.iloc[:, 1:]
            
        data_frames.append(df_dados)
    
    # Une todos os DataFrames de sais em um único
    df_concatenado = pd.concat(data_frames, ignore_index=True)
    total_inicial = len(df_concatenado)
    print(f"--> Total de registros antes do filtro: {total_inicial}")
    
    # 3. Filtragem de Temperatura (elimina < 5 e > 95)
    print("--> Aplicando filtro de temperatura (5 <= T <= 95)...")
    df_concatenado['Temperature'] = pd.to_numeric(df_concatenado['Temperature'], errors='coerce')
    
    df_filtrado = df_concatenado[
        (df_concatenado['Temperature'] >= 5) & 
        (df_concatenado['Temperature'] <= 95)
    ].copy()
    
    # Limpa possíveis linhas de observações nos nomes dos sais
    df_filtrado = df_filtrado[
        ~df_filtrado['Salt 1'].astype(str).str.contains('obs:', case=False, na=False) &
        ~df_filtrado['Salt 2'].astype(str).str.contains('obs:', case=False, na=False)
    ].copy()
    
    total_final = len(df_filtrado)
    removidos = total_inicial - total_final
    print(f"--> Registros restantes: {total_final} (Foram removidas {removidos} linhas)")
    
    # 4. Criando diretório de destino e salvando arquivo temporário/preliminar
    diretorio_destino = os.path.dirname(caminho_saida)
    if diretorio_destino and not os.path.exists(diretorio_destino):
        os.makedirs(diretorio_destino, exist_ok=True)
        print(f"--> Diretório criado: {diretorio_destino}")
        
    print(f"--> Salvando arquivo preliminar concatenado em: {caminho_saida}")
    with pd.ExcelWriter(caminho_saida, engine='openpyxl') as writer:
        df_readme.to_excel(writer, sheet_name='README', index=False)
        df_filtrado.to_excel(writer, sheet_name='Dados Concatenados', index=False)
        
    print("--> Concatenação finalizada com sucesso!\n")
    return df_filtrado


def gerar_planilhas_por_dupla(df_filtrado: pd.DataFrame, pasta_saida: str):
    """
    Recebe o DataFrame concatenado/filtrado e gera uma planilha no modelo da
    mistura ternária para cada dupla única de sais encontrada.
    """
    print(f"--> [ETAPA 2] Gerando planilhas no formato padrão em: {pasta_saida}")
    os.makedirs(pasta_saida, exist_ok=True)
    
    agrupado = df_filtrado.groupby(['Salt 1', 'Salt 2'])
    total_planilhas = 0

    for (sal1, sal2), grupo in agrupado:
        # Pula se sal1 ou sal2 for inválido
        if pd.isna(sal1) or pd.isna(sal2):
            continue

        nome_arquivo = f"{sal1}-{sal2}.xlsx"
        caminho_arquivo = os.path.join(pasta_saida, nome_arquivo)

        # Busca massa molar (padrão 0.1 kg/mol caso não esteja listado)
        mm1 = MOLAR_MASSES_KG_MOL.get(str(sal1).strip(), 0.1)
        mm2 = MOLAR_MASSES_KG_MOL.get(str(sal2).strip(), 0.1)

        # Monta DataFrame estruturado no cabeçalho exato da planilha modelo
        df_modelo = pd.DataFrame()

        df_modelo['sal1'] = grupo['Salt 1']
        df_modelo['sal2'] = grupo['Salt 2']
        df_modelo['MM1 / (kg/mol)'] = mm1
        df_modelo['MM2 / (kg/mol)'] = mm2

        # Fração mássica w (convertendo x1 e x2 de g/100g para fração decimal)
        x1_val = pd.to_numeric(grupo['x1'], errors='coerce') / 100.0
        x2_val = pd.to_numeric(grupo['x2'], errors='coerce') / 100.0

        df_modelo['w1'] = x1_val
        df_modelo['w2'] = x2_val
        df_modelo['wH2O'] = 1.0 - df_modelo['w1'] - df_modelo['w2']

        # Base mtotal = 100 kg
        df_modelo['mtotal'] = 100.0
        df_modelo['m1 / (kg)'] = df_modelo['w1'] * df_modelo['mtotal']
        df_modelo['m2 / (kg)'] = df_modelo['w2'] * df_modelo['mtotal']
        df_modelo['mH2O / (kg)'] = df_modelo['wH2O'] * df_modelo['mtotal']

        # Cálculo da Molalidade b = m_sal / (MM_sal * m_H2O) em mol/kg
        df_modelo['b_sal1 / (mol/kg)'] = df_modelo['m1 / (kg)'] / (df_modelo['MM1 / (kg/mol)'] * df_modelo['mH2O / (kg)'])
        df_modelo['b_sal2 / (mol/kg)'] = df_modelo['m2 / (kg)'] / (df_modelo['MM2 / (kg/mol)'] * df_modelo['mH2O / (kg)'])
        df_modelo['b_total / (mol/kg)'] = df_modelo['b_sal1 / (mol/kg)'] + df_modelo['b_sal2 / (mol/kg)']

        # Frações molares/iónicas dos sais
        df_modelo['x1'] = df_modelo['b_sal1 / (mol/kg)'] / df_modelo['b_total / (mol/kg)']
        df_modelo['x2'] = df_modelo['b_sal2 / (mol/kg)'] / df_modelo['b_total / (mol/kg)']

        # Temperatura e Pressão
        temp_c = pd.to_numeric(grupo['Temperature'], errors='coerce')
        df_modelo['temperature / (ºC)'] = temp_c
        df_modelo['temperature / (K)'] = temp_c + 273.15
        df_modelo['pressure / (atm)'] = 1.0

        # Densidade experimental (se existir na tabela de entrada)
        if 'Density' in grupo.columns:
            dens = pd.to_numeric(grupo['Density'], errors='coerce')
            # Converte g/cm³ -> kg/m³ se necessário
            df_modelo['density / (kg/m³)'] = dens.apply(lambda v: v * 1000.0 if pd.notna(v) and v < 10 else v)
        else:
            df_modelo['density / (kg/m³)'] = None

        # Campos reservados para Dinâmica Molecular (MD)
        df_modelo['density_MD'] = None
        df_modelo['diff'] = None
        df_modelo['diff_percent'] = None
        df_modelo['T_MD'] = None
        df_modelo['M_MD'] = None

        # Salva o arquivo individual
        df_modelo.to_excel(caminho_arquivo, index=False)
        total_planilhas += 1
        print(f"   [+] Gerada: {nome_arquivo} ({len(df_modelo)} linhas)")

    print(f"--> Total de {total_planilhas} planilhas geradas com sucesso!")