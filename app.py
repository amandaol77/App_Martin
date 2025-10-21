# ====================================================================
# ARCHIVO PRINCIPAL DE LA APLICACIÓN WEB: app.py (VERSIÓN FINAL EN LA NUBE)
# ====================================================================

import streamlit as st
import pandas as pd
import gspread 
import uuid
from datetime import datetime
import os
import re
import unidecode 

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(layout="wide")

# ====================================================================
### ➡️ TUS ENLACES DE GOOGLE SHEETS AQUÍ (¡CRÍTICO!)
# INSERTADOS AUTOMÁTICAMENTE: NO TOCAR
# ====================================================================

INVENTARIO_URL = 'https://docs.google.com/spreadsheets/d/1G6V65-y81QryxPV6qKZBX4ClccTrVYbAAB7FBT9tuKk/edit?usp=drivesdk' 
VENTAS_URL = 'https://docs.google.com/spreadsheets/d/1XwYeFGGBF9M2CuY3-8nBUnyzkqsR1U_xEpHxrmHOqR4/edit?usp=drivesdk'

# Columnas Requeridas
INVENTARIO_COLS = [
    'ID_PRODUCTO', 'CODIGO_SKU', 'NOMBRE_PRODUCTO', 'CANTIDAD_ACTUAL', 
    'COSTO_UNITARIO', 'PRECIO_BASE', 'PRECIO_PUBLICO', 'UBICACION_FISICA'
]
VENTAS_COLS = [
    'ID_VENTA', 'FECHA_HORA', 'CODIGO_SKU_VENDIDO', 'NOMBRE_PRODUCTO_VENDIDO', 'CANTIDAD_UNIDADES', 
    'TIPO_CLIENTE', 'PRECIO_VENTA_FINAL', 'COSTO_DEL_PRODUCTO_TOTAL', 
    'GASTOS_DIRECTOS_VIAJE', 'GANANCIA_NETA', 'VENDEDOR_REGISTRA'
]

# --- FUNCIONES DE CONEXIÓN Y DATOS ---

@st.cache_resource
def get_gc_connection():
    try:
        # Esto usará la conexión pública/anónima de gspread
        gc = gspread.service_account_anonymous()
        return gc
    except Exception as e:
        st.error(f"❌ Error de Conexión a Google Sheets: {e}")
        st.stop()
        
def read_sheet_to_df(url, sheet_name=0):
    """Lee una hoja de cálculo por URL y la convierte a DataFrame."""
    gc = get_gc_connection()
    try:
        sh = gc.open_by_url(url)
        # Selecciona la primera hoja de trabajo (por defecto)
        worksheet = sh.sheet1
        data = worksheet.get_all_values()
        
        if not data:
            if url == INVENTARIO_URL:
                 return pd.DataFrame(columns=INVENTARIO_COLS)
            else:
                 return pd.DataFrame(columns=VENTAS_COLS)

        headers = data[0]
        df = pd.DataFrame(data[1:], columns=headers)
        return df
    except Exception as e:
        st.error(f"❌ ERROR al leer los datos de Google Sheets. Verifique que los enlaces sean correctos y que la hoja exista: {e}")
        st.stop()

def write_df_to_sheet(url, df):
    """Escribe un DataFrame completo a una hoja de cálculo, reemplazando todo."""
    gc = get_gc_connection()
    try:
        sh = gc.open_by_url(url)
        worksheet = sh.sheet1
        data = [df.columns.values.tolist()] + df.values.tolist()
