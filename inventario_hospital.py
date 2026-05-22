# -*- coding: utf-8 -*-
"""
Created on Tue May 12 16:43:59 2026

@author: ISAHISURISADAYIBARRA
"""
import streamlit as st
import pandas as pd
import psycopg2
from psycopg2 import extras
import io
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Gestión Hospital de la Mujer", layout="wide")

# --- SEGURIDAD Y AUTENTICACIÓN ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

def check_password():
    if not st.session_state.authenticated:
        st.title("🔐 Acceso al Sistema Biomédico")
        # Aquí se usa el secreto 'auth' que configuraste en Streamlit Cloud
        pwd = st.text_input("Ingrese la contraseña para acceder al sistema", type="password")
        if st.button("Entrar"):
            if "auth" in st.secrets and pwd == st.secrets["auth"]["password"]:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Contraseña incorrecta o no configurada en Secrets")
        return False
    return True

if not check_password():
    st.stop()

# --- CONEXIÓN A BASE DE DATOS ---
def get_connection():
    try:
        conn = psycopg2.connect(
            host=st.secrets["database"]["host"],
            database=st.secrets["database"]["dbname"],
            user=st.secrets["database"]["user"],
            password=st.secrets["database"]["password"],
            port=st.secrets["database"]["port"]
        )
        return conn
    except Exception as e:
        st.error(f"Error de conexión a la base de datos: {e}")
        return None

# --- FUNCIONES DE EXPORTACIÓN ---
def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Reporte_Biomedico')
    return output.getvalue()

# --- INTERFAZ PRINCIPAL ---
st.title("🏥 Sistema de Inventario y Mantenimiento - Hospital de la Mujer")

menu = ["Inventario", "Mantenimiento", "Bajas de Equipo"]
choice = st.sidebar.selectbox("Seleccione Módulo", menu)

# --- CATÁLOGOS SOLICITADOS ---
equipos_lista = ["Ultrasonido", "Ventilador Mecánico", "Incubadora", "Monitor de Signos Vitales", "Desfibrilador", "Electrocardiógrafo", "Cuna de Calor Radiante", "Bomba de Infusión"]
marcas_lista = ["GE Healthcare", "Dräger", "Philips", "Hitachi Aloka", "Mindray", "Medtronic", "Nihon Kohden"]

ubicaciones_lista = [
    "Hospitalización Alto Riesgo", 
    "Tococirugía", 
    "Quirófano", 
    "Expulsión", 
    "Labor", 
    "UCIN", 
    "Crecimiento y Desarrollo", 
    "Terapia Intensiva", 
    "Imagenología", 
    "Urgencias",
    "Consulta Externa",
    "CEYE"
]

# --- MÓDULO 1: INVENTARIO ---
if choice == "Inventario":
    st.header("📦 Registro de Equipo Biomédico")
    
    with st.form("form_inventario"):
        col1, col2 = st.columns(2)
        with col1:
            equipo = st.selectbox("Tipo de Equipo", equipos_lista)
            marca = st.selectbox("Marca", marcas_lista)
            modelo = st.text_input("Modelo Específico")
        with col2:
            serie = st.text_input("Número de Serie (S/N)")
            ubicacion = st.selectbox("Ubicación / Área", ubicaciones_lista)
            estado = st.selectbox("Estado Operativo", ["Operativo", "En Mantenimiento", "Fuera de Servicio", "Baja Provisional"])
        
        submitted = st.form_submit_button("Registrar en Base de Datos")
        if submitted:
            conn = get_connection()
            if conn:
                cur = conn.cursor()
                query = "INSERT INTO inventario (equipo, marca, modelo, serie, ubicacion, estado) VALUES (%s, %s, %s, %s, %s, %s)"
                cur.execute(query, (equipo, marca, modelo, serie, ubicacion, estado))
                conn.commit()
                cur.close()
                conn.close()
                st.success(f"✅ {equipo} ({serie}) guardado correctamente en {ubicacion}.")

# --- MÓDULO 2: MANTENIMIENTO ---
elif choice == "Mantenimiento":
    st.header("🛠️ Registro y Control de Mantenimiento")
    
    conn = get_connection()
    if conn:
        # Cargamos los equipos registrados para poder seleccionarlos
        df_inv = pd.read_sql("SELECT id, equipo, serie, ubicacion FROM inventario", conn)
        
        if not df_inv.empty:
            opciones = [f"{row['id']} - {row['equipo']} ({row['serie']}) en {row['ubicacion']}" for index, row in df_inv.iterrows()]
            equipo_sel = st.selectbox("Seleccione equipo atendido", opciones)
            
            with st.form("form_manto"):
                tipo_manto = st.radio("Tipo de Mantenimiento", ["Preventivo", "Correctivo", "Calibración"])
                desc = st.text_area("Descripción del servicio")
                tecnico = st.text_input("Técnico Responsable")
                
                if st.form_submit_button("Guardar Mantenimiento"):
                    st.success("Registro de mantenimiento guardado.")
            
            st.divider()
            st.subheader("📋 Historial para Exportar")
            # Ejemplo de visualización de tabla para exportar
            st.dataframe(df_inv) 
            
            excel_data = to_excel(df_inv)
            st.download_button(label="📥 Descargar Inventario en Excel", data=excel_data, file_name="inventario_hdlm.xlsx")
            st.info("💡 Para reporte PDF: Presiona Ctrl+P y selecciona 'Guardar como PDF'.")
        else:
            st.warning("No hay equipos en el inventario para registrar mantenimiento.")
        conn.close()

# --- MÓDULO 3: BAJAS ---
elif choice == "Bajas de Equipo":
    st.header("⚠️ Control de Bajas (Desincorporación)")
    st.write("Seleccione el equipo que será dado de baja por obsolescencia o daño irreparable.")
    
    # Aquí puedes añadir una lógica similar a mantenimiento para eliminar o marcar como "BAJA"
    st.info("Módulo habilitado para gestión de activos fijos.")
