import streamlit as st
import pandas as pd
import os
import datetime

st.set_page_config(page_title="Sistema de Control de Facturación Kashio", layout="wide")

archivo_base = "base_tarifas_guardada.xlsx"
archivo_historial = "historial_tarifas.xlsx"

# -----------------------------
# NORMALIZADOR INTELIGENTE
# -----------------------------

def normalizar_columnas(df):

    df.columns = df.columns.str.strip().str.lower()

    mapeo = {
        "producto": ["producto","product"],
        "tipo": ["tipo"],
        "bracket": ["bracket"],
        "id_cuenta": ["id_cuenta","id cuenta"],
        "cliente": ["cliente"],
        "comision_variable": ["comision_variable","fee"],
        "comision_fija": ["comision_fija"]
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
    st.title("🔐 Acceso")

    user = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")

    if st.button("Ingresar"):
        if user in USERS and USERS[user] == password:
            st.session_state["auth"] = True
        else:
            st.error("Error")

if "auth" not in st.session_state or not st.session_state["auth"]:
    check_login()
    st.stop()

# -----------------------------
# CARGA
# -----------------------------

if os.path.exists(archivo_base):
    base_guardada = normalizar_columnas(pd.read_excel(archivo_base))
else:
    base_guardada = pd.DataFrame()

if os.path.exists(archivo_historial):
    historial = pd.read_excel(archivo_historial)
else:
    historial = pd.DataFrame(columns=[
        "fecha","cliente","producto","tipo","bracket","valor_anterior","valor_nuevo"
    ])

# -----------------------------
# UPLOAD
# -----------------------------

archivo = st.file_uploader("Sube base", type=["xlsx","csv"])

if archivo is not None:

    df_nuevo = pd.read_excel(archivo)
    df_nuevo = normalizar_columnas(df_nuevo)

    if st.button("Reemplazar base"):
        df_nuevo.to_excel(archivo_base, index=False)
        st.success("Base cargada")
        st.rerun()

# -----------------------------
# ALERTAS
# -----------------------------

def generar_alertas(df):

    alertas = []

    if "comision_variable" in df.columns:

        def limpiar(x):
            try:
                if isinstance(x, str):
                    x = x.replace("%","")
                return float(x)
            except:
                return None

        df["fee"] = df["comision_variable"].apply(limpiar)

        if (df["fee"] == 0).any():
            alertas.append("🔴 Hay comisiones en 0")

        if (df["fee"] > 5).any():
            alertas.append("⚠️ Hay comisiones muy altas")

    if df.duplicated(subset=["id_cuenta","producto","tipo","bracket"]).any():
        alertas.append("⚠️ Hay duplicados")

    return alertas

# -----------------------------
# DASHBOARD
# -----------------------------

def limpiar_num(x):
    try:
        if isinstance(x, str):
            x = x.replace("%","").replace("S/","")
        return float(x)
    except:
        return None

# -----------------------------
# SIDEBAR
# -----------------------------

buscar_id = st.sidebar.text_input("Buscar ID")
buscar_cliente = st.sidebar.text_input("Buscar cliente")

df = base_guardada.copy()

if buscar_id:
    df = df[df["id_cuenta"].astype(str).str.contains(buscar_id)]

if buscar_cliente:
    df = df[df["cliente"].astype(str).str.contains(buscar_cliente, case=False)]

# -----------------------------
# NAV
# -----------------------------

if "pagina" not in st.session_state:
    st.session_state.pagina = "inicio"

col1,col2,col3,col4 = st.columns(4)

if col1.button("Dashboard"): st.session_state.pagina="inicio"
if col2.button("Payin"): st.session_state.pagina="payin"
if col3.button("Payout"): st.session_state.pagina="payout"
if col4.button("Historial"): st.session_state.pagina="historial"

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

    if st.button("Guardar cambios"):

        base_actual = pd.read_excel(archivo_base)
        base_actual = normalizar_columnas(base_actual)

        for _, fila in editado.iterrows():

            filtro = (
                (base_actual["id_cuenta"].astype(str) == str(fila["id_cuenta"])) &
                (base_actual["producto"] == fila["producto"]) &
                (base_actual["tipo"] == fila["tipo"]) &
                (base_actual["bracket"].astype(str) == str(fila["bracket"]))
            )

            if filtro.any():
                for col in base_actual.columns:
                    if col in fila:
                        viejo = base_actual.loc[filtro, col].iloc[0]
                        nuevo = fila[col]

                        if str(viejo) != str(nuevo):
                            historial.loc[len(historial)] = {
                                "fecha": datetime.datetime.now(),
                                "cliente": fila.get("cliente",""),
                                "producto": fila["producto"],
                                "tipo": fila["tipo"],
                                "bracket": fila["bracket"],
                                "valor_anterior": viejo,
                                "valor_nuevo": nuevo
                            }

                            base_actual.loc[filtro, col] = nuevo
            else:
                base_actual = pd.concat([base_actual, pd.DataFrame([fila])])

        base_actual.to_excel(archivo_base, index=False)
        historial.to_excel(archivo_historial, index=False)

        st.success("Guardado correctamente")

# -----------------------------
# VISTAS
# -----------------------------

if st.session_state.pagina == "inicio":

    st.header("Dashboard")

    df_dash = base_guardada.copy()

    if "comision_variable" in df_dash.columns:
        df_dash["fee"] = df_dash["comision_variable"].apply(limpiar_num)

    col1,col2,col3 = st.columns(3)

    col1.metric("Clientes", df_dash["cliente"].nunique())
    col2.metric("Registros", len(df_dash))
    col3.metric("Fee promedio", f"{df_dash['fee'].mean():.2f}%" if "fee" in df_dash else "0")

    st.subheader("Alertas")

    alertas = generar_alertas(df_dash)

    for a in alertas:
        st.warning(a)

elif st.session_state.pagina == "payin":
    mostrar_tabla(df[df["producto"]=="PAYIN"])

elif st.session_state.pagina == "payout":
    mostrar_tabla(df[df["producto"]=="PAYOUT"])

elif st.session_state.pagina == "historial":
    st.dataframe(historial)
