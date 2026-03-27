import streamlit as st
import pandas as pd
import datetime
import requests
import base64
from io import BytesIO

st.set_page_config(page_title="Sistema de Control de Facturación Kashio", layout="wide")

# -----------------------------
# 🔐 CONFIG GITHUB
# -----------------------------
GITHUB_TOKEN = st.secrets["TOKEN_GITHUB"]
REPO = "Yoshidone/app-kashio"

FILE_BASE = "DASH.xlsx"
FILE_HISTORIAL = "historial_cambios.xlsx"

# -----------------------------
# FUNCIONES GITHUB
# -----------------------------
def leer_excel_github(file_path):
    url = f"https://api.github.com/repos/{REPO}/contents/{file_path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)

    if r.status_code == 200:
        content = base64.b64decode(r.json()["content"])
        return pd.read_excel(BytesIO(content))
    else:
        return pd.DataFrame()

def subir_excel_github(df, file_path, mensaje):
    url = f"https://api.github.com/repos/{REPO}/contents/{file_path}"

    buffer = BytesIO()
    df.to_excel(buffer, index=False)
    content = base64.b64encode(buffer.getvalue()).decode()

    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)

    sha = r.json()["sha"] if r.status_code == 200 else None

    data = {"message": mensaje, "content": content}
    if sha:
        data["sha"] = sha

    requests.put(url, json=data, headers=headers)

# -----------------------------
# NORMALIZAR
# -----------------------------
def normalizar_columnas(df):
    df.columns = df.columns.str.strip().str.lower()
    return df

# -----------------------------
# 🔥 FILTRO VISUAL (SIN BORRAR BASE)
# -----------------------------
def filtrar_filas_validas(df):

    columnas_monto = [
        "comision_variable",
        "comision_fija",
        "comision_minima_usd",
        "comision_minima_pen"
    ]

    columnas_monto = [c for c in columnas_monto if c in df.columns]

    if not columnas_monto:
        return df

    df_copy = df.copy()

    # 🔥 limpiar valores falsos
    df_copy[columnas_monto] = df_copy[columnas_monto].replace(
        ["None", "none", "", "nan"], pd.NA
    )

    return df_copy.dropna(subset=columnas_monto, how="all")

# -----------------------------
# LOGIN
# -----------------------------
USERS = {
    "yoshira": "1234",
    "conta": "kashio2026",
    "admin": "admin123"
}

def login():
    st.title("🔐 Login Kashio")
    u = st.text_input("Usuario")
    p = st.text_input("Contraseña", type="password")

    if st.button("Ingresar"):
        if u in USERS and USERS[u] == p:
            st.session_state["auth"] = True
            st.session_state["usuario"] = u
        else:
            st.error("Credenciales incorrectas")

if "auth" not in st.session_state:
    login()
    st.stop()

# -----------------------------
# HEADER
# -----------------------------
st.title("💖 Sistema de Control de Facturación Kashio")
st.subheader(f"Bienvenida {st.session_state['usuario']} 👋")

# -----------------------------
# CARGA DATA
# -----------------------------
base = normalizar_columnas(leer_excel_github(FILE_BASE))
historial = leer_excel_github(FILE_HISTORIAL)

# -----------------------------
# UPLOAD
# -----------------------------
archivo = st.file_uploader("📂 Sube tu base", type=["xlsx","csv"])

if archivo:
    nuevo = normalizar_columnas(pd.read_excel(archivo))

    if st.button("📥 Reemplazar base"):
        subir_excel_github(nuevo, FILE_BASE, "Nueva base")
        st.success("Base actualizada 🚀")
        st.rerun()

# -----------------------------
# FILTROS
# -----------------------------
st.sidebar.header("Buscar")

f_id = st.sidebar.text_input("ID Cuenta")
f_cliente = st.sidebar.text_input("Cliente")

df = base.copy()

if f_id:
    df = df[df["id_cuenta"].astype(str).str.contains(f_id)]

if f_cliente:
    df = df[df["cliente"].astype(str).str.contains(f_cliente, case=False)]

# -----------------------------
# MENÚ
# -----------------------------
if "page" not in st.session_state:
    st.session_state.page = "inicio"

c1,c2,c3,c4,c5,c6,c7 = st.columns(7)

if c1.button("Dashboard"): st.session_state.page="inicio"
if c2.button("Payin"): st.session_state.page="payin"
if c3.button("Payout"): st.session_state.page="payout"
if c4.button("PAAS"): st.session_state.page="paas"
if c5.button("Licencias"): st.session_state.page="licencias"
if c6.button("Interconexión"): st.session_state.page="inter"
if c7.button("Historial"): st.session_state.page="hist"

st.divider()

# -----------------------------
# TABLA
# -----------------------------
def mostrar_tabla(data):

    if data.empty:
        st.warning("Sin datos")
        return

    data = filtrar_filas_validas(data)

    editado = st.data_editor(data, use_container_width=True)

    if st.button("💾 Guardar cambios"):

        base_actual = base.copy()
        cambios = []

        for _, fila in editado.iterrows():

            filtro = (
                (base_actual["id_cuenta"].astype(str) == str(fila["id_cuenta"])) &
                (base_actual["producto"] == fila["producto"]) &
                (base_actual["tipo"] == fila["tipo"])
            )

            # 🔥 manejar bracket opcional
            if "bracket" in base_actual.columns and "bracket" in fila:
                filtro = filtro & (base_actual["bracket"].astype(str) == str(fila["bracket"]))

            # 🔥 alinear columnas
            fila_dict = fila.to_dict()
            for col in base_actual.columns:
                if col not in fila_dict:
                    fila_dict[col] = None

            fila_ok = pd.Series(fila_dict)[base_actual.columns]

            if filtro.any():
                base_actual.loc[filtro, :] = fila_ok.values
                accion = "modificado"
            else:
                base_actual = pd.concat([base_actual, pd.DataFrame([fila_ok])], ignore_index=True)
                accion = "nuevo"

            cambios.append({
                "fecha": datetime.datetime.now(),
                "id_cuenta": fila["id_cuenta"],
                "cliente": fila["cliente"],
                "accion": accion
            })

        subir_excel_github(base_actual, FILE_BASE, "update base")

        hist = leer_excel_github(FILE_HISTORIAL)
        hist = pd.concat([hist, pd.DataFrame(cambios)])

        subir_excel_github(hist, FILE_HISTORIAL, "update historial")

        st.success("Guardado en GitHub + historial 🚀")

# -----------------------------
# VISTAS
# -----------------------------
if st.session_state.page == "inicio":

    st.header("Dashboard")
    c1,c2,c3 = st.columns(3)

    c1.metric("Clientes", df["cliente"].nunique())
    c2.metric("Registros", len(df))
    c3.metric("Productos", df["producto"].nunique())

elif st.session_state.page == "payin":
    mostrar_tabla(df[df["producto"]=="PAYIN"])

elif st.session_state.page == "payout":
    mostrar_tabla(df[df["producto"]=="PAYOUT"])

elif st.session_state.page == "paas":
    mostrar_tabla(df[df["producto"].isin(["PAAS","PASS"])])

elif st.session_state.page == "licencias":
    mostrar_tabla(df[df["producto"]=="LICENCIA"])

elif st.session_state.page == "inter":
    mostrar_tabla(df[df["producto"]=="INTERCONEXION"])

elif st.session_state.page == "hist":
    st.dataframe(historial)
