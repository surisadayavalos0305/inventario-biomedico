# -*- coding: utf-8 -*-
"""
Created on Tue May 12 16:43:59 2026

@author: ISAHISURISADAYIBARRA
"""
# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import psycopg2
import io
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# Configuración de la página
st.set_page_config(layout="wide", page_title="Sistema Biomédico HDLM")

# --- CONEXIÓN PWA (PARA INSTALAR LA APP) ---
st.markdown("""
    <link rel="manifest" href="manifest.json">
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black">
    <meta name="theme-color" content="#0083B8">
""", unsafe_allow_html=True)

# --- FUNCIONES DE BASE DE DATOS ---
def get_connection(): 
    return psycopg2.connect(**st.secrets["database"])

# --- FUNCIONES DE REPORTES ---
def generate_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

def generate_pdf(df, titulo):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter))
    styles = getSampleStyleSheet()
    elements = [Paragraph(titulo, styles['Title']), Spacer(1, 12)]
    data = [df.columns.tolist()] + df.values.tolist()
    t = Table(data)
    t.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.black), ('BACKGROUND', (0,0), (-1,0), colors.grey)]))
    elements.append(t); doc.build(elements)
    return buffer.getvalue()

# --- SEGURIDAD ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if not st.session_state.authenticated:
    st.title("Acceso al Sistema Biomédico")
    pwd = st.text_input("Contraseña:", type="password")
    if st.button("Ingresar"):
        if "auth" in st.secrets and pwd == st.secrets["auth"]["password"]:
            st.session_state.authenticated = True
            st.rerun()
    st.stop()

# --- INTERFAZ PRINCIPAL ---
choice = st.sidebar.selectbox("Módulo", ["Inventario", "Mantenimiento", "Bajas"])

if choice == "Inventario":
    st.header("Inventario de Equipos")
    with st.form("reg"):
        c1, c2 = st.columns(2)
        with c1: eq = st.text_input("Nombre del Equipo"); ma = st.text_input("Marca"); mo = st.text_input("Modelo")
        with c2: se = st.text_input("Serie"); ub = st.text_input("Ubicación"); es = st.text_input("Estado")
        if st.form_submit_button("Guardar"):
            conn = get_connection(); cur = conn.cursor()
            cur.execute("INSERT INTO inventario (equipo, marca, modelo, serie, ubicacion, estado) VALUES (%s,%s,%s,%s,%s,%s)", (eq, ma, mo, se, ub, es))
            conn.commit(); conn.close(); st.rerun()
    conn = get_connection(); df = pd.read_sql("SELECT * FROM inventario", conn); conn.close()
    st.dataframe(df, use_container_width=True)

elif choice == "Mantenimiento":
    st.header("Registro de Mantenimiento")
    with st.form("form_manto"):
        c1, c2 = st.columns(2)
        with c1: equipo = st.text_input("Nombre del Equipo"); serie = st.text_input("Serie del Equipo"); fecha = st.text_input("Fecha")
        with c2: tipo = st.text_input("Tipo de Mantenimiento"); tec = st.text_input("Técnico"); costo = st.text_input("Costo")
        prox = st.text_input("Próximo mantenimiento"); desc = st.text_area("Descripción detallada del trabajo")
        if st.form_submit_button("Guardar Mantenimiento"):
            conn = get_connection(); cur = conn.cursor()
            cur.execute("INSERT INTO mantenimientos (equipo_info, fecha_mantenimiento, tipo, tecnico, costo, descripcion, proximo_mantenimiento) VALUES (%s,%s,%s,%s,%s,%s,%s)", (f"{equipo} (S/N: {serie})", fecha, tipo, tec, costo, desc, prox))
            conn.commit(); conn.close(); st.success("Guardado")
    conn = get_connection(); df = pd.read_sql("SELECT * FROM mantenimientos", conn); conn.close()
    st.dataframe(df, use_container_width=True)

elif choice == "Bajas":
    st.header("Control de Bajas")
    import datetime 

    conn = get_connection()
    df = pd.read_sql("SELECT * FROM inventario WHERE estado != 'Baja'", conn)
    conn.close()

    if not df.empty:
        with st.form("form_baja_completo"):
            st.subheader("📝 Datos del Equipo a dar de baja")
            seleccion = st.selectbox("Seleccione el equipo", df["equipo"] + " - " + df["serie"])
            equipo_sel = df[df["equipo"] + " - " + df["serie"] == seleccion].iloc[0]
            
            c1, c2 = st.columns(2)
            with c1:
                motivo = st.text_input("Motivo de la baja")
                obs = st.text_area("Descripción detallada del motivo")
                autorizado = st.text_input("Autorizado por")
            with c2:
                destino = st.text_input("Destino del equipo")
                folio = st.text_input("Folio de acta")
                fecha_acta = st.date_input("Fecha del acta")
                valor_res = st.number_input("Valor residual", min_value=0.0, format="%.2f")

            if st.form_submit_button("🔴 Confirmar Baja Definitiva"):
                try:
                    conn = get_connection()
                    cur = conn.cursor()
                    
                    # Actualizar estado
                    cur.execute("UPDATE inventario SET estado='Baja' WHERE id=%s", (int(equipo_sel['id']),))
                    
                    # INSERT usando comillas dobles para forzar el nombre de la columna
                    # Esto evita errores si Postgres interpretó el nombre de forma sensible
                    sql_insert = """INSERT INTO bajas 
                    ("equipo_info", "fecha_baja", "motivo", "descripcion_motivo", "quien_autorizo", "destino", "folio_acta", "fecha_acta", "valor_residual") 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"""
                    
                    cur.execute(sql_insert, (
                        f"{equipo_sel['equipo']} {equipo_sel['marca']}", 
                        datetime.date.today(), 
                        motivo, 
                        obs, 
                        autorizado, 
                        destino, 
                        folio, 
                        fecha_acta, 
                        valor_res
                    ))
                    
                    conn.commit()
                    cur.close()
                    conn.close()
                    st.success("¡Baja procesada con éxito!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error de base de datos: {e}")
