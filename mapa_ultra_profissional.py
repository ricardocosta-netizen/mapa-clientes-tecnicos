
import streamlit as st
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
from math import radians, cos, sin, asin, sqrt
from pathlib import Path

# =====================================================
# CONFIGURAÇÃO
# =====================================================

st.set_page_config(
    page_title="Mapa Inteligente Operacional",
    page_icon="🗺️",
    layout="wide"
)

# =====================================================
# ESTILO VISUAL
# =====================================================

st.markdown("""
<style>
.main { background-color:#f5f7fb; }
section[data-testid="stSidebar"] { background:#ffffff; border-right:1px solid #e6e9ef; }
h1 { font-weight:700; color:#1f2937; }
.stMetric { background:white; padding:15px; border-radius:12px; box-shadow:0 2px 8px rgba(0,0,0,0.05); }
.block-container { padding-top:2rem; }
</style>
""", unsafe_allow_html=True)

# =====================================================
# FUNÇÕES AUXILIARES
# =====================================================

def normalizar_colunas(df):
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace("á","a").str.replace("ã","a")
        .str.replace("é","e").str.replace("í","i")
        .str.replace("ó","o").str.replace("ú","u")
        .str.replace("ç","c")
    )
    return df

def encontrar_coluna(df, opcoes):
    for c in df.columns:
        for o in opcoes:
            if o in c:
                return c
    return None

def haversine(lat1, lon1, lat2, lon2):
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    return 6371 * c

# =====================================================
# CARREGAMENTO AUTOMÁTICO PADRÃO
# =====================================================

CAMINHO_CLIENTES_PADRAO = Path("clientes.xlsx")
CAMINHO_TECNICOS_PADRAO = Path("tecnicos.xlsx")

# =====================================================
# SIDEBAR - ATUALIZAÇÃO OPCIONAL
# =====================================================

st.sidebar.header("📂 Atualizar Dados (opcional)")

upload_clientes = st.sidebar.file_uploader("Atualizar CLIENTES", type=["xlsx"])
upload_tecnicos = st.sidebar.file_uploader("Atualizar TÉCNICOS", type=["xlsx"])

# =====================================================
# LEITURA DOS DADOS
# =====================================================

try:
    if upload_clientes:
        df_clientes = pd.read_excel(upload_clientes)
    else:
        df_clientes = pd.read_excel(CAMINHO_CLIENTES_PADRAO)

    if upload_tecnicos:
        df_tecnicos = pd.read_excel(upload_tecnicos)
    else:
        df_tecnicos = pd.read_excel(CAMINHO_TECNICOS_PADRAO)

except Exception as e:
    st.error("Erro ao carregar planilhas padrão. Coloque clientes.xlsx e tecnicos.xlsx na pasta do app.")
    st.stop()

df_clientes = normalizar_colunas(df_clientes)
df_tecnicos = normalizar_colunas(df_tecnicos)

# =====================================================
# IDENTIFICAR COLUNAS AUTOMATICAMENTE
# =====================================================

col_cliente = encontrar_coluna(df_clientes, ["cliente"])
col_unidade = encontrar_coluna(df_clientes, ["unidade"])
col_lat_c = encontrar_coluna(df_clientes, ["lat"])
col_lon_c = encontrar_coluna(df_clientes, ["lon","long"])

col_tecnico = encontrar_coluna(df_tecnicos, ["nome","tecnico"])
col_lat_t = encontrar_coluna(df_tecnicos, ["lat"])
col_lon_t = encontrar_coluna(df_tecnicos, ["lon","long"])

if None in [col_cliente,col_unidade,col_lat_c,col_lon_c,col_tecnico,col_lat_t,col_lon_t]:
    st.error("Não foi possível identificar automaticamente as colunas nas planilhas.")
    st.write("Colunas encontradas CLIENTES:", df_clientes.columns.tolist())
    st.write("Colunas encontradas TECNICOS:", df_tecnicos.columns.tolist())
    st.stop()

# =====================================================
# FILTROS
# =====================================================

st.sidebar.header("🎯 Filtros")

clientes_sel = st.sidebar.multiselect(
    "Clientes",
    df_clientes[col_cliente].unique(),
    default=df_clientes[col_cliente].unique()
)

unidades_sel = st.sidebar.multiselect(
    "Unidades",
    df_clientes[col_unidade].unique(),
    default=df_clientes[col_unidade].unique()
)

tecnicos_sel = st.sidebar.multiselect(
    "Técnicos",
    df_tecnicos[col_tecnico].unique(),
    default=df_tecnicos[col_tecnico].unique()
)

df_clientes = df_clientes[
    df_clientes[col_cliente].isin(clientes_sel) &
    df_clientes[col_unidade].isin(unidades_sel)
]

df_tecnicos = df_tecnicos[
    df_tecnicos[col_tecnico].isin(tecnicos_sel)
]

# =====================================================
# DASHBOARD EXECUTIVO
# =====================================================

st.title("Mapa Inteligente de Clientes e Técnicos")

col1,col2,col3,col4 = st.columns(4)
col1.metric("Clientes", len(df_clientes))
col2.metric("Técnicos", len(df_tecnicos))
col3.metric("Unidades", df_clientes[col_unidade].nunique())
col4.metric("Cobertura padrão", "200 km")

# =====================================================
# MAPA
# =====================================================

lat_centro = df_clientes[col_lat_c].mean()
lon_centro = df_clientes[col_lon_c].mean()

mapa = folium.Map(
    location=[lat_centro, lon_centro],
    zoom_start=6,
    tiles="cartodbpositron"
)

cluster = MarkerCluster().add_to(mapa)

# clientes
for _, r in df_clientes.iterrows():
    folium.Marker(
        [r[col_lat_c], r[col_lon_c]],
        popup=f"<b>{r[col_cliente]}</b><br>{r[col_unidade]}",
        icon=folium.Icon(color="blue")
    ).add_to(cluster)

# técnicos
for _, r in df_tecnicos.iterrows():
    folium.Marker(
        [r[col_lat_t], r[col_lon_t]],
        popup=f"<b>Técnico:</b> {r[col_tecnico]}",
        icon=folium.Icon(color="green", icon="wrench", prefix="fa")
    ).add_to(mapa)

# =====================================================
# COBERTURA
# =====================================================

st.sidebar.header("🎯 Cobertura do Técnico")

tec_escolhido = st.sidebar.selectbox("Selecionar técnico", df_tecnicos[col_tecnico])

tec = df_tecnicos[df_tecnicos[col_tecnico]==tec_escolhido].iloc[0]

folium.Circle(
    [tec[col_lat_t], tec[col_lon_t]],
    radius=200000,
    color="red",
    fill=True,
    fill_opacity=0.08
).add_to(mapa)

# =====================================================
# CLIENTES NO RAIO
# =====================================================

clientes_proximos = []

for _, c in df_clientes.iterrows():
    d = haversine(tec[col_lat_t],tec[col_lon_t],c[col_lat_c],c[col_lon_c])
    if d <= 200:
        clientes_proximos.append(c)

st.subheader("Clientes dentro do raio de 200km")

if clientes_proximos:
    st.dataframe(pd.DataFrame(clientes_proximos))
else:
    st.info("Nenhum cliente dentro do raio.")

# =====================================================
# MAPA
# =====================================================

st_folium(mapa, width=1400, height=700)
