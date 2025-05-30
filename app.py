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
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

import os
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
    cuentas_data = sheet.worksheet("Cuentas").col_values(1)[1:]  # Omite la primera fila (encabezado)
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
# Obtener la ruta del archivo JSON desde la variable de entorno .env

def autenticacion_google_sheets():
    # Detectar entorno: si existe la variable de entorno STREAMLIT_SERVER_SOFTWARE, asumimos cloud
    is_streamlit_cloud = "STREAMLIT_SERVER_SOFTWARE" in os.environ
    
    if is_streamlit_cloud:
        # En Streamlit Cloud cargamos las credenciales desde secrets
        # secrets["GOOGLE_SERVICE_ACCOUNT"] debe tener todo el JSON como dict
        service_account_info = st.secrets["GOOGLE_SERVICE_ACCOUNT"]
        credentials = Credentials.from_service_account_info(
            service_account_info,
            scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        )
        print("Autenticado en Streamlit Cloud")
    else:
        # Localmente cargamos dotenv y la ruta al archivo JSON
        load_dotenv()
        ruta_credenciales = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        if ruta_credenciales is None or ruta_credenciales.strip() == "":
            raise ValueError("No se encontró la ruta a las credenciales en la variable de entorno.")
        credentials = Credentials.from_service_account_file(
            ruta_credenciales,
            scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        )
        print("Autenticado localmente con archivo JSON")
    
    cliente = gspread.authorize(credentials)
    return cliente
#-----------------------------------------------------------------------------------------
# --- Función para cargar los datos de Google Sheets en un dataframe---
 
def cargar_datos_principales():
    
 
 # 🔗 Llamar la función para autenticar y obtener el cliente
    cliente = autenticacion_google_sheets()
    # creamos el archivo .env para guardar las claves sensibles que guardan data como google sheet
    # de esta manera si lo subimos Git Hub nadie puede ver la data

 # 📄 Reemplaza con tu Sheet ID obtenido de la URL de Google Sheets
    # Cargar las variables de entorno desde el archivo .env
    

    # Obtener el SHEET_ID desde la variable de entorno
    SHEET_ID = os.getenv('SHEET_ID')

 # 🔍 Acceder a la primera hoja del archivo
    # esta parte es para cargar los datos al programa para trabajar con ellos en las diferentes
    # secciones
    
    archivo = cliente.open_by_key(SHEET_ID)
    
    # Leer los datos de Google Sheets
    worksheet = archivo.sheet1 # ✅ obtener la primera hoja correctamente
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)

    # con esto vamos a guardar la hoja worksheet en session st para usarla en las 
    # otros modulos 
    st.session_state.worksheet = worksheet
    st.session_state.df = df


    # Verificar si existe la columna "ID"
    if "ID" not in df.columns:
        st.error("No se encontró la columna 'ID' en los datos.")
    
    return df, archivo
#-------------------------------------------------------------------------------------
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
def agregar_registro(fecha, categoria, descripcion, monto, tipo_pago, tasa_cambio=None, 
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
        "monto", "tipo_pago", "tasa_cambio"
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
     
    fecha = st.date_input("Fecha de la transacción", value=datetime.today().date(), key="fecha")
    #fecha_formateada = fecha.strftime("%d/%m/%Y")

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

    tipo_pago = st.selectbox("Selecciona el tipo de pago", ["Dólares","BSF"], key="tipo_pago")
    if tipo_pago == "BSF":
        tasa_cambio = st.number_input("Tasa de cambio", min_value=0.0, format="%.2f")
        if tasa_cambio == 0.0:
            st.warning("⚠️ Para pagos en BSF debes ingresar la tasa de cambio.")
    else:
        tasa_cambio = 1.0
        st.session_state.tasa_cambio = tasa_cambio

    cuenta_bancaria = st.selectbox("Cuenta bancaria", [""] + cuentas, key="cuenta_bancaria")
   
#--------------------------------------------------------------------------------------
# Botón para agregar el registro

    if st.button("Agregar registro"):

        if tipo_pago == "BSF" and tasa_cambio in [0.0, 1.0]:
            st.warning("❌ No puedes guardar el registro sin ingresar una tasa de cambio.")
            return
                   
        
        if descripcion and monto > 0 and cuenta_bancaria:

        
            # Aquí iría la lógica para agregar el registro a la base de datos
         
            agregar_registro(fecha, categoria, descripcion, monto, tipo_pago, tasa_cambio, subcategoria, responsable,cuenta_bancaria)
            st.success("Registro agregado correctamente")
            time.sleep(0.5)
     
                # Activar la limpieza de campos
            st.session_state.limpiar = True

        else:
            st.warning("Por favor, completa todos los campos antes de agregar el registro.")  

#-----------------------------------------------------------------------------------------------------
# CREACION DEL REPORTE DE GASTOS POR CATEGORIAS
def mostrar_resumen_ingresos(df, titulo):
    if "SUBCATEGORIA" in df.columns and "TIPO DE PAGO" in df.columns and "TASA DE CAMBIO" in df.columns and "MONTO" in df.columns:
        st.subheader(titulo)
        
        # Resumen por subcategoría de ingreso
        resumen_subcategorias = df.groupby(["SUBCATEGORIA", "TIPO DE PAGO"])["MONTO"].sum().reset_index()
        st.dataframe(resumen_subcategorias)
        
        # Sumar los montos por tipo de pago (Dólares, Zelle y BsF por separado)
        total_ingresos = df.groupby("TIPO DE PAGO")["MONTO"].sum().reset_index()


        # Filtrar solo ingresos en BsF
        df_bsf = df[df["TIPO DE PAGO"] == "BSF"].copy()

        # Agregar columna con monto en dólares
        df_bsf["MONTO EN USD"] = df_bsf["MONTO"] / df_bsf["TASA DE CAMBIO"]

        # Seleccionar solo las columnas necesarias
        df_bsf_resumen = df_bsf[["SUBCATEGORIA", "MONTO", "TASA DE CAMBIO", "MONTO EN USD"]]

        # Calcular el total de BsF convertidos a USD
        total_usd = df_bsf["MONTO EN USD"].sum()

        # Mostrar en Streamlit solo si hay datos en BsF
        if not df_bsf_resumen.empty:
            st.subheader("Ingresos en BsF convertidos a USD")
            st.dataframe(df_bsf_resumen)
        # Agregar el total en USD debajo del DataFrame
        st.markdown(f"##### **Total de BsF en USD: ${total_usd:,.2f}**")
        st.markdown("--------------------------------------------------")
        
        # Mostrar los totales correctamente
        for _, row in total_ingresos.iterrows():
            tipo_pago = row["TIPO DE PAGO"]
            total = row["MONTO"]
            if tipo_pago == "BSF":
                st.metric(f"Total en {tipo_pago}", f"BsF {total:,.2f}")
            else:
                st.metric(f"Total en {tipo_pago}", f"${total:,.2f}")
    else:
        st.error("Las columnas necesarias no están presentes en los datos.")
#----------------------------------------------------------------------------------------------------

# SECCION DE REPORTES

def reporte_ingresos_por_fecha():

    
    # df, _ = cargar_datos()  # Cargamos los datos desde Google Sheets
    df = st.session_state.df
    

    if df.empty:
        st.warning("No hay datos disponibles para generar reportes.")
        return

    # Convertir la columna de fecha a tipo datetime``
    df["FECHA"] = pd.to_datetime(df["FECHA"], format="%d/%m/%Y", errors="coerce")


    # Filtrar solo los ingresos
    df_ingresos = df[df["CATEGORIA"] == "Ingreso"]

    st.subheader("💰 Reporte de Ingresos por Tipo y Subcategoría")
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
        fecha_inicio = pd.to_datetime(fecha_inicio)
        fecha_fin = pd.to_datetime(fecha_fin)

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
    
          # Llamar a la función de resumen por subcategoría de ingresos
            mostrar_resumen_ingresos(df_filtrado_ingresos, "Resumen de Ingresos por Subcategoría")   

    else:
        st.warning("⚠️ Por favor, selecciona un rango de fechas válido.")

#-------------------------------------------------------------------------------------------------------
# CREACION DEL REPORTE DE GASTOS POR CATEGORIAS
def mostrar_resumen(df, titulo):
     
            
     if "SUBCATEGORIA" in df.columns and "TIPO DE PAGO" in df.columns and "MONTO" in df.columns:
         st.subheader(titulo)
         resumen = df.groupby(["SUBCATEGORIA", "TIPO DE PAGO"]) ["MONTO"].sum().reset_index()
         st.dataframe(resumen)
                # 🔹 Sumar los montos por tipo de pago (Dólares, Zelle y BsF por separado)
         total_general = df.groupby("TIPO DE PAGO")["MONTO"].sum().reset_index()

                # 🔹 Mostrar los totales correctamente
         for _, row in total_general.iterrows():
            tipo_pago = row["TIPO DE PAGO"]
            total = row["MONTO"]
            if tipo_pago == "BSF":
                st.metric(f"Total en {tipo_pago}", f"BsF {total:,.2f}")
            else:
                st.metric(f"Total en {tipo_pago}", f"${total:,.2f}")
     else:
            st.error("Las columnas necesarias no están presentes en los datos.")      

#----------------------------------------------------------------------------------------------------
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

            st.dataframe(df_gastos_filtrado)
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


        # Totales
        
        total_general_usd = total_fijos_usd+total_variables_usd
        total_general_bsf = total_fijos_bsf+total_variables_bsf


        # cuadros resumenes

        st.subheader("💰 Subtotales de Gastos Fijos por Tipo de moneda")
        st.dataframe(subtotal_fijos_pago.style.format({"MONTO": "{:,.2f}"}))
        st.markdown(f"**Total Gastos Fijos en US$:  {total_fijos_usd:,.2f}**")
        st.markdown(f"**Total Gastos Fijos en BSF: {total_fijos_bsf:,.2f}**")

        st.markdown("---")

        st.subheader("💸 Subtotales de Gastos Variables por Tipo de moneda")
        st.dataframe(subtotal_variables_pago.style.format({"MONTO": "{:,.2f}"}))
        st.markdown(f"**Total Gastos Variables en US$: {total_variables_usd:,.2f}**")
        st.markdown(f"**Total Gastos Variables en BSF: {total_variables_bsf:,.2f}**")

        st.subheader("💸 Total de gastos por tipo de moneda")
        
        st.markdown(f"**Total Gastos en US$:  {total_general_usd:,.2f}**")
        st.markdown(f"**Total Gastos en BSF:  {total_general_bsf:,.2f}**")

        st.markdown("---")

        st.subheader("👤 Detalle para SAHA-Gastos Fijos")

        # Filtrar solo SAHA
        fijos_saha = df_fijos[df_fijos["RESPONSABLE"] == "SAHA"]
        detalle_fijos = fijos_saha.groupby("TIPO DE PAGO")["MONTO"].sum().reset_index()

        for tipo_pago in detalle_fijos["TIPO DE PAGO"].unique():
            st.markdown(f"**Tipo de Pago: {tipo_pago}**")
            monto = detalle_fijos[detalle_fijos["TIPO DE PAGO"] == tipo_pago]["MONTO"].values[0]
            df_temp = fijos_saha[fijos_saha["TIPO DE PAGO"] == tipo_pago].groupby("RESPONSABLE")["MONTO"].sum().reset_index()
            st.dataframe(df_temp.style.format({"MONTO": "{:,.2f}"}), use_container_width=True)
            st.markdown(f"**Total Gastos Fijos de SAHA con {tipo_pago}: {monto:,.2f}**")

        st.markdown("---")
        st.subheader("👤 Detalle para SAHA - Gastos Variables")

        # Filtrar solo SAHA
        variables_saha = df_variables[df_variables["RESPONSABLE"] == "SAHA"]
        detalle_variables = variables_saha.groupby("TIPO DE PAGO")["MONTO"].sum().reset_index()

        for tipo_pago in detalle_variables["TIPO DE PAGO"].unique():
            st.markdown(f"**Tipo de Pago: {tipo_pago}**")
            monto = detalle_variables[detalle_variables["TIPO DE PAGO"] == tipo_pago]["MONTO"].values[0]
            df_temp = variables_saha[variables_saha["TIPO DE PAGO"] == tipo_pago].groupby("RESPONSABLE")["MONTO"].sum().reset_index()
            st.dataframe(df_temp.style.format({"MONTO": "{:,.2f}"}), use_container_width=True)
            st.markdown(f"**Total Gastos Variables de SAHA con {tipo_pago}: {monto:,.2f}**")

        st.subheader("📊 Totales Generales de SAHA por Tipo de Gasto y Tipo de Pago")

        # Totales por tipo de gasto y tipo de pago
        total_saha_fijos = fijos_saha.groupby("TIPO DE PAGO")["MONTO"].sum().reset_index()
        total_saha_fijos["TIPO DE GASTO"] = "Gasto Fijo"

        total_saha_variables = variables_saha.groupby("TIPO DE PAGO")["MONTO"].sum().reset_index()
        total_saha_variables["TIPO DE GASTO"] = "Gasto Variable"

        # Combinar ambos
        total_saha_completo = pd.concat([total_saha_fijos, total_saha_variables])
        total_saha_completo = total_saha_completo[["TIPO DE GASTO", "TIPO DE PAGO", "MONTO"]]
        total_saha_completo = total_saha_completo.sort_values(by=["TIPO DE GASTO", "TIPO DE PAGO"])

        st.dataframe(total_saha_completo.style.format({"MONTO": "{:,.2f}"}), use_container_width=True)



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

    #st.write("Columnas del DataFrame:")
    #st.write(df.columns.tolist())

    fecha_raw = registro["FECHA"]

    try:
        # Intenta con formato dia/mes/año
        fecha_obj = datetime.strptime(fecha_raw, "%d/%m/%Y").date()
    except:
        try:
            # Intenta con formato año-mes-día si falla el anterior
            fecha_obj = datetime.strptime(fecha_raw, "%Y-%m-%d").date()
        except:
            # Si todo falla, usa la fecha de hoy
            fecha_obj = date.today()
        
    fecha = st.date_input("Fecha de la transacción", value=fecha_obj, key="fecha")
    

    
    categoria = st.selectbox("Categoria", ["Ingreso", "Gasto"], index=["Ingreso", "Gasto"].index(registro["CATEGORIA"]))
    
    df_subs = st.session_state.df_subs  # ✅ DataFrame completo con subcategorías, tipos y categorías
    
    # Tipo de Gasto (solo si es "Gasto")
   
    if categoria == "Gasto":
        
        subcategoria_actual = registro.get("SUB-CATEGORIA", "")

                
        # Detectar tipo de gasto desde la subcategoría
        # Filtrar solo subcategorías de gastos antes de buscar tipo
        tipo_detectado = df_subs[
            (df_subs["CATEGORIA"] == "Gasto") & 
            (df_subs["SUBCATEGORIA"] == subcategoria_actual)
        ]["TIPO"].values

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
            (df_subs["TIPO"] == tipo_gasto)
        ]
        subcats_lista = subcats_filtradas["SUBCATEGORIA"].unique().tolist()

        # Selectbox para subcategoría, con valor actual preseleccionado
        subcategoria = st.selectbox(
            "Subcategoría",
            subcats_lista,
            index=subcats_lista.index(subcategoria_actual) if subcategoria_actual in subcats_lista else 0
         )
    else:
        tipo_gasto = None
        subcats_ingreso = df_subs[df_subs["CATEGORIA"] == "Ingreso"]["SUBCATEGORIA"].unique().tolist()
        subcategoria_actual = registro.get("SUB-CATEGORIA", "")
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
    tipo_pago = st.selectbox("Selecciona el tipo de pago", ["Dólares", "Zelle", "BSF"], 
                             index=["Dólares","BSF"].index(registro["TIPO DE PAGO"]), 
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


# ESTA SECCION ES PARA CREAR EL MENU DE SELECCION ENTRE HOJA DE FORMULARIO Y REGISTROS SIDEBAR

st.sidebar.title("Navegación")
pagina = st.sidebar.radio("Selecciona una página", ["Formulario de Registro", "Ver Registros","Reporte de Ingresos","Reporte de Gastos"], key="pagina_radio")


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
    st.title("Reporte de Ingresos por Tipo de Pago")
    reporte_ingresos_por_fecha()

else: 
    pagina == "Reporte de Gastos"
    st.title("Reporte de Gastos por Tipo de Pago")
    reporte_de_gastos_por_fecha()


#==============================================================================================================#




    

    

