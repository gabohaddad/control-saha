#IMPORTAR LOS DICCIONARIOS DE LIBRERIAS PARA QUE SE CARGUEN AL PROGRAMA

import streamlit as st
import pandas as pd
from datetime import datetime, date
import time  # Importar el módulo time
import numpy as np
import unicodedata # para estandarizar formato de titulo de columnas


#from google_sheets import obtener_registros
from google_sheets import cargar_registros_a_google_sheets
import gspread
from gspread_pandas import Spread

from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
import json
import os
import requests
#______________________________________________________________________________

# ------------------- Inicialización segura de variables en session_state -------------------
if "registros" not in st.session_state:
    st.session_state.registros = []

if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame()

#----------------------------------------------------------------------------
# Funcion para estandarizar columnas de los df colocando los encabzados de columnas
# en mayusculas

def estandarizar_columnas(df):
    df.columns = [
        unicodedata.normalize('NFKD', col).encode('ascii', 'ignore').decode('utf-8')
        for col in df.columns
    ]
    df.columns = df.columns.str.strip().str.upper()
    return df
#-------------------------------------------------------------------------------------

# Función para cargar las subcategorías
def cargar_subcategorias(sheet):
    data = sheet.worksheet("Subcategorias").get_all_records()
    df_subs = pd.DataFrame(data)
    df_subs = estandarizar_columnas(df_subs)  # Estandarizar columnas
    return df_subs

# Función para cargar los responsables
def cargar_responsables(sheet):
    data = sheet.worksheet("Responsables").get_all_records()
    responsables_df = pd.DataFrame(data)
    responsables_df = estandarizar_columnas(responsables_df)  # Estandarizar columnas
    return responsables_df

# Función para cargar las cuentas bancarias
def cargar_cuentas(sheet):
    cuentas_data = sheet.worksheet("Saldos").col_values(1)[1:]  # Omite la primera fila (encabezado)
    cuentas = [cuenta for cuenta in cuentas_data if cuenta]  # Filtra las cuentas no vacías
    return cuentas
#--------------------------------------------------------------------------------------------------
# Función para cargar todos los datos en session_state (solo si no están ya cargados)
def cargar_datos_auxiliares(sheet):
    # Cargar datos solo si no están almacenados en session_state
    if "df_subs" not in st.session_state:
        st.session_state.df_subs = cargar_subcategorias(sheet)
    
    if "responsables_df" not in st.session_state:
        st.session_state.responsables_df = cargar_responsables(sheet)
    
    if "cuentas" not in st.session_state:
        st.session_state.cuentas = cargar_cuentas(sheet)
#----------------------------------------------------------------------------------------------

def autenticacion_google_sheets():
    
    # Intenta autenticarse usando st.secrets (Streamlit Cloud)
    if "GOOGLE_SERVICE_ACCOUNT" in st.secrets:
        try:
            st.write("🟢 Entorno Streamlit Cloud detectado.")
            service_account_info = json.loads(st.secrets["GOOGLE_SERVICE_ACCOUNT"])
            credentials = Credentials.from_service_account_info(
                service_account_info,
                scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
            )
            cliente = gspread.authorize(credentials)
            return cliente
        except Exception as e:
            st.error("❌ Error al autenticar con st.secrets en Streamlit Cloud.")
            st.exception(e)
            raise e

    # Si no está en st.secrets, intenta entorno local
    else:
        try:
            st.write("🔵 Entorno local detectado.")
            load_dotenv()
            ruta_credenciales = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
            if not ruta_credenciales or not os.path.exists(ruta_credenciales):
                raise ValueError("No se encontró la ruta a las credenciales en la variable de entorno.")
            credentials = Credentials.from_service_account_file(
                ruta_credenciales,
                scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
            )
            cliente = gspread.authorize(credentials)
            return cliente
        except Exception as e:
            st.error("❌ Error al autenticar en entorno local.")
            st.exception(e)
            raise e
#-----------------------------------------------------------------------------------       
# 2. Conexión al workbook
cliente = autenticacion_google_sheets()
workbook = cliente.open("BD DE REGISTROS FINANCIEROS")
sheet_bancos = workbook.worksheet("Bancos")
sheet_saldos = workbook.worksheet("Saldos")


#------------------------------------------------------------------------------------------------
from gspread_pandas import Spread
# el dicccionario gspread-pandas me ayuda para gestionar mejor las cuentas en google sheets
def obtener_spread():
    try:
    
        # Duplicamos la lógica pero devolvemos cliente y creds
        if "GOOGLE_SERVICE_ACCOUNT" in st.secrets:
            service_account_info = json.loads(st.secrets["GOOGLE_SERVICE_ACCOUNT"])
            credentials = Credentials.from_service_account_info(
                service_account_info,
                scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
            )
        else:
            load_dotenv()
            ruta_credenciales = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
            credentials = Credentials.from_service_account_file(
                ruta_credenciales,
                scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
            )

        #cliente = gspread.authorize(credentials)
        #spread = Spread("BD DE REGISTROS FINANCIEROS", client=cliente, creds=credentials)
        spread = Spread("BD DE REGISTROS FINANCIEROS", creds=credentials)

        return spread

    except Exception as e:
        raise RuntimeError(f"No se pudo autenticar con Google Sheets: {e}")
#-----------------------------------------------------------------------------------------
# --- Función para cargar los datos de Google Sheets en un dataframe---
def cargar_datos_principales():
    st.subheader("🔄 Cargando datos desde Google Sheets...")

    # Autenticación con Google Sheets
    cliente = autenticacion_google_sheets()

    # Obtener SHEET_ID desde secrets o .env
    try:
        SHEET_ID = st.secrets["SHEET_ID"]
        st.write("🟢 SHEET_ID obtenido desde secrets.toml")
    except KeyError:
        SHEET_ID = os.getenv("SHEET_ID")
        st.write("🔵 SHEET_ID obtenido desde .env")

    if not SHEET_ID:
        st.error("❌ No se encontró SHEET_ID en secrets.toml ni en .env")
        return None, None

    # Acceder a la hoja
    try:
        archivo = cliente.open_by_key(SHEET_ID)
        worksheet = archivo.sheet1
    except Exception as e:
        st.error(f"❌ No se pudo abrir el archivo con ID: {SHEET_ID}")
        st.exception(e)
        return None, None

    # Leer y cargar los datos
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)

    # Guardar en session_state
    st.session_state.worksheet = worksheet
    st.session_state.df = df

    # Validar columna ID
    if "ID" not in df.columns:
        st.warning("⚠️ La columna 'ID' no está presente en los datos.")

    st.success("✅ Datos cargados correctamente.")
    return df, archivo

#--------------------------------------------------------------------------------------
 # BLOQUE PRINCIPAL DE CARGA

# Verificar si los datos principales ya están en session_state
if "df_data" not in st.session_state or "spreadsheet" not in st.session_state:
    with st.spinner("Cargando datos principales..."):
        df, archivo = cargar_datos_principales()
        st.session_state.df_data = df
        st.session_state.spreadsheet = archivo

# Cargar datos auxiliares (una sola vez)
cargar_datos_auxiliares(st.session_state.spreadsheet)

#----------------------------------------------------------------------------------------
# --- Función para ver registros ---  creacion del data frame para google sheet
# --- Función para ver registros y actualizar df desde Google Sheets ---
def ver_registros():
    # ✅ Limpia estado previo de edición
    st.session_state.pop("edicion_activa", None)

    # ✅ Usar datos ya cargados
    df_actualizado = st.session_state.df.copy()

        # Cambiar los nombres de las columnas a mayúsculas
    df_actualizado.columns = df_actualizado.columns.str.upper()

    
# ✅ Conversión segura de fechas
    if "FECHA" in df_actualizado.columns:
     df_actualizado["FECHA"] = pd.to_datetime(df_actualizado["FECHA"], format="%d/%m/%Y", errors="coerce")
         # ✅ Formato de fecha para visualización
    df_actualizado["FECHA"] = df_actualizado["FECHA"].dt.strftime("%d/%m/%Y")


    st.session_state.df = df_actualizado

    # Limpieza y conversión de columna "Monto"
    if "Monto" in st.session_state.df.columns:
        st.session_state.df["Monto"] = (
            st.session_state.df["Monto"]
            .astype(str)
            .str.replace(",", ".", regex=False)
            .astype(float)
        )

   # ✅ Mostrar la tabla actualizada (solo visual)
    st.dataframe(df_actualizado, hide_index=True)

    # ✅ Actualizar el DataFrame en session_state
    st.session_state.df = df_actualizado

    # ✅ Guardar versión en dict para otros módulos
    st.session_state.registros = df_actualizado.to_dict("records")


#----------------------------------------------------------------------------------------
# esta funcion es para estandarizar los formatos de tipo panda a tipo basico de python para
# evitar conflictos
def convertir_a_tipos_nativos(lista_valores):
    """
    Convierte elementos numpy (int64, float64) a tipos nativos de Python (int, float).
    """
    return [
        int(x) if isinstance(x, (np.int64, np.int32)) else
        float(x) if isinstance(x, (np.float64, np.float32)) else
        str(x) if not isinstance(x, (int, float, str)) else x
        for x in lista_valores
    ]

#------------------------------------------------------------------------------------------
# ESTE BLOQUE ES LA INTERACCION ENTRE LA LISTA DE GOOGLE SHEET QUE VIENE A LA PANTALLA PARA EDITAR Y LA HOJA DE CALCULO 
# Suponiendo que 'edited_df' es el DataFrame con los datos editados
# Y 'worksheet' es el objeto de la hoja de Google Sheets ACA SE VAN REGISTRA LOS DATOS EDITADOS DE LA PAGINA
# VER REGISTROS

def actualizar_datos_modificados(worksheet, edit_id, fecha, categoria, subcategoria, 
                                 responsable, descripcion,monto,tipo_pago,tasa_cambio,cuenta_bancaria):
    
    # Convertir la fecha a formato datetime si es necesario
    if isinstance(fecha, str):  # Si la fecha viene como string
        fecha = datetime.strptime(fecha, "%d/%m/%Y")
    
    edit_id = str(edit_id)

    # Buscar el índice del registro en session_state.df (sin recargar Google Sheets)
    df = st.session_state.df.copy()
    idx = df[df["ID"].astype(str) == edit_id].index


    if len(idx) == 0:
        st.error(f"No se encontró el registro con ID {edit_id}.")
        return

    # Obtener fila exacta en Google Sheets (asumiendo que ID está en orden)
    fila_editada = idx[0] + 2  # +2 por encabezado + base cero

    # Valores nuevos
    nuevos_valores = [
        fecha.strftime("%d/%m/%Y"),
        categoria,
        subcategoria,
        responsable,
        descripcion,
        str(monto),
        tipo_pago,
        str(tasa_cambio),
        cuenta_bancaria,
        
    ]

    # Crear rango de celdas para update (columnas B a I si ID está en A)
    rango = f'B{fila_editada}:J{fila_editada}'

    # Enviar los nuevos datos con batch_update
    worksheet.batch_update([{
        'range': rango,
        'values': [nuevos_valores]
    }])

    # 🔁 Actualizar el DataFrame en memoria directamente
    df.at[idx[0], "FECHA"] = fecha.strftime("%d/%m/%Y")
    df.at[idx[0], "CATEGORIA"] = categoria
    df.at[idx[0], "SUBCATEGORIA"] = subcategoria
    df.at[idx[0], "RESPONSABLE"] = responsable
    df.at[idx[0], "DESCRIPCION"] = descripcion
    df.at[idx[0], "MONTO"] = monto
    df.at[idx[0], "TIPO DE PAGO"] = tipo_pago
    df.at[idx[0], "TASA DE CAMBIO"] = tasa_cambio
    df.at[idx[0], "CUENTA"] = cuenta_bancaria

    st.session_state.df = df

    st.success(f"¡El registro con ID {edit_id} se ha actualizado correctamente!")
    st.rerun()

    
#=========================================================================================================

# ------------------- Función para obtener el último ID en Google Sheets -------------------
def obtener_ultimo_id(sheet):
    """
    Obtiene el último ID registrado en la primera columna de Google Sheets.
    Si la hoja está vacía, comienza desde 1.
    """
    valores = sheet.get_all_values()
    if len(valores) <= 1:
        return 1  # Solo encabezado
    try:
        ultimo_id = int(valores[-1][0])  # ID está en la primera columna
        return ultimo_id + 1
    except ValueError:
        return 1

# ------------------- Función para cargar registros en Google Sheets con ID -------------------
# ESTA SECCION ME PERMITE DARLE CONTINUIDAD EN GOOGLE SHEET POR NUMERO DE REGISTRO
def cargar_registros_a_google_sheets(registros,nombre_archivo="BD REGISTROS FINANCIEROS"):
    cliente = autenticacion_google_sheets()
    
    try:
        archivo_google_sheets = cliente.open(nombre_archivo)  # Abrir el archivo de Google Sheets
        hoja = archivo_google_sheets.sheet1  # Usar la primera hoja
    except gspread.SpreadsheetNotFound:
        st.error(f"El archivo de Google Sheets '{nombre_archivo}' no fue encontrado.")
        return
    
    # Obtener el siguiente ID disponible en Google Sheets
    siguiente_id = obtener_ultimo_id(hoja)
    
    # Agregar los registros con IDs consecutivos
    registros_con_id = []
    for registro in registros:
        fila = [siguiente_id] + list(registro.values())
        registros_con_id.append(fila)
        siguiente_id += 1

       #Cargar todos los registros en una sola llamada
    hoja.append_rows(registros_con_id, value_input_option="USER_ENTERED")  
    
#---------------------------------------------------------------------------------------------
# Función para agregar un nuevo registro

# DEFINICION DE VARIABLES PARA NUEVO REGISTRO
def agregar_registro(fecha, categoria, descripcion, monto, tipo_pago, tasa_cambio,base_de_cambio =None, 
                     subcategoria=None, responsable=None,cuenta_bancaria=None):

    worksheet = st.session_state.worksheet
    
    # Convertir la fecha a formato "día/mes/año"
    fecha_formateada = fecha.strftime("%d/%m/%Y")  # Fecha convertida a formato adecuado
        
    # Validación de datos
    if not fecha_formateada or not descripcion or not monto or not tipo_pago or  not cuenta_bancaria:
        st.warning("Por favor, complete todos los campos obligatorios.")
        return

    if monto <= 0:
        st.warning("El monto debe ser un número positivo.")
        return
    
    # Si la categoría es "Gasto", hacer el monto negativo
    if categoria == "Gasto":
        monto = -abs(monto)  # Asegura que el monto siempre sea negativo para gastos
    
    
    # Si el tipo de pago es BSF, se asegura que la tasa de cambio sea válida
    if tipo_pago == "BSF" and tasa_cambio is not None:
        if not tasa_cambio or tasa_cambio <= 0:
            st.warning("La tasa de cambio debe ser un número positivo.")
            return
                
    else:
        tasa_cambio = 1  # Si no es BSF, siempre será 1# No es necesario pedir la tasa de cambio si no es BSF

    # ✅ Asegura que la fecha sea string antes de pasarla al registro
    if isinstance(fecha, (datetime, date)):
        fecha = fecha.strftime("%d/%m/%Y")

    # Si la validación pasa, agregar el registro a la tabla resumen en streamlit
    # estos son los datos que pasan a la tabla de df
    registro = {
        "Fecha": fecha_formateada,  # ✅ Convertir fecha a cadena se necesita para google sheet
        "Categoría": categoria,
        "Subcategoría": subcategoria if subcategoria else "No especificado",  # Valor predeterminado si es None
        "Responsable": responsable if responsable else "No especificado",  # Valor predeterminado si es None
        "Descripción": descripcion,
        "Monto": monto,
        "Tipo de pago": tipo_pago,
        "Tasa de cambio": float(tasa_cambio) if tasa_cambio else 1, # Solo incluir tasa de cambio si es BSF
        "Cuenta":cuenta_bancaria,
        "Base de cambio":base_de_cambio,
    }

# Agregar el registro a la lista
    st.session_state.registros.append(registro)

# Intentar guardar en Google Sheets
    try:
        cargar_registros_a_google_sheets([registro], "BD DE REGISTROS FINANCIEROS")
        st.success("¡Registro agregado exitosamente en Google sheet!")


        # Reiniciar la variable cuando el botón es presionado

         #Marca una bandera para limpiar en el próximo ciclo
        st.session_state.limpiar = True

        # Actualizar DataFrame en session_state
        datos_actualizados = st.session_state.worksheet.get_all_records()
        st.session_state.df = pd.DataFrame(datos_actualizados)


        st.rerun()

    except Exception as e:
        st.error(f"Hubo un problema al guardar el registro en Google Sheets: {e}")

#===================================================================================================
def limpiar_campos():
    keys_a_borrar = [
        "categoria", "subcategoria_tipo", "subcategoria_fijo", "subcategoria_variable",
        "responsable", "subcategoria_ingreso", "responsable_ingreso", "descripcion",
        "monto", "tipo_pago", "tasa_cambio","base_de_cambio"
    ]
    for key in keys_a_borrar:
        if key == "descripcion":
            st.session_state[key] = ""
        elif key in st.session_state:
            del st.session_state[key]
    st.session_state.limpiar = False
    st.rerun()

#---------------------------------------------------------------------------------------

# Interfaz de usuario SECCION DONDE SE CARGAN LOS DATOS (WIDGETS) (formulario)
# creacion de diccionarios dinamicos, subcategorias, responsables 

def formulario_de_registros(sheet):

    # Recuperar datos ya cargados en session_state
    df_subs = st.session_state.df_subs
    responsables_df = st.session_state.responsables_df
    cuentas = st.session_state.cuentas 
    #-------------------------------------
     
    if st.session_state.get("limpiar", False):
        limpiar_campos()
        return
     
    fecha = st.date_input("Fecha de la transaccion", value=date.today(), format="DD/MM/YYYY",key="fecha") 
    
    categoria = st.selectbox("Selecciona la categoría", ["", "Ingreso", "Gasto"], key="categoria")
    subcategoria = None
    tipo_gasto = None
    responsable = None

    
    lista_responsables = responsables_df["RESPONSABLE"].dropna().tolist()
    

    if categoria == "Ingreso":
        subcategorias_disponibles = df_subs[
            (df_subs["CATEGORIA"] == "Ingreso")
        ]["SUBCATEGORIA"].unique().tolist()
        
        subcategoria = st.selectbox("Selecciona la subcategoría de ingreso", ["" ] + subcategorias_disponibles, key="sub_ingreso")
        responsable = st.selectbox("¿A quién corresponde el ingreso?", [""] + lista_responsables, key="responsable_ingreso")
        
    elif categoria == "Gasto":
        tipo_gasto = st.selectbox("Selecciona el tipo de gasto", ["", "Gasto Fijo", "Gasto Variable"], key="tipo_gasto")

        if tipo_gasto:
            subcategorias_disponibles = df_subs[
                (df_subs["CATEGORIA"] == "Gasto") &
                (df_subs["TIPO DE GASTO"] == tipo_gasto)
            ]["SUBCATEGORIA"].unique().tolist()
            
            subcategoria = st.selectbox("Selecciona la subcategoría", ["" ] + subcategorias_disponibles, key="sub_gasto")
            responsable = st.selectbox("¿A quién corresponde el gasto?", [""] + lista_responsables, key="responsable_gasto")

    descripcion = st.text_input("Descripción", key="descripcion")


    if "monto" not in st.session_state:
        st.session_state.monto = 0.0
    monto = st.number_input("Ingrese el monto", step=0.01, format="%.2f", key="monto")

    tipo_pago = st.selectbox("Selecciona el tipo de pago", ["Dolares","BSF","Euros"], key="tipo_pago")

    # ✅ Define antes para evitar error si el tipo de pago no es BSF
    base_de_cambio = None

    if tipo_pago == "BSF":
        moneda = st.selectbox(
        "¿La tasa de cambio corresponde a?",
        ["USD", "EUR"],
        help="Indica si la tasa que vas a ingresar corresponde al Dólar o al Euro."
    )
        base_de_cambio = moneda

        tasa_cambio = st.number_input(f"Ingrese la tasa de cambio BsF/{moneda}", min_value=0.0, format="%.2f")
        if tasa_cambio == 0.0:
            st.warning("⚠️ Para pagos en BSF debes ingresar la tasa de cambio.")
    else:
        tasa_cambio = 1.0
        st.session_state.tasa_cambio = tasa_cambio

    cuenta_bancaria = st.selectbox("Cuenta bancaria", [""] + cuentas, key="cuenta_bancaria")
   
#--------------------------------------------------------------------------------------
# Botón para agregar el registro

    if st.button("Agregar registro"):

        # Validación de tasa de cambio para BSF
        if tipo_pago == "BSF" and (tasa_cambio in [0.0, 1.0] or tasa_cambio is None):
            st.warning("❌ No puedes guardar el registro sin ingresar una tasa de cambio.")
        # Validación de campos obligatorios
        elif not descripcion or monto is None or monto <= 0 or not cuenta_bancaria:
            st.warning("❌ Por favor, completa todos los campos antes de agregar el registro.")
        else:
            # Todo está correcto, agregar registro
            agregar_registro(
                fecha, categoria, descripcion, monto, tipo_pago, 
                tasa_cambio, base_de_cambio, subcategoria, responsable, cuenta_bancaria
            )
            st.success("Registro agregado correctamente")
            time.sleep(0.5)
            st.session_state.limpiar = True

#----------------------------------------------------------------------------------------------------
# este codigo usa una api externa para el encontrar la tasa de cambio eur/$ 
            

# Caché simple para no repetir llamadas a la API
tasa_cache = {}

def obtener_tasa_eur_usd(fecha):
    """
    Consulta la tasa EUR→USD desde Frankfurter.app (datos del BCE)
    """
    # Si ya tenemos la tasa en caché, la devolvemos sin pedirla otra vez
    if fecha in tasa_cache:
        return tasa_cache[fecha]

    url = f"https://api.frankfurter.app/{fecha}?from=EUR&to=USD"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            st.warning(f"⚠️ Error HTTP {r.status_code} al consultar la tasa para {fecha}")
            tasa_cache[fecha] = 1.0
            return 1.0

        data = r.json()
        tasa = data.get("rates", {}).get("USD", 1.0)

        if not tasa:
            st.warning(f"No se encontró tasa para {fecha}. Se usará 1.0 por defecto.")
            tasa = 1.0

        # Guardamos en caché
        tasa_cache[fecha] = tasa
        return tasa

    except Exception as e:
        st.warning(f"⚠️ Error al consultar la API: {e}")
        return 1.0

#------------------------------------------------------------------------------------------------------
# ESTE MODULO SE USARA EN AMBAS SECCION , POR SUCATEGORIA Y POR RESPONSABLE

def convertir_bsf_a_usd(row):
                if row["TIPO DE PAGO"] == "BSF":
                    base = row.get("BASE DE CAMBIO", None)
                    if base == "USD":
                        return row["MONTO"] / row["TASA DE CAMBIO"]
                    elif base == "EUR":
                        # Convertir fecha si viene como texto
                        fecha = row["FECHA"]
                        if isinstance(fecha, str):
                            fecha = pd.to_datetime(fecha, format="%d/%m/%Y", errors="coerce")

                        if pd.isna(fecha):
                            return None  # o podrías retornar el monto original

                        fecha_api = row["FECHA"].strftime("%Y-%m-%d")
                        tasa_eur_usd = obtener_tasa_eur_usd(fecha_api)
                        
                        # Mostrar en Streamlit
                        st.info(f"💱 Tasa EUR→USD para {fecha_api}: {tasa_eur_usd}")

                        return (row["MONTO"] / row["TASA DE CAMBIO"]) * tasa_eur_usd
                return row["MONTO"]  # ya está en USD o no es BSF


#-------------------------------------------------------------------------------------
# SECCION DE REPORTES

def reporte_ingresos_por_subcategoria():

    # Cargamos los datos desde Google Sheets
    df = st.session_state.df
    
    if df.empty:
        st.warning("No hay datos disponibles para generar reportes.")
        return

    # Convertir la columna de fecha a tipo datetime``
    df["FECHA"] = pd.to_datetime(df["FECHA"], format="%d/%m/%Y", errors="coerce")


    # Filtrar solo los ingresos
    df_ingresos = df[df["CATEGORIA"] == "Ingreso"]

    #st.subheader("💰 Reporte de Ingresos por Tipo y Subcategoría")
# Verificar si hay datos en df_ingresos antes de calcular min/max fecha
    if df_ingresos.empty:
        st.warning("No hay ingresos registrados en la base de datos.")
        return

    # 🔹 OBTENER EL RANGO DE FECHAS
    min_fecha, max_fecha = df_ingresos["FECHA"].min(), df_ingresos["FECHA"].max()

    
# 🔹 3️⃣ SELECCIÓN DEL RANGO DE FECHAS EN STREAMLIT
    rango_fechas = st.date_input(
    "Selecciona el rango de fechas",
    [min_fecha, max_fecha],  # Valores predeterminados
    min_value=min_fecha,
    max_value=max_fecha )


# 🔹 4️⃣ VALIDAR LA SELECCIÓN Y FILTRAR EL DATAFRAME
    if isinstance(rango_fechas, tuple) and len(rango_fechas) == 2:
        fecha_inicio, fecha_fin = rango_fechas

        # Convertimos las fechas seleccionadas a datetime
        fecha_inicio = pd.to_datetime(fecha_inicio, format="%d/%m/%Y")
        fecha_fin = pd.to_datetime(fecha_fin, format="%d/%m/%Y")


        # Filtrar ingresos dentro del rango de fechas
        df_filtrado_ingresos = df_ingresos[
            (df_ingresos["FECHA"] >= fecha_inicio) & 
            (df_ingresos["FECHA"] <= fecha_fin)
        ]

        if df_filtrado_ingresos.empty:
            st.warning("⚠️ No se encontraron ingresos en este rango de fechas.")
        else:
            st.success(f"📅 Mostrando datos desde {fecha_inicio} hasta {fecha_fin}")

            # Mostrar la fecha en formato visual
            df_filtrado_ingresos["FECHA"] = df_filtrado_ingresos["FECHA"].dt.strftime("%d/%m/%Y")

            st.dataframe(df_filtrado_ingresos)

            df_filtrado_ingresos["FECHA"] = pd.to_datetime(
                df_filtrado_ingresos["FECHA"], format="%d/%m/%Y", errors="coerce"
            )
#................................................................................................
        # CREACION DEL REPORTE DE INGRESOS POR CATEGORIAS

                        
            resumen_subcategorias = df_ingresos.groupby(["SUBCATEGORIA", "TIPO DE PAGO"])["MONTO"].sum().reset_index()
        
            st.subheader("💸 Reporte de Ingresos por Subcategoría")
            st.dataframe(resumen_subcategorias)
         
            
            # Total en USD ya totalizados de euros y BSF convertidos a $
            total_usd_directo = df_ingresos[df_ingresos["TIPO DE PAGO"] == "Dolares"]["MONTO"].sum()
            

            # valor total de los BSF convertidos a USD
            df_filtrado_ingresos["MONTO_USD"] = df_filtrado_ingresos.apply(convertir_bsf_a_usd, axis=1)
            total_bsf_convertido = df_filtrado_ingresos[df_filtrado_ingresos["TIPO DE PAGO"] == "BSF"]["MONTO_USD"].sum()
            
             
        
            # Sumar los montos por tipo de pago (Dólares, Zelle y BsF, euros por separado)
            total_ingresos = df_ingresos.groupby("TIPO DE PAGO")["MONTO"].sum().reset_index()
            # Mostrar los totales correctamente
        
            st.markdown(
                f"**🔢 Total General (USD):** ${total_usd_directo+total_bsf_convertido:,.2f}"
            )

        
            for _, row in total_ingresos.iterrows():
                tipo_pago = row["TIPO DE PAGO"]
                total = row["MONTO"]
                if tipo_pago == "BSF":
                                
                    st.markdown(f"- 🪙 Total Ingresos en BsF: {total:,.2f}")
                elif tipo_pago == "Euros":
                    st.markdown(f"- 💶  Total Ingresos en Euros: {total:,.2f}")
                     
                else: 
                    st.markdown(f"- 💵  Total Ingresos en (USD): {total:,.2f}")
                                             
            st.markdown(
                f" - 💰 Total  BsF convertidos a (USD): **${total_bsf_convertido:,.2f}**")
        
    else:
        st.warning("⚠️ Por favor, selecciona un rango de fechas válido.")

#-------------------------------------------------------------------------------------------------------
 # SECCION DE REPORTES

def reporte_ingresos_por_responsable():

    # Cargamos los datos desde Google Sheets
    df = st.session_state.df
    
    if df.empty:
        st.warning("No hay datos disponibles para generar reportes.")
        return

    # Convertir la columna de fecha a tipo datetime``
    df["FECHA"] = pd.to_datetime(df["FECHA"], format="%d/%m/%Y", errors="coerce")


    # Filtrar solo los ingresos
    df_ingresos = df[df["CATEGORIA"] == "Ingreso"]

    #st.subheader("💰 Reporte de Ingresos por Tipo y Subcategoría")
# Verificar si hay datos en df_ingresos antes de calcular min/max fecha
    if df_ingresos.empty:
        st.warning("No hay ingresos registrados en la base de datos.")
        return

    # 🔹 OBTENER EL RANGO DE FECHAS
    min_fecha, max_fecha = df_ingresos["FECHA"].min(), df_ingresos["FECHA"].max()

    
# 🔹 3️⃣ SELECCIÓN DEL RANGO DE FECHAS EN STREAMLIT
    rango_fechas = st.date_input(
    "Selecciona el rango de fechas",
    [min_fecha, max_fecha],  # Valores predeterminados
    min_value=min_fecha,
    max_value=max_fecha )


# 🔹 4️⃣ VALIDAR LA SELECCIÓN Y FILTRAR EL DATAFRAME
    if isinstance(rango_fechas, tuple) and len(rango_fechas) == 2:
        fecha_inicio, fecha_fin = rango_fechas

        # Convertimos las fechas seleccionadas a datetime
        fecha_inicio = pd.to_datetime(fecha_inicio, format="%d/%m/%Y")
        fecha_fin = pd.to_datetime(fecha_fin, format="%d/%m/%Y")


        # Filtrar ingresos dentro del rango de fechas
        df_filtrado_ingresos = df_ingresos[
            (df_ingresos["FECHA"] >= fecha_inicio) & 
            (df_ingresos["FECHA"] <= fecha_fin)
        ]

        if df_filtrado_ingresos.empty:
            st.warning("⚠️ No se encontraron ingresos en este rango de fechas.")
        else:
            st.success(f"📅 Mostrando datos desde {fecha_inicio} hasta {fecha_fin}")

            # Mostrar la fecha en formato visual
            df_filtrado_ingresos["FECHA"] = df_filtrado_ingresos["FECHA"].dt.strftime("%d/%m/%Y")

            st.dataframe(df_filtrado_ingresos)
           
            # se convierte la fecha a formato panda para poder hacer uso de la api
            df_filtrado_ingresos["FECHA"] = pd.to_datetime(
                df_filtrado_ingresos["FECHA"], format="%d/%m/%Y", errors="coerce"
            )
#.............................................................................................

        # CREACION DEL REPORTE DE INGRESOS POR RESPONSABLES

                        
        resumen_responsable = df_ingresos.groupby(["RESPONSABLE", "TIPO DE PAGO"])["MONTO"].sum().reset_index()
        
        st.subheader("💸 Reporte de Ingresos por Responsable")
        st.dataframe(resumen_responsable)

#-----------------------------------------------------------------------------------------------  
        # este codigo usa una api externa para el encontrar la tasa de cambio eur/$ 
            

        # Obtener la tasa EUR/USD reutilizando la función ya creada
        fecha = df_ingresos["FECHA"].max()
        tasa_eur = obtener_tasa_eur_usd(fecha)
 
        # Aplicar conversión BSF → USD
        df_ingresos["MONTO_CONVERTIDO"] = df_ingresos.apply(convertir_bsf_a_usd, axis=1)
        total_bsf_convertido = df_filtrado_ingresos[df_filtrado_ingresos["TIPO DE PAGO"] == "BSF"]["MONTO_USD"].sum()
 
 
 

  

      
        # Total en USD de pagos distintos a BSF
        total_usd_directo = df_ingresos[df_ingresos["TIPO DE PAGO"] == "Dolares"]["MONTO"].sum()

                    
        # Crear una nueva columna MONTO_USD que convierta a dólares solo si es BSF, usando la tasa de cambio
        df_filtrado_ingresos["MONTO_USD"] = df_filtrado_ingresos.apply(
            lambda row: row["MONTO"] / row["TASA DE CAMBIO"] if row["TIPO DE PAGO"] == "BSF" else row["MONTO"],
            axis=1
        )

        # Total convertido de BSF a USD
        total_bsf_convertido = df_filtrado_ingresos[df_filtrado_ingresos["TIPO DE PAGO"] == "BSF"]["MONTO_USD"].sum()


        # Sumar los montos por tipo de pago (Dólares, Zelle y BsF, euros por separado)
        total_ingresos = df_ingresos.groupby("TIPO DE PAGO")["MONTO"].sum().reset_index()
        # Mostrar los totales correctamente
        
        st.markdown(
            f"**🔢 Total General (USD):** ${total_usd_directo+total_bsf_convertido:,.2f}"
        )

        
        for _, row in total_ingresos.iterrows():
            tipo_pago = row["TIPO DE PAGO"]
            total = row["MONTO"]
            if tipo_pago == "BSF":
                                
                st.markdown(f"- 🪙 Total Ingresos en BsF: {total:,.2f}")
            elif tipo_pago == "Euros":
                st.markdown(f"- 💶  Total Ingresos en Euros: {total:,.2f}")
                     
            else: 
             st.markdown(f"- 💵  Total Ingresos en (USD): {total:,.2f}")
                                             
             st.markdown(
                f" - 💰 Total  BsF convertidos a (USD): **${total_bsf_convertido:,.2f}**")
        
    else:
        st.warning("⚠️ Por favor, selecciona un rango de fechas válido.")
      
#----------------------------------------------------------------------------------------------------



#-----------------------------------------------------------------------------------------------




def reporte_de_gastos_por_fecha():
    
    df = st.session_state.df
    # Obtener df_subs desde session_state
    df_subs = st.session_state.df_subs

    if df.empty:
        st.warning("No hay datos disponibles para generar reportes.")
        return
    
    
    # Convertir la columna de fecha a tipo datetime
    df["FECHA"] = pd.to_datetime(df["FECHA"], format="%d/%m/%Y", errors="coerce")

    # Filtrar solo los Gastos
    df_gastos = df[df["CATEGORIA"] == "Gasto"]

    st.subheader("💸 Reporte de Gastos por Tipo y Subcategoría")

    # Verificar si hay datos en df_gastos antes de calcular min/max fecha
    if df_gastos.empty:
        st.warning("No hay gastos registrados en la base de datos.")
        return

    # Obtener el rango de fechas
    min_fecha, max_fecha = df_gastos["FECHA"].min(), df_gastos["FECHA"].max()

    # Seleccionar el rango de fechas
    rango_fechas = st.date_input(
        "Selecciona el rango de fechas",
        (min_fecha, max_fecha),  # Se usa una tupla en lugar de lista
        min_value=min_fecha,
        max_value=max_fecha
    )
    # Validación para asegurar que se seleccionaron fechas válidas
    if isinstance(rango_fechas, tuple) and len(rango_fechas) == 2:
        fecha_inicio, fecha_fin = rango_fechas

        # Convertimos las fechas seleccionadas a datetime
        fecha_inicio = pd.to_datetime(fecha_inicio)
        fecha_fin = pd.to_datetime(fecha_fin)


        # Filtrar gastos dentro del rango de fechas
        df_gastos_filtrado = df_gastos[
            (df_gastos["FECHA"] >= fecha_inicio) & 
            (df_gastos["FECHA"] <= fecha_fin)
        ]

        # Si no hay datos filtrados, mostrar mensaje de advertencia
        if df_gastos_filtrado.empty:
            st.warning("⚠️ No hay gastos registrados en el rango seleccionado.")
        else:
            st.success(f"📅 Mostrando datos desde {fecha_inicio} hasta {fecha_fin}")


            # Convertir las fechas a formato día/mes/año solo para mostrar
            df_gastos_filtrado["FECHA"] = df_gastos_filtrado["FECHA"].dt.strftime("%d/%m/%Y")

            st.dataframe(df_gastos_filtrado.style.format({
        "MONTO": "{:,.2f}",
        "TASA DE CAMBIO": "{:.2f}"
    }))
#------------------------------------------------------------------------------------------------------------
            
           
        # Limpiar columnas para unir correctamente
        df_gastos_filtrado["SUBCATEGORIA"] = df_gastos_filtrado["SUBCATEGORIA"].str.strip().str.lower()
        df_subs["SUBCATEGORIA"] = df_subs["SUBCATEGORIA"].str.strip().str.lower()
           
         # Unir con df_subs para obtener el tipo de gasto
        df_gastos_filtrado = df_gastos_filtrado.merge(
            df_subs[df_subs["CATEGORIA"] == "Gasto"][["SUBCATEGORIA", "TIPO DE GASTO"]],
            on="SUBCATEGORIA",
            how="left"
        )
   
        # Filtrar solo los gastos y excluir al responsable "SAHA"
        df_filtrado = df[
            (df["CATEGORIA"] == "Gasto") & 
            (df["RESPONSABLE"] != "SAHA")
        ]
        
        # 1. Calcular MONTO_USD en cada fila del df original
        df_filtrado["MONTO_USD"] = df_filtrado.apply(
            lambda row: row["MONTO"] / row["TASA DE CAMBIO"] if row["TIPO DE PAGO"] == "BSF" else row["MONTO"],
            axis=1
        )

        
        # Filtrar solo los registros que son gastos
        df_gastos = df[df["CATEGORIA"] == "Gasto"]

        
        # Crear una nueva columna MONTO_USD que convierta a dólares solo si es BSF, usando la tasa de cambio
        df_gastos["MONTO_USD"] = df_gastos.apply(
            lambda row: row["MONTO"] / row["TASA DE CAMBIO"] if row["TIPO DE PAGO"] == "BSF" else row["MONTO"],
            axis=1
        )

        # Agrupar por tipo de pago y sumar los montos
        total_gastos_por_moneda = df_gastos.groupby("TIPO DE PAGO")["MONTO"].sum().reset_index()

        # Total en BSF de pagos distintos
        total_bsf = df_gastos[df_gastos["TIPO DE PAGO"] == "BSF"]["MONTO"].sum()

        # Total en USD de pagos distintos a BSF
        total_usd_directo = df_gastos[df_gastos["TIPO DE PAGO"] != "BSF"]["MONTO"].sum()

        # Total convertido de BSF a USD
        total_bsf_convertido = df_gastos[df_gastos["TIPO DE PAGO"] == "BSF"]["MONTO_USD"].sum()

        #--------------------------------------------------------------------------------
        # Agrupar SOLO por RESPONSABLE y TIPO DE PAGO
        # CORRECTO: usando lista
        resumen_por_responsable = df_filtrado.groupby(["RESPONSABLE", "TIPO DE PAGO"])[["MONTO", "MONTO_USD"]].sum().reset_index()


        # Reordenar las columnas: MONTO va primero, luego TASA DE CAMBIO
        columnas_ordenadas = ["RESPONSABLE", "TIPO DE PAGO", "MONTO", "MONTO_USD"]

        resumen_por_responsable = resumen_por_responsable[columnas_ordenadas]

        # Total en USD de pagos distintos a BSF
        total_usd_responsable = resumen_por_responsable[resumen_por_responsable["TIPO DE PAGO"] != "BSF"]["MONTO"].sum()

        # Total en USD de pagos distintos a BSF
        total_BSF_responsable = resumen_por_responsable[resumen_por_responsable["TIPO DE PAGO"] == "BSF"]["MONTO"].sum()
        
        # Total convertido de BSF a USD
        total_bsf_responsable_convert = resumen_por_responsable[resumen_por_responsable["TIPO DE PAGO"] == "BSF"]["MONTO_USD"].sum()

        # Total general combinado
        total_general_usd_responsable = total_usd_responsable + total_bsf_responsable_convert

        #----------------------------------------------------------------------------------------

        # Separar fijos y variables
        df_fijos = df_gastos_filtrado[df_gastos_filtrado["TIPO DE GASTO"] == "Gasto Fijo"]
        df_variables = df_gastos_filtrado[df_gastos_filtrado["TIPO DE GASTO"] == "Gasto Variable"]

               

        # Subtotales por tipo de pago
        subtotal_fijos_pago = df_fijos.groupby("TIPO DE PAGO")["MONTO"].sum().reset_index()
        subtotal_variables_pago = df_variables.groupby("TIPO DE PAGO")["MONTO"].sum().reset_index()


        # Gastos fijos
        total_fijos_bsf = df_fijos[df_fijos["TIPO DE PAGO"] == "BSF"]["MONTO"].sum()
        total_fijos_usd = df_fijos[df_fijos["TIPO DE PAGO"] != "BSF"]["MONTO"].sum()

        # Gastos variables
        total_variables_bsf = df_variables[df_variables["TIPO DE PAGO"] == "BSF"]["MONTO"].sum()
        total_variables_usd = df_variables[df_variables["TIPO DE PAGO"] != "BSF"]["MONTO"].sum()

        #--------------------------------------------------------------------------------------------
        # Partimos del DataFrame que ya tiene "TIPO DE GASTO PARA SAHA"

        df_saha = df_gastos_filtrado[df_gastos_filtrado["RESPONSABLE"] == "SAHA"]

        columnas_deseadas = ["FECHA", "SUBCATEGORIA", "DESCRIPCION", "MONTO", "TIPO DE PAGO", "TASA DE CAMBIO", "CUENTA"]
        df_saha_mostrar = df_saha[columnas_deseadas]


        # Crear una nueva columna MONTO_USD que convierta a dólares solo si es BSF, usando la tasa de cambio
        df_saha["MONTO_USD"] = df_saha.apply(
            lambda row: row["MONTO"] / row["TASA DE CAMBIO"] if row["TIPO DE PAGO"] == "BSF" else row["MONTO"],
            axis=1
        )

        
        df_saha_fijos = df_saha[df_saha["TIPO DE GASTO"] == "Gasto Fijo"]
        df_saha_variables = df_saha[df_saha["TIPO DE GASTO"] == "Gasto Variable"]

        
        # Total en USD de pagos distintos a BSF
        total_usd_saha = df_saha[df_saha["TIPO DE PAGO"] != "BSF"]["MONTO"].sum()

        # Total BSF
        total_bsf_saha = df_saha[df_saha["TIPO DE PAGO"] == "BSF"]["MONTO"].sum()
        
        # Total convertido de BSF a USD
        total_bsf_conver_saha = df_saha[df_saha["TIPO DE PAGO"] == "BSF"]["MONTO_USD"].sum()


        columnas_deseadas = ["FECHA", "SUBCATEGORIA", "DESCRIPCION", 
                 "MONTO", "TIPO DE PAGO", "TASA DE CAMBIO", "CUENTA"]
        
        

        df_saha_fijos = df_saha_fijos[columnas_deseadas]
        df_saha_variables = df_saha_variables[columnas_deseadas]

        # Totales Fijos de SAHA
        total_fijos_usd_saha = df_saha_fijos[df_saha_fijos["TIPO DE PAGO"].isin(["Dólares", "Zelle"])]["MONTO"].sum()
        total_fijos_bsf_saha = df_saha_fijos[df_saha_fijos["TIPO DE PAGO"] == "BSF"]["MONTO"].sum()

        # Totales Variables de SAHA
        total_variables_usd_saha = df_saha_variables[df_saha_variables["TIPO DE PAGO"].isin(["Dólares", "Zelle"])]["MONTO"].sum()
        total_variables_bsf_saha = df_saha_variables[df_saha_variables["TIPO DE PAGO"] == "BSF"]["MONTO"].sum()



#-----------------------------------------------------------------------------------------------

        # cuadros resumenes

        st.subheader("💰 Total de Gastos por Tipo de moneda")
        st.dataframe(total_gastos_por_moneda.style.format({"MONTO": "{:,.2f}"}))
        


        st.write(f"""
        **🔢 Total General (USD):** ${total_usd_directo+total_bsf_convertido:,.2f}  
        - 🪙 Total gastos en BSF: {total_bsf:,.2f}
        - 💵 USD directos: ${total_usd_directo:,.2f}  
        - 🪙 BSF convertidos a USD: ${total_bsf_convertido:,.2f}
        """)
        #-----------------------------------------------------------------------
                
        
        # Mostrar resumen
        st.subheader("🧾 Resumen Total de Gastos por Responsable (Excepto SAHA)")
        st.dataframe(resumen_por_responsable.style.format({"MONTO": "{:,.2f}","MONTO_USD": "{:,.2f}","TASA DE CAMBIO": "{:.2f}"}), use_container_width=True)


        st.write(f"""
        **🔢 Total General (USD):** ${total_general_usd_responsable:,.2f} 
        - 🪙 Total gastos en BSF: {total_BSF_responsable:,.2f}
        - 💵 USD directos: ${total_usd_responsable:,.2f}  
        - 🪙 BSF convertidos a USD: ${total_bsf_responsable_convert:,.2f}
        """)


        st.subheader("💰 Subtotales de Gastos Fijos por Tipo de moneda")
        st.dataframe(subtotal_fijos_pago.style.format({"MONTO": "{:,.2f}"}))
        st.markdown(f"**💵Total Gastos Fijos en US$:  {total_fijos_usd:,.2f}**")
        st.markdown(f"**💴Total Gastos Fijos en BSF: {total_fijos_bsf:,.2f}**")

        st.markdown("---")

        st.subheader("💸 Subtotales de Gastos Variables por Tipo de moneda")
        st.dataframe(subtotal_variables_pago.style.format({"MONTO": "{:,.2f}"}))
        st.markdown(f"**💵Total Gastos Variables en US$: {total_variables_usd:,.2f}**")
        st.markdown(f"**💴Total Gastos Variables en BSF: {total_variables_bsf:,.2f}**")

         #================================================================================
         # REGISTROS DE SAHA     
        
        st.markdown("---")

        st.subheader("📌 Registros filtrados para SAHA")
        st.dataframe(df_saha_mostrar.style.format({"MONTO": "{:,.2f}","MONTO_USD": "{:.2f}","TASA DE CAMBIO": "{:.2f}"}))
        st.write(f"""
         
         
        **🔢 Total General (USD):** ${total_usd_saha+total_bsf_conver_saha:,.2f} 
        - 🪙 Total gastos en BSF: {total_bsf_saha:,.2f}
        - 💵 USD directos: ${total_usd_saha:,.2f} 
        - 🪙 BSF convertidos a USD: ${total_bsf_conver_saha:,.2f}
        """)

        
        #formateo a 2 decimales
        # Mostrar con formato
        st.subheader("📘 Gastos Fijos de SAHA")
        st.dataframe(df_saha_fijos.style.format({
         "MONTO": "{:,.2f}",
            "TASA DE CAMBIO": "{:.2f}"
        }))

        
        # Mostrar totales fijos
        st.markdown(f"**💵 Total Gastos Fijos SAHA en US$: {total_fijos_usd_saha:,.2f}**")
        st.markdown(f"**💴 Total Gastos Fijos SAHA en BSF: {total_fijos_bsf_saha:,.2f}**")

        st.markdown("---")

        st.subheader("📙 Gastos Variables de SAHA")
        st.dataframe(df_saha_variables.style.format({
            "MONTO": "{:,.2f}",
            "TASA DE CAMBIO": "{:.2f}"
        }))

        
        # Mostrar totales variables
        st.markdown(f"**💵 Total Gastos Variables SAHA en US$: {total_variables_usd_saha:,.2f}**")
        st.markdown(f"**💴 Total Gastos Variables SAHA en BSF: {total_variables_bsf_saha:,.2f}**")

        st.markdown("---")

        

    else:
        st.warning("⚠️ Por favor, selecciona un rango de fechas válido.")

#====================================================================================
# Función para estandarizar columnas de los df
def estandarizar_columnas(df):
    df.columns = [
        unicodedata.normalize('NFKD', col).encode('ascii', 'ignore').decode('utf-8')
        for col in df.columns
    ]
    df.columns = df.columns.str.strip().str.upper()
    return df

#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

# Función para mostrar el formulario de edición
def formulario_edicion(registro, worksheet, df,sheet):
    st.subheader("Formulario de Edición")

        # Recuperar datos ya cargados en session_state
    df_subs = st.session_state.df_subs
    responsables_df = st.session_state.responsables_df
    cuenta_bancaria = st.session_state.cuentas 

    
    # Convertir directamente el string en formato dd/mm/yyyy a date
    fecha_str = registro["FECHA"]

    try:
        fecha_obj = datetime.strptime(fecha_str, "%d/%m/%Y").date()
    except:
        fecha_obj = date.today()

    # Mostrar en el formulario
    fecha = st.date_input("Fecha de la transacción", value=fecha_obj, key="fecha")
    

    
    categoria = st.selectbox("Categoria", ["Ingreso", "Gasto"], index=["Ingreso", "Gasto"].index(registro["CATEGORIA"]))
    
    df_subs = st.session_state.df_subs  # ✅ DataFrame completo con subcategorías, tipos y categorías
    
    # Tipo de Gasto (solo si es "Gasto")
   
    if categoria == "Gasto":
        
        # Limpia y normaliza el valor del registro
        subcategoria_actual = registro.get("SUBCATEGORIA", "").strip().title()

                
        # Detectar tipo de gasto desde la subcategoría
        # Filtrar solo subcategorías de gastos antes de buscar tipo
        tipo_detectado = df_subs[
            (df_subs["CATEGORIA"] == "Gasto") & 
            (df_subs["SUBCATEGORIA"] == subcategoria_actual)
        ]["TIPO DE GASTO"].values

        tipo_gasto = tipo_detectado[0] if len(tipo_detectado) > 0 else "Gasto Fijo"
        
        # Selectbox para tipo de gasto (ya deducido)
        tipo_gasto = st.selectbox(
            "Tipo de Gasto",
            ["Gasto Fijo", "Gasto Variable"],
            index=["Gasto Fijo", "Gasto Variable"].index(tipo_gasto)
        )

    # Filtrar subcategorías según tipo y categoría
        subcats_filtradas = df_subs[
            (df_subs["CATEGORIA"] == "Gasto") & 
            (df_subs["TIPO DE GASTO"] == tipo_gasto)
        ]
        # También normaliza las opciones antes de comparar
        subcats_lista = [s.strip().title() for s in subcats_filtradas["SUBCATEGORIA"].unique().tolist()]

        # Selectbox para subcategoría, con valor actual preseleccionado
        subcategoria = st.selectbox(
            "Subcategoría",
            subcats_lista,
            index=subcats_lista.index(subcategoria_actual) if subcategoria_actual in subcats_lista else 0
         )
    else:
        tipo_gasto = None
        subcats_ingreso = df_subs[df_subs["CATEGORIA"] == "Ingreso"]["SUBCATEGORIA"].unique().tolist()
        subcategoria_actual = registro.get("SUBCATEGORIA", "").strip().title()
        subcategoria = st.selectbox(
        "Subcategoría",
        subcats_ingreso,
        index=subcats_ingreso.index(subcategoria_actual) if subcategoria_actual in subcats_ingreso else 0
    )
    
    

    # Responsable

    responsables_raw = st.session_state.df["RESPONSABLE"].dropna().unique()
    responsables_df = [r.strip() for r in responsables_raw if r.strip().upper() != "RESPONSABLE"]

    responsable_actual = registro.get("RESPONSABLE", "").strip()

    
    responsable = st.selectbox(
        "Responsable",
        responsables_df,
        index=responsables_df.index(responsable_actual) if responsable_actual in responsables_df else 0
        )

       

    # Descripción
    descripcion = st.text_input("Descripción", value=registro["DESCRIPCION"], key="descripcion")

    try:
     monto= float(registro.get("MONTO", 0))
    except:
     monto = 0.0

    monto = st.number_input("Ingrese el monto", value=monto, step=0.01, format="%.2f", key="monto")

    # Ajuste automático del signo del monto según la categoría
    if categoria == "Ingreso" and monto < 0:
        st.warning("El monto era negativo pero la categoría es Ingreso. Se ha convertido a positivo automáticamente.")
        monto = abs(monto)

    elif categoria == "Gasto" and monto > 0:
        st.warning("El monto era positivo pero la categoría es Gasto. Se ha convertido a negativo automáticamente.")
        monto = -abs(monto)
    
    
    # Tipo de pago
    tipo_pago = st.selectbox("Selecciona el tipo de pago", ["Dolares", "Zelle", "BSF", "Euros",], 
                             index=["Dólares","Zelle","BSF","Euros"].index(registro["TIPO DE PAGO"]), 
                             key="tipo_pago")

    
    
    # Mostrar input de tasa solo si es BSF
    if tipo_pago == "BSF":
       tasa_inicial = float(registro["TASA DE CAMBIO"]) if registro["TIPO DE PAGO"] == "BSF" else 0.0
       
       st.number_input(
            "Tasa de cambio", 
            min_value=0.0, 
            format="%.2f", 
            value=tasa_inicial,
            key="tasa_cambio_edicion"
        )

    #  Obtener el valor actualizado de la tasa
    if tipo_pago == "BSF":
        tasa_cambio = st.session_state["tasa_cambio_edicion"]
    else:
        tasa_cambio = 1.0

   
    # Validación visual si tasa es incorrecta
    if tipo_pago == "BSF" and tasa_cambio in [0.0, 1.0]:
        st.warning("⚠️ Para pagos en BSF debes ingresar una tasa de cambio válida (> 1).")

    
    # Cuenta Bancaria
    lista_cuentas = [c.strip() for c in st.session_state.cuentas]  # limpiar espacios
    cuenta_actual = str(registro.get("CUENTA", "")).strip()  # limpiar también el valor actual
    
    try:
        idx_cuenta = lista_cuentas.index(cuenta_actual)
    except ValueError:
        st.warning(f"La cuenta '{cuenta_actual}' no está en la lista. Se usará la primera por defecto.")
        idx_cuenta = 0


    cuenta_bancaria = st.selectbox(
        "Cuenta bancaria",
        lista_cuentas,
        index=idx_cuenta
    )


#--------------------------------------------------------------------------------------------------------
    # Botón para guardar los cambios
        
    if st.button("Actualizar Registro"):
        
        if tipo_pago == "BSF" and tasa_cambio in [0.0, 1.0]:
            st.warning("❌ No puedes guardar el registro sin ingresar una tasa de cambio.")
            return
        
         
        # Verificar que todos los campos sean válidos (puedes agregar validación extra si es necesario)
        if categoria and subcategoria and responsable and monto:


            # Actualizamos el registro en el DataFrame y Google Sheets

            
            actualizar_datos_modificados(worksheet, registro["ID"], fecha, 
                                         categoria, subcategoria, responsable, descripcion, 
                                         monto, tipo_pago, tasa_cambio,cuenta_bancaria)
            st.success("Registro actualizado exitosamente!")
        else:
            st.warning("Por favor, completa todos los campos.")

#====================================================================================================
# BOTON PARA ELIMINAR EL REGISTRO
    st.subheader("Eliminar un registro")

    if not df.empty:
        id_eliminar = st.text_input("Ingresa el ID a eliminar:", key="input_id_eliminar")

        if id_eliminar:
            try:
                id_eliminar = int(id_eliminar)
            except ValueError:
                st.warning("Por favor ingresa un número válido como ID.")
                st.stop()

            if id_eliminar in df["ID"].values:
                if st.button("❌ Eliminar seleccionado"):
                    # 1. Eliminar el registro
                    df = df[df["ID"] != id_eliminar].copy()

                    # 2. Resetear índices internos
                    df.reset_index(drop=True, inplace=True)

                        # 3. Reasignar valores a la columna "ID"
                    df["ID"] = range(1, len(df) + 1)

                    # 4. Actualizar hoja si no está vacía
                    if not df.empty:
                        df = df.fillna("")
                        worksheet.clear()
                        worksheet.update([df.columns.values.tolist()] + df.values.tolist())
                    else:
                        st.warning("El DataFrame está vacío. No se actualizará la hoja para evitar borrar los datos.")

                    # 5. Limpiar sesión
                    if "edicion_activa" in st.session_state:
                        del st.session_state.edicion_activa

                    # 6. Mensaje de éxito y recarga
                    st.success(f"Registro con ID {id_eliminar} eliminado con éxito.")
                    st.session_state["df"] = df
                    st.rerun()
        else:
            st.warning("El ID ingresado no existe en la base de datos.")
    else:
        st.warning("No hay registros disponibles para eliminar.")


#---------------------------------------------------------------------------------------------------

# ✅ Cachear la carga del workbook y los saldos
@st.cache_resource
def cargar_workbook():
    return obtener_spread()

@st.cache_data(ttl=60)
def cargar_saldos(_spread):
    return _spread.sheet_to_df(sheet='Saldos', index=None)

def gestionar_saldos():
    st.subheader("Agregar o Modificar Saldo de Apertura")

    try:
        #spread = cargar_workbook()
        spread = obtener_spread()
        #df_cuentas = cargar_saldos(spread)
        df_cuentas = spread.sheet_to_df(sheet='Saldos', index=None)
    except Exception as e:
        st.error("No se pudo leer la hoja 'Saldos'. Verifica que exista.")
        st.exception(e)
        return

    # Forzar formato dd/mm/yyyy en la columna FECHA
    if 'FECHA' in df_cuentas.columns:
        df_cuentas['FECHA'] = pd.to_datetime(
            df_cuentas['FECHA'], errors='coerce',dayfirst=True
        ).dt.strftime("%d/%m/%Y")


    columnas_esperadas = ['CUENTA', 'FECHA', 'SALDO APERTURA', 'MONEDA']
    for col in columnas_esperadas:
        if col not in df_cuentas.columns:
            st.error(f"Falta la columna '{col}' en la hoja 'Saldos'.")
            return

    st.write("### 📋 Saldos de aperturas registrados")
    if df_cuentas.empty:
        st.warning("Aún no hay saldos registrados.")
    else:
        st.dataframe(df_cuentas)

    # Pregunta inicial
    agregar_nueva = st.radio(
        "¿Desea agregar una nueva cuenta?",
        ("No", "Sí"),
        horizontal=True
    )

    cuentas_existentes = df_cuentas['CUENTA'].dropna().unique().tolist()

    if agregar_nueva == "Sí":
        cuenta_final = st.text_input("Nombre de la nueva cuenta")

        fecha_saldo = st.date_input(
            "Fecha del Saldo Apertura",
            value=date.today(),
            format="DD/MM/YYYY"
        )

        fecha_formateada = fecha_saldo.strftime("%d/%m/%Y")  # <-- aquí el formato correcto

        saldo_apertura = st.number_input("Saldo Apertura", step=0.01, format="%.2f")
        moneda = st.selectbox("Moneda del saldo Apertura", ["BSF", "Dólares", "Euros"])

    else:
        if not cuentas_existentes:
            st.warning("No hay cuentas existentes. Debe crear una nueva.")
            return

        cuenta_seleccionada = st.selectbox("Selecciona una cuenta existente", cuentas_existentes)
        datos_cuenta = df_cuentas[df_cuentas['CUENTA'] == cuenta_seleccionada].iloc[0]

        cuenta_final = cuenta_seleccionada

        try:
            fecha_dt = datetime.strptime(str(datos_cuenta['FECHA']), "%d/%m/%Y").date()
        except Exception:
            fecha_dt = date.today()

        fecha_saldo = st.date_input(
            "Fecha del Saldo Apertura",
            value=fecha_dt,
            format="DD/MM/YYYY"
        )

        fecha_formateada = fecha_saldo.strftime("%d/%m/%Y")  # <-- convertir aquí también

        saldo_apertura = st.number_input(
            "Saldo Apertura",
            value=float(datos_cuenta['SALDO APERTURA']),
            step=0.01,
            format="%.2f"
        )
        moneda = st.selectbox(
            "Moneda del saldo Apertura",
            ["BSF", "Dólares", "Euros"],
            index=["BSF", "Dólares", "Euros"].index(str(datos_cuenta['MONEDA']))
        )

    if st.button("Guardar Saldo Apertura"):
        if not cuenta_final or cuenta_final.strip() == "":
            st.error("Debe especificar un nombre de cuenta.")
            return

        try:
            if agregar_nueva == "Sí":
                nueva_fila = pd.DataFrame([{
                    'CUENTA': cuenta_final.strip(),
                    'FECHA': fecha_formateada,
                    'SALDO APERTURA': saldo_apertura,
                    'MONEDA': moneda
                }])
                df_cuentas = pd.concat([df_cuentas, nueva_fila], ignore_index=True)
                accion = "registrado"
            else:
                idx = df_cuentas.index[df_cuentas['CUENTA'] == cuenta_final][0]
                df_cuentas.at[idx, 'FECHA'] = fecha_formateada
                df_cuentas.at[idx, 'SALDO APERTURA'] = saldo_apertura
                df_cuentas.at[idx, 'MONEDA'] = moneda
                accion = "actualizado"

            # Guardar de vuelta en Google Sheets
            spread.df_to_sheet(df_cuentas, sheet='Saldos', index=False)
            st.success(f"Saldo apertura {accion} para '{cuenta_final.strip()}'")
            st.rerun()

        except Exception as e:
            st.error("Error al guardar el saldo apertura.")
            st.exception(e)



#===============================================================================================

@st.cache_data(ttl=60)
def cargar_movimientos(_spread):
    df = _spread.sheet_to_df(sheet='Hoja 1', index=None)
    # Convertir la columna de fecha a tipo datetime
    df["FECHA"] = pd.to_datetime(df["FECHA"], format="%d/%m/%Y", errors="coerce").dt.date
    
    #df["FECHA"] = pd.to_datetime(df["FECHA"], errors="coerce").dt.date
    return df

@st.cache_data(ttl=60)
def cargar_saldos(_spread):
    df = _spread.sheet_to_df(sheet='Saldos', index=None)
    df["FECHA"] = pd.to_datetime(df["FECHA"], format="%d/%m/%Y", errors="coerce").dt.date
    #df["FECHA"] = pd.to_datetime(df["FECHA"], errors="coerce").dt.date
    return df
#----------------------------------------------------------------------------------------------------
def gestionar_cuentas(spread):
    st.header("Gestión de Cuentas Bancarias")

    # 1. Cargar datos desde Google Sheets con caché
    try:
        df_mov = cargar_movimientos(spread)
        df_saldos = cargar_saldos(spread)
    except Exception as e:
        st.error("Error al cargar los datos desde Google Sheets.")
        st.exception(e)
        return

    # 2. Validar columnas necesarias
    for col in ["FECHA", "CUENTA", "CATEGORIA", "MONTO"]:
        if col not in df_mov.columns:
            st.error(f"Falta la columna '{col}' en la hoja de movimientos.")
            return
    for col in ["CUENTA", "FECHA", "SALDO APERTURA"]:
        if col not in df_saldos.columns:
            st.error(f"Falta la columna '{col}' en la hoja de saldos.")
            return

    # 3. Convertir MONTO a float para evitar errores
    df_mov["MONTO"] = pd.to_numeric(df_mov["MONTO"], errors="coerce").fillna(0)
    df_saldos["SALDO APERTURA"] = pd.to_numeric(df_saldos["SALDO APERTURA"], errors="coerce").fillna(0)
    # Convertimos FECHA_APERTURA a datetime
    df_saldos["FECHA"] = pd.to_datetime(df_saldos["FECHA"])

    # 4. Selección de cuenta
    cuentas = df_saldos["CUENTA"].dropna().unique().tolist()
    if not cuentas:
        st.warning("No hay cuentas registradas en los movimientos.")
        return
    cuenta_sel = st.selectbox("Seleccione la cuenta", options=cuentas)

    # 5. Selección de rango de fechas
    rango_fechas = st.date_input(
        "Seleccione el rango de fechas",
        value=(date.today().replace(day=1), date.today())
    )
    if not isinstance(rango_fechas, (list, tuple)) or len(rango_fechas) != 2:
        st.warning("Debe seleccionar un rango de fechas válido.")
        return
    fecha_inicio, fecha_fin = rango_fechas

    # Obtenemos la fecha de apertura y saldo inicial de la cuenta seleccionada
    fecha_apertura = df_saldos.loc[df_saldos["CUENTA"] == cuenta_sel, "FECHA"].iloc[0]
    fecha_apertura = pd.to_datetime(fecha_apertura).date()  # lo convertimos a datetime.date

    if fecha_inicio < fecha_apertura:
        st.error(f"La fecha inicial no puede ser menor que la fecha de apertura de la cuenta ({fecha_apertura.strftime('%d/%m/%Y')})")
        return
    else:
        st.success("Rango de fechas válido ✅")


    # Mostrar rango seleccionado en DD/MM/YYYY
    st.write("Rango seleccionado:", fecha_inicio.strftime("%d/%m/%Y"), " - ", fecha_fin.strftime("%d/%m/%Y"))

    # 6. Filtrar movimientos
    df_filtrado = df_mov[
        (df_mov["CUENTA"] == cuenta_sel) &
        (df_mov["FECHA"] >= fecha_inicio) &
        (df_mov["FECHA"] <= fecha_fin)
    ].copy()

    # 10. Mostrar tabla de movimientos con fechas en DD/MM/YYYY
    st.write("### Movimientos filtrados")
    if df_filtrado.empty:
        st.info("No hay movimientos para este rango de fechas.")
    else:
        df_filtrado_display = df_filtrado.copy()
        df_filtrado_display["FECHA"] = df_filtrado_display["FECHA"].apply(lambda x: x.strftime("%d/%m/%Y"))
        st.dataframe(df_filtrado_display)



    # --- 1. Obtener saldo de apertura para la cuenta seleccionada ---
    saldo_apertura = df_saldos.loc[
        df_saldos["CUENTA"] == cuenta_sel, "SALDO APERTURA"
    ].values[0]

    # --- 2. Filtrar movimientos de la cuenta ---
    df_cuenta = df_mov[df_mov["CUENTA"] == cuenta_sel].copy()

    # --- 3. Movimientos ANTES del rango seleccionado ---
    # --- 3. Movimientos ANTES del rango seleccionado ---
    mov_antes = df_cuenta[
        (df_cuenta["FECHA"] >= fecha_apertura) &  # 🚨 Solo considerar desde apertura
        (df_cuenta["FECHA"] < fecha_inicio)
    ]


    #mov_antes = df_cuenta[df_cuenta["FECHA"] < fecha_inicio]

    ingresos_antes = mov_antes.loc[mov_antes["CATEGORIA"] == "Ingreso", "MONTO"].sum()
    egresos_antes = mov_antes.loc[mov_antes["CATEGORIA"] == "Gasto", "MONTO"].sum()

    saldo_inicial_intervalo = saldo_apertura + ingresos_antes + egresos_antes
    # NOTA LOS EGRESOS YA ESTAN EN NEGATIVO POR ESO SE SUMAN

    # --- 4. Movimientos DENTRO del rango seleccionado ---
    mov_intervalo = df_cuenta[
        (df_cuenta["FECHA"] >= fecha_inicio) &
        (df_cuenta["FECHA"] <= fecha_fin)
    ]

    ingresos_intervalo = mov_intervalo.loc[mov_intervalo["CATEGORIA"] == "Ingreso", "MONTO"].sum()
    egresos_intervalo = mov_intervalo.loc[mov_intervalo["CATEGORIA"] == "Gasto", "MONTO"].sum()

    saldo_final_intervalo = saldo_inicial_intervalo + ingresos_intervalo + egresos_intervalo
    # NOTA LOS EGRESOS YA ESTAN EN NEGATIVO POR ESO SE SUMAN

    col1,col2=st.columns(2)

    col1.metric("💰 Saldo Inicial", f"${saldo_inicial_intervalo:,.2f}")
    col1.metric("📊 Saldo Final", f"${saldo_final_intervalo:,.2f}")
    col2.metric("💰 Total Ingresos", f"${ingresos_intervalo:,.2f}")
    col2.metric("📊 Total Egresos", f"${egresos_intervalo:,.2f}")
    
    st.write("Ingresos Antes",f"${ingresos_antes:,.2f}")
    st.write("Egresos Antes",f"${egresos_antes:,.2f}")

#--------------------------------------------------------------------------------------------------

# ESTA SECCION ES PARA CREAR EL MENU DE SELECCION ENTRE HOJA DE FORMULARIO Y REGISTROS SIDEBAR

st.sidebar.title("Navegación")
pagina = st.sidebar.radio("Selecciona una página", ["Formulario de Registro", "Ver Registros","Reporte de Ingresos","Reporte de Gastos","Bancos"], key="pagina_radio")


# --- Control de flujo según la selección de la barra lateral ---
if pagina == "Formulario de Registro":
    st.title("Control de Ingresos y Gastos")# Título debe ir antes del formulario
    # 1. Autenticación con Google Sheets
    cliente = autenticacion_google_sheets()

    # 2. Abrir el archivo de Google Sheets por nombre
    sheet = cliente.open("BD DE REGISTROS FINANCIEROS")

    # 3. Llamar al formulario y pasarle el sheet
    formulario_de_registros(sheet)



    #formulario_de_registros()  # Llamamos a la función que maneja la lógica del formulario

# ACA SE CREA LA TABLA CON LOS REGISTROS INTRODUCIDOS EN STREAMLIT (TABLA RESUMEN)
# Mostrar los registros guardados (solo si existen)
    if st.session_state.registros:
      df = pd.DataFrame(st.session_state.registros)
      st.subheader("Registros de transacciones")
      st.dataframe(df.reset_index(drop=True))


# --- VER REGISTROS (Edición) ---
elif pagina == "Ver Registros":
    st.title("Editar Registro Existente")

    # Si el DataFrame no está cargado, cargamos desde Google Sheets
    if st.session_state.df.empty:
        cliente = autenticacion_google_sheets()
        sheet = cliente.open("BD DE REGISTROS FINANCIEROS")
        worksheet = sheet.sheet1  # o la hoja correspondiente
        datos = worksheet.get_all_records()
        st.session_state.df = pd.DataFrame(datos)


        st.write("Tipo de datos en Fecha:", type(df['Fecha'].iloc[0]))

        # Convertir y formatear la columna 'Fecha' primero se convierte a date-time y luego date 
        df["Fecha"] = pd.to_datetime(df["Fecha"], errors='coerce')
        # Verifica si existen fechas no convertidas (NaT)
        if df['Fecha'].isnull().any():
            st.warning("Hay fechas inválidas en el DataFrame.")

    # Solo aplica strftime si hay valores no nulos
        df['Fecha'] = df['Fecha'].apply(lambda x: x.strftime('%d/%m/%Y') if pd.notnull(x) else '')


        #df["Fecha"] = df["Fecha"].dt.strftime('%d/%m/%Y')


        st.session_state.df = df
        st.session_state.worksheet = worksheet  # Guardar la referencia de la hoja en session_state
    else:
        sheet = None  # Ya está cargado en session_state.df

    df = st.session_state.df
    worksheet = st.session_state.worksheet  # Accediendo a worksheet desde session_state
    # Mostrar los registros
    st.dataframe(df.reset_index(drop=True))  # Esto oculta el índice al mostrarlo


   
    # Si hay registros, permitir seleccionar el ID
    if not df.empty:
        st.subheader("Paso 1: Selecciona el ID del registro a editar")

        # Limpiar variables de edición si es necesario
        if "registro_editado" in st.session_state:
            del st.session_state["registro_editado"]

        # Asegurarte que la columna ID sea tipo int
        df["ID"] = df["ID"].astype(int)

        # Ordena por ID para evitar errores
        df = df.sort_values("ID")
        
        
        ids_disponibles = df["ID"].astype(int).sort_values().tolist()
        min_id, max_id = min(ids_disponibles), max(ids_disponibles)

        id_registro = st.number_input(
            "Introduce manualmente el ID que deseas editar:",
            min_value=min_id,
            max_value=max_id,
            step=1,
            key="id_input"
        )

        # Buscar registro por ID
        if id_registro in ids_disponibles:

            # Asegúrate de convertir la columna TASA DE CAMBIO antes de usarla
            df["TASA DE CAMBIO"] = df["TASA DE CAMBIO"].astype(float)

            # Filtrar por ID y resetear índice para evitar desfases
            registro = df[df["ID"] == id_registro].reset_index(drop=True).iloc[0]
            


            st.session_state.registro_editado = registro

            # Asegúrate de convertir la columna TASA DE CAMBIO antes de usarla
            df["TASA DE CAMBIO"] = df["TASA DE CAMBIO"].astype(float)

            st.success(f"ID {id_registro} encontrado. Cargando formulario...")

            # Pasamos al paso 2 (mostramos el formulario editable)
            formulario_edicion(registro, worksheet,df,sheet)

        else:
            st.warning("El ID introducido no está en los registros.")
    else:
        st.warning("No hay registros para editar.")

elif pagina == "Reporte de Ingresos":
    st.title("Reporte de Ingresos")
    submenu = st.sidebar.radio(
        "Opciones de Ingresos",
        ["Por Subcategoria","Por Responsable"])
    
    if submenu == "Por Subcategoria":
     st.subheader("💰 Resumen de Ingresos por subcategoria")
     reporte_ingresos_por_subcategoria()
    elif submenu == "Por Responsable":
     st.subheader("💰 Resumen de Ingresos por Responsable")
     reporte_ingresos_por_responsable() 




elif pagina == "Reporte de Gastos":
    st.title("Reporte de Gastos")
    reporte_de_gastos_por_fecha()


elif pagina == "Bancos":
    st.title("Estado de Cuentas")
    submenu = st.sidebar.radio(
        "Opciones de Bancos",
        ["Saldos Iniciales", "Gestión de Cuentas"])
    
    if submenu == "Saldos Iniciales":
        st.subheader("💰 Registro de Saldos Iniciales")
        # Aquí llamas a la función que maneja los saldos iniciales
        gestionar_saldos()

    elif submenu == "Gestión de Cuentas":
        st.subheader("📑 Gestión de Cuentas Bancarias")
        # Aquí llamas a la función que ya tenías
        spread = obtener_spread()  # conecta a Google Sheets
        gestionar_cuentas(spread)  # pasa el objeto a la función
        
        
        


    


#==============================================================================================================#




    

    

