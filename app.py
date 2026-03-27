import streamlit as st
import pandas as pd
import os
import datetime

st.set_page_config(page_title="Sistema de Control de Facturación Kashio", layout="wide")

archivo_base = "base_tarifas_guardada.xlsx"
archivo_historial = "historial_tarifas.xlsx"

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
        st.success("Base limpiada")
        st.rerun()

    if colB.button("📥 Cargar como nueva base"):
        df_nuevo.to_excel(archivo_base, index=False)
        st.success("Base cargada")
        st.rerun()

# -----------------------------
# ALERTAS
# -----------------------------

def generar_alertas(df):

    alertas = []

    def limpiar(x):
        try:
            if isinstance(x, str):
                x = x.replace("%","")
            return float(x)
        except:
            return None

    if "comision_variable" in df.columns:
        df["fee"] = df["comision_variable"].apply(limpiar)

        if (df["fee"] == 0).any():
            alertas.append("🔴 Hay comisiones en 0")

        if (df["fee"] > 5).any():
            alertas.append("⚠️ Comisiones muy altas")

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

if buscar_id:
    df = df[df["id_cuenta"].astype(str).str.contains(buscar_id)]

if buscar_cliente:
    df = df[df["cliente"].astype(str).str.contains(buscar_cliente, case=False)]

# -----------------------------
# NAVEGACIÓN (TU ORIGINAL)
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

    data = data.loc[~data.isna().all(axis=1)]
    data = data.loc[:, ~data.isna().all()]

    editado = st.data_editor(data, use_container_width=True)

    if st.button("💾 Guardar cambios"):

        base_actual = normalizar_columnas(pd.read_excel(archivo_base))

        for _, fila in editado.iterrows():

            filtro = (
                (base_actual["id_cuenta"].astype(str) == str(fila["id_cuenta"])) &
                (base_actual["producto"] == fila["producto"]) &
                (base_actual["tipo"] == fila["tipo"]) &
                (base_actual["bracket"].astype(str) == str(fila["bracket"]))
            )

            if filtro.any():
                base_actual.loc[filtro, :] = fila
            else:
                base_actual = pd.concat([base_actual, pd.DataFrame([fila])])

        base_actual.to_excel(archivo_base, index=False)
        st.success("Guardado correctamente")

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
