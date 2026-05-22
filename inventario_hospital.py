# -*- coding: utf-8 -*-
"""
Created on Tue May 12 16:43:59 2026

@author: ISAHISURISADAYIBARRA
"""
import streamlit as st
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Gestión Biomédica HDLM", layout="wide")

# --- CONEXIÓN A NEON ---
# Asegúrate de poner tu contraseña real aquí
DB_URL = "postgresql://neondb_owner:npg_RzItUCSb19Tw@ep-aged-dream-aqi1e0aj-pooler.c-8.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

# --- ESTILO AZUL HOSPITALARIO ---
st.markdown("""
    <style>
    .stApp { background-color: #F0F4F8; }
    h1, h2, h3 { color: #1A5276; font-family: 'Segoe UI', sans-serif; }
    [data-testid="stMetricValue"] { color: #2E86C1; }
    .stButton>button { background-color: #2E86C1; color: white; border-radius: 5px; width: 100%; }
    [data-testid="stForm"] { background-color: #FFFFFF; border: 1px solid #D4E6F1; border-radius: 10px; padding: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNCIÓN PARA EJECUTAR CONSULTAS ---
def ejecutar_query(query, params=None, commit=False):
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(query, params)
        resultado = None
        if commit:
            conn.commit()
            resultado = True
        else:
            resultado = cur.fetchall()
        cur.close()
        conn.close()
        return resultado
    except Exception as e:
        st.error(f"Error de conexión con Neon: {e}")
        return None

# --- CARGA DE DATOS ---
datos_db = ejecutar_query("SELECT * FROM inventario ORDER BY fecha_sinc DESC")
df = pd.DataFrame(datos_db) if datos_db else pd.DataFrame(columns=["id", "nombre", "marca", "modelo", "serie", "ubicacion", "estado", "observaciones", "fecha_sinc"])

st.title("🏥 Sistema de Inventario Hospitalario - HDLM")

# DASHBOARD DE MÉTRICAS
st.markdown("### Resumen de Activos")
c1, c2, c3, c4 = st.columns(4)
c1.metric("TOTAL EQUIPOS", len(df))
c2.metric("ACTIVOS", len(df[df["estado"] == "Activo"]) if not df.empty else 0)
c3.metric("MANTENIMIENTO", len(df[df["estado"] == "Mantenimiento"]) if not df.empty else 0)
c4.metric("BAJAS", len(df[df["estado"] == "Baja"]) if not df.empty else 0)

st.divider()

# PESTAÑAS DE ACCIÓN
pestanas = st.tabs(["🆕 Registro", "🔧 Mantenimiento", "❌ Bajas"])

# 1. REGISTRO
with pestanas[0]:
    with st.form("registro_form", clear_on_submit=True):
        st.subheader("📝 Información del Activo")
        col1, col2, col3 = st.columns(3)
        nombre = col1.text_input("Nombre del Equipo *")
        marca = col2.text_input("Marca")
        modelo = col3.text_input("Modelo")
        
        col4, col5, col6 = st.columns(3)
        inv = col4.text_input("No. Inventario (ID) *")
        serie = col5.text_input("N/S (Serie)")
        area = col6.selectbox("Ubicación", ["Tococirugía", "UCIN", "Urgencias", "CEYE", "Quirófano", "Almacén"])
        
        obs = st.text_area("Observaciones")
        
        if st.form_submit_button("💾 Guardar en Neon SQL"):
            if nombre and inv:
                sql = """INSERT INTO inventario (id, nombre, marca, modelo, serie, ubicacion, estado, observaciones, fecha_sinc) 
                         VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                         ON CONFLICT (id) DO UPDATE SET 
                            nombre = EXCLUDED.nombre, 
                            estado = EXCLUDED.estado, 
                            fecha_sinc = EXCLUDED.fecha_sinc"""
                params = (inv, nombre, marca, modelo, serie, area, "Activo", obs, datetime.now())
                if ejecutar_query(sql, params, commit=True):
                    st.success(f"✅ Equipo {inv} guardado correctamente.")
                    st.rerun()
            else:
                st.error("⚠️ El Nombre y el No. de Inventario son obligatorios.")

# 2. MANTENIMIENTO
with pestanas[1]:
    if not df.empty:
        equipos_vivos = df[df["estado"] != "Baja"]
        with st.form("mtto_form"):
            st.subheader("🔧 Reporte de Servicio")
            opciones = equipos_vivos["id"] + " - " + equipos_vivos["nombre"]
            sel = st.selectbox("Seleccionar Equipo", opciones)
            detalles = st.text_area("Descripción del trabajo")
            if st.form_submit_button("🔧 Actualizar a Mantenimiento"):
                id_sel = sel.split(" - ")[0]
                sql_update = "UPDATE inventario SET estado='Mantenimiento', observaciones=%s, fecha_sinc=%s WHERE id=%s"
                if ejecutar_query(sql_update, (detalles, datetime.now(), id_sel), commit=True):
                    st.rerun()

# 3. BAJAS
with pestanas[2]:
    if not df.empty:
        equipos_para_baja = df[df["estado"] != "Baja"]
        with st.form("baja_form"):
            st.subheader("❌ Retiro de Equipo")
            sel_b = st.selectbox("Equipo para Baja", equipos_para_baja["id"] + " - " + equipos_para_baja["nombre"])
            motivo = st.text_input("Motivo de la baja")
            if st.form_submit_button("🔴 Confirmar Baja"):
                id_b = sel_b.split(" - ")[0]
                sql_baja = "UPDATE inventario SET estado='Baja', observaciones=%s, fecha_sinc=%s WHERE id=%s"
                if ejecutar_query(sql_baja, (f"Baja: {motivo}", datetime.now(), id_b), commit=True):
                    st.rerun()

# --- TABLA DE RESULTADOS ---
st.divider()
st.subheader("📋 Inventario Sincronizado (Neon Cloud)")
if not df.empty:
    st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.info("La base de datos está vacía. Registra el primer equipo arriba.")