import streamlit as st
import pandas as pd
import os
import datetime

st.set_page_config(page_title="Sistema de Control de Facturación Kashio", layout="wide")

archivo_base = "base_tarifas_guardada.xlsx"
archivo_historial = "historial_tarifas.xlsx"

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
    base_guardada = pd.read_excel(archivo_base)
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

archivo = st.file_uploader("Sube tu base tarifaria", type=["xlsx","csv"])

if archivo is not None:

    if archivo.name.endswith(".csv"):
        df_nuevo = pd.read_csv(archivo)
    else:
        df_nuevo = pd.read_excel(archivo)

    df_nuevo.columns = df_nuevo.columns.str.strip().str.lower()

    if st.button("🧹 LIMPIAR BASE COMPLETA"):
        pd.DataFrame().to_excel(archivo_base, index=False)
        historial = historial.iloc[0:0]
        historial.to_excel(archivo_historial, index=False)
        st.success("Base limpiada")
        st.rerun()

    if st.button("📥 Cargar esta como nueva base"):
        df_nuevo.to_excel(archivo_base, index=False)
        st.success("Nueva base cargada")
        st.rerun()

# -----------------------------
# FORMATO VISUAL
# -----------------------------

def formatear_para_mostrar(df):

    df = df.copy()

    def safe_percent(x):
        try:
            if isinstance(x, str) and "%" in x:
                return x
            if pd.notnull(x):
                return f"{float(x)*100:.2f}%"
        except:
            return x
        return x

    def safe_money(x, simbolo="S/"):
        try:
            if isinstance(x, str):
                return x
            if pd.notnull(x):
                return f"{simbolo} {float(x):.2f}"
        except:
            return x
        return x

    if "comision_variable" in df.columns:
        df["comision_variable"] = df["comision_variable"].apply(safe_percent)

    if "comision_fija" in df.columns:
        df["comision_fija"] = df["comision_fija"].apply(lambda x: safe_money(x, "S/"))

    if "comision_minima_pen" in df.columns:
        df["comision_minima_pen"] = df["comision_minima_pen"].apply(lambda x: safe_money(x, "S/"))

    return df

# -----------------------------
# SIDEBAR
# -----------------------------

st.sidebar.header("🔎 Buscar cliente")

if st.sidebar.button("Cerrar sesión"):
    st.session_state["auth"] = False
    st.rerun()

buscar_id = st.sidebar.text_input("Buscar por ID CUENTA")
buscar_cliente = st.sidebar.text_input("Buscar por nombre")

df = base_guardada.copy()

if buscar_id:
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
# TABLA LIMPIA (🔥 FIX VISUAL)
# -----------------------------

def mostrar_tabla(data):

    if data.empty:
        st.warning("No hay datos")
        return

    data = data.copy()

    # 🔥 eliminar filas vacías
    data = data.loc[~data.isna().all(axis=1)]

    # 🔥 eliminar columnas vacías (LO QUE QUERÍAS)
    data = data.loc[:, ~data.isna().all()]

    data_display = formatear_para_mostrar(data)

    editado = st.data_editor(data_display, use_container_width=True)

    if st.button("Guardar cambios"):

        base_actual = pd.read_excel(archivo_base)

        def limpiar(x):
            if isinstance(x, str):
                return x.replace("%","").replace("S/","").strip()
            return x

        editado = editado.applymap(limpiar)

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
                        base_actual.loc[filtro, col] = fila[col]
            else:
                base_actual = pd.concat([base_actual, pd.DataFrame([fila])])

        base_actual.to_excel(archivo_base, index=False)
        historial.to_excel(archivo_historial, index=False)

        st.success("Cambios guardados")

# -----------------------------
# DASHBOARD
# -----------------------------

def limpiar_num(x):
    try:
        if isinstance(x, str):
            x = x.replace("%","").replace("S/","").replace("$","").strip()
        return float(x)
    except:
        return None

# -----------------------------
# VISTAS
# -----------------------------

if st.session_state.pagina == "inicio":

    st.header("📊 Dashboard")

    df_dash = base_guardada.copy()

    if "comision_variable" in df_dash.columns:
        df_dash["comision_variable_num"] = df_dash["comision_variable"].apply(limpiar_num)

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Clientes", df_dash["cliente"].nunique())
    col2.metric("Registros", len(df_dash))
    col3.metric("Promedio Fee", f"{df_dash['comision_variable_num'].mean():.2f}%" if "comision_variable_num" in df_dash else "0%")
    col4.metric("Productos", df_dash["producto"].nunique())

    st.divider()

    st.subheader("Distribución por producto")
    st.bar_chart(df_dash["producto"].value_counts())

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
    st.dataframe(historial, use_container_width=True)
