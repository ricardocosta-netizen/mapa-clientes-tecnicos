
import streamlit as st
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
from math import radians, cos, sin, asin, sqrt

# =====================================================
# CONFIGURAÇÃO DA PÁGINA
# =====================================================

st.set_page_config(
    page_title="Mapa Inteligente Operacional",
    page_icon="🗺️",
    layout="wide"
)

# =====================================================
# ESTILO VISUAL PROFISSIONAL
# =====================================================

st.markdown("""
<style>

.main {
    background-color: #f5f7fb;
}

section[data-testid="stSidebar"] {
    background-color: #ffffff;
    border-right: 1px solid #e6e9ef;
}

h1 {
    font-weight: 700;
    color: #1f2937;
}

.stMetric {
    background-color: white;
    padding: 15px;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
}

.block-container {
    padding-top: 2rem;
}

</style>
""", unsafe_allow_html=True)

# =====================================================
# FUNÇÕES
# =====================================================

def haversine(lat1, lon1, lat2, lon2):
    """Calcula distância em KM"""
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    km = 6371 * c
    return km

# =====================================================
# SIDEBAR - UPLOAD DE DADOS
# =====================================================

st.sidebar.header("📂 Carregar Dados")

arquivo_clientes = st.sidebar.file_uploader(
    "Upload planilha CLIENTES",
    type=["xlsx"]
)

arquivo_tecnicos = st.sidebar.file_uploader(
    "Upload planilha TÉCNICOS",
    type=["xlsx"]
)

if not arquivo_clientes or not arquivo_tecnicos:
    st.warning("Carregue as duas planilhas para iniciar.")
    st.stop()

df_clientes = pd.read_excel(arquivo_clientes)
df_tecnicos = pd.read_excel(arquivo_tecnicos)

# =====================================================
# FILTROS
# =====================================================

st.sidebar.header("🎯 Filtros")

clientes_sel = st.sidebar.multiselect(
    "Clientes",
    df_clientes["Cliente"].unique(),
    default=df_clientes["Cliente"].unique()
)

unidades_sel = st.sidebar.multiselect(
    "Unidades",
    df_clientes["Unidade"].unique(),
    default=df_clientes["Unidade"].unique()
)

tecnicos_sel = st.sidebar.multiselect(
    "Técnicos",
    df_tecnicos["Nome"].unique(),
    default=df_tecnicos["Nome"].unique()
)

df_clientes = df_clientes[
    (df_clientes["Cliente"].isin(clientes_sel)) &
    (df_clientes["Unidade"].isin(unidades_sel))
]

df_tecnicos = df_tecnicos[
    df_tecnicos["Nome"].isin(tecnicos_sel)
]

# =====================================================
# DASHBOARD EXECUTIVO
# =====================================================

st.title("Mapa Inteligente de Clientes e Técnicos")

st.subheader("📊 Visão Executiva")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Clientes", len(df_clientes))
col2.metric("Técnicos", len(df_tecnicos))
col3.metric("Unidades", df_clientes["Unidade"].nunique())
col4.metric("Raio padrão", "200 km")

# =====================================================
# MAPA BASE
# =====================================================

lat_centro = df_clientes["Latitude"].mean()
lon_centro = df_clientes["Longitude"].mean()

mapa = folium.Map(
    location=[lat_centro, lon_centro],
    zoom_start=6,
    tiles="cartodbpositron"
)

cluster_clientes = MarkerCluster().add_to(mapa)

# =====================================================
# MARCAR CLIENTES
# =====================================================

for _, row in df_clientes.iterrows():
    folium.Marker(
        [row["Latitude"], row["Longitude"]],
        popup=f"""
        <b>Cliente:</b> {row["Cliente"]}<br>
        <b>Unidade:</b> {row["Unidade"]}
        """,
        icon=folium.Icon(color="blue", icon="info-sign")
    ).add_to(cluster_clientes)

# =====================================================
# SELEÇÃO DE TÉCNICO PARA RAIO
# =====================================================

st.sidebar.header("🎯 Cobertura")

tecnico_raio = st.sidebar.selectbox(
    "Selecionar técnico para ver cobertura 200km",
    df_tecnicos["Nome"]
)

tec = df_tecnicos[df_tecnicos["Nome"] == tecnico_raio].iloc[0]

# =====================================================
# MARCAR TÉCNICOS
# =====================================================

for _, row in df_tecnicos.iterrows():

    folium.Marker(
        [row["Latitude"], row["Longitude"]],
        popup=f"<b>Técnico:</b> {row['Nome']}",
        icon=folium.Icon(color="green", icon="wrench", prefix="fa")
    ).add_to(mapa)

# =====================================================
# DESENHAR RAIO 200KM
# =====================================================

folium.Circle(
    location=[tec["Latitude"], tec["Longitude"]],
    radius=200000,
    color="red",
    fill=True,
    fill_opacity=0.08
).add_to(mapa)

# =====================================================
# CLIENTES DENTRO DO RAIO
# =====================================================

clientes_proximos = []

for _, c in df_clientes.iterrows():
    dist = haversine(
        tec["Latitude"], tec["Longitude"],
        c["Latitude"], c["Longitude"]
    )
    if dist <= 200:
        clientes_proximos.append(c)

st.subheader("🎯 Clientes dentro do raio de 200km")

if clientes_proximos:
    st.dataframe(pd.DataFrame(clientes_proximos))
else:
    st.info("Nenhum cliente dentro do raio.")

# =====================================================
# EXIBIR MAPA
# =====================================================

st.subheader("🗺️ Mapa Operacional")

st_folium(mapa, width=1400, height=700)
