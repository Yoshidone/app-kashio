import streamlit as st
import pandas as pd
import os
import datetime
import requests
import base64
from io import BytesIO

st.set_page_config(page_title="Sistema Tarifario Kashio", layout="wide")

archivo_base = "base_tarifas_guardada.xlsx"
archivo_historial = "historial_tarifas.xlsx"

# -----------------------------
# 🔐 GITHUB
# -----------------------------
GITHUB_TOKEN = st.secrets["TOKEN_GITHUB"]
REPO = "Yoshidone/app-kashio"

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
# CARGA BASE
# -----------------------------
if os.path.exists(archivo_base):
    base_guardada = normalizar_columnas(pd.read_excel(archivo_base))
else:
    base_guardada = pd.DataFrame()

if os.path.exists(archivo_historial):
    historial = pd.read_excel(archivo_historial)
else:
    historial = pd.DataFrame()

# -----------------------------
# BUSCADOR PRO
# -----------------------------
st.sidebar.header("🔎 Buscar")

buscar_id = st.sidebar.text_input("ID Cuenta")
buscar_cliente = st.sidebar.text_input("Cliente")

df = base_guardada.copy()

if "producto" in df.columns:
    df["producto"] = df["producto"].astype(str).str.upper().str.strip()

if "id_cuenta" in df.columns:
    df["id_cuenta"] = df["id_cuenta"].astype(str).str.replace(".0","", regex=False)

if buscar_id:
    df = df[df["id_cuenta"] == str(buscar_id).strip()]

if buscar_cliente:
    df = df[df["cliente"].astype(str).str.contains(buscar_cliente, case=False)]

# -----------------------------
# TABLA CON FORMATO %
# -----------------------------
def mostrar_tabla(data):

    if data.empty:
        st.warning("No hay datos")
        return

    data = data.dropna(how="all")
    data = data.dropna(axis=1, how="all")

    # 🔥 FORMATO BONITO (como tu Excel)
    data_mostrar = data.copy()

    if "comision_variable" in data_mostrar.columns:
        data_mostrar["comision_variable"] = data_mostrar["comision_variable"].apply(
            lambda x: f"{float(x)*100:.2f}%" if pd.notnull(x) and str(x).replace('.','',1).isdigit() else x
        )

    editado = st.data_editor(data_mostrar, use_container_width=True)

    if st.button("💾 Guardar cambios"):

        base_actual = normalizar_columnas(pd.read_excel(archivo_base))
        cambios = []

        for _, fila in editado.iterrows():

            # 🔥 convertir de % a decimal para guardar
            fila = fila.copy()
            if "comision_variable" in fila:
                try:
                    if "%" in str(fila["comision_variable"]):
                        fila["comision_variable"] = float(str(fila["comision_variable"]).replace("%",""))/100
                except:
                    pass

            filtro = (
                (base_actual["id_cuenta"].astype(str) == str(fila["id_cuenta"])) &
                (base_actual["producto"] == fila["producto"]) &
                (base_actual["tipo"] == fila["tipo"]) &
                (base_actual["bracket"].astype(str) == str(fila["bracket"]))
            )

            if filtro.any():

                fila_antigua = base_actual.loc[filtro].iloc[0].to_dict()

                for col in fila.index:
                    if str(fila_antigua.get(col)) != str(fila[col]):
                        cambios.append({
                            "fecha": datetime.datetime.now(),
                            "usuario": st.session_state["usuario"],
                            "id_cuenta": fila["id_cuenta"],
                            "columna": col,
                            "valor_anterior": fila_antigua.get(col),
                            "valor_nuevo": fila[col]
                        })

                base_actual.loc[filtro, :] = fila

            else:
                base_actual = pd.concat([base_actual, pd.DataFrame([fila])], ignore_index=True)

        base_actual.to_excel(archivo_base, index=False)
        subir_excel_github(base_actual, archivo_base, "update base")

        if cambios:
            hist_df = pd.DataFrame(cambios)

            if os.path.exists(archivo_historial):
                hist_actual = pd.read_excel(archivo_historial)
                hist_df = pd.concat([hist_actual, hist_df], ignore_index=True)

            hist_df.to_excel(archivo_historial, index=False)
            subir_excel_github(hist_df, archivo_historial, "update historial")

        st.success("Guardado con formato + historial + GitHub 🚀")

# -----------------------------
# VISTAS
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

if st.session_state.pagina == "inicio":
    st.header("📊 Dashboard")
    st.bar_chart(df["producto"].value_counts())

elif st.session_state.pagina == "payin":
    mostrar_tabla(df[df["producto"]=="PAYIN"])

elif st.session_state.pagina == "payout":
    mostrar_tabla(df[df["producto"]=="PAYOUT"])

elif st.session_state.pagina == "paas":
    mostrar_tabla(df[df["producto"].isin(["PAAS","PASS"])])

elif st.session_state.pagina == "licencias":
    mostrar_tabla(df[df["producto"]=="LICENCIA"])

elif st.session_state.pagina == "interconexion":
    mostrar_tabla(df[df["producto"]=="INTERCONEXION"])

elif st.session_state.pagina == "historial":
    st.dataframe(historial)
