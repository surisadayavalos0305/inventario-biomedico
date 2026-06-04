# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import psycopg2
import io
import xlsxwriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape, letter

# Configuración de la página
st.set_page_config(layout="wide", page_title="Sistema Biomédico HDLM")

# --- DISEÑO Y ESTILO DE PÁGINA ---
st.markdown("""
    <style>
    .stApp { background-color: #f4f7f6; }
    .stForm { background-color: #ffffff; border: 1px solid #dcdcdc; border-radius: 8px; padding: 20px; }
    [data-testid="stSidebar"] { background-color: #e6eaf1; }
    </style>
""", unsafe_allow_html=True)

# --- FUNCIONES DE BASE DE DATOS ---
def get_connection(): 
    return psycopg2.connect(**st.secrets["database"])

# --- FUNCIONES DE REPORTES ---
def generate_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        # Los datos inician en la fila 7 (índice 6)
        df.to_excel(writer, index=False, sheet_name='Inventario', startrow=6)
        
        workbook = writer.book
        worksheet = writer.sheets['Inventario']
        
        # --- FORMATOS ---
        header_format = workbook.add_format({
            'bold': True, 'align': 'center', 'valign': 'center',
            'fg_color': '#D3D3D3', 'border': 1
        })
        title_format = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'center'})
        subtitle_format = workbook.add_format({'bold': True, 'font_size': 12, 'align': 'center'})
        cell_format = workbook.add_format({'border': 1, 'align': 'left'})
        
        # --- 1. TÍTULOS Y ENCABEZADOS (Igual al PDF) ---
        worksheet.merge_range('A2:G2', 'HOSPITAL DE LA MUJER', title_format)
        worksheet.merge_range('A3:G3', 'INGENIERÍA BIOMÉDICA', subtitle_format)
        worksheet.merge_range('A4:G4', 'INVENTARIO DE EQUIPO MÉDICO', title_format)
        worksheet.merge_range('A5:G5', '(F-HM-BM-01)', subtitle_format)
        
        # --- 2. DIBUJAR TABLA ---
        # Aplicamos el encabezado a la fila 7
        headers = ["ID", "NOMBRE", "MARCA", "MODELO", "SERIE", "UBICACIÓN", "ESTADO"]
        for i, h in enumerate(headers):
            worksheet.write(6, i, h, header_format)
            worksheet.set_column(i, i, 18) # Ancho de columna
            
        # --- 3. PIE DE PÁGINA ---
        # Calculamos la fila final para poner el REV-01
        last_row = len(df) + 7
        worksheet.write(last_row, 6, "REV-01", workbook.add_format({'align': 'right'}))
        
        # --- 4. LOGO ---
        try:
            worksheet.insert_image('A1', 'issea.png', {'x_scale': 0.5, 'y_scale': 0.5})
        except:
            pass

    return output.getvalue()


def generate_pdf_custom(df, titulo):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=landscape(letter))
    
    # --- 1. LOGO Y ENCABEZADO ---
    try:
        c.drawImage("issea.png", 50, 520, width=120, height=60)
    except:
        pass
    
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(450, 560, "HOSPITAL DE LA MUJER")
    c.drawCentredString(450, 540, "INGENIERÍA BIOMÉDICA")
    
    # Título principal más arriba
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(450, 500, "INVENTARIO DE EQUIPO MEDICO")
    
    c.setFont("Helvetica", 10)
    c.drawCentredString(450, 480, "(F-HM-BM-01)")
    
    # --- 2. DIBUJO DE LA TABLA ---
    y = 440
    pos_x = [60, 110, 260, 370, 480, 580, 700] 
    headers = ["ID", "NOMBRE", "MARCA", "MODELO", "SERIE", "UBICACIÓN", "ESTADO"]
    c.rect(50, y, 700, 30) 
    c.setFont("Helvetica-Bold", 10)
    for i, h in enumerate(headers):
        c.drawString(pos_x[i], y + 10, h)
        
    # --- 3. CONTENIDO Y PIE DE PÁGINA ---
    y -= 25
    c.setFont("Helvetica", 9)
    
    def draw_footer(canvas_obj):
        canvas_obj.setFont("Helvetica", 8)
        canvas_obj.drawRightString(750, 20, "REV-01")
        
    draw_footer(c)
    
    for _, row in df.iterrows():
        c.line(50, y + 20, 750, y + 20)
        datos = [str(row.get('id', '')), str(row.get('equipo', '')), str(row.get('marca', '')), 
                 str(row.get('modelo', '')), str(row.get('serie', '')), str(row.get('ubicacion', '')), 
                 str(row.get('estado', ''))]
        for i, val in enumerate(datos):
            c.drawString(pos_x[i], y + 5, val)
        y -= 25
        if y < 50:
            c.showPage()
            draw_footer(c)
            y = 450
            c.rect(50, y, 700, 30)
            c.setFont("Helvetica-Bold", 10)
            for i, h in enumerate(headers):
                c.drawString(pos_x[i], y + 10, h)
            y -= 25
            c.setFont("Helvetica", 9)
            
    c.save()
    return buffer.getvalue()
# --- IMPRESO ---    
def export_module(df, nombre):
    st.write("---")
    st.subheader("📤 Exportar Datos")
    indices = st.multiselect("Selecciona registros para exportar:", df.index.tolist())
    df_f = df.loc[indices] if indices else df
    
    if not df_f.empty:
        c1, c2 = st.columns(2)
        c1.download_button("📥 Exportar a Excel", generate_excel(df_f), f"{nombre}.xlsx", "application/vnd.ms-excel")
        c2.download_button("📄 Exportar a PDF", generate_pdf_custom(df_f, nombre), f"{nombre}.pdf", "application/pdf")
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

def get_connection(): 
    return psycopg2.connect(**st.secrets["database"])

if choice == "Inventario":
    st.header("Inventario de Equipos")
    with st.form("reg", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1: eq = st.text_input("Nombre del Equipo"); ma = st.text_input("Marca"); mo = st.text_input("Modelo")
        with c2: se = st.text_input("Serie"); ub = st.text_input("Ubicación"); es = st.text_input("Estado")
        if st.form_submit_button("Guardar"):
            conn = get_connection(); cur = conn.cursor()
            cur.execute("INSERT INTO inventario (equipo, marca, modelo, serie, ubicacion, estado) VALUES (%s,%s,%s,%s,%s,%s)", (eq, ma, mo, se, ub, es))
            conn.commit(); conn.close(); st.rerun()
    conn = get_connection(); df = pd.read_sql("SELECT * FROM inventario", conn); conn.close()
    st.dataframe(df, use_container_width=True)
    export_module(df, "Inventario_Equipos")

elif choice == "Mantenimiento":
    st.header("Registro de Mantenimiento")
    with st.form("form_manto", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1: 
            equipo = st.text_input("Nombre del Equipo")
            serie = st.text_input("Serie del Equipo")
            # Usamos date_input para asegurar el formato de fecha correcto
            fecha = st.date_input("Fecha de Mantenimiento")
        with c2: 
            tipo = st.text_input("Tipo de Mantenimiento")
            tec = st.text_input("Técnico")
            costo = st.text_input("Costo")
        prox = st.date_input("Próximo mantenimiento")
        desc = st.text_area("Descripción detallada del trabajo")
        
        if st.form_submit_button("Guardar Mantenimiento"):
            conn = get_connection()
            cur = conn.cursor()
            try:
                query = "INSERT INTO mantenimientos (equipo_info, fecha_mantenimiento, tipo, tecnico, costo, descripcion, proximo_mantenimiento) VALUES (%s, %s, %s, %s, %s, %s, %s)"
                valores = (f"{equipo} - Serie: {serie}", fecha, tipo, tec, float(costo) if costo else 0.0, desc, prox)
                
                cur.execute(query, valores)
                conn.commit() # Fuerza el guardado
                
                # VERIFICACIÓN: Consultamos inmediatamente después de insertar
                cur.execute("SELECT count(*) FROM mantenimientos")
                count = cur.fetchone()[0]
                st.write(f"Total de registros en la tabla ahora: {count}")
                
                st.success("Guardado correctamente")
            except Exception as e:
                st.error(f"Error: {e}")
            finally:
                cur.close()
                conn.close()

elif choice == "Bajas":
    st.header("Control de Bajas")
    conn = get_connection(); df = pd.read_sql("SELECT * FROM inventario WHERE estado != 'Baja'", conn); conn.close()
    
    if not df.empty:
        # Cambiamos "reg" por "form_baja" para que sea único
        with st.form("form_baja", clear_on_submit=True):
            seleccion = st.selectbox("Seleccione el equipo", df["equipo"] + " - " + df["serie"])
            # Nota: Al usar clear_on_submit, debemos asegurarnos de que la lógica de guardado procese los datos antes de limpiar
            c1, c2 = st.columns(2)
            with c1: 
                motivo = st.text_input("Motivo")
                obs = st.text_area("Descripción")
                autor = st.text_input("Autorizado por")
            with c2: 
                destino = st.text_input("Destino")
                folio = st.text_input("Folio")
                f_acta = st.date_input("Fecha acta")
                val = st.number_input("Valor residual", format="%.2f")
            
            if st.form_submit_button("Confirmar Baja"):
                # Obtenemos el equipo seleccionado justo antes de procesar
                equipo_sel = df[df["equipo"] + " - " + df["serie"] == seleccion].iloc[0]
                
                conn = get_connection(); cur = conn.cursor()
                cur.execute("UPDATE inventario SET estado='Baja' WHERE id=%s", (int(equipo_sel['id']),))
                cur.execute("INSERT INTO bajas (id_equipo, fecha_baja, motivo, descripcion_motivo, quien_autorizo, destino, folio_acta, fecha_acta, valor_residual) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)", 
                            (int(equipo_sel['id']), datetime.date.today(), motivo, obs, autor, destino, folio, f_acta, val))
                conn.commit(); cur.close(); conn.close()
                st.success("Baja procesada")
                st.rerun() # Esto recargará la página y el formulario se limpiará
    else: 
        st.info("No hay equipos para dar de baja.")
    
    # Mostrar tabla de bajas históricas
    conn = get_connection(); df_bajas = pd.read_sql("SELECT * FROM bajas", conn); conn.close()
    st.dataframe(df_bajas, use_container_width=True)
    export_module(df_bajas, "Reporte_Bajas")
