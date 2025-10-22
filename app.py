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
        'ID_VENTA': str(uuid.uuid4())[:8],
        'FECHA_HORA': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'CODIGO_SKU_VENDIDO': codigo_sku, 
        'NOMBRE_PRODUCTO_VENDIDO': nombre_producto,
        'CANTIDAD_UNIDADES': cantidad,
        'TIPO_CLIENTE': tipo_cliente,
        'PRECIO_VENTA_FINAL': precio_final,
        'COSTO_DEL_PRODUCTO_TOTAL': costo_total_venta,
        'GASTOS_DIRECTOS_VIAJE': gastos_viaje,
        'GANANCIA_NETA': ganancia_neta,
        'VENDEDOR_REGISTRA': vendedor
    }).to_frame().T
    
    # Añadimos la nueva venta al principio del DataFrame de Ventas (más fácil de ver)
    ventas_df = pd.concat([registro_venta, ventas_df], ignore_index=True)
    
    # Actualización de Stock
    inventario_df.loc[idx, 'CANTIDAD_ACTUAL'] -= cantidad
    
    st.success(f"✅ Venta de {cantidad} x '{nombre_producto}' registrada. Stock actualizado.")
    st.markdown(f"**💰 Ganancia Neta (oculta para Martín):** **${ganancia_neta:,.2f}**")
    
    return inventario_df, ventas_df, True

# --- INTERFAZ DE USUARIO (Streamlit) ---

def mostrar_registro_ventas(inventario_df, ventas_df):
    """Muestra la interfaz para registrar una nueva venta con búsqueda inteligente."""
    st.header("💰 Registro Rápido de Venta")
    st.markdown("---")
    
    producto_busqueda = st.text_input("1. Escribe 3 letras del producto o SKU:", key='prod_busqueda')
    
    producto_seleccionado = 'Seleccione un Producto'

    if len(producto_busqueda) >= 3:
        search_cleaned = clean_input(producto_busqueda)
        
        # Filtramos por Nombre de Producto o SKU, ignorando tildes y mayúsculas
        sugerencias = inventario_df[
            inventario_df['NOMBRE_PRODUCTO'].astype(str).apply(clean_input).str.contains(search_cleaned, na=False) |
            inventario_df['CODIGO_SKU'].astype(str).apply(clean_input).str.contains(search_cleaned, na=False)
        ]['NOMBRE_PRODUCTO'].tolist()
        
        if sugerencias:
            producto_seleccionado = st.selectbox("Selecciona el producto:", ['Seleccione un Producto'] + sugerencias)
        else:
            st.warning("No se encontraron productos con ese texto.")
    else:
        st.info("Escribe al menos 3 letras o el SKU para buscar.")

    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    producto_encontrado = None
    precio_sugerido_display = 0.0
    stock = 0
    sku = ""

    if producto_seleccionado != 'Seleccione un Producto':
        producto_encontrado = inventario_df[inventario_df['NOMBRE_PRODUCTO'] == producto_seleccionado].iloc[0]
        stock = producto_encontrado['CANTIDAD_ACTUAL']
        sku = producto_encontrado['CODIGO_SKU']


    with col1:
        cantidad = st.number_input("2. Cantidad (unidades)", min_value=1, value=1, step=1, key='cant_input')
        
        tipo_cliente = st.selectbox("3. Tipo de Cliente", ['Minorista', 'Mayorista'])
        
        if producto_encontrado is not None:
            if tipo_cliente == 'Mayorista':
                precio_sugerido_display = producto_encontrado['PRECIO_BASE']
            else: 
                precio_sugerido_display = producto_encontrado['PRECIO_PUBLICO']
                
        # Usamos el input de texto para el precio, permitiendo el formato "punto de mil"
        precio_final_str = st.text_input("4. Precio Final $", value=f"{precio_sugerido_display:,.0f}" if precio_sugerido_display else "0")
        precio_final = parse_price(precio_final_str)

    with col2:
        gastos_viaje_str = st.text_input("5. Gastos de la Venta $", value="0")
        gastos_viaje = parse_price(gastos_viaje_str)
        
        vendedor = st.selectbox("6. Registrado por", ['Martin', 'Amanda', 'Otro']) 
        
    # Mostrar info del producto
    if producto_seleccionado != 'Seleccione un Producto':
        st.info(f"SKU: **{sku}** | Stock: **{stock}** | Sugerido ({tipo_cliente}): **${precio_sugerido_display:,.2f}**")
    
    st.markdown("---")
    
    # Botón de Registro
    if st.button("REGISTRAR VENTA y ACTUALIZAR INVENTARIO", type="primary"):
        if producto_seleccionado not in ('Seleccione un Producto', '') and precio_final > 0:
            # Recargamos para evitar conflictos si alguien más cambió la hoja
            st.session_state['inventario_df'], st.session_state['ventas_df'] = load_data() 
            
            st.session_state['inventario_df'], st.session_state['ventas_df'], exito = registrar_venta(
                st.session_state['inventario_df'], st.session_state['ventas_df'], 
                producto_seleccionado, cantidad, tipo_cliente, precio_final, gastos_viaje, vendedor
            )
            if exito:
                save_data(st.session_state['inventario_df'], st.session_state['ventas_df'])
                st.rerun() # Recarga para mostrar el stock actualizado
        elif producto_seleccionado in ('Seleccione un Producto', ''):
            st.error("Por favor, seleccione un producto o complete la búsqueda.")
        elif precio_final <= 0:
             st.error("El Precio Final debe ser mayor que cero.")

def eliminar_producto(inventario_df, nombre_producto):
    """Elimina un producto del inventario."""
    df_actualizado = inventario_df[inventario_df['NOMBRE_PRODUCTO'] != nombre_producto].reset_index(drop=True)
    return df_actualizado

def mostrar_inventario(df):
    """Muestra la interfaz de gestión de inventario."""
    st.header("📦 Gestión de Inventario (Completa)")
    st.markdown("---")
    
    st.subheader("⚠️ Eliminar Productos del Catálogo")
    eliminar_opciones = ['Seleccione un Producto para eliminar'] + df['NOMBRE_PRODUCTO'].tolist()
    producto_a_eliminar = st.selectbox("Producto a Eliminar (¡ACCIÓN PERMANENTE!)", eliminar_opciones)
    
    if st.button("ELIMINAR PRODUCTO", type="secondary"):
        if producto_a_eliminar != 'Seleccione un Producto para eliminar':
            st.session_state['inventario_df'] = eliminar_producto(st.session_state['inventario_df'], producto_a_eliminar)
            save_data(st.session_state['inventario_df'], st.session_state['ventas_df'])
            st.success(f"🗑️ Producto '{producto_a_eliminar}' eliminado del inventario.")
            st.rerun()
        else:
            st.warning("Seleccione un producto para eliminar.")
    
    st.markdown("---")
    
    st.subheader("🔎 Inventario Actual")
    search_term = st.text_input("Buscar producto por nombre o SKU:", key='inv_search')
    if search_term:
        search_term_lower = clean_input(search_term)
        df_filtered = df[
            df['NOMBRE_PRODUCTO'].astype(str).apply(clean_input).str.contains(search_term_lower, na=False) |
            df['CODIGO_SKU'].astype(str).apply(clean_input).str.contains(search_term_lower, na=False)
        ]
    else:
        df_filtered = df

    # Formatear las columnas de precios para la visualización
    df_display = df_filtered.copy()
    for col in ['COSTO_UNITARIO', 'PRECIO_BASE', 'PRECIO_PUBLICO']:
        df_display[col] = df_display[col].apply(lambda x: f"${x:,.2f}")
    
    st.dataframe(df_display, use_container_width=True, height=300)
    st.markdown(f"**Total de Productos en Catálogo: {len(df)}**")
    
def mostrar_carga_masiva():
    """Interfaz para cargar un archivo CSV de inventario."""
    st.header("⬆️ Carga Masiva de Inventario")
    st.markdown("---")
    
    st.markdown("💡 **Instrucción:** Asegúrese de que su archivo CSV contenga **exactamente** las 7 columnas (sin incluir ID_PRODUCTO). Si deja **`CODIGO_SKU`** vacío, se generará automáticamente.")
    st.markdown("- `CODIGO_SKU`, `NOMBRE_PRODUCTO`, `CANTIDAD_ACTUAL`, `COSTO_UNITARIO`, `PRECIO_BASE`, `PRECIO_PUBLICO`, `UBICACION_FISICA`")

    uploaded_file = st.file_uploader("Suba el archivo 'inventario_completo.csv'", type=["csv"])
    
    if uploaded_file is not None:
        try:
            # Intentar leer con separador coma. Si falla, intentar con punto y coma (solución a problemas de formato regional)
            try:
                df_a_cargar = pd.read_csv(uploaded_file, sep=',', encoding='utf-8')
            except:
                uploaded_file.seek(0)
                df_a_cargar = pd.read_csv(uploaded_file, sep=';', encoding='latin-1')
                
            required_cols_upload = [c for c in INVENTARIO_COLS if c not in ['ID_PRODUCTO']]
            
            if not all(col in df_a_cargar.columns for col in required_cols_upload):
                st.error(f"❌ ERROR: El archivo CSV debe contener TODAS las 7 columnas requeridas: {', '.join(required_cols_upload)}. Revise mayúsculas y guiones.")
                return
            
            # Limpieza y generación de IDs/SKUs
            df_a_cargar['ID_PRODUCTO'] = [str(uuid.uuid4())[:8] for _ in range(len(df_a_cargar))]
            df_a_cargar['CODIGO_SKU'] = df_a_cargar.apply(
                lambda row: generar_sku(row['NOMBRE_PRODUCTO']) if pd.isna(row['CODIGO_SKU']) or str(row['CODIGO_SKU']).strip() == '' else row['CODIGO_SKU'], axis=1
            )
            
            # Reordenamos las columnas al orden final del inventario
            df_a_cargar = df_a_cargar[INVENTARIO_COLS]
            
            st.session_state['inventario_df'], st.session_state['ventas_df'] = load_data()
            
            # Consolidar: Las nuevas entradas reemplazan a las antiguas si tienen el mismo NOMBRE_PRODUCTO
            inventario_df = pd.concat([st.session_state['inventario_df'], df_a_cargar], ignore_index=True)
            inventario_df.drop_duplicates(subset=['NOMBRE_PRODUCTO'], keep='last', inplace=True)
            inventario_df.reset_index(drop=True, inplace=True)
            
            st.session_state['inventario_df'] = inventario_df
            save_data(inventario_df, st.session_state['ventas_df'])
            
            st.success(f"🎉 ¡ÉXITO! {len(df_a_cargar)} productos cargados/actualizados. Revise los SKUs generados en el Inventario.")
            
        except Exception as e:
            st.error(f"❌ Ocurrió un error al procesar el archivo. El formato podría ser incorrecto o la codificación: {e}")

# --- ESTRUCTURA PRINCIPAL DE LA APLICACIÓN ---
def main():
    
    if 'inventario_df' not in st.session_state:
        st.session_state['inventario_df'], st.session_state['ventas_df'] = load_data()
    
    st.title("⚙️ App de Negocio: Inventario y Ganancia (CLOUD READY ☁️)")
    
    page = st.sidebar.selectbox("MENÚ", ["Registro Rápido", "Carga Masiva", "Gestión de Inventario", "Reportes de Venta"])

    st.sidebar.markdown("---")
    
    if page == "Registro Rápido":
        mostrar_registro_ventas(st.session_state['inventario_df'], st.session_state['ventas_df'])
    
    elif page == "Carga Masiva":
        mostrar_carga_masiva()
    
    elif page == "Gestión de Inventario":
        mostrar_inventario(st.session_state['inventario_df'])
    
    elif page == "Reportes de Venta":
        st.header("📈 Reportes de Venta (Ganancia Neta)")
        st.markdown("---")
        st.markdown("**Ganancia Neta es el resultado de: Venta - Costo - Gastos**")
        
        # Recargar datos antes de reportes para tener la información más actual
        st.session_state['inventario_df'], st.session_state['ventas_df'] = load_data()
        
        ventas_df_clean = st.session_state['ventas_df'].copy()
        
        # Formatear para la visualización
        ventas_df_clean['GANANCIA_NETA_DISPLAY'] = ventas_df_clean['GANANCIA_NETA'].apply(lambda x: f"${x:,.2f}")
        ventas_df_clean['PRECIO_VENTA_FINAL_DISPLAY'] = ventas_df_clean['PRECIO_VENTA_FINAL'].apply(lambda x: f"${x:,.2f}")
        
        st.dataframe(ventas_df_clean[['FECHA_HORA', 'CODIGO_SKU_VENDIDO', 'NOMBRE_PRODUCTO_VENDIDO', 'TIPO_CLIENTE', 'PRECIO_VENTA_FINAL_DISPLAY', 'GASTOS_DIRECTOS_VIAJE', 'GANANCIA_NETA_DISPLAY']].head(20).rename(columns={'PRECIO_VENTA_FINAL_DISPLAY': 'PRECIO VENTA', 'GANANCIA_NETA_DISPLAY': 'GANANCIA NETA'}), use_container_width=True)
        
        total_ganancia = ventas_df_clean['GANANCIA_NETA'].sum()
        st.metric("GANANCIA NETA TOTAL (Acumulada)", f"${total_ganancia:,.2f}")
        
    st.sidebar.markdown("---")
    st.sidebar.caption(f"Último Guardado: {st.session_state.get('data_saved', 'Nunca')}")


if __name__ == "__main__":
    main()
# ====================================================================
