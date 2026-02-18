
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import math

st.set_page_config(layout="wide")
st.title("Mapa Inteligente de Clientes e Técnicos")

# -------------------------
# FUNÇÕES AUXILIARES
# -------------------------
def parse_latlon(value):
    try:
        lat, lon = str(value).split(",")
        return float(lat.strip()), float(lon.strip())
    except:
        return None, None

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1-a))

def detectar_coluna(df, palavras):
    for col in df.columns:
        nome = col.lower()
        for p in palavras:
            if p in nome:
                return col
    return None

# -------------------------
# CARREGAR DADOS
# -------------------------
st.sidebar.header("Dados")

clientes = pd.read_excel("clientes.xlsx")
tecnicos = pd.read_excel("tecnicos.xlsx")

clientes.columns = clientes.columns.str.strip()
tecnicos.columns = tecnicos.columns.str.strip()

# -------------------------
# DETECTAR COLUNAS
# -------------------------
col_cliente = detectar_coluna(clientes, ["cliente", "empresa", "nome"])
col_unidade = detectar_coluna(clientes, ["unidade", "filial"])
col_frota = detectar_coluna(clientes, ["frota", "veiculo"])
col_latlon_cliente = detectar_coluna(clientes, ["latitude", "lat"])

col_nome_tecnico = detectar_coluna(tecnicos, ["nome"])
col_endereco = detectar_coluna(tecnicos, ["endereco", "endereço"])
col_latlon_tecnico = detectar_coluna(tecnicos, ["latitude", "lat"])

# validação
if not col_latlon_cliente or not col_latlon_tecnico:
    st.error("Não encontrei colunas de latitude/longitude.")
    st.stop()

# -------------------------
# COORDENADAS
# -------------------------
clientes[["lat","lon"]] = clientes[col_latlon_cliente].apply(lambda x: pd.Series(parse_latlon(x)))
tecnicos[["lat","lon"]] = tecnicos[col_latlon_tecnico].apply(lambda x: pd.Series(parse_latlon(x)))

clientes = clientes.dropna(subset=["lat","lon"])
tecnicos = tecnicos.dropna(subset=["lat","lon"])

# -------------------------
# FILTROS CLIENTE + UNIDADE
# -------------------------
st.sidebar.header("Filtros")

if col_cliente:
    clientes_escolhidos = st.sidebar.multiselect(
        "Clientes",
        clientes[col_cliente].unique(),
        default=list(clientes[col_cliente].unique())
    )
    clientes = clientes[clientes[col_cliente].isin(clientes_escolhidos)]

if col_unidade:
    unidades_escolhidas = st.sidebar.multiselect(
        "Unidades",
        clientes[col_unidade].unique(),
        default=list(clientes[col_unidade].unique())
    )
    clientes = clientes[clientes[col_unidade].isin(unidades_escolhidas)]

if col_nome_tecnico:
    tecnicos_escolhidos = st.sidebar.multiselect(
        "Técnicos",
        tecnicos[col_nome_tecnico].unique(),
        default=list(tecnicos[col_nome_tecnico].unique())
    )
    tecnicos = tecnicos[tecnicos[col_nome_tecnico].isin(tecnicos_escolhidos)]

# -------------------------
# MAPA
# -------------------------
centro = [clientes["lat"].mean(), clientes["lon"].mean()]
m = folium.Map(location=centro, zoom_start=5)

# clientes
for _, row in clientes.iterrows():
    html = f"""
    <b>Cliente:</b> {row.get(col_cliente,'')}<br>
    <b>Unidade:</b> {row.get(col_unidade,'')}<br>
    <b>Frota:</b> {row.get(col_frota,'')}
    """
    folium.Marker(
        location=[row["lat"], row["lon"]],
        popup=html,
        icon=folium.Icon(color="blue")
    ).add_to(m)

# técnicos
coords_tecnicos = []
for _, row in tecnicos.iterrows():
    coords_tecnicos.append((row["lat"], row["lon"], row))
    html = f"""
    <b>Técnico:</b> {row.get(col_nome_tecnico,'')}<br>
    <b>Endereço:</b> {row.get(col_endereco,'')}
    """
    folium.Marker(
        location=[row["lat"], row["lon"]],
        popup=html,
        icon=folium.Icon(color="green", icon="wrench")
    ).add_to(m)

map_data = st_folium(m, width=1200, height=650)

# -------------------------
# RAIO 200KM AO CLICAR TÉCNICO
# -------------------------
if map_data and map_data.get("last_clicked"):
    click_lat = map_data["last_clicked"]["lat"]
    click_lon = map_data["last_clicked"]["lng"]
    
    tecnico_encontrado = None
    
    for lat, lon, row in coords_tecnicos:
        if abs(lat - click_lat) < 0.05 and abs(lon - click_lon) < 0.05:
            tecnico_encontrado = row
            break
    
    if tecnico_encontrado is not None:
        st.success(f"Raio de atendimento do técnico: {tecnico_encontrado.get(col_nome_tecnico,'')}")
        
        m2 = folium.Map(location=[tecnico_encontrado["lat"], tecnico_encontrado["lon"]], zoom_start=7)
        
        folium.Circle(
            location=[tecnico_encontrado["lat"], tecnico_encontrado["lon"]],
            radius=200000,
            color="red",
            fill=True,
            fill_opacity=0.2
        ).add_to(m2)
        
        folium.Marker(
            location=[tecnico_encontrado["lat"], tecnico_encontrado["lon"]],
            icon=folium.Icon(color="green", icon="wrench")
        ).add_to(m2)
        
        st.subheader("Área de cobertura do técnico (200km)")
        st_folium(m2, width=1200, height=500)

# -------------------------
# DASHBOARD EXECUTIVO
# -------------------------
st.header("Dashboard Executivo")

col1, col2, col3 = st.columns(3)

col1.metric("Total Clientes", len(clientes))
col2.metric("Total Técnicos", len(tecnicos))

# distância média cliente -> técnico mais próximo
distancias = []

for _, cliente in clientes.iterrows():
    menor = 999999
    for _, tecnico in tecnicos.iterrows():
        d = haversine(cliente["lat"], cliente["lon"], tecnico["lat"], tecnico["lon"])
        if d < menor:
            menor = d
    distancias.append(menor)

if distancias:
    media = sum(distancias) / len(distancias)
else:
    media = 0

col3.metric("Distância média cliente → técnico (km)", round(media,1))

# tabela melhores técnicos
st.subheader("Melhor técnico por cliente")

dados = []

for _, cliente in clientes.iterrows():
    melhor = None
    menor = 999999
    
    for _, tecnico in tecnicos.iterrows():
        d = haversine(cliente["lat"], cliente["lon"], tecnico["lat"], tecnico["lon"])
        if d < menor:
            menor = d
            melhor = tecnico
    
    dados.append({
        "Cliente": cliente.get(col_cliente,''),
        "Unidade": cliente.get(col_unidade,''),
        "Melhor Técnico": melhor.get(col_nome_tecnico,''),
        "Distância (km)": round(menor,1)
    })

st.dataframe(pd.DataFrame(dados), use_container_width=True)
