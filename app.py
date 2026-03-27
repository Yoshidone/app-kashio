import streamlit as st
import pandas as pd
import os
import datetime
import requests
import base64
from io import BytesIO

st.set_page_config(page_title="Sistema de Control de Facturación Kashio", layout="wide")

archivo_base = "base_tarifas_guardada.xlsx"
archivo_historial = "historial_tarifas.xlsx"

# -----------------------------
# 🔐 GITHUB CONFIG
# -----------------------------
GITHUB_TOKEN = st.secrets["TOKEN_GITHUB"]
REPO = "Yoshidone/app-kashio"

def leer_excel_github(file_path):
    url = f"https://api.github.com/repos/{REPO}/contents/{file_path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)

    if r.status_code == 200:
        content = base64.b64decode(r.json()["content"])
        return pd.read_excel(BytesIO(content))
    return None

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
# NORMALIZADOR
# -----------------------------
def normalizar_columnas(df):
    df.columns = df.columns.str.strip().str.lower()

    mapeo = {
        "producto": ["producto","product","prod"],
        "tipo": ["tipo","type"],
        "bracket": ["bracket","rango"],
        "id_cuenta": ["id_cuenta","id cuenta","cuenta"],
        "cliente": ["cliente","client","nombre"],
        "ruc": ["ruc"],
        "comision_variable": ["comision_variable","fee"],
        "comision_fija": ["comision_fija"],
        "comision_minima_pen": ["comision_minima_pen"]
    }

    for col_final, posibles in mapeo.items():
        for col in df.columns:
            if col in posibles:
                df.rename(columns={col: col_final}, inplace=True)

    return df

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
# HEADER
# -----------------------------
st.title("💖 Sistema de Control de Facturación Kashio")
st.subheader(f"Bienvenida {st.session_state['usuario']} 👋")

# -----------------------------
# CARGA BASE (LOCAL + GITHUB)
# -----------------------------
base_github = leer_excel_github(archivo_base)

if base_github is not None:
    base_guardada = normalizar_columnas(base_github)
elif os.path.exists(archivo_base):
    base_guardada = normalizar_columnas(pd.read_excel(archivo_base))
else:
    base_guardada = pd.DataFrame()

# 🔥 FIX columnas necesarias
if not base_guardada.empty:
    if "producto" not in base_guardada.columns:
        base_guardada["producto"] = ""
    if "id_cuenta" not in base_guardada.columns:
        base_guardada["id_cuenta"] = range(1, len(base_guardada) + 1)
    if "bracket" not in base_guardada.columns:
        base_guardada["bracket"] = ""

if os.path.exists(archivo_historial):
    historial = pd.read_excel(archivo_historial)
else:
    historial = pd.DataFrame(columns=[
        "fecha","id_cuenta","cliente","producto","tipo","bracket",
        "valor_anterior","valor_nuevo"
    ])

# -----------------------------
# UPLOAD
# -----------------------------
archivo = st.file_uploader("📂 Sube tu base tarifaria", type=["xlsx","csv"])

if archivo is not None:

    df_nuevo = pd.read_excel(archivo)
    df_nuevo = normalizar_columnas(df_nuevo)

    colA, colB = st.columns(2)

    if colA.button("🧹 Limpiar base completa"):
        pd.DataFrame().to_excel(archivo_base, index=False)
        historial.iloc[0:0].to_excel(archivo_historial, index=False)

        subir_excel_github(pd.DataFrame(), archivo_base, "limpiar base")
        subir_excel_github(pd.DataFrame(), archivo_historial, "limpiar historial")

        st.success("Base limpiada")
        st.rerun()

    if colB.button("📥 Cargar como nueva base"):
        df_nuevo.to_excel(archivo_base, index=False)
        subir_excel_github(df_nuevo, archivo_base, "nueva base")

        st.success("Base cargada 🚀")
        st.rerun()

# -----------------------------
# ALERTAS
# -----------------------------
def generar_alertas(df):

    alertas = []

    if "comision_variable" in df.columns:
        df["fee"] = pd.to_numeric(df["comision_variable"], errors="coerce")

        if (df["fee"] == 0).any():
            alertas.append("🔴 Hay comisiones en 0")

        if (df["fee"] > 5).any():
            alertas.append("⚠️ Comisiones muy altas")

    if {"id_cuenta","producto","tipo","bracket"}.issubset(df.columns):
        if df.duplicated(subset=["id_cuenta","producto","tipo","bracket"]).any():
            alertas.append("⚠️ Hay duplicados")

    return alertas

# -----------------------------
# SIDEBAR
# -----------------------------
st.sidebar.header("🔎 Buscar")

buscar_id = st.sidebar.text_input("ID Cuenta")
buscar_cliente = st.sidebar.text_input("Cliente")

df = base_guardada.copy()

if "producto" in df.columns:
    df["producto"] = df["producto"].astype(str).str.upper().str.strip()

if buscar_id and "id_cuenta" in df.columns:
    df = df[df["id_cuenta"].astype(str).str.contains(buscar_id)]

if buscar_cliente:
    df = df[df["cliente"].astype(str).str.contains(buscar_cliente, case=False)]

# -----------------------------
# NAVEGACIÓN
# -----------------------------
if "pagina" not in st.session_state:
    st.session_state.pagina = "inicio"

col1,col2,col3,col4,col5,col6,col7 = st.columns(7)

if col1.button("Dashboard"): st.session_state.pagina="inicio"
if col2.button("Payin"): st.session_state.pagina="payin"
if col3.button("Payout"): st.session_state.pagina="payout"
if col4.button("PAAS"): st.session_state.pagina="paas"
if col5.button("Licencias"): st.session_state.pagina="licencias"
if col6.button("Interconexión"): st.session_state.pagina="interconexion"
if col7.button("Historial"): st.session_state.pagina="historial"

st.divider()

# -----------------------------
# TABLA EDITABLE
# -----------------------------
def mostrar_tabla(data):

    if data.empty:
        st.warning("No hay datos")
        return

    editado = st.data_editor(data, use_container_width=True)

    if st.button("💾 Guardar cambios"):

        base_actual = normalizar_columnas(pd.read_excel(archivo_base))

        for _, fila in editado.iterrows():

            for col in ["id_cuenta","producto","tipo","bracket"]:
                if col not in base_actual.columns:
                    base_actual[col] = ""

            filtro = (
                (base_actual["id_cuenta"].astype(str) == str(fila.get("id_cuenta",""))) &
                (base_actual["producto"] == fila.get("producto","")) &
                (base_actual["tipo"] == fila.get("tipo",""))
            )

            if "bracket" in base_actual.columns:
                filtro = filtro & (base_actual["bracket"].astype(str) == str(fila.get("bracket","")))

            fila_dict = fila.to_dict()
            for col in base_actual.columns:
                if col not in fila_dict:
                    fila_dict[col] = None

            fila_ok = pd.Series(fila_dict)[base_actual.columns]

            if filtro.any():
                base_actual.loc[filtro, :] = fila_ok.values
            else:
                base_actual = pd.concat([base_actual, pd.DataFrame([fila_ok])], ignore_index=True)

        base_actual.to_excel(archivo_base, index=False)
        subir_excel_github(base_actual, archivo_base, "update desde app")

        st.success("Guardado en local + GitHub 🚀")

# -----------------------------
# SAFE FILTER
# -----------------------------
def safe_filter(df, col, val):
    if col not in df.columns:
        return pd.DataFrame()
    return df[df[col] == val]

# -----------------------------
# VISTAS
# -----------------------------
if st.session_state.pagina == "inicio":

    st.header("📊 Dashboard")

    col1,col2,col3 = st.columns(3)

    col1.metric("Clientes", df["cliente"].nunique())
    col2.metric("Registros", len(df))
    col3.metric("Productos", df["producto"].nunique())

    st.subheader("🚨 Alertas")

    alertas = generar_alertas(df)

    if alertas:
        for a in alertas:
            st.warning(a)
    else:
        st.success("Todo OK")

elif st.session_state.pagina == "payin":
    mostrar_tabla(safe_filter(df,"producto","PAYIN"))

elif st.session_state.pagina == "payout":
    mostrar_tabla(safe_filter(df,"producto","PAYOUT"))

elif st.session_state.pagina == "paas":
    if "producto" in df.columns:
        mostrar_tabla(df[df["producto"].isin(["PAAS","PASS"])])
    else:
        mostrar_tabla(pd.DataFrame())

elif st.session_state.pagina == "licencias":
    mostrar_tabla(safe_filter(df,"producto","LICENCIA"))

elif st.session_state.pagina == "interconexion":
    mostrar_tabla(safe_filter(df,"producto","INTERCONEXION"))

elif st.session_state.pagina == "historial":
    st.dataframe(historial)
