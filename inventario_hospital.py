# -*- coding: utf-8 -*-
"""
Created on Tue May 12 16:43:59 2026

@author: ISAHISURISADAYIBARRA
"""
import streamlit as st
import pandas as pd
import psycopg2
import io
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

st.set_page_config(layout="wide", page_title="Gestión Biomédica HDLM")

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

# --- CONEXIÓN Y PDF ---
def get_connection(): return psycopg2.connect(**st.secrets["database"])

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

# --- INTERFAZ ---
choice = st.sidebar.selectbox("Módulo", ["Inventario", "Mantenimiento", "Bajas"])

if choice == "Inventario":
    st.header("Inventario de Equipos")
    with st.expander("Registrar Nuevo Equipo"):
        with st.form("reg"):
            c1, c2 = st.columns(2)
            with c1: eq = st.text_input("Equipo"); ma = st.text_input("Marca"); mo = st.text_input("Modelo")
            with c2: se = st.text_input("Serie"); ub = st.text_input("Ubicación"); es = st.selectbox("Estado", ["Operativo", "En Mantenimiento", "Baja"])
            if st.form_submit_button("Guardar"):
                conn = get_connection(); cur = conn.cursor()
                cur.execute("INSERT INTO inventario (equipo, marca, modelo, serie, ubicacion, estado) VALUES (%s,%s,%s,%s,%s,%s)", (eq, ma, mo, se, ub, es))
                conn.commit(); conn.close(); st.rerun()
    conn = get_connection(); df = pd.read_sql("SELECT * FROM inventario", conn); conn.close()
    st.dataframe(df, use_container_width=True)

elif choice == "Mantenimiento":
    st.header("Registro de Mantenimiento")
    conn = get_connection()
    equipos = pd.read_sql("SELECT id, equipo || ' (S/N: ' || serie || ')' as label FROM inventario", conn)
    with st.form("form_manto"):
        sel = st.selectbox("Seleccionar equipo", equipos['label'])
        c1, c2 = st.columns(2)
        with c1: fecha = st.date_input("Fecha"); tipo = st.selectbox("Tipo", ["Preventivo", "Correctivo"]); tec = st.text_input("Técnico")
        with c2: costo = st.number_input("Costo ($)", 0.0); prox = st.date_input("Próximo mantenimiento")
        desc = st.text_area("Descripción detallada")
        if st.form_submit_button("Guardar Mantenimiento"):
            cur = conn.cursor()
            cur.execute("INSERT INTO mantenimientos (equipo_info, fecha_mantenimiento, tipo, tecnico, costo, descripcion, proximo_mantenimiento) VALUES (%s,%s,%s,%s,%s,%s,%s)", (sel, fecha, tipo, tec, costo, desc, prox))
            conn.commit(); st.success("Guardado")
    df = pd.read_sql("SELECT * FROM mantenimientos", conn); conn.close()
    st.dataframe(df, use_container_width=True)
    st.download_button("Descargar PDF", generate_pdf(df, "Reporte de Mantenimiento"), "mantenimiento.pdf")

elif choice == "Bajas":
    st.header("Acta de Baja de Equipo")
    conn = get_connection()
    equipos = pd.read_sql("SELECT id, equipo || ' (S/N: ' || serie || ')' as label FROM inventario", conn)
    with st.form("form_baja"):
        sel = st.selectbox("Seleccionar equipo", equipos['label'])
        c1, c2 = st.columns(2)
        with c1: fecha = st.date_input("Fecha de baja"); mot = st.selectbox("Motivo", ["Robo", "Obsolescencia", "Daño irreparable", "Donación"]); aut = st.text_input("Quién autoriza"); fol = st.text_input("Folio de acta")
        with c2: dest = st.text_input("Destino del equipo"); fac = st.date_input("Fecha del acta"); val = st.number_input("Valor residual ($)", 0.0)
        obs = st.text_area("Observaciones detalladas")
        if st.form_submit_button("Confirmar Baja"):
            cur = conn.cursor()
            cur.execute("INSERT INTO bajas (equipo_info, fecha_baja, motivo, descripcion_motivo, quien_autorizo, destino, folio_acta, fecha_acta, valor_residual) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)", (sel, fecha, mot, obs, aut, dest, fol, fac, val))
            conn.commit(); st.warning("Baja documentada")
    df = pd.read_sql("SELECT * FROM bajas", conn); conn.close()
    st.dataframe(df, use_container_width=True)
    st.download_button("Descargar Acta PDF", generate_pdf(df, "Acta de Bajas"), "bajas.pdf")
