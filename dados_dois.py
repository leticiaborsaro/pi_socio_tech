import pandas as pd
import numpy as np
from samplics.categorical import Tabulation
from samplics.utils.types import PopParam  # <-- Importação necessária para corrigir o erro do parâmetro

# Carregando a base de dados
amostra = pd.read_excel('DADOS/base_amostral_2_censo.xlsx')

def calcular_estimativas_cv(df, coluna_grupo, coluna_peso='fator'):
    """
    Replica o comportamento do survey_total(vartype="cv") do R.
    Calcula totais, proporções, erro padrão e CV considerando o peso amostral.
    """
    # 1. Limpar nulos apenas para as colunas que vamos usar (evita erros no cálculo)
    df_clean = df.dropna(subset=[coluna_grupo, coluna_peso]).copy()
    
    # 2. Calcular Totais Ponderados e Erro Padrão
    # Usando o PopParam.count conforme exigido pela biblioteca
    tab_total = Tabulation(param=PopParam.count)
    tab_total.tabulate(vars=df_clean[coluna_grupo], samp_weight=df_clean[coluna_peso])
    df_total = tab_total.to_dataframe()

    tabela = tab_total.to_dataframe()
    
    # Renomear colunas para o nosso padrão
    df_total = df_total.rename(columns={
        'category': coluna_grupo, # O samplics costuma retornar a categoria na coluna '_level'
        PopParam.count: 'n_ponderado',
        'stderror': 'erro_padrao'
    })
    
    # Calcular o CV: Coeficiente de Variação = Erro Padrão / Estimativa
    df_total['cv'] = df_total['erro_padrao'] / df_total['n_ponderado']
    
    # 3. Calcular Proporções
    # Usando o PopParam.prop conforme exigido pela biblioteca
    tab_prop = Tabulation(param=PopParam.prop)
    tab_prop.tabulate(vars=df_clean[coluna_grupo], samp_weight=df_clean[coluna_peso])
    df_prop = tab_prop.to_dataframe()

    # Trazer a proporção para o DataFrame principal
    df_total['proporcao'] = df_prop[PopParam.prop]
    
    # 4. Formatação e Arredondamento
    df_total['n_ponderado'] = df_total['n_ponderado'].round()
    
    # Ordenar de forma decrescente
    df_total = df_total.sort_values(by='n_ponderado', ascending=False).reset_index(drop=True)
    
    # Selecionar apenas as colunas de interesse
    return df_total[[coluna_grupo, 'n_ponderado', 'cv', 'proporcao']]


# =========================================================
# APLICAÇÃO NO SEU SCRIPT: Acesso à internet ----
# =========================================================

# Você tem celular?
Tem_cel = calcular_estimativas_cv(amostra, '13.1', coluna_peso='fator')
print("Você tem celular?")
print(Tem_cel, "\n")

# Você acessa a internet nesse celular ou em outros aparelhos?
amostra_sim_13_1 = amostra[amostra['13.1'] == 'Sim']

Acesso_net  = calcular_estimativas_cv(amostra_sim_13_1, '13.2.1')
Acesso_net2 = calcular_estimativas_cv(amostra_sim_13_1, '13.2.2')
Acesso_net3 = calcular_estimativas_cv(amostra_sim_13_1, '13.2.3')

# Em qual local você usa internet?
dados = calcular_estimativas_cv(
    amostra[amostra['13.3.1'] != 'Não se aplica'], 
    '13.3.1'
)

casa = calcular_estimativas_cv(
    amostra[amostra['13.3.2'] != 'Não se aplica'], 
    '13.3.2'
)

serv_publicos = calcular_estimativas_cv(
    amostra[amostra['13.3.3'] != 'Não se aplica'], 
    '13.3.3'
)

comercio = calcular_estimativas_cv(
    amostra[amostra['13.3.4'] != 'Não se aplica'], 
    '13.3.4'
)

inst_sociais = calcular_estimativas_cv(
    amostra[amostra['13.3.5'] != 'Não se aplica'], 
    '13.3.5'
)

# Exibindo os resultados das outras variáveis para conferir
print("Acesso à internet - 13.2.1")
print(Acesso_net, "\n")

print("Local de uso - Casa")
print(casa, "\n")