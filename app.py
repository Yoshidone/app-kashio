import streamlit as st
import pandas as pd
import os
import datetime
import requests
import base64
from io import BytesIO

st.set_page_config(page_title="Sistema de Control de Facturación Kashio", layout="wide")

# -----------------------------
# LOGIN
# -----------------------------

USERS = {
    "yoshira": "1234",
    "conta": "kashio2026",
    "admin": "admin123"
}

def check_login():
    st.title("🔐 Acceso al Sistema Kashio")

    user = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")

    if st.button("Ingresar"):
        if user in USERS and USERS[user] == password:
            st.session_state["auth"] = True
            st.session_state["usuario"] = user
        else:
            st.error("❌ Credenciales incorrectas")

if "auth" not in st.session_state or not st.session_state["auth"]:
    check_login()
    st.stop()

# -----------------------------
# CONFIG
# -----------------------------

archivo_base = "base_tarifas_guardada.xlsx"
archivo_historial = "historial_tarifas.xlsx"

# -----------------------------
# GUARDAR EN GITHUB 🔥
# -----------------------------

def guardar_en_github(df, archivo):
    token = st.secrets["GITHUB_TOKEN"]
    repo = st.secrets["REPO"]

    url = f"https://api.github.com/repos/{repo}/contents/{archivo}"

    r = requests.get(url, headers={"Authorization": f"token {token}"})
    if r.status_code == 200:
        sha = r.json()["sha"]
    else:
        sha = None

    output = BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    contenido = base64.b64encode(output.getvalue()).decode()

    data = {
        "message": f"Actualización desde app - {archivo}",
        "content": contenido,
        "branch": "main"
    }

    if sha:
        data["sha"] = sha

    requests.put(url, json=data, headers={"Authorization": f"token {token}"})


# -----------------------------
# CARGAR BASE
# -----------------------------

if os.path.exists(archivo_base):
    base_guardada = pd.read_excel(archivo_base)
else:
    base_guardada = pd.DataFrame()

for col in ["id_cuenta","producto","tipo","bracket"]:
    if col not in base_guardada.columns:
        base_guardada[col] = ""

# -----------------------------
# HISTORIAL
# -----------------------------

if os.path.exists(archivo_historial):
    historial = pd.read_excel(archivo_historial)
else:
    historial = pd.DataFrame(columns=[
        "fecha","id_cuenta","cliente","producto",
        "tipo","bracket","valor_anterior","valor_nuevo"
    ])

# -----------------------------
# UI
# -----------------------------

st.title("💖 Sistema de Control de Facturación Kashio")
st.subheader(f"Bienvenida {st.session_state['usuario']} 👋")

# -----------------------------
# SUBIR ARCHIVO
# -----------------------------

archivo = st.file_uploader("Sube tu base tarifaria", type=["xlsx","csv"])

if archivo is not None:

    df_nuevo = pd.read_csv(archivo) if archivo.name.endswith(".csv") else pd.read_excel(archivo)
    df_nuevo.columns = df_nuevo.columns.str.strip().str.lower()

    for col in ["id_cuenta","producto","tipo","bracket"]:
        if col not in df_nuevo.columns:
            df_nuevo[col] = ""

    df_nuevo = df_nuevo.dropna(how="all")

    for _, fila in df_nuevo.iterrows():

        if not base_guardada.empty:
            filtro = (
                (base_guardada["id_cuenta"].astype(str) == str(fila["id_cuenta"])) &
                (base_guardada["producto"] == fila["producto"]) &
                (base_guardada["tipo"] == fila["tipo"]) &
                (base_guardada["bracket"].astype(str) == str(fila["bracket"]))
            )
        else:
            filtro = None

        if filtro is not None and filtro.any():
            viejo = base_guardada.loc[filtro]

            viejo_valor = viejo.iloc[0].get("comision_variable",0)
            nuevo_valor = fila.get("comision_variable",0)

            if str(viejo_valor) != str(nuevo_valor):

                historial.loc[len(historial)] = {
                    "fecha": datetime.datetime.now(),
                    "id_cuenta": fila["id_cuenta"],
                    "cliente": fila["cliente"],
                    "producto": fila["producto"],
                    "tipo": fila["tipo"],
                    "bracket": fila["bracket"],
                    "valor_anterior": viejo_valor,
                    "valor_nuevo": nuevo_valor
                }

    base_guardada = pd.concat([base_guardada, df_nuevo])
    base_guardada = base_guardada.drop_duplicates(
        subset=["id_cuenta","producto","tipo","bracket"],
        keep="last"
    )

    # 🔥 GUARDADO AUTOMÁTICO
    guardar_en_github(base_guardada, archivo_base)
    guardar_en_github(historial, archivo_historial)

    st.success("✅ Base guardada en GitHub correctamente")

df = base_guardada.copy()

# -----------------------------
# SIDEBAR
# -----------------------------

st.sidebar.header("🔎 Buscar cliente")

if st.sidebar.button("Cerrar sesión"):
    st.session_state["auth"] = False
    st.rerun()

buscar_id = st.sidebar.text_input("Buscar por ID CUENTA")
buscar_cliente = st.sidebar.text_input("Buscar por nombre")

if buscar_id:
    df = df[df["id_cuenta"].astype(str).str.contains(buscar_id)]

if buscar_cliente:
    df = df[df["cliente"].astype(str).str.contains(buscar_cliente, case=False)]

# -----------------------------
# TABLA
# -----------------------------

def mostrar_tabla(data):

    if data.empty:
        st.warning("No hay datos disponibles")
        return

    editado = st.data_editor(data, use_container_width=True)

    if st.button("Guardar cambios"):
        guardar_en_github(editado, archivo_base)
        st.success("💾 Cambios guardados en GitHub")

# -----------------------------
# DASHBOARD
# -----------------------------

st.header("📊 Dashboard")

if not df.empty:

    c1,c2,c3,c4 = st.columns(4)

    c1.metric("Clientes", df["cliente"].nunique())
    c2.metric("Tipos", df["tipo"].nunique() if "tipo" in df.columns else 0)
    c3.metric("Registros", len(df))
    c4.metric("IDs únicos", df["id_cuenta"].nunique())

st.divider()
st.header("Base de Tarifarios")
mostrar_tabla(df)

# -----------------------------
# HISTORIAL
# -----------------------------

st.divider()
st.header("📜 Historial")

if historial.empty:
    st.warning("No hay cambios registrados")
else:
    st.dataframe(historial, use_container_width=True)
