from flask import Flask, render_template
import pandas as pd
import geopandas as gpd
import plotly.express as px
from shapely import wkt
import json
import numpy as np
from samplics.categorical import Tabulation
from samplics.utils.types import PopParam  # <-- Importação necessária para corrigir o erro do parâmetro da amostra



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

print("Carregamento dos dados...")
grafico_2022 = base_cen_2022()
grafico_2025 = base_cen_2025()
print("...realizado com sucesso!")

@app.route('/')
def dashboard():
    # O Flask abre o 'index.html' (que deve estar na pasta 'templates') 
    # e injeta as variáveis lá dentro.
    return render_template(
        'index.html', 
        mapa_2022=grafico_2022, 
        mapa_2025=grafico_2025
    )

@app.route('/get-mapa-2022')
def get_mapa_2022():
    return grafico_2022

@app.route('/get-mapa-2025')
def get_mapa_2025():
    return grafico_2025

@app.route('/tic_inclusao') # O endereço que você vai digitar no navegador
def tic_inclusao():
    # Certifique-se de que o arquivo 'detalhes.html' existe na pasta 'templates'
    return render_template('tic_inclusao.html')

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