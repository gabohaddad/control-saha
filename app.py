#IMPORTAR LOS DICCIONARIOS DE LIBRERIAS PARA QUE SE CARGUEN AL PROGRAMA

import streamlit as st
import pandas as pd
from datetime import datetime
import time  # Importar el módulo time
import numpy as np

#from google_sheets import obtener_registros
from google_sheets import cargar_registros_a_google_sheets
import gspread
from google.oauth2.service_account import Credentials


#----------------------------------------------------------------------------
def autenticacion_google_sheets():
    # Define el alcance de la autenticación
    alcance = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    
    # Cargar las credenciales
    credenciales = Credentials.from_service_account_file(
        'C:/Users/USUARIO/Documents/Proyecto python finanzas personales/coastal-range-452621-e4-14db891d7262.json',  # Ruta al archivo JSON
        scopes=alcance
    )
    
    # Autenticar y obtener el cliente de Google Sheets
    cliente = gspread.authorize(credenciales)
    
    return cliente

#-----------------------------------------------------------------------------------------
# --- Función para cargar los datos de Google Sheets en un dataframe---
def cargar_datos():
 
 # 🔗 Llamar la función para autenticar y obtener el cliente
    cliente = autenticacion_google_sheets()

 # 📄 Reemplaza con tu Sheet ID obtenido de la URL de Google Sheets
    SHEET_ID = "1bbzGDZxsppCplXh7A1OEOAH1rVMXbk6sfCEYkNVrMoQ"

 # 🔍 Acceder a la primera hoja del archivo
    worksheet = cliente.open_by_key(SHEET_ID).sheet1
    # Leer los datos de Google Sheets
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)

    # Verificar si existe la columna "ID"
    if "ID" not in df.columns:
        st.error("No se encontró la columna 'ID' en los datos.")
    
    return pd.DataFrame(data), worksheet

#----------------------------------------------------------------------------------------
# --- Función para ver registros ---  creacion del data frame para google sheet

# 📥 Cargar datos de Google Sheets en un DataFrame aca se traen los registros de la hoja de calculo
def ver_registros():
    st.title("Registros de Transacciones")
    
    # Cargar los datos de Google Sheets
    df, worksheet = cargar_datos()
#--------------------
    # Guardar los datos en st.session_state si no están ya almacenados
    if "df" not in st.session_state:
        st.session_state.df = df
        st.session_state.worksheet = worksheet

    # Verifica si "Monto" está en df antes de hacer cambios
    if "Monto" in st.session_state.df.columns:
        # Reemplazar comas por puntos y convertir a float
        st.session_state.df["Monto"] = st.session_state.df["Monto"].astype(str).str.replace(",", ".").astype(float) 

   
    # Mostrar la tabla sin índice en modo solo lectura
    st.dataframe(df, hide_index=True)

    
#----------------------------------------------------------------------------------------

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

    
#------------------------------------------------------------------------------------------


# ESTE BLOQUE ES LA INTERACCION ENTRE LA LISTA DE GOOGLE SHEET QUE VIENE A LA PANTALLA PARA EDITAR Y LA HOJA DE CALCULO 
# Suponiendo que 'edited_df' es el DataFrame con los datos editados
# Y 'worksheet' es el objeto de la hoja de Google Sheets ACA SE VAN REGISTRA LOS DATOS EDITADOS DE LA PAGINA
# VER REGISTROS

def actualizar_datos_modificados(worksheet,df,edit_id):
    pass
    # Leer los datos actuales desde Google Sheets
    data_actual = worksheet.get_all_values()

# Asegurarse de que los datos de Google Sheets tengan suficientes filas
    num_filas = len(data_actual)
     

    for i, row in df.iterrows():  # Iterar sobre las filas del DataFrame
        for j, col_name in enumerate(df.columns):
            new_value = row[col_name]


            if col_name == "TASA DE CAMBIO" and (data_actual[i + 1][j] == "" or data_actual[i + 1][j] is None):
                    st.write(f"La columna 'TASA DE CAMBIO' está vacía en la fila {i + 2}. Se asignará 1.")
                    new_value = 1  # Asignamos el valor por defecto
            else:
                    new_value = row[col_name]  # Usamos el valor existente

            if i + 1 < num_filas:  # Verificar que i + 1 esté dentro del rango
                if data_actual[i + 1][j] != str(new_value):  # Compara con los valores existentes
                    worksheet.update_cell(i + 2, j + 1, str(new_value))  # Actualizar la celda en la hoja de Google Sheets
            else:
                st.error(f"Índice {i + 1} está fuera del rango de filas de Google Sheets")
                return

    # Mostrar mensaje de éxito al usuario después de la actualización
    st.success(f"¡El registro con ID {edit_id} se ha actualizado correctamente en Google Sheets!")
    
    
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

# DEFINICION DE VARIABLES PARA NUEVO REGISTRO
def agregar_registro(fecha, categoria, descripcion, monto, tipo_pago, tasa_cambio=None, 
                     subcategoria=None, responsable=None):
        
    # Validación de datos
    if not fecha or not descripcion or not monto or not tipo_pago:
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


    # Si la validación pasa, agregar el registro a la tabla resumen en streamlit
    # estos son los datos que pasan a la tabla de st
    registro = {
        "Fecha": fecha.strftime("%Y-%m-%d"),  # ✅ Convertir fecha a cadena se necesita para google sheet
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
        #st.session_state.registro_a_editar["DESCRIPCION"] = ""
        
        #limpiar_campos()
        st.rerun()

    except Exception as e:
        st.error(f"Hubo un problema al guardar el registro en Google Sheets: {e}")

#===================================================================================================
# Interfaz de usuario SECCION DONDE SE CARGAN LOS DATOS (WIDGETS) (formulario)

def formulario_de_registro():


    # Ingreso de datos
    fecha = st.date_input("Fecha de la transacción", value=datetime.today().date(), key="fecha")
    categoria = st.selectbox("Selecciona la categoría", ["Ingreso", "Gasto"], key="categoria")

    # Subcategorías para ingresos 
    subcategorias_ingreso = ["","Ventas Saha", "Ventas Netlink", "Alquiler", "Aporte de Capital",
     
                                    "Otros Ingresos"]
    
    # Subcategorías para gastos
    subcategorias_gasto_fijo = ["","Alquiler", "Nómina", "Servicios", "Gas", "Piscina", "Contadora","Mantenimiento"]
    subcategorias_gasto_variable = ["","Publicidad", "Comisiones", "Transporte", "Comida","SEMAT","IVA","ISLR","IVSS","FAO","Pensiones","Patente","Otros"]

    subcategoria = None
    responsable = None

    if categoria == "Gasto":
        subcategoria_tipo = st.selectbox("Selecciona el tipo de gasto", ["","Gasto fijo", "Gasto variable"], key="subcategoria_tipo")
        
        if subcategoria_tipo == "Gasto fijo":
            subcategoria = st.selectbox("Selecciona la subcategoría de gasto fijo", subcategorias_gasto_fijo, key="subcategoria_fijo")
        elif subcategoria_tipo == "Gasto variable":
            subcategoria = st.selectbox("Selecciona la subcategoría de gasto variable", subcategorias_gasto_variable, key="subcategoria_variable")
        
        # Selección del responsable
        responsable = st.selectbox("¿A quién corresponde el gasto?", ["","SAHA", "AMINE", "Gabriel", "NETLINK"], key="responsable")

    elif categoria == "Ingreso":
        subcategoria = st.selectbox("Selecciona la subcategoría de ingreso", 
                                    subcategorias_ingreso,
                                    index=0, key="subcategoria_ingreso")
        
        responsable = st.selectbox("¿A quién corresponde el ingreso?", ["","SAHA", "AMINE", "Gabriel"], key="responsable_ingreso")

    descripcion = st.text_input("Descripción", value=st.session_state.get("descripcion", ""), key="descripcion")

    # Si no existe un valor inicial para 'monto', lo establecemos en 0
    if "monto" not in st.session_state:
        st.session_state.monto = 0.0

    monto = st.number_input("Ingrese el monto",  step=0.01, format="%.2f", key="monto")
    

    # Opciones de pago
    tipo_pago = st.selectbox("Selecciona el tipo de pago", ["Dólares", "Zelle", "BSF"], key="tipo_pago")

        
    # Si el pago es en BSF, solicitar la tasa de cambio
    tasa_cambio = 1  # Valor predeterminado
    if tipo_pago == "BSF":
        tasa_cambio = st.number_input("Por favor ingrese la tasa de cambio:", 
                                      min_value=0.01, step=0.01, 
                                      key="tasa_cambio")
    else:
        # Si no es en BSF, asignamos 1 y lo guardamos en session_state
        st.session_state.tasa_cambio = tasa_cambio  # Asegurar que session_state refleje este valor

 #-------------------------------------------------------------------------------------------   
 # Botón para agregar el registro

    if st.button("Agregar registro"):
                
        if descripcion and monto > 0 :
        #or subcategorias_ingreso != "" or subcategorias_gasto_fijo != "" 
            #or subcategorias_gasto_variable != "" or responsable != ""):  # Validar que los campos no estén vacíos
        
        # Aquí iría la lógica para agregar el registro a la base de datos
         
         agregar_registro(fecha, categoria, descripcion, monto, tipo_pago, tasa_cambio, subcategoria, responsable)
         st.success("Registro agregado correctamente")
         time.sleep(0.5)

        # Limpiar los campos después de agregar el registro
               
        else:
          st.warning("Por favor, completa todos los campos antes de agregar el registro.")    

#------------------------------------------------------------------------------------- 
#ESTE MODULO ES EL FORMATO QUE APARECE DEBAJO DEL DATA FRAME DE GOOGLE SHEET PARA REALIZAR LA EDICION DE 
# LOS CAMPOS DEL REGISTRO SELECCIONADO

    # Función para editar un registro específico
def edicion_de_registro(id_registro):
    df, worksheet = cargar_datos()

    if df.empty:
        st.warning("No hay registros disponibles para editar.")
        return

    df["ID"] = df["ID"].astype(int)  # Asegurar que los IDs sean enteros
    min_id, max_id = df["ID"].min(), df["ID"].max()
    
    st.write("Número total de registros en el DataFrame:", len(df)) 

    
# Verificamos si el ID está en el rango
    if id_registro < min_id or id_registro > max_id:
        st.error("El ID seleccionado no existe.")
        return
    
    # UNA VEZ SELECCIONADO EL ID Y VERIFICADO QUE EXISTE A CONTINUACION SE DESARROLLA OTRO
    # FORMULARIO
    # El df loc selecoiona todos los datos de ese registro y rellena los campos
    edit_index = df[df["ID"] == id_registro].index[0]
    registro_a_editar = df.loc[edit_index]

    

    fecha = st.date_input("Fecha de la transacción", value=pd.to_datetime(registro_a_editar["FECHA"]).date())
#----------------------------------------------------------------------------------------
# Esta seccion impide que se cambie de ingreso a gasto o viceversa para editar
# da un warning de eliminar el registro
    if "edicion_activa" not in st.session_state:
        st.session_state.edicion_activa = registro_a_editar["CATEGORIA"]  # Guarda la categoría original

    categoria = st.selectbox("Selecciona la categoría", ["Ingreso", "Gasto"], index=["Ingreso", "Gasto"].index(registro_a_editar["CATEGORIA"]))
    
# Si el usuario intenta cambiar de Ingreso a Gasto o viceversa
    if st.session_state.edicion_activa != categoria:
        st.warning("No puedes cambiar de Ingreso a Gasto o viceversa. Si necesitas corregirlo, elimina este registro y crea uno nuevo.")
        st.stop()  # Detiene la ejecución del formulario
#-----------------------------------------------------------------------------------
    subcategorias = {
        "Ingreso": ["","Ventas Saha", "Ventas Netlink", "Alquiler", "Aporte de Capital", "Otros Ingresos"]}

    subcategorias_gasto_fijo ={
        "Gasto fijo": ["","Alquiler", "Nómina", "Servicios", "Gas", "Piscina", "Contadora", "Mantenimiento"]}

    subcategorias_gasto_variable={
        "Gasto variable": ["","Publicidad", "Comisiones", "Transporte","Comida","SEMAT","IVA","ISLR","IVSS","FAO","Pensiones","Patente","Otros"]
    }

    if categoria == "Ingreso":
        monto = max(0.01, float(registro_a_editar["MONTO"]))
        #monto = st.number_input("Monto", min_value=0.01, step=0.01, value=monto)
        subcategoria = st.selectbox("Selecciona la subcategoría de ingreso", subcategorias["Ingreso"], index=subcategorias["Ingreso"].index(registro_a_editar["SUB-CATEGORIA"]))
        responsable = st.selectbox("¿A quién corresponde el ingreso?", ["SAHA", "AMINE", "Gabriel"], index=["SAHA", "AMINE", "Gabriel"].index(registro_a_editar["RESPONSABLE"]))
    
    else:
        subcategoria_tipo = st.selectbox("Selecciona el tipo de gasto", ["Gasto fijo", "Gasto variable"])
        if subcategoria_tipo == "Gasto fijo": 

             subcategoria = st.selectbox(f"Selecciona la subcategoría de {subcategoria_tipo}", subcategorias_gasto_fijo["Gasto fijo"], index=subcategorias_gasto_fijo["Gasto fijo"].index(registro_a_editar["SUB-CATEGORIA"]))
                         
        elif subcategoria_tipo == "Gasto variable":
             subcategoria = st.selectbox(f"Selecciona la subcategoría de {subcategoria_tipo}", subcategorias_gasto_variable["Gasto variable"], index=subcategorias_gasto_variable["Gasto variable"].index(registro_a_editar["SUB-CATEGORIA"]))
             

        responsable = st.selectbox("¿A quién corresponde el gasto?", ["SAHA", "AMINE", "Gabriel", "NETLINK"], index=["SAHA", "AMINE", "Gabriel", "NETLINK"].index(registro_a_editar["RESPONSABLE"]))
        
        monto = min(-0.01, float(registro_a_editar["MONTO"]))
        #monto = st.number_input("Monto", min_value=-1000000.0, max_value=-0.01, step=0.01, value=monto)
    
    
    descripcion = st.text_input("Descripción de la transacción", value=registro_a_editar["DESCRIPCION"])
    monto = st.number_input("Monto", min_value=0.01, step=0.01, value=monto)
    tipo_pago = st.selectbox("Selecciona el tipo de pago", ["Dólares", "Zelle", "BSF", "BSF Transfer"], index=["Dólares", "Zelle", "BSF", "BSF Transfer"].index(registro_a_editar["TIPO DE PAGO"]))
    tasa_cambio = st.text_input("Tasa de cambio del día (si aplica)", value=registro_a_editar["TASA DE CAMBIO"] if tipo_pago == "BSF" else "")
   #
   # ESTE BOTON YA ME ESTA ACTUALIZANDO LA DATA EN EL DATA FRAME Y EN GOOGLE SHEET YA QUE DA LA INSTRUCCION DE
   # IR A ACTUALIZAR DATOS MODIFICADOS
    if st.button("Actualizar registro"):
        df.at[edit_index, "FECHA"] = fecha
        df.at[edit_index, "CATEGORIA"] = categoria
        df.at[edit_index, "DESCRIPCION"] = descripcion
        df.at[edit_index, "MONTO"] = monto
        df.at[edit_index, "SUB-CATEGORIA"] = subcategoria
        df.at[edit_index, "RESPONSABLE"] = responsable
        df.at[edit_index, "TIPO DE PAGO"] = tipo_pago
        if tipo_pago == "BSF":
            df.at[edit_index, "TASA DE CAMBIO"] = tasa_cambio
        
        actualizar_datos_modificados(worksheet, df, id_registro)


# Limpiar los campos después de actualizar
        st.session_state.descripcion = ""  # Limpiar descripción
        st.session_state.categoria_index = 0  # Limpiar categoría
        st.session_state.subcategoria_index = 0  # Limpiar subcategoría
        st.session_state.monto = 0.0  # Limpiar monto
        st.session_state.tasa_de_cambio = ""  # Limpiar tasa de cambio

        # Recargar la página para limpiar los campos
        st.rerun()
             
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
        st.success("esta s una prueba")

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
    df, _ = cargar_datos()  # Cargamos los datos desde Google Sheets

    if df.empty:
        st.warning("No hay datos disponibles para generar reportes.")
        return

    # Convertir la columna de fecha a tipo datetime``
    df["FECHA"] = pd.to_datetime(df["FECHA"], errors="coerce").dt.date

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

        # Filtrar ingresos dentro del rango de fechas
        df_filtrado_ingresos = df_ingresos[
            (df_ingresos["FECHA"] >= fecha_inicio) & 
            (df_ingresos["FECHA"] <= fecha_fin)
        ]

        if df_filtrado_ingresos.empty:
            st.warning("⚠️ No se encontraron ingresos en este rango de fechas.")
        else:
            st.success(f"📅 Mostrando datos desde {fecha_inicio} hasta {fecha_fin}")
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
    df, _ = cargar_datos()  # Cargamos los datos desde Google Sheets

    if df.empty:
        st.warning("No hay datos disponibles para generar reportes.")
        return
    
    
    # Convertir la columna de fecha a tipo datetime
    df["FECHA"] = pd.to_datetime(df["FECHA"], errors="coerce").dt.date

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

       
 #---------------------------------------------------------------------------------
  
       
      
           
                
                
        









        
#====================================================================================================

# ESTA SECCION ES PARA CREAR EL MENU DE SELECCION ENTRE HOJA DE FORMULARIO Y REGISTROS

st.sidebar.title("Navegación")
pagina = st.sidebar.radio("Selecciona una página", ["Formulario de Registro", "Ver Registros","Reporte de Ingresos","Reporte de Gastos"], key="pagina_radio")


# --- Control de flujo según la selección de la barra lateral ---
if pagina == "Formulario de Registro":

# 🔹 Título debe ir antes del formulario
    st.title("Control de Ingresos y Gastos")
    formulario_de_registro()  # Llamamos a la función que maneja la lógica del formulario

# ACA SE CREA LA TABLA CON LOS REGISTROS INTRODUCIDOS EN STREAMLIT (TABLA RESUMEN)
# Mostrar los registros guardados (solo si existen)
    if st.session_state.registros:
      df = pd.DataFrame(st.session_state.registros)
      st.subheader("Registros de transacciones")
      st.dataframe(df) 

elif pagina == "Ver Registros":
    # 🔹 Cargar los registros desde Google Sheets correctamente
    df, worksheet = cargar_datos()  # Asegúrate de que esta función esté bien definida

    st.title("Edición de Registro")
    ver_registros()  # Llamamos a la función que muestra los registros desde Google Sheets

  
# Verificar si existen registros en Google Sheets o DataFrame
    if not df.empty:
        st.subheader("Selecciona un registro a editar")

        # Selección del ID para la edición a través de un selectbox
        id_registro = st.selectbox("Selecciona el ID a editar:", df["ID"].tolist(), key="select_id_editar")

        # Si se selecciona un ID válido, llamamos a la función de edición
        if id_registro:
            edicion_de_registro(id_registro)
    
 #---------------------------------------------------------------------------------------------------
# BOTON PARA ELIMINAR EL REGISTRO
        st.subheader("Eliminar un registro")
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

                st.success(f"Registro con ID {id_eliminar} eliminado con éxito.")


                st.rerun()  # Recargar la app
            else:
                st.warning("El ID seleccionado no existe en la base de datos.")
    else:
        st.warning("No hay registros disponibles para editar.")


elif pagina == "Reporte de Ingresos":
    st.title("Reporte de Ingresos por Tipo de Pago")
    reporte_ingresos_por_fecha()


elif pagina == "Reporte de Gastos":
    st.title ("Reporte de Gastos")
    reporte_de_gastos_por_fecha()

#==============================================================================================================#




    

    

