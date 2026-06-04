from flask import Flask, render_template
import pandas as pd
import geopandas as gpd
import plotly.express as px
from shapely import wkt
import json
import numpy as np
from samplics.categorical import Tabulation
from samplics.utils.types import PopParam  # <-- Importação necessária para corrigir o erro do parâmetro da amostra

# FUNCÃO PARA CALCULO AMOSTRAL POSTERIOR
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


# inicia o app Flask
app = Flask(__name__)

# --- Carregamento de Dados PARTE 1 ---

# Base do censo populacional (PSR 2022)
def base_cen_2022(): 
    df_psr = pd.read_excel(
    "https://docs.google.com/spreadsheets/d/1kUtdHRKd_UhLYwe3RVtPhI5-7J-LosBU/export?format=xlsx",
    engine='openpyxl'
    )
    
    # Base geográfica das RAs (CSV com WKT)
    csv_url = 'https://raw.githubusercontent.com/leticiaborsaro/pi_socio_tech/main/DADOS/Limite_RA_20190.csv'
    df_raw_geo_temp = pd.read_csv(csv_url)

    # Converte WKT para objetos de geometria
    df_raw_geo_temp['geometry'] = df_raw_geo_temp['the_geom'].apply(wkt.loads)
    df_raw_geo = df_raw_geo_temp

    # --- Limpeza e Seleção de Colunas ---

    print("--- Verificação e Limpeza de Dados ---")

    df_psr_relevant_cols = ['Região Administrativa', 'ID_CONTROLE']
    df_raw_geo_relevant_cols = ['ra', 'geometry', 'the_geom']

    # Remove NaNs nas colunas essenciais do df_psr
    initial_rows_df_psr = len(df_psr)
    for col in df_psr_relevant_cols:
        if col in df_psr.columns:
            if df_psr[col].isnull().sum() > 0:
                df_psr.dropna(subset=[col], inplace=True)

    df_psr = df_psr[[col for col in df_psr_relevant_cols if col in df_psr.columns]]

    # Remove NaNs nas colunas essenciais do geo_df
    initial_rows_df_raw_geo = len(df_raw_geo)
    for col in df_raw_geo_relevant_cols:
        if col in df_raw_geo.columns:
            if df_raw_geo[col].isnull().sum() > 0:
                df_raw_geo.dropna(subset=[col], inplace=True)

    df_raw_geo = df_raw_geo[[col for col in df_raw_geo_relevant_cols if col in df_raw_geo.columns]]

    # --- Processamento Populacional e Geográfico ---

    # Agrupa contagem por RA
    region_counts = df_psr.groupby('Região Administrativa')['ID_CONTROLE'].count().reset_index()
    region_counts.rename(columns={'ID_CONTROLE': 'count'}, inplace=True)

    # Cria GeoDataFrame e define o sistema de coordenadas (WGS84)
    gdf_ra = gpd.GeoDataFrame(df_raw_geo, geometry='geometry')
    gdf_ra = gdf_ra.set_crs(epsg=4326, allow_override=True)

    # --- Análise de Discrepâncias ---
    print("\n--- Análise de Discrepâncias de Regiões ---")
    unique_regions_psr = set(df_psr['Região Administrativa'].unique())
    unique_regions_gdf = set(gdf_ra['ra'].unique())

    print(f"RAs no PSR: {len(unique_regions_psr)} | RAs no Mapa: {len(unique_regions_gdf)}")
    print(f"Não mapeadas: {unique_regions_psr - unique_regions_gdf}")
    print(f"Sem dados: {unique_regions_gdf - unique_regions_psr}")

    # --- Cruzamento de Dados ---

    # Une bases geográficas e populacionais (left join)
    gdf_merged_ra = gdf_ra.merge(
        region_counts,
        left_on='ra',
        right_on='Região Administrativa',
        how='left'
    )

    # Trata valores vazios como zero
    gdf_merged_ra['count'] = pd.to_numeric(gdf_merged_ra['count'], errors='coerce').fillna(0)
    gdf_merged_ra = gdf_merged_ra.to_crs(epsg=4326)

    # Extrai interface GeoJSON para o Plotly
    geojson_dict = gdf_merged_ra.__geo_interface__

    # --- Configuração do Mapa ---

    max_count = gdf_merged_ra['count'].max()

    # Escala de cores: Cinza para zero, Tons de Vermelho para > 0
    if max_count == 0:
        custom_color_scale_tuples = [(0.0, 'lightgray'), (1.0, 'lightgray')]
    else:
        custom_color_scale_tuples = [(0.0, 'lightgray')]
        red_colors = px.colors.sequential.Reds[2:] # Pula tons muito claros
        min_positive_z = 1 / max_count

        for i, color in enumerate(red_colors):
            z = min_positive_z + (1.0 - min_positive_z) * (i / (len(red_colors) - 1))
            custom_color_scale_tuples.append((z, color))

    # Gera mapa coroplético
    fig = px.choropleth(
        data_frame=gdf_merged_ra,
        geojson=geojson_dict,
        locations='ra',
        featureidkey='properties.ra',
        color='count',
        color_continuous_scale=custom_color_scale_tuples,
        range_color=[-0.1, 900.0],
        hover_name='ra',
        hover_data={'count': ':.0f'},
        projection='mercator',
        title='Pessoas em Situação de Rua por RA (Censo PSR DF 2022)'
    )

    # Ajustes visuais finais
    fig.update_geos(
        fitbounds='locations',
        visible=False,
        showland=True,
        landcolor='white'
    )

    fig.update_layout(
        margin={'r': 0, 't': 50, 'l': 0, 'b': 0},
        dragmode=False,
        autosize = True
    )

    return fig.to_html(full_html=False, include_plotlyjs='cdn', config={
        'scrollZoom': False,
        'responsive': True,
        'displayModeBar': False})

def base_cen_2025():

    # --- Carregamento de Dados ---

    # Base do segundo censo populacional (PSR 2025)

    df_dois_psr = pd.read_excel(
    "https://docs.google.com/spreadsheets/d/1hPqPU9oexlj3K-e3l5rdu5AW8hWkSV5M/export?format=xlsx",
    engine='openpyxl')

    # Base geográfica das RAs (CSV com WKT)
    csv_url = 'https://raw.githubusercontent.com/leticiaborsaro/pi_socio_tech/main/DADOS/Limite_RA_20190.csv'
    df_raw_geo_temp = pd.read_csv(csv_url)

    # Converte WKT para objetos de geometria
    df_raw_geo_temp['geometry'] = df_raw_geo_temp['the_geom'].apply(wkt.loads)
    df_raw_geo = df_raw_geo_temp

    # --- Limpeza e Seleção de Colunas ---

    print("--- Verificação e Limpeza de Dados ---")

    df_dois_psr_relevant_cols = ['1.1.1', 'ID'] # Colunas corretas para df_dois_psr
    df_raw_geo_relevant_cols = ['ra', 'geometry', 'the_geom']

    # Remove NaNs nas colunas essenciais do df_dois_psr
    initial_rows_df_dois_psr = len(df_dois_psr)
    for col in df_dois_psr_relevant_cols:
        if col in df_dois_psr.columns:
            if df_dois_psr[col].isnull().sum() > 0:
                df_dois_psr.dropna(subset=[col], inplace=True)

    df_dois_psr = df_dois_psr[[col for col in df_dois_psr_relevant_cols if col in df_dois_psr.columns]]

    # CHECK RÁPIDO QUANTIDADE TOTAL
    n_entrevistados = len(df_dois_psr[df_dois_psr['1.1.1'].notna()])
    print(f"######### {n_entrevistados} ###########")

    # Remove NaNs nas colunas essenciais do geo_df
    initial_rows_df_dois_raw_geo = len(df_raw_geo)
    for col in df_raw_geo_relevant_cols:
        if col in df_raw_geo.columns:
            if df_raw_geo[col].isnull().sum() > 0:
                df_raw_geo.dropna(subset=[col], inplace=True)

    df_raw_geo = df_raw_geo[[col for col in df_raw_geo_relevant_cols if col in df_raw_geo.columns]]

    # --- Processamento Populacional e Geográfico ---

    # Agrupa contagem por RA
    region_counts = df_dois_psr.groupby('1.1.1')['ID'].count().reset_index()
    region_counts.rename(columns={'ID': 'count'}, inplace=True)

    # Cria GeoDataFrame e define o sistema de coordenadas (WGS84)
    gdf_ra = gpd.GeoDataFrame(df_raw_geo, geometry='geometry')
    gdf_ra = gdf_ra.set_crs(epsg=4326, allow_override=True)

    # --- Ajuste para padronizar nomes de Regiões Administrativas entre as bases ---
    # Aplica uma limpeza geral para padronizar espaços e uso de barra
    gdf_ra['ra'] = gdf_ra['ra'].str.replace(r'\s*[/-]\s*', '/', regex=True) # Unifica '/' ou '-' e remove espaços ao redor
    gdf_ra['ra'] = gdf_ra['ra'].str.strip().str.replace(r'\s+', ' ', regex=True) # Padroniza múltiplos espaços e remove espaços extras

    # Substituições específicas para casos onde a limpeza geral não é suficiente
    gdf_ra['ra'] = gdf_ra['ra'].replace({
        'Sobradinho': 'Sobradinho I',
        'Arniqueira': 'Arniqueiras',
        'Riacho Fundo': 'Riacho Fundo I',
        'SCIA': 'Estrutural/Scia'
        # 'Sol Nascente/ Pôr do Sol' deve ser tratado pela regex acima
        # 'Sudoeste/ Octogonal' deve ser tratado pela regex e padronização de espaços
    })

    # --- Análise de Discrepâncias ---
    print("\n--- Análise de Discrepâncias de Regiões ---")
    unique_regions_psr = set(df_dois_psr['1.1.1'].unique())
    unique_regions_gdf = set(gdf_ra['ra'].unique())

    print(f"RAs no PSR: {len(unique_regions_psr)} | RAs no Mapa: {len(unique_regions_gdf)}")
    print(f"Não mapeadas: {unique_regions_psr - unique_regions_gdf}")
    print(f"Sem dados: {unique_regions_gdf - unique_regions_psr}")

    # --- Cruzamento de Dados ---

    # Une bases geográficas e populacionais (left join)
    gdf_merged_ra = gdf_ra.merge(
        region_counts,
        left_on='ra',
        right_on='1.1.1',
        how='left'
    )

    # Trata valores vazios como zero
    gdf_merged_ra['count'] = pd.to_numeric(gdf_merged_ra['count'], errors='coerce').fillna(0)
    gdf_merged_ra = gdf_merged_ra.to_crs(epsg=4326)

    # Extrai interface GeoJSON para o Plotly
    geojson_dict = gdf_merged_ra.__geo_interface__

    # --- Configuração do Mapa ---

    max_count = gdf_merged_ra['count'].max()

    # Escala de cores: Cinza para zero, Tons de Vermelho para > 0
    if max_count == 0:
        custom_color_scale_tuples = [(0.0, 'lightgray'), (1.0, 'lightgray')]
    else:
        custom_color_scale_tuples = [(0.0, 'lightgray')]
        red_colors = px.colors.sequential.Reds[2:] # Pula tons muito claros
        min_positive_z = 1 / max_count

        for i, color in enumerate(red_colors):
            z = min_positive_z + (1.0 - min_positive_z) * (i / (len(red_colors) - 1))
            custom_color_scale_tuples.append((z, color))

    # Gera mapa coroplético
    fig = px.choropleth(
        data_frame=gdf_merged_ra,
        geojson=geojson_dict,
        locations='ra',
        featureidkey='properties.ra',
        color='count',
        color_continuous_scale=custom_color_scale_tuples,
        range_color=[-0.1, 900.0],
        hover_name='ra',
        hover_data={'count': ':.0f'},
        projection='mercator',
        title='Pessoas em Situação de Rua por RA (Censo PSR DF 2025)'
    )

    # Ajustes visuais finais
    fig.update_geos(
        fitbounds='locations',
        visible=False,
        showland=True,
        landcolor='white'
    )

    fig.update_layout(
        margin={'r': 0, 't': 50, 'l': 0, 'b': 0},
        dragmode=False,
        autosize=True
    )

    return fig.to_html(full_html=False, include_plotlyjs='cdn', config={
        'scrollZoom': False,
        'responsive': True,
        'displayModeBar': False
    })

# Carregando a base de dados amostral do censo
amostra = pd.read_excel('DADOS/base_amostral_2_censo.xlsx')

def mapa_net_cel_2025(df_amostra):
    """
    Gera o mapa coroplético da proporção ponderada de uso de internet por celular por RA.
    Retorna uma string HTML pronta para ser renderizada pelo Flask.
    """
    # 1. Carregar base geográfica das RAs
    csv_url = 'https://raw.githubusercontent.com/leticiaborsaro/pi_socio_tech/main/DADOS/Limite_RA_20190.csv'
    df_raw_geo = pd.read_csv(csv_url)
    df_raw_geo['geometry'] = df_raw_geo['the_geom'].apply(wkt.loads)
    gdf_ra = gpd.GeoDataFrame(df_raw_geo, geometry='geometry')
    gdf_ra = gdf_ra.set_crs(epsg=4326, allow_override=True)

    # Padronização de nomes de RA no GeoDataFrame
    gdf_ra['ra'] = gdf_ra['ra'].str.replace(r'\s*[/-]\s*', '/', regex=True).str.strip().str.replace(r'\s+', ' ', regex=True)
    gdf_ra['ra'] = gdf_ra['ra'].replace({
        'Sobradinho': 'Sobradinho I',
        'Arniqueira': 'Arniqueiras',
        'Riacho Fundo': 'Riacho Fundo I',
        'SCIA': 'Estrutural/Scia'
    })

    gdf_ra['ra_join'] = gdf_ra['ra'].str.upper().str.strip()

    # 2. Processar dados de internet da 'amostra'
    # Filtrando apenas quem respondeu 'Sim' na pergunta de ter celular.
    # Ou seja, quem não tem celular não está incluso
    df_internet = df_amostra[df_amostra['13.1'] == 'Sim'].copy()
    df_internet['RA'] = df_internet['RA'].astype(str).str.replace(r'\s*[/-]\s*', '/', regex=True).str.strip().str.replace(r'\s+', ' ', regex=True)
    df_internet['RA'] = df_internet['RA'].replace({
        'Sobradinho': 'Sobradinho I',
        'Arniqueira': 'Arniqueiras',
        'Riacho Fundo': 'Riacho Fundo I',
        'SCIA': 'Estrutural/Scia'
    })

    # Chamada 1: Total ponderado de pessoas com celular por RA (Denominador)
    df_total_ra = calcular_estimativas_cv(df_internet, 'RA', coluna_peso='fator')
    df_total_ra = df_total_ra.rename(columns={'n_ponderado': 'total_ra'})

    # Chamada 2: Total ponderado e CV de quem ACESSA internet (Numerador e CV oficial)
    # 13.2.1 - Quem possui celular e acessa nele
    df_uso_celular = df_internet[df_internet['13.2.1'].str.contains('Sim', na=False)].copy()
    df_uso_ra = calcular_estimativas_cv(df_uso_celular, 'RA', coluna_peso='fator')
    df_uso_ra = df_uso_ra.rename(columns={'n_ponderado': 'n_ponderado_uso', 'cv': 'cv_oficial'})

    # Unimos os dois resultados gerados pela sua função usando um merge por RA
    stats_ra = pd.merge(
        df_total_ra[['RA', 'total_ra']], 
        df_uso_ra[['RA', 'n_ponderado_uso', 'cv_oficial']], 
        on='RA', 
        how='outer'
    ).fillna(0)

    # Calcular a proporção final de uso ponderado por RA
    stats_ra['proporcao_uso'] = np.where(stats_ra['total_ra'] > 0, stats_ra['n_ponderado_uso'] / stats_ra['total_ra'], 0)
    
    # Converter o CV para porcentagem para exibição no balão do mapa
    stats_ra['cv_porcentagem'] = stats_ra['cv_oficial'] * 100

    stats_ra['RA_join'] = stats_ra['RA'].str.upper().str.strip()

    # Cole isso logo após o merge das estatísticas para conferir no terminal:
    print("\n--- Verificação de Dados por RA que vão para o Mapa ---")
    print(stats_ra[['RA', 'total_ra', 'n_ponderado_uso', 'cv_porcentagem']].head(10))

    
    # Criar a classificação de confiabilidade com base no CV calculado pela função
    stats_ra['confiabilidade'] = np.select(
        [stats_ra['total_ra'] == 0, stats_ra['cv_porcentagem'] <= 15, stats_ra['cv_porcentagem'] <= 30],
        ['Sem dados amostrais', 'Alta Confiabilidade', 'Confiabilidade Moderada'],
        default='Baixa Confiabilidade (CV > 30%)'
    )

    # 3. Mesclar os dados geográficos com as estatísticas processadas
    gdf_mapa = gdf_ra.merge(stats_ra, left_on='ra_join', right_on='RA_join', how='left')

    # --- TRATAMENTO DOS NULOS PARA O HOVER NÃO EXIBIR 'NaN' ---
    gdf_mapa['proporcao_uso'] = gdf_mapa['proporcao_uso'].fillna(0)
    gdf_mapa['n_ponderado_uso'] = gdf_mapa['n_ponderado_uso'].fillna(0)
    gdf_mapa['total_ra'] = gdf_mapa['total_ra'].fillna(0)
    gdf_mapa['cv_porcentagem'] = gdf_mapa['cv_porcentagem'].fillna(0)
    gdf_mapa['confiabilidade'] = gdf_mapa['confiabilidade'].fillna('Sem dados amostrais')

    # Filtro de segurança visual para a cor do mapa
    gdf_mapa['valor'] = np.where(gdf_mapa['cv_porcentagem'] > 30, -0.1, gdf_mapa['proporcao_uso'].fillna(-0.1))
   
    # Escala de cores matemática
    custom_scale = [
        [0.0, "#d3d3d3"],       
        [0.0909, "#d3d3d3"],   
        [0.0910, "white"],     
        [0.15, "#e0f3ff"],     
        [1.0, "darkblue"]      
    ]

    # Gera o mapa coroplético enviando os dados brutos organizados no 'custom_data'
    fig = px.choropleth(
        gdf_mapa,
        geojson=gdf_mapa.__geo_interface__,
        locations='ra',
        featureidkey='properties.ra',
        color='valor',
        color_continuous_scale=custom_scale,
        range_color=[-0.1, 1.0],
        title='Uso de Internet por Celular por RA (Dados Ponderados IPEDF)',
        # Injetamos a lista ordenada de colunas que o nosso balão vai ler
        custom_data=['ra', 'proporcao_uso', 'n_ponderado_uso', 'total_ra', 'cv_porcentagem', 'confiabilidade']
    )

    # --- DESIGN DO HOVER TEMPLATE CUSTOMIZADO (HTML) ---
    # %{customdata[X]} puxa a coluna correspondente à ordem que definimos ali em cima!
    hovertemplate = (
        "<span style='font-size: 14px; font-weight: bold;'>RA: %{customdata[0]}</span><br><br>"
        "Proporção Estimada de Uso: <span style='color: #1a73e8; font-weight: bold;'>%{customdata[1]:.1%}</span> de quem tem celular<br>"
        "População Estimada que Usa: <b>%{customdata[2]:.0f} pessoas</b><br>"
        "Total de Pessoas com Celular na RA: <b>%{customdata[3]:.0f}</b><br>"
        "<hr style='margin: 5px 0; border-top: 1px solid #ccc;'>"
        "<span style='font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; color: #666; font-weight: bold;'>Rigor Estatístico (IPEDF):</span><br>"
        "• Coeficiente de Variação (CV): <b>%{customdata[4]:.1f}%</b><br>"
        "• Status dos Dados: <b>%{customdata[5]}</b>"
        "<extra></extra>" # O <extra></extra> remove aquela caixinha cinza lateral irritante do Plotly
    )

    # Aplica o nosso design de balão na estrutura do mapa
    fig.update_traces(hovertemplate=hovertemplate)

    # Ajustes de visualização geográfica e layout (Mantenha igual ao seu)
    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_layout(
        margin={"r": 0, "t": 50, "l": 0, "b": 0},
        dragmode=False,
        autosize=True
    )
    # 3. Mesclar os dados geográficos com as estatísticas processadas
    gdf_mapa = gdf_ra.merge(stats_ra, left_on='ra_join', right_on='RA_join', how='left')
    gdf_mapa['proporcao_uso'] = gdf_mapa['proporcao_uso'].fillna(0) # troca NaN por 0
    gdf_mapa['n_ponderado_uso'] = gdf_mapa['n_ponderado_uso'].fillna(0)
    gdf_mapa['total_ra'] = gdf_mapa['total_ra'].fillna(0)
    gdf_mapa['cv_porcentagem'] = gdf_mapa['cv_porcentagem'].fillna(0)
    gdf_mapa['confiabilidade'] = gdf_mapa['confiabilidade'].fillna('Sem dados amostrais')
    
    # Filtro de Segurança:
    # forçamos o valor para -0.1 para que a RA fique cinza no mapa.
    gdf_mapa['valor'] = np.where(gdf_mapa['total_ra'] == 0, -0.1, gdf_mapa['proporcao_uso'])

    # --- AJUSTE FINO: Escala de cores matemática para range_color=[-0.1, 1.0] ---
    custom_scale = [
        [0.0, "#d3d3d3"],       # Para o valor -0.1 (Cinza para RAs sem dados)
        [0.0909, "#d3d3d3"],   # Estende o cinza até o limite antes do zero absoluto
        [0.0910, "white"],     # O valor exato de 0% de uso fica totalmente branco
        [0.15, "#e0f3ff"],     # Transição suave para o azul bem claro quando o uso inicia
        [1.0, "darkblue"]      # 100% de uso mapeado em Azul Escuro
    ]

    # Gera o mapa coroplético via Plotly Express
    fig = px.choropleth(
        gdf_mapa,
        geojson=gdf_mapa.__geo_interface__,
        locations='ra',
        featureidkey='properties.ra',
        color='valor',
        color_continuous_scale=custom_scale,
        range_color=[-0.1, 1.0],
        hover_name='ra',
        hover_data={
            'valor': False,
            'proporcao_uso': ':.2%',
            'n_ponderado_uso': ':.0f'
        },
        title='Proporção de Uso de Internet por Celular por RA (2025)',
        #labels={
        #   'proporcao_uso': 'Proporção de Uso', 
        #    'n_ponderado_uso': 'N. Ponderado',
        #    'cv_porcentagem' : 'CV %',
        #    'confiabilidade': 'Status'
        #}'''
        # Injetamos a lista ordenada de colunas que o nosso balão vai ler
        custom_data=['ra', 'proporcao_uso', 'n_ponderado_uso', 'total_ra', 'cv_porcentagem', 'confiabilidade']
    )   

    hovertemplate = (
        "<b>RA:</b> %{customdata[0]}<br><br>"
        "<b>Proporção de Uso:</b> %{customdata[1]:.1%} (de quem tem celular)<br>"
        "<b>População Estimada:</b> %{customdata[2]:.0f} pessoas<br>"
        "<b>Total com Celular na RA:</b> %{customdata[3]:.0f}<br><br>"
        "<b>Rigor Estatístico (IPEDF)</b><br>"
        "• Coeficiente de Variação (CV): %{customdata[4]:.1f}%<br>"
        "• Status: %{customdata[5]}"
        "<extra></extra>"
    )

    # Aplica o nosso design de balão na estrutura do mapa
    fig.update_traces(hovertemplate=hovertemplate)
    
    # Ajustes de visualização geográfica e layout
    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_layout(
        margin={"r": 0, "t": 50, "l": 0, "b": 0},
        dragmode=False,
        autosize=True
    )
    
    # Retorna o HTML em formato de string estruturada (compatível com a injeção do Jinja2 no Flask)
    return fig.to_html(full_html=False, include_plotlyjs='cdn', config={
        'scrollZoom': False,
        'responsive': True,
        'displayModeBar': False
    })

print("Carregamento dos dados...")
grafico_2022 = base_cen_2022()
grafico_2025 = base_cen_2025()
grafico_internet_celular_2025 = mapa_net_cel_2025(amostra)
print("...realizado com sucesso!")

@app.route('/')
def dashboard():
    # O Flask abre o 'index.html' (que deve estar na pasta 'templates') 
    # e injeta as variáveis lá dentro.
    return render_template(
        'index.html', 
        mapa_2022=grafico_2022, 
        mapa_2025=grafico_2025,
        mapa_net_cel_amostra_2025=grafico_internet_celular_2025
    )

@app.route('/get-mapa-2022')
def get_mapa_2022():
    return grafico_2022

@app.route('/get-mapa-2025')
def get_mapa_2025():
    return grafico_2025

@app.route('/get-mapa-net-cel-2025')
def get_mapa_net_cel_2025():
    return grafico_internet_celular_2025

@app.route('/tic_psr') # O endereço que você vai digitar no navegador
def tic_psr():
    # Certifique-se de que o arquivo 'detalhes.html' existe na pasta 'templates'
    return render_template('tic_psr.html')

@app.route('/tic_brasil') # O endereço que você vai digitar no navegador
def tic_brasil():
    # Certifique-se de que o arquivo 'detalhes.html' existe na pasta 'templates'
    return render_template('tic_brasil.html')

@app.route('/projetos') # O endereço que você vai digitar no navegador
def projetos():
    # Certifique-se de que o arquivo 'detalhes.html' existe na pasta 'templates'
    return render_template('projetos.html')

@app.route('/centro_pop') # O endereço que você vai digitar no navegador
def centro_pop():
    # Certifique-se de que o arquivo 'detalhes.html' existe na pasta 'templates'
    return render_template('centro_pop.html')

@app.route('/feedback') # O endereço que você vai digitar no navegador
def feedback():
    # Certifique-se de que o arquivo 'detalhes.html' existe na pasta 'templates'
    return render_template('feedback.html')

@app.route('/newsletter') # O endereço que você vai digitar no navegador
def newsletter():
    # Certifique-se de que o arquivo 'detalhes.html' existe na pasta 'templates'
    return render_template('newsletter.html')

if __name__ == '__main__':
    app.run(debug=True)