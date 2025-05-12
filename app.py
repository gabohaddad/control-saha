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



#----------------------------------------------------------------------------
# Obtener la ruta del archivo JSON desde la variable de entorno .env

def autenticacion_google_sheets():

    load_dotenv()
    GOOGLE_APPLICATION_CREDENTIALS = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')

    if GOOGLE_APPLICATION_CREDENTIALS:
        print(f"La ruta de las credenciales es: {GOOGLE_APPLICATION_CREDENTIALS}")
    else:
        print("La variable de entorno 'GOOGLE_APPLICATION_CREDENTIALS' no se ha cargado correctamente.")
    
    if GOOGLE_APPLICATION_CREDENTIALS is None or GOOGLE_APPLICATION_CREDENTIALS.strip() == "":
        raise ValueError("No se encontró la clave en la variable de entorno o está vacía.")

    # Define el alcance de la autenticación

    SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    
    # Cargar las credenciales desde el archivo JSON

    # ESTOS SON LOS CREDEDENCIALES QUE SE GENERARON EN GOOGLE CLOUD PARA ESTE PROYECTO
    credentials = Credentials.from_service_account_file(GOOGLE_APPLICATION_CREDENTIALS,scopes=SCOPES)
    #credentials = Credentials.from_service_account_file("C:/Users/USUARIO/Documents/coastal-range-452621-e4-14db891d7262.json",scopes=SCOPES)
    
    
    # Autenticar y obtener el cliente de Google Sheets
    cliente = gspread.authorize(credentials)
    
    return cliente
   
#-----------------------------------------------------------------------------------------
# --- Función para cargar los datos de Google Sheets en un dataframe---
 
def cargar_datos():
    
 
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
    
    worksheet = cliente.open_by_key(SHEET_ID).sheet1
    # Leer los datos de Google Sheets
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)

    # Verificar si existe la columna "ID"
    if "ID" not in df.columns:
        st.error("No se encontró la columna 'ID' en los datos.")
    
    return pd.DataFrame(data), worksheet

    # Cargar datos solo si no están en session_state
if "df" not in st.session_state or "worksheet" not in st.session_state:
    st.session_state.df, st.session_state.worksheet = cargar_datos()


#----------------------------------------------------------------------------------------
# --- Función para ver registros ---  creacion del data frame para google sheet
# --- Función para ver registros y actualizar df desde Google Sheets ---
def ver_registros():
    # ✅ Limpia estado previo de edición
    st.session_state.pop("edicion_activa", None)

    # ✅ Carga o actualiza los datos desde Google Sheets
    if "df" not in st.session_state or "worksheet" not in st.session_state:
        st.session_state.df, st.session_state.worksheet = cargar_datos()

    # Actualiza los datos desde worksheet (por si ya estaban)
    data_actual = st.session_state.worksheet.get_all_records()
    df_actualizado = pd.DataFrame(data_actual)
    
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
    st.dataframe(st.session_state.df, hide_index=True)

#------------------------------------------------------------------------------
# Inicializar una lista vacía para almacenar los registros
# Inicializar variables en session_state si no existen

if "registros" not in st.session_state:
    st.session_state.registros = []

def resetear_variables ():    
    if "subcategoria_ingreso" not in st.session_state:
        st.session_state.subcategoria_ingreso = ""
    if "subcategoria_gasto_fijo" not in st.session_state:
        st.session_state.subcategoria_gasto_fijo = ""
    if "subcategoria_gasto_variable" not in st.session_state:
        st.session_state.subcategoria_gasto_variable = ""
    if "descripcion" not in st.session_state:
        st.session_state.descripcion = ""
    if "tasa_cambio" not in st.session_state:
        st.session_state.tasa_cambio = "1.0"
# Actualizar el valor de st.session_state.monto antes de la creación del widget
if 'monto' in st.session_state:
    monto = st.session_state.monto
else:
    monto = 0.01  # Valor predeterminado si no está en session_state

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
                                 responsable, descripcion,monto,tipo_pago,tasa_cambio):
    
    # Convertir la fecha a formato datetime si es necesario
    if isinstance(fecha, str):  # Si la fecha viene como string
        fecha = datetime.strptime(fecha, "%d/%m/%Y")
    
    # Leer los datos actuales desde Google Sheets
    data_actual = worksheet.get_all_values()
    edit_id = str(edit_id)

    # Asegurarse de que los datos de Google Sheets tengan suficientes filas
    #num_filas = len(data_actual)

    # Buscar el ID del registro que se quiere editar en Google Sheets
    for i, row in enumerate(data_actual[1:], start=1):  # Comienza desde la fila 2 (para omitir encabezado)
        if row[0] == edit_id:  # Suponiendo que el ID está en la primera columna
            fila_editada = i + 1  # Fila donde se encuentra el registro que se quiere editar
            break
        

    else:
        st.error(f"No se encontró el registro con ID {edit_id}.")
        return

    # Obtener los nuevos valores del DataFrame y asegurarse de que no sean vacíos
    new_values = {
        "FECHA": fecha.strftime("%d/%m/%Y"),
        "CATEGORIA": categoria,
        "SUBCATEGORIA": subcategoria,
        "RESPONSABLE": responsable,
        "DESCRIPCION": descripcion,
        "MONTO":monto,
        "TIPO DE PAGO":tipo_pago,
        "TASA DE CAMBIO": tasa_cambio

    }

             # Actualizar los valores en Google Sheets (empezando desde la columna 2)
    for j, (col_name, new_value) in enumerate(new_values.items(), start=2):
        if data_actual[fila_editada - 1][j - 1] != str(new_value):
            worksheet.update_cell(fila_editada, j, str(new_value))

    # ✅ Refrescar el DataFrame una sola vez al final
    data_actualizada = worksheet.get_all_values()
    df_actualizado = pd.DataFrame(data_actualizada[1:], columns=data_actualizada[0])

    # Actualizar en session_state si se está usando
    st.session_state.df = df_actualizado

    st.rerun()

    # También puedes devolver el df actualizado si lo necesitas fuera
    st.success(f"¡El registro con ID {edit_id} se ha actualizado correctamente!")

    
#=========================================================================================================

# ------------------- Función para obtener el último ID en Google Sheets -------------------
def obtener_ultimo_id(sheet):
    """
    Obtiene el último ID registrado en la primera columna de Google Sheets.
    Si la hoja está vacía, comienza desde 1.
    """
    registros = sheet.col_values(1)  # Obtener todos los valores de la columna A (ID)
    if len(registros) > 1:  # Si hay registros (excluyendo el encabezado)
        try:
            ultimo_id = int(registros[-1])  # Tomar el último ID como entero
            return ultimo_id + 1  # Siguiente ID
        except ValueError:
            return 1  # Si hay un error, empezar en 1
    else:
        return 1  # Si no hay registros, empieza desde 1

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
    for registro in registros:
        registro_con_id = [siguiente_id] + list(registro.values())  # Asegurar que el ID sea la primera columna
        hoja.append_row(registro_con_id)  # Agregar la fila en Google Sheets
        siguiente_id += 1  # Incrementar para el próximo registro
    

#---------------------------------------------------------------------------------------------
# Función para agregar un nuevo registro

# DEFINICION DE VARIABLES PARA NUEVO REGISTRO
def agregar_registro(fecha, categoria, descripcion, monto, tipo_pago, tasa_cambio=None, 
                     subcategoria=None, responsable=None):
        
    # Convertir la fecha a formato "día/mes/año"
    fecha_formateada = fecha.strftime("%d/%m/%Y")  # Fecha convertida a formato adecuado
        
    # Validación de datos
    if not fecha_formateada or not descripcion or not monto or not tipo_pago:
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
        "Tasa de cambio": float(tasa_cambio) if tasa_cambio else 1 # Solo incluir tasa de cambio si es BSF
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
        if key in st.session_state:
            del st.session_state[key]
    st.session_state.limpiar = False
    st.rerun()
#---------------------------------------------------------------------------------
# Funcion para estandarizar columnas de los df

def estandarizar_columnas(df):
    df.columns = [
        unicodedata.normalize('NFKD', col).encode('ascii', 'ignore').decode('utf-8')
        for col in df.columns
    ]
    df.columns = df.columns.str.strip().str.upper()
    return df

#++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# carga un df de las categorias tipo y subcategorias de google sheet

def cargar_subcategorias(sheet):
    data = sheet.worksheet("Subcategorias").get_all_records()
    df_subs = pd.DataFrame(data)
    df_subs = estandarizar_columnas(df_subs)  # Estandarizar columnas
    return df_subs

    

def cargar_responsables(sheet):
    data = sheet.worksheet("Responsables").get_all_records()
    responsables_df = pd.DataFrame(data)
    responsables_df = estandarizar_columnas(responsables_df)  # Estandarizar columnas
    return responsables_df
#-----------------------------------------------------------------------

# Interfaz de usuario SECCION DONDE SE CARGAN LOS DATOS (WIDGETS) (formulario)
# creacion de diccionarios dinamicos, subcategorias, responsables 

def formulario_de_registros(sheet):

    
    df_subs = cargar_subcategorias(sheet)  # Cargar subcategorías

    if st.session_state.get("limpiar", False):
        limpiar_campos()
        return

    fecha = st.date_input("Fecha de la transacción", value=datetime.today().date(), key="fecha")
    fecha_formateada = fecha.strftime("%d/%m/%Y")

    categoria = st.selectbox("Selecciona la categoría", ["", "Ingreso", "Gasto"], key="categoria")
    subcategoria = None
    tipo_gasto = None
    responsable = None

    # carga la lista de responsables del google sheet y crea el diccionario en el df 
    responsables_df = cargar_responsables(sheet)
    
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
                (df_subs["TIPO"] == tipo_gasto)
            ]["SUBCATEGORIA"].unique().tolist()
            
            subcategoria = st.selectbox("Selecciona la subcategoría", ["" ] + subcategorias_disponibles, key="sub_gasto")
            responsable = st.selectbox("¿A quién corresponde el gasto?", [""] + lista_responsables, key="responsable_gasto")

    descripcion = st.text_input("Descripción", value=st.session_state.get("descripcion", ""), key="descripcion")

    if "monto" not in st.session_state:
        st.session_state.monto = 0.0
    monto = st.number_input("Ingrese el monto", step=0.01, format="%.2f", key="monto")

    tipo_pago = st.selectbox("Selecciona el tipo de pago", ["Dólares", "Zelle", "BSF"], key="tipo_pago")
    if tipo_pago == "BSF":
        tasa_cambio = st.number_input("Tasa de cambio", min_value=0.0, format="%.2f")
        if tasa_cambio == 0.0:
            st.warning("⚠️ Para pagos en BSF debes ingresar la tasa de cambio.")
    else:
        tasa_cambio = 1.0
        st.session_state.tasa_cambio = tasa_cambio

    # Aquí puedes colocar el botón para guardar y la lógica adicional...
#--------------------------------------------------------------------------------------
# Botón para agregar el registro

    if st.button("Agregar registro"):

        if tipo_pago == "BSF" and tasa_cambio in [0.0, 1.0]:
            st.warning("❌ No puedes guardar el registro sin ingresar una tasa de cambio.")
            return
                   
        
        if descripcion and monto > 0 :
        
            # Aquí iría la lógica para agregar el registro a la base de datos
         
            agregar_registro(fecha, categoria, descripcion, monto, tipo_pago, tasa_cambio, subcategoria, responsable)
            st.success("Registro agregado correctamente")
            time.sleep(0.5)
     
                # Activar la limpieza de campos
            st.session_state.limpiar = True

        else:
            st.warning("Por favor, completa todos los campos antes de agregar el registro.")  

#-----------------------------------------------------------------------------------------------------
# CREACION DEL REPORTE DE GASTOS POR CATEGORIAS
def mostrar_resumen_ingresos(df, titulo):
    if "SUB-CATEGORIA" in df.columns and "TIPO DE PAGO" in df.columns and "TASA DE CAMBIO" in df.columns and "MONTO" in df.columns:
        st.subheader(titulo)
        
        # Resumen por subcategoría de ingreso
        resumen_subcategorias = df.groupby(["SUB-CATEGORIA", "TIPO DE PAGO"])["MONTO"].sum().reset_index()
        st.dataframe(resumen_subcategorias)
        
        # Sumar los montos por tipo de pago (Dólares, Zelle y BsF por separado)
        total_ingresos = df.groupby("TIPO DE PAGO")["MONTO"].sum().reset_index()

#-------------------------------------------------------------------------
        # Filtrar solo ingresos en BsF
        df_bsf = df[df["TIPO DE PAGO"] == "BSF"].copy()

        # Agregar columna con monto en dólares
        df_bsf["MONTO EN USD"] = df_bsf["MONTO"] / df_bsf["TASA DE CAMBIO"]

        # Seleccionar solo las columnas necesarias
        df_bsf_resumen = df_bsf[["SUB-CATEGORIA", "MONTO", "TASA DE CAMBIO", "MONTO EN USD"]]

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
            
     if "SUB-CATEGORIA" in df.columns and "TIPO DE PAGO" in df.columns and "MONTO" in df.columns:
         st.subheader(titulo)
         resumen = df.groupby(["SUB-CATEGORIA", "TIPO DE PAGO"]) ["MONTO"].sum().reset_index()
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
    #df, _ = cargar_datos()  # Cargamos los datos desde Google Sheets
    df = st.session_state.df

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
        df_filtrado = df_gastos[
            (df_gastos["FECHA"] >= fecha_inicio) & 
            (df_gastos["FECHA"] <= fecha_fin)
        ]

        # Si no hay datos filtrados, mostrar mensaje de advertencia
        if df_filtrado.empty:
            st.warning("⚠️ No hay gastos registrados en el rango seleccionado.")
        else:
            st.success(f"📅 Mostrando datos desde {fecha_inicio} hasta {fecha_fin}")


            # Convertir las fechas a formato día/mes/año solo para mostrar
            df_filtrado["FECHA"] = df_filtrado["FECHA"].dt.strftime("%d/%m/%Y")

            st.dataframe(df_filtrado)

            # Subcategorías para los tipos de gastos
            subcategorias_fijas = ["Alquiler", "Nómina", "Servicios", "Gas", "Piscina", 
                               "Contadora", "Mantenimiento"]
            subcategorias_variables = ["Publicidad", "Comisiones", "Transporte", "Comida","SEMAT","IVA","ISLR","IVSS","FAO","Pensiones","Patente","Otros"]

                    # Reporte de Gasto Fijo (basado en subcategorías)
            df_fijo = df_filtrado[df_filtrado["SUB-CATEGORIA"].isin(subcategorias_fijas)]
            if not df_fijo.empty:
                mostrar_resumen(df_fijo, "Gastos Fijos")
        
                    # Reporte de Gasto Variable (basado en subcategorías)
            df_variable = df_filtrado[df_filtrado["SUB-CATEGORIA"].isin(subcategorias_variables)]
            if not df_variable.empty:
                mostrar_resumen(df_variable, "Gastos Variables")


            # Crear una tabla resumen totalizando ambos (Gastos Fijos + Variables)
            total_fijos = df_fijo.groupby("TIPO DE PAGO")["MONTO"].sum().reset_index()
            total_variables = df_variable.groupby("TIPO DE PAGO")["MONTO"].sum().reset_index()

            # Unir ambos dataframes para mostrar el resumen
            resumen_total = pd.merge(total_fijos, total_variables, on="TIPO DE PAGO", how="outer", suffixes=('_fijos', '_variables'))

            # Rellenar NaN con 0 para evitar errores al mostrar
            resumen_total = resumen_total.fillna(0)

            # Sumar los totales por tipo de pago
            resumen_total["Total"] = resumen_total["MONTO_fijos"] + resumen_total["MONTO_variables"]

            # Mostrar la tabla resumen
            st.subheader("🔹 Resumen Total de Gastos por Tipo de Pago")
            st.dataframe(resumen_total)


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

#+====================================================================================

#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

# Función para mostrar el formulario de edición
def formulario_edicion(registro, worksheet, df,sheet):
    st.subheader("Formulario de Edición")

   # Cargar subcategorías y responsables desde Google Sheets
    subcategorias_df = cargar_subcategorias(sheet)
    responsables_df = cargar_responsables(sheet)

    
    # Convertir a listas simples
    
    subcategoria = subcategorias_df["SUBCATEGORIA"].tolist()
    responsables = responsables_df["RESPONSABLE"].tolist()
   
    # Mostrar los campos con los valores actuales del registro
    try:
        fecha_obj = datetime.strptime(registro["FECHA"], "%d/%m/%Y").date()
    except:
        fecha_obj = datetime.today().date()  # fallback en caso de error

    fecha = st.date_input("Fecha de la transacción", value=fecha_obj, key="fecha")

    
    categoria = st.selectbox("Categoria", ["Ingreso", "Gasto"], index=["Ingreso", "Gasto"].index(registro["CATEGORIA"]))
    

    # Tipo de Gasto (solo si es "Gasto")
   
    if categoria == "Gasto":
        
        subcategoria_actual = registro.get("SUB-CATEGORIA", "")

                
        # Detectar tipo de gasto desde la subcategoría
        tipo_detectado = subcategorias_df.loc[
            subcategorias_df["SUBCATEGORIA"] == subcategoria_actual, "TIPO"
        ].values

        tipo_gasto = tipo_detectado[0] if len(tipo_detectado) > 0 else "Fijo"
        
        # Selectbox para tipo de gasto (ya deducido)
        tipo_gasto = st.selectbox(
            "Tipo de Gasto",
            ["Gasto Fijo", "Gasto Variable"],
            index=["Gasto Fijo", "Gasto Variable"].index(tipo_gasto)
        )

    # Filtrar subcategorías según tipo y categoría
        subcats_filtradas = subcategorias_df[
            (subcategorias_df["CATEGORIA"] == "Gasto") & 
            (subcategorias_df["TIPO"] == tipo_gasto)
        ]
        subcategorias = subcats_filtradas["SUBCATEGORIA"].unique().tolist()

        # Selectbox para subcategoría, con valor actual preseleccionado
        subcategoria = st.selectbox(
            "Subcategoría",
            subcategorias,
            index=subcategorias.index(subcategoria_actual) if subcategoria_actual in subcategorias else 0
        )
    else:
        tipo_gasto = None
        subcategoria = st.selectbox(
            "Subcategoría",
            subcategorias_df[subcategorias_df["CATEGORIA"] == categoria]["SUBCATEGORIA"].unique().tolist(),
            index=0
        )

    # Responsable
    responsables = responsables_df["RESPONSABLE"].tolist()
    responsable = st.selectbox(
        "Responsable",
        responsables,
        index=responsables.index(registro["RESPONSABLE"]) if registro["RESPONSABLE"] in responsables else 0
    )

    # Descripción
    descripcion = st.text_input("Descripción", value=registro["DESCRIPCION"], key="descripcion")

    try:
     monto= float(registro.get("MONTO", 0))
    except:
     monto = 0.0

    monto = st.number_input("Ingrese el monto", value=monto, step=0.01, format="%.2f", key="monto")

    # Si es gasto, el monto debe ser negativo
    if categoria == "Gasto" and monto > 0:
        monto = -monto
    else:
        monto = monto
    
    
    # Tipo de pago
    tipo_pago = st.selectbox("Selecciona el tipo de pago", ["Dólares", "Zelle", "BSF"], 
                             index=["Dólares", "Zelle", "BSF"].index(registro["TIPO DE PAGO"]), 
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
                                         monto, tipo_pago, tasa_cambio)
            st.success("Registro actualizado exitosamente!")
        else:
            st.warning("Por favor, completa todos los campos.")

#====================================================================================================
# BOTON PARA ELIMINAR EL REGISTRO
    st.subheader("Eliminar un registro")

    if not df.empty:  
       id_eliminar = st.selectbox("Selecciona el ID a eliminar:", df["ID"].tolist(), key="select_id_eliminar")
        
       if st.button("❌ Eliminar seleccionado"):
            # Verificar si el ID existe en el DataFrame
            if id_eliminar in df["ID"].values:
                df = df[df["ID"] != id_eliminar]  # Eliminar el registro con ese ID
                df.reset_index(drop=True, inplace=True)  # Resetear índices

                df['ID'] = range(1, len(df) + 1)  # Reasignar IDs comenzando desde 1

                # Actualizar Google Sheets sin dejar espacios vacíos
                worksheet.clear()
                worksheet.update([df.columns.values.tolist()] + df.values.tolist())

                # ✅ Limpia edicion_activa
                if "edicion_activa" in st.session_state:
                    del st.session_state.edicion_activa

                    st.success(f"Registro con ID {id_eliminar} eliminado con éxito.")


                st.rerun()  # Recargar la app
            else:
                st.warning("El ID seleccionado no existe en la base de datos.")
    else:
        st.warning("No hay registros disponibles para editar.")

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
      st.dataframe(df) 

# --- VER REGISTROS (Edición) ---
elif pagina == "Ver Registros":
    st.title("Editar Registro Existente")

    # Cargar y actualizar el DataFrame desde Google Sheets
    ver_registros()  # Esto actualiza st.session_state.df

    df = st.session_state.df
    worksheet = st.session_state.worksheet  # Accediendo a worksheet desde session_state

    # Definir 'sheet' antes de pasarla a formulario_edicion
    cliente = autenticacion_google_sheets()
    sheet = cliente.open("BD DE REGISTROS FINANCIEROS")

    # Si hay registros, permitir seleccionar el ID
    if not df.empty:
        st.subheader("Paso 1: Selecciona el ID del registro a editar")

        # Limpiar variables de edición si es necesario
        if "registro_editado" in st.session_state:
            del st.session_state["registro_editado"]

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

            registro = df[df["ID"] == id_registro].iloc[0]
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




    

    

