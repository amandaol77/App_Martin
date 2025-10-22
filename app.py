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
        worksheet.clear()
        worksheet.update(data)
        st.session_state['data_saved'] = datetime.now().strftime('%H:%M:%S')
    except Exception as e:
        st.error(f"❌ ERROR al guardar los datos en Google Sheets. ¿El permiso de la hoja es 'Editor' para cualquier usuario con el enlace?: {e}")
        st.stop()

def clean_input(text):
    """Limpia el texto, elimina tildes/ñ y convierte a mayúsculas para la búsqueda."""
    if not isinstance(text, str):
        return ""
    text = unidecode.unidecode(text)
    return text.upper()

def parse_price(value):
    """Convierte un string de precio (ej: '2.000,50') a float (2000.50)."""
    if not isinstance(value, (str, float, int)):
        return 0.0
    try:
        if isinstance(value, str):
            # Elimina el punto de mil (ej: 2.000,50 -> 2000,50)
            value = value.replace('.', '') 
            # Reemplaza la coma decimal por punto (ej: 2000,50 -> 2000.50)
            value = value.replace(',', '.')
        
        return float(value)
    except:
        return 0.0

# --------------------------------------------------------------------
# LÓGICA DE CARGA Y GUARDADO
# --------------------------------------------------------------------

def load_data():
    """Carga los datos desde Google Sheets y aplica la limpieza de tipos."""
    
    inventario_df = read_sheet_to_df(INVENTARIO_URL)
    ventas_df = read_sheet_to_df(VENTAS_URL)

    if not inventario_df.empty:
        inventario_df['CANTIDAD_ACTUAL'] = pd.to_numeric(inventario_df['CANTIDAD_ACTUAL'], errors='coerce').fillna(0).astype(int)
        inventario_df['COSTO_UNITARIO'] = inventario_df['COSTO_UNITARIO'].apply(parse_price)
        inventario_df['PRECIO_BASE'] = inventario_df['PRECIO_BASE'].apply(parse_price)
        inventario_df['PRECIO_PUBLICO'] = inventario_df['PRECIO_PUBLICO'].apply(parse_price)
        
    if not ventas_df.empty:
        for col in ['CANTIDAD_UNIDADES', 'PRECIO_VENTA_FINAL', 'COSTO_DEL_PRODUCTO_TOTAL', 'GASTOS_DIRECTOS_VIAJE', 'GANANCIA_NETA']:
            ventas_df[col] = ventas_df[col].apply(parse_price)
            if col == 'CANTIDAD_UNIDADES':
                 ventas_df[col] = ventas_df[col].fillna(0).astype(int)

    return inventario_df, ventas_df

def save_data(inventario_df, ventas_df):
    """Guarda ambos DataFrames en Google Sheets."""
    # Aseguramos que solo guardamos las columnas correctas en el orden correcto
    write_df_to_sheet(INVENTARIO_URL, inventario_df[[c for c in INVENTARIO_COLS if c in inventario_df.columns]]) 
    write_df_to_sheet(VENTAS_URL, ventas_df[[c for c in VENTAS_COLS if c in ventas_df.columns]])
    st.session_state['data_saved'] = datetime.now().strftime('%H:%M:%S')

def generar_sku(nombre):
    """Genera un SKU intuitivo (ej: Lámpara LED 12V -> LED12V-XXX)"""
    if not nombre or pd.isna(nombre):
        return str(uuid.uuid4())[:6].upper()
    
    nombre_limpio = clean_input(nombre)
    letras = ''.join(c for c in nombre_limpio if c.isalpha())[:3]
    numeros = ''.join(c for c in nombre_limpio if c.isdigit())
    
    sku_base = f"{letras}{numeros}"
    sufijo = str(uuid.uuid4())[:3].upper()
    return f"{sku_base}-{sufijo}"


def registrar_venta(inventario_df, ventas_df, nombre_producto, cantidad, tipo_cliente, precio_final, gastos_viaje, vendedor):
    """
    Registra una transacción de venta, calcula la ganancia y actualiza el stock.
    """
    
    producto_index = inventario_df[inventario_df['NOMBRE_PRODUCTO'] == nombre_producto].index 
    
    if producto_index.empty:
        st.error(f"❌ ERROR: Producto '{nombre_producto}' no encontrado.")
        return inventario_df, ventas_df, False
        
    idx = producto_index[0]
    producto = inventario_df.loc[idx].copy()
        
    cantidad_actual = producto['CANTIDAD_ACTUAL']
    
    if cantidad_actual < cantidad:
        st.warning(f"❌ Stock insuficiente. Solo quedan {cantidad_actual} unidades.")
        return inventario_df, ventas_df, False

    costo_unitario = pd.to_numeric(producto['COSTO_UNITARIO'])
    costo_total_venta = costo_unitario * cantidad
    
    codigo_sku = producto['CODIGO_SKU'] 
    
    ganancia_neta = precio_final - costo_total_venta - gastos_viaje

    registro_venta = pd.Series({
        'ID_
