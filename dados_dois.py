import pandas as pd
import numpy as np
from samplics.categorical import Tabulation
from samplics.utils.types import PopParam  # <-- Importação necessária para corrigir o erro do parâmetro

# Carregando a base de dados
amostra = pd.read_excel('DADOS/base_amostral_2_censo.xlsx')

#print(list(amostra.columns))
#dados = amostra[['13.1', '13.2.1', '13.2.2', '13.2.3', '13.2.4', '13.3.1', '13.3.2', '13.3.3', '13.3.4', '13.3.5', '13.3.6', '13.3.7']]
#dados = amostra[['13.1', '13.1.1']]

#print(dados)

#valores = amostra['13.2.1'].unique()
#print(valores)

#valores2 = amostra['13.2.2'].unique()
#print(valores2)

#Você usa a internet? Sim, nesse celular, não se aplica
#print(list(amostra['13.2.1']))

#pseudoidea

# 13.1 - VOCÊ TEM CELULAR? (Sim, Não, Não respondeu)

# SE 13.1 == Sim
# 13.2 - VOCÊ ACESSA A INTERNET NESSE CELULAR OU EM OUTROS APARELHOS?
# 13.2.1 - Sim, nesse celular
# 13.2.2 - Sim em outros aparelhos
# 13.2.3 - Não acesso
# 13.2.4 - Não respondeu

# SE 13.2.1 e/ou 13.2.2 == Sim
# 13.3 - EM QUAL LOCAL VOCÊ USA INTERNET?
# 13.3.1 - Própria de dados móveis ???????
# 13.3.2 - Em casa ou onde dorme
# 13.3.3 - Serviços públicos 
# 13.3.4 - Lugares comerciais
# 13.3.5 - Lugares sociais
# 13.3.6 - Não sabe
# 13.3.7 - Não respondeu

#fator = amostra['fator']
#print(fator)

# FATOR - quantas pessoas aquela resposta representa
# esstimativa total = somatório(valor x fator)

#TESTE 1: 

#  Quantidade de pessoas entrevistadas (linhas na amostra)
n_entrevistados = len(amostra[amostra['13.1'].notna()]) # .notna() é para não mostrar nulos ou NAN
# no dados.py deu 3520!!! em 2025

# Total de pessoas que elas representam no mundo real (soma do fator)
N_populacao = amostra[amostra['13.1'].notna()]['fator'].sum()

print(f"Quantidade de pessoas entrevistadas: {n_entrevistados}")
print(f"Total de pessoas representadas na população: {N_populacao:,.0f}")

# 1. Instanciar a classe Tabulation configurada para CONTAR (param="count")
tab = Tabulation(param=PopParam.count)

# 2. Executar a tabulação na coluna de interesse usando o peso 'fator'
# (Substitua 'sua_coluna' pelo nome real da variável que quer analisar)
tab.tabulate(vars=amostra['13.1'], samp_weight=amostra['fator'])

# 3. Exibir o resultado completo
print(tab)


""" 

V1: 
def calcular_estimativas_cv(df, coluna_grupo, coluna_peso='fator'):
   
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

# Você tem celular? 13.1
Tem_cel = calcular_estimativas_cv(amostra, '13.1', coluna_peso='fator')
print("Você tem celular?")
print(Tem_cel, "\n")

# Você acessa a internet nesse celular ou em outros aparelhos? (REVISAR ISSO AQUI)
#(Regra: Habilitar para quem respondeu “Sim” na 13.1)
amostra_sim_13_1 = amostra[amostra['13.1'] == 'Sim']

# Rever isso aqui, acho que pode estar equivocado
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

print("Locais de uso")
print(casa, "\n")

print()
"""


#V2: 

import pandas as pd
import numpy as np
from samplics.categorical import Tabulation
from samplics.utils.types import PopParam

def calcular_estimativas_cv(df, coluna_grupo, coluna_peso='fator'):
    """
    Calcula totais, proporções, erro padrão e CV considerando o peso amostral.
    Garante o alinhamento correto dos dados via merge e protege contra bases vazias.
    """
    # 1. Limpar nulos para a coluna atual
    df_clean = df.dropna(subset=[coluna_grupo, coluna_peso]).copy()
    
    # --- PROTEÇÃO CONTRA ZERO DIVISION ERROR (ADICIONADO AQUI) ---
    # Se a base filtrada estiver vazia ou a soma dos pesos for zero, evitamos o Samplics
    if df_clean.empty or df_clean[coluna_peso].sum() == 0:
        print(f"Aviso: Nenhuma observação válida encontrada para '{coluna_grupo}'. Ignorando Samplics.")
        # Retorna um DataFrame vazio com a mesma estrutura para não quebrar os prints seguintes
        return pd.DataFrame(columns=[coluna_grupo, 'n_ponderado', 'cv', 'proporcao'])
    
    # 2. Calcular Totais Ponderados
    tab_total = Tabulation(param=PopParam.count)
    tab_total.tabulate(vars=df_clean[coluna_grupo], samp_weight=df_clean[coluna_peso])
    df_total = tab_total.to_dataframe()
    
    # 3. Calcular Proporções
    tab_prop = Tabulation(param=PopParam.prop)
    tab_prop.tabulate(vars=df_clean[coluna_grupo], samp_weight=df_clean[coluna_peso])
    df_prop = tab_prop.to_dataframe()
    
    # Identificar nomes das colunas dinamicamente
    col_total_name = PopParam.count if PopParam.count in df_total.columns else str(PopParam.count)
    col_prop_name = PopParam.prop if PopParam.prop in df_prop.columns else str(PopParam.prop)

    # 4. Unir os DataFrames pela coluna 'category' para evitar desalinhamento
    df_final = pd.merge(
        df_total[['category', col_total_name, 'stderror']], 
        df_prop[['category', col_prop_name]], 
        on='category'
    )
    
    # 5. Renomear e Calcular Indicadores
    df_final = df_final.rename(columns={
        'category': coluna_grupo,
        col_total_name: 'n_ponderado',
        'stderror': 'erro_padrao',
        col_prop_name: 'proporcao'
    })
    
    # CV = Erro Padrão / Estimativa
    df_final['cv'] = df_final['erro_padrao'] / df_final['n_ponderado']
    df_final['n_ponderado'] = df_final['n_ponderado'].round()
    
    # Ordenar e selecionar colunas finais
    df_final = df_final.sort_values(by='n_ponderado', ascending=False).reset_index(drop=True)
    return df_final[[coluna_grupo, 'n_ponderado', 'cv', 'proporcao']]

# =========================================================
# APLICAÇÃO CORRIGIDA SEGUINDO O FLUXO DO QUESTIONÁRIO
# =========================================================

# --- BLOCO 13.1 ---
# Universo: Todos os entrevistados
Tem_cel = calcular_estimativas_cv(amostra, '13.1')
print("13.1 - Você tem celular?")
print(Tem_cel, "\n")


# --- BLOCO 13.2 ---
# Universo FILTRADO: Apenas quem respondeu 'Sim' na 13.1
amostra_sim_13_1 = amostra[amostra['13.1'] == 'Sim'].copy()

# 13.2 - VOCÊ ACESSA A INTERNET NESSE CELULAR OU EM OUTROS APARELHOS?
# 13.2.3 - Não acesso
# 13.2.4 - Não respondeu

Acesso_net  = calcular_estimativas_cv(amostra_sim_13_1, '13.2.1') # 13.2.1 - Sim, nesse celular
Acesso_net2 = calcular_estimativas_cv(amostra_sim_13_1, '13.2.2') # 13.2.2 - Sim em outros aparelhos
Acesso_net3 = calcular_estimativas_cv(amostra_sim_13_1, '13.2.3') # 13.2.4 - Não respondeu

print("13.2.1 - Sim, nesse celular")
print(Acesso_net, "\n")

print("13.2.2 - Sim, em outros aparelhos")
print(Acesso_net2, "\n")

print("13.2.3 - Não acesso")
print(Acesso_net3, "\n")

print("13.2.4 - Não respondeu")

# =========================================================
# --- BLOCO 13.3 – EM QUAL LOCAL VOCÊ USA A INTERNET? ---
# =========================================================

# Buscando de forma parcial pela palavra 'Sim' para capturar qualquer variação de texto
# Para quem respondeu "Sim, nesse celular" e "Sim, em outros aparelhos"
amostra_internet = amostra_sim_13_1[
    (amostra_sim_13_1['13.2.1'].str.contains('Sim', na=False)) | 
    (amostra_sim_13_1['13.2.2'].str.contains('Sim', na=False))
].copy()

#As opções de resposta: 
dados         = calcular_estimativas_cv(amostra_internet, '13.3.1') # 1. Própria de dados móveis (3G, 4G ou 5G de uma operadora, como Claro, Vivo e Tim)
casa          = calcular_estimativas_cv(amostra_internet, '13.3.2') # 2. Em casa ou onde dorme
serv_publicos = calcular_estimativas_cv(amostra_internet, '13.3.3') # 3. Serviços públicos (Bibliotecas, rodoviária, CREAS, CRAS, Centro Pop e outros)
comercio      = calcular_estimativas_cv(amostra_internet, '13.3.4') # 4. Lugares comerciais (shoppings, mercados e outros)
inst_sociais  = calcular_estimativas_cv(amostra_internet, '13.3.5') # 5. Instituições sociais (igreja, ONGs e outros)

print("13.3.1")
print(dados, "\n")

print("13.3.2 - Uso de Internet em Casa:")
print(casa, "\n")

print("13.3.3 - Uso de Internet em serviços públicos:")
print(serv_publicos, "\n")

print("13.3.4 - Uso de Internet em comércio:")
print(comercio, "\n")

print("13.3.5 - Uso de Internet em instituições sociais:")
print(inst_sociais, "\n")
print("OBS: Estimativa com alta variabilidade amostral (CV > 30%), deve ser interpretada apenas como tendência".)

#"""