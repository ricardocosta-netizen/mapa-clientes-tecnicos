
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import math

st.set_page_config(layout="wide")
st.title("Mapa Inteligente de Clientes e Técnicos")

# -------------------------
# FUNÇÕES
# -------------------------
def parse_latlon(value):
    lat, lon = str(value).split(",")
    return float(lat.strip()), float(lon.strip())

def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # km
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1-a))

# -------------------------
# CARREGAR DADOS
# -------------------------
st.sidebar.header("Dados")

clientes_file = st.sidebar.file_uploader("Atualizar base de CLIENTES", type=["xlsx"])
tecnicos_file = st.sidebar.file_uploader("Atualizar base de TÉCNICOS", type=["xlsx"])

if clientes_file:
    clientes = pd.read_excel(clientes_file)
else:
    clientes = pd.read_excel("clientes.xlsx")

if tecnicos_file:
    tecnicos = pd.read_excel(tecnicos_file)
else:
    tecnicos = pd.read_excel("tecnicos.xlsx")

# coordenadas
clientes[["lat","lon"]] = clientes["latitude / longitude"].apply(lambda x: pd.Series(parse_latlon(x)))
tecnicos[["lat","lon"]] = tecnicos["Latitude / longitude"].apply(lambda x: pd.Series(parse_latlon(x)))

# -------------------------
# FILTROS
# -------------------------
st.sidebar.header("Filtros")

selecionar_todos_clientes = st.sidebar.checkbox("Selecionar TODOS clientes", value=True)
selecionar_todos_tecnicos = st.sidebar.checkbox("Selecionar TODOS técnicos", value=True)

if selecionar_todos_clientes:
    clientes_filtrados = clientes.copy()
else:
    lista_clientes = clientes["cliente"].unique()
    clientes_escolhidos = st.sidebar.multiselect("Cliente", lista_clientes)
    clientes_filtrados = clientes[clientes["cliente"].isin(clientes_escolhidos)]

if selecionar_todos_tecnicos:
    tecnicos_filtrados = tecnicos.copy()
else:
    tecnicos.columns = tecnicos.columns.str.strip()
    tecnicos_escolhidos = st.sidebar.multiselect("Técnico", lista_tecnicos)
    tecnicos_filtrados = tecnicos[tecnicos["col_nome_tecnico:"].isin(tecnicos_escolhidos)]

# -------------------------
# MAPA
# -------------------------
centro = [-22.9, -47.05]
m = folium.Map(location=centro, zoom_start=5)

# --- Clientes
clientes_group = folium.FeatureGroup(name="Clientes").add_to(m)

for _, row in clientes_filtrados.iterrows():
    html = f"""
    <b>Cliente:</b> {row['cliente']}<br>
    <b>Unidade:</b> {row['unidade']}<br>
    <b>Frota:</b> {row['frota']}
    """
    folium.Marker(
        location=[row["lat"], row["lon"]],
        popup=html,
        icon=folium.Icon(color="blue", icon="building")
    ).add_to(clientes_group)

# --- Técnicos com raio ao clicar
tecnicos_group = folium.FeatureGroup(name="Técnicos").add_to(m)

for i, row in tecnicos_filtrados.iterrows():
    popup = f"""
    <b>Técnico:</b> {row['col_nome_tecnico']}<br>
    <b>Endereço:</b> {row['Endereço:']}
    """
    
    marker = folium.Marker(
        location=[row["lat"], row["lon"]],
        popup=popup,
        icon=folium.Icon(color="green", icon="wrench")
    )
    marker.add_to(tecnicos_group)
    
    # JS para desenhar círculo ao clicar
    circle_js = f"""
    <script>
    var marker_{i} = {{
        lat: {row["lat"]},
        lon: {row["lon"]}
    }};
    </script>
    """
    m.get_root().html.add_child(folium.Element(circle_js))

folium.LayerControl().add_to(m)

st.subheader("Mapa")
st_folium(m, width=1200, height=650)

# -------------------------
# MELHOR TÉCNICO POR CLIENTE
# -------------------------
st.subheader("Sugestão automática: melhor técnico por cliente")

velocidade_media = st.slider("Velocidade média deslocamento (km/h)", 40, 120, 80)

sugestoes = []

for _, cliente in clientes_filtrados.iterrows():
    melhor = None
    menor_dist = 999999
    
    for _, tecnico in tecnicos_filtrados.iterrows():
        dist = haversine(cliente["lat"], cliente["lon"], tecnico["lat"], tecnico["lon"])
        if dist < menor_dist:
            menor_dist = dist
            melhor = tecnico
    
    if melhor is not None:
        tempo = menor_dist / velocidade_media
        sugestoes.append({
            "Cliente": cliente["cliente"],
            "Unidade": cliente["unidade"],
            "Melhor Técnico": melhor["Nome:"],
            "Distância (km)": round(menor_dist, 1),
            "Tempo estimado (h)": round(tempo, 2)
        })

if sugestoes:
    st.dataframe(pd.DataFrame(sugestoes), use_container_width=True)
else:
    st.info("Nenhuma sugestão disponível com os filtros atuais.")

st.markdown("---")
st.caption("Atualize as planilhas sempre que houver novos clientes ou técnicos.")
