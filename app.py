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

USERS = {"yoshira": "1234"}

def check_login():
    st.title("🔐 Acceso")
    user = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")

    if st.button("Ingresar"):
        if user in USERS and USERS[user] == password:
            st.session_state["auth"] = True
            st.session_state["usuario"] = user
        else:
            st.error("Error")

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

# -----------------------------
# ALERTAS + DUPLICADOS
# -----------------------------

def detectar_duplicados(df):
    return df[df.duplicated(
        subset=["id_cuenta","producto","tipo","bracket"],
        keep=False
    )]

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
# NAV (TU ORIGINAL)
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

    duplicados = detectar_duplicados(data)

    def highlight(row):
        if row.name in duplicados.index:
            return ['background-color: #ffcccc'] * len(row)
        return [''] * len(row)

    st.subheader("✏️ Edita tu base")

    st.dataframe(data.style.apply(highlight, axis=1), use_container_width=True)

    editado = st.data_editor(data, use_container_width=True)

    # -------------------------
    # SELECCIÓN DE DUPLICADOS
    # -------------------------

    if not duplicados.empty:

        st.subheader("🔴 Duplicados detectados (elige cuál eliminar)")

        duplicados["eliminar"] = False

        seleccion = st.data_editor(duplicados, use_container_width=True)

        if st.button("🗑️ Eliminar seleccionados"):

            a_eliminar = seleccion[seleccion["eliminar"] == True]

            nueva_base = data.copy()

            for _, fila in a_eliminar.iterrows():
                filtro = (
                    (nueva_base["id_cuenta"] == fila["id_cuenta"]) &
                    (nueva_base["producto"] == fila["producto"]) &
                    (nueva_base["tipo"] == fila["tipo"]) &
                    (nueva_base["bracket"] == fila["bracket"])
                )
                nueva_base = nueva_base[~filtro]

            nueva_base.to_excel(archivo_base, index=False)

            st.success("Duplicados eliminados correctamente")
            st.rerun()

    # -------------------------
    # GUARDAR CAMBIOS
    # -------------------------

    if st.button("💾 Guardar cambios"):

        editado.to_excel(archivo_base, index=False)

        st.success("Cambios guardados")

# -----------------------------
# VISTAS
# -----------------------------

if st.session_state.pagina == "inicio":

    st.header("📊 Dashboard")

    col1,col2,col3 = st.columns(3)

    col1.metric("Clientes", df["cliente"].nunique())
    col2.metric("Registros", len(df))
    col3.metric("Productos", df["producto"].nunique())

    duplicados = detectar_duplicados(df)

    if not duplicados.empty:
        st.warning(f"⚠️ Hay {len(duplicados)} registros duplicados")
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
