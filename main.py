from sternario.rotines import processar_e_concatenar_planilha, gerar_planilhas_por_dupla

def main():
    print("==================================================")
    print("   INICIANDO PROCESSAMENTO - MISTURA TERNÁRIA     ")
    print("==================================================\n")
    
    caminho_entrada = r"C:\Users\labsi\Documents\densidade_mistura_ternaria\data\tabela de sais linke.xlsx"
    caminho_saida = r"C:\Users\labsi\Documents\densidade_mistura_ternaria\teste\dados preliminares concatenados.xlsx"
    pasta_misturas = r"C:\Users\labsi\Documents\densidade_mistura_ternaria\teste\planilhas_duplas"
    
    print("[ETAPA 1] Leitura, Concatenação e Filtro por Temperatura")
    df_filtrado = processar_e_concatenar_planilha(caminho_entrada, caminho_saida)
    
    print("[ETAPA 2] Separação por Duplas e Cálculo das Molalidades")
    gerar_planilhas_por_dupla(df_filtrado, pasta_saida=pasta_misturas)
    
    print("\n==================================================")
    print("              PROCESSAMENTO CONCLUÍDO             ")
    print("==================================================")


if __name__ == "__main__":
    main()