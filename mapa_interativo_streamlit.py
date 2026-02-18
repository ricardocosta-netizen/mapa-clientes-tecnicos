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

# limpar nomes das colunas
clientes.columns = clientes.columns.str.strip()
tecnicos.columns = tecnicos.columns.str.strip()

# -------------------------
# DETECTAR COLUNAS CLIENTES
# -------------------------
col_cliente = detectar_coluna(clientes, ["cliente", "empresa", "nome"])
col_unidade = detectar_coluna(clientes, ["unidade", "filial"])
col_frota = detectar_coluna(clientes, ["frota", "veiculo"])
col_latlon_cliente = detectar_coluna(clientes, ["latitude", "lat"])

# -------------------------
# DETECTAR COLUNAS TECNICOS
# -------------------------
col_nome_tecnico = detectar_coluna(tecnicos, ["nome"])
col_endereco = detectar_coluna(tecnicos, ["endereco", "endereço"])
col_latlon_tecnico = detectar_coluna(tecnicos, ["latitude", "lat"])

# validação
if not col_latlon_cliente or not col_latlon_tecnico:
    st.error("Não encontrei colunas de latitude/longitude nas planilhas.")
    st.write("Clientes:", list(clientes.columns))
    st.write("Técnicos:", list(tecnicos.columns))
    st.stop()

# -------------------------
# EXTRAIR COORDENADAS
# -------------------------
clientes[["lat","lon"]] = clientes[col_latlon_cliente].apply(lambda x: pd.Series(parse_latlon(x)))
tecnicos[["lat","lon"]] = tecnicos[col_latlon_tecnico].apply(lambda x: pd.Series(parse_latlon(x)))

clientes = clientes.dropna(subset=["lat","lon"])
tecnicos = tecnicos.dropna(subset=["lat","lon"])

# -------------------------
# FILTROS
# -------------------------
st.sidebar.header("Filtros")

selecionar_todos_clientes = st.sidebar.checkbox("Selecionar TODOS clientes", True)
selecionar_todos_tecnicos = st.sidebar.checkbox("Selecionar TODOS técnicos", True)

if selecionar_todos_clientes or not col_cliente:
    clientes_filtrados = clientes.copy()
else:
    lista_clientes = clientes[col_cliente].unique()
    escolhidos = st.sidebar.multiselect("Cliente", lista_clientes)
    clientes_filtrados = clientes[clientes[col_cliente].isin(escolhidos)]

if selecionar_todos_tecnicos or not col_nome_tecnico:
    tecnicos_filtrados = tecnicos.copy()
else:
    lista_tecnicos = tecnicos[col_nome_tecnico].unique()
    escolhidos = st.sidebar.multiselect("Técnico", lista_tecnicos)
    tecnicos_filtrados = tecnicos[tecnicos[col_nome_tecnico].isin(escolhidos)]

# -------------------------
# MAPA
# -------------------------
centro = [clientes_filtrados["lat"].mean(), clientes_filtrados["lon"].mean()]
m = folium.Map(location=centro, zoom_start=5)

# clientes
for _, row in clientes_filtrados.iterrows():
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
for _, row in tecnicos_filtrados.iterrows():
    html = f"""
    <b>Técnico:</b> {row.get(col_nome_tecnico,'')}<br>
    <b>Endereço:</b> {row.get(col_endereco,'')}
    """
    folium.Marker(
        location=[row["lat"], row["lon"]],
        popup=html,
        icon=folium.Icon(color="green", icon="wrench")
    ).add_to(m)

st.subheader("Mapa")
st_folium(m, width=1200, height=650)

# -------------------------
# MELHOR TECNICO
# -------------------------
st.subheader("Sugestão automática do melhor técnico")

velocidade_media = st.slider("Velocidade média (km/h)", 40, 120, 80)

sugestoes = []

for _, cliente in clientes_filtrados.iterrows():
    melhor = None
    menor = 999999
    
    for _, tecnico in tecnicos_filtrados.iterrows():
        dist = haversine(cliente["lat"], cliente["lon"], tecnico["lat"], tecnico["lon"])
        if dist < menor:
            menor = dist
            melhor = tecnico
    
    if melhor is not None:
        tempo = menor / velocidade_media
        sugestoes.append({
            "Cliente": cliente.get(col_cliente,''),
            "Unidade": cliente.get(col_unidade,''),
            "Melhor Técnico": melhor.get(col_nome_tecnico,''),
            "Distância (km)": round(menor,1),
            "Tempo estimado (h)": round(tempo,2)
        })

if sugestoes:
    st.dataframe(pd.DataFrame(sugestoes), use_container_width=True)
