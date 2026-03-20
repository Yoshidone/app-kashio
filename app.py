import streamlit as st
import pandas as pd
import os
import datetime

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
# APP PRINCIPAL
# -----------------------------

st.title("💖 Sistema de Control de Facturación Kashio")
st.subheader(f"Bienvenida {st.session_state['usuario']} 👋")

archivo_base = "base_tarifas_guardada.xlsx"
archivo_historial = "historial_tarifas.xlsx"

# -----------------------------
# Cargar base
# -----------------------------

if os.path.exists(archivo_base):
    base_guardada = pd.read_excel(archivo_base)
else:
    base_guardada = pd.DataFrame()

for col in ["id_cuenta","producto","tipo","bracket"]:
    if col not in base_guardada.columns:
        base_guardada[col] = ""

# -----------------------------
# Historial
# -----------------------------

if os.path.exists(archivo_historial):
    historial = pd.read_excel(archivo_historial)
else:
    historial = pd.DataFrame(columns=[
        "fecha","id_cuenta","cliente","producto","tipo","bracket",
        "valor_anterior","valor_nuevo"
    ])

# -----------------------------
# Subir archivo
# -----------------------------

archivo = st.file_uploader("Sube tu base tarifaria", type=["xlsx","csv"])

if archivo is not None:

    if archivo.name.endswith(".csv"):
        df_nuevo = pd.read_csv(archivo)
    else:
        df_nuevo = pd.read_excel(archivo)

    df_nuevo.columns = df_nuevo.columns.str.strip().str.lower()

    for col in ["id_cuenta","producto","tipo","bracket"]:
        if col not in df_nuevo.columns:
            df_nuevo[col] = ""

    df_nuevo = df_nuevo.dropna(how="all")

    df_nuevo["producto"] = df_nuevo["producto"].astype(str).str.upper().str.strip()
    df_nuevo["producto"] = df_nuevo["producto"].replace("INTERCONEXIÓN","INTERCONEXION")

    for _, fila in df_nuevo.iterrows():

        if base_guardada.empty:
            filtro = None
        else:
            filtro = (
                (base_guardada["id_cuenta"].astype(str) == str(fila["id_cuenta"])) &
                (base_guardada["producto"] == fila["producto"]) &
                (base_guardada["tipo"] == fila["tipo"]) &
                (base_guardada["bracket"].astype(str) == str(fila["bracket"]))
            )

        if not base_guardada.empty and fila["id_cuenta"] not in base_guardada["id_cuenta"].values:
            st.info(f"🆕 Nuevo cliente detectado: {fila.get('cliente','')}")

        if base_guardada.empty or (filtro is not None and not filtro.any()):
            st.info(f"📊 Nueva tarifa detectada: {fila.get('cliente','')} - {fila['producto']}")

        if filtro is not None and filtro.any():

            viejo = base_guardada.loc[filtro]

            if "comision_variable" in df_nuevo.columns:

                viejo_valor = viejo.iloc[0].get("comision_variable",0)
                nuevo_valor = fila.get("comision_variable",0)

                if str(viejo_valor) != str(nuevo_valor):

                    st.warning(
                        f"⚠ Cambio de comisión detectado: {fila.get('cliente','')} | {viejo_valor} → {nuevo_valor}"
                    )

                    historial.loc[len(historial)] = {
                        "fecha": datetime.datetime.now(),
                        "id_cuenta": fila["id_cuenta"],
                        "cliente": fila.get("cliente",""),
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

    base_guardada.to_excel(archivo_base, index=False)
    historial.to_excel(archivo_historial, index=False)

    st.success("Base actualizada correctamente")

df = base_guardada.copy()

df["producto"] = df["producto"].astype(str).str.upper().str.strip()
df["producto"] = df["producto"].replace("INTERCONEXIÓN","INTERCONEXION")

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
# Navegación
# -----------------------------

if "pagina" not in st.session_state:
    st.session_state.pagina = "inicio"

col1,col2,col3,col4,col5,col6,col7,col8 = st.columns(8)

if col1.button("Dashboard"): st.session_state.pagina="inicio"
if col2.button("Licencias"): st.session_state.pagina="licencias"
if col3.button("PAAS"): st.session_state.pagina="paas"
if col4.button("Payouts"): st.session_state.pagina="payouts"
if col5.button("Payin"): st.session_state.pagina="payin"
if col6.button("Notificaciones"): st.session_state.pagina="notificaciones"
if col7.button("Interconexión"): st.session_state.pagina="interconexion"
if col8.button("Historial"): st.session_state.pagina="historial"

st.divider()

# -----------------------------
# TABLA EDITABLE (FIX APLICADO)
# -----------------------------

def mostrar_tabla(data):

    if data.empty:
        st.warning("No hay datos disponibles")
        return

    data = data.dropna(how="all")
    data = data.dropna(axis=1, how="all")

    editado = st.data_editor(data, use_container_width=True, num_rows="dynamic")

    if st.button("Guardar cambios"):

        base_actual = pd.read_excel(archivo_base)

        # 🔥 FIX ERROR KEY
        for col in ["id_cuenta","producto","tipo","bracket"]:
            if col not in base_actual.columns:
                base_actual[col] = ""

        for col in ["id_cuenta","producto","tipo","bracket"]:
            if col not in editado.columns:
                editado[col] = ""

        base_actual["id_cuenta"] = base_actual["id_cuenta"].astype(str)
        editado["id_cuenta"] = editado["id_cuenta"].astype(str)

        for _, fila in editado.iterrows():

            filtro = (
                (base_actual["id_cuenta"] == fila["id_cuenta"]) &
                (base_actual["producto"] == fila["producto"]) &
                (base_actual["tipo"] == fila["tipo"]) &
                (base_actual["bracket"].astype(str) == str(fila["bracket"]))
            )

            if filtro.any():
                base_actual.loc[filtro, :] = fila

        base_actual.to_excel(archivo_base, index=False)
        st.success("✅ Cambios guardados")

# -----------------------------
# VISTAS
# -----------------------------

if st.session_state.pagina == "inicio":
    st.header("📊 Dashboard")
    mostrar_tabla(df)

elif st.session_state.pagina == "paas":
    st.header("PAAS")
    mostrar_tabla(df[df["producto"].isin(["PAAS","PASS"])])

elif st.session_state.pagina == "payin":
    st.header("PAYIN")
    mostrar_tabla(df[df["producto"]=="PAYIN"])

elif st.session_state.pagina == "payouts":
    st.header("PAYOUTS")
    mostrar_tabla(df[df["producto"]=="PAYOUT"])

elif st.session_state.pagina == "notificaciones":
    st.header("NOTIFICACIONES WSP")
    mostrar_tabla(df[df["producto"]=="WSP"])

elif st.session_state.pagina == "licencias":
    st.header("LICENCIAS")
    mostrar_tabla(df[df["producto"]=="LICENCIA"])

elif st.session_state.pagina == "interconexion":
    st.header("INTERCONEXIÓN")
    mostrar_tabla(df[df["producto"]=="INTERCONEXION"])

elif st.session_state.pagina == "historial":

    st.header("Historial de cambios de tarifas")

    if historial.empty:
        st.warning("No hay cambios registrados")
    else:
        st.dataframe(historial, use_container_width=True)
