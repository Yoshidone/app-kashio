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
# APP
# -----------------------------
st.title("💖 Sistema de Control de Facturación Kashio")
st.subheader(f"Bienvenida {st.session_state['usuario']} 👋")

archivo_base = "base_tarifas_guardada.xlsx"
archivo_historial = "historial_tarifas.xlsx"

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

# NORMALIZACIÓN GLOBAL 🔥
def normalizar(df):
    if "producto" in df.columns:
        df["producto"] = (
            df["producto"]
            .astype(str)
            .str.upper()
            .str.strip()
            .str.replace("Ó","O")
        )
    return df

base_guardada = normalizar(base_guardada)

# -----------------------------
# HISTORIAL
# -----------------------------
if os.path.exists(archivo_historial):
    historial = pd.read_excel(archivo_historial)
else:
    historial = pd.DataFrame(columns=[
        "fecha","id_cuenta","cliente","producto",
        "tipo","bracket","campo","valor_anterior","valor_nuevo"
    ])

# -----------------------------
# UPLOAD
# -----------------------------
archivo = st.file_uploader("Sube tu base tarifaria", type=["xlsx","csv"])

if archivo is not None:

    df_nuevo = pd.read_csv(archivo) if archivo.name.endswith(".csv") else pd.read_excel(archivo)
    df_nuevo.columns = df_nuevo.columns.str.strip().str.lower()

    for col in ["id_cuenta","producto","tipo","bracket"]:
        if col not in df_nuevo.columns:
            df_nuevo[col] = ""

    df_nuevo = normalizar(df_nuevo)

    base_guardada = pd.concat([base_guardada, df_nuevo])
    base_guardada = base_guardada.drop_duplicates(subset=["id_cuenta","producto"], keep="last")

    base_guardada.to_excel(archivo_base, index=False)
    st.success("Base actualizada")

df = base_guardada.copy()

# -----------------------------
# SIDEBAR
# -----------------------------
st.sidebar.header("🔎 Buscar cliente")

if st.sidebar.button("Cerrar sesión"):
    st.session_state["auth"] = False
    st.rerun()

buscar = st.sidebar.text_input("Buscar cliente")

if buscar:
    df = df[df["cliente"].astype(str).str.contains(buscar, case=False, na=False)]

# -----------------------------
# NAV
# -----------------------------
if "pagina" not in st.session_state:
    st.session_state.pagina = "inicio"

cols = st.columns(8)
botones = ["inicio","LICENCIA","PAAS","PAYOUT","PAYIN","WSP","INTERCONEXION","historial"]

for i, b in enumerate(botones):
    if cols[i].button(b.capitalize()):
        st.session_state.pagina = b

st.divider()

# -----------------------------
# TABLA EDITABLE
# -----------------------------
def mostrar_tabla(data):

    if data.empty:
        st.warning("No hay datos")
        return

    editado = st.data_editor(data, use_container_width=True)

    if st.button("Guardar cambios"):

        base_actual = pd.read_excel(archivo_base)
        base_actual = normalizar(base_actual)

        base_actual = base_actual.fillna("")
        editado = editado.fillna("")

        for _, fila in editado.iterrows():

            filtro = (
                (base_actual["id_cuenta"].astype(str) == str(fila["id_cuenta"])) &
                (base_actual["producto"] == fila["producto"])
            )

            if filtro.any():
                original = base_actual.loc[filtro].iloc[0]

                for col in editado.columns:

                    viejo = str(original.get(col,"")).strip()
                    nuevo = str(fila.get(col,"")).strip()

                    if viejo != nuevo:

                        st.warning(f"⚠ {col}: {viejo} → {nuevo}")

                        historial.loc[len(historial)] = {
                            "fecha": datetime.datetime.now(),
                            "id_cuenta": fila["id_cuenta"],
                            "cliente": fila.get("cliente",""),
                            "producto": fila["producto"],
                            "tipo": fila.get("tipo",""),
                            "bracket": fila.get("bracket",""),
                            "campo": col,
                            "valor_anterior": viejo,
                            "valor_nuevo": nuevo
                        }

                        base_actual.loc[filtro, col] = fila[col]

        base_actual.to_excel(archivo_base, index=False)
        historial.to_excel(archivo_historial, index=False)

        st.success("✅ Guardado correctamente")

# -----------------------------
# VISTAS
# -----------------------------
if st.session_state.pagina == "inicio":
    st.header("📊 Dashboard")
    mostrar_tabla(df)

elif st.session_state.pagina == "LICENCIA":
    st.header("LICENCIAS")
    mostrar_tabla(df[df["producto"].str.contains("LICEN", case=False)])

elif st.session_state.pagina == "PAAS":
    st.header("PAAS")
    mostrar_tabla(df[df["producto"].str.contains("PAAS", case=False)])

elif st.session_state.pagina == "PAYOUT":
    st.header("PAYOUTS")
    mostrar_tabla(df[df["producto"].str.contains("PAYOUT", case=False)])

elif st.session_state.pagina == "PAYIN":
    st.header("PAYIN")
    mostrar_tabla(df[df["producto"].str.contains("PAYIN", case=False)])

elif st.session_state.pagina == "WSP":
    st.header("NOTIFICACIONES")
    mostrar_tabla(df[df["producto"].str.contains("WSP", case=False)])

elif st.session_state.pagina == "INTERCONEXION":
    st.header("INTERCONEXIÓN")
    mostrar_tabla(df[df["producto"].str.contains("INTERCONEX", case=False)])

elif st.session_state.pagina == "historial":
    st.header("📜 Historial de cambios")
    if historial.empty:
        st.warning("Sin cambios registrados")
    else:
        st.dataframe(historial, use_container_width=True)
