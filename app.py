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
#------------------------------------------------------------------------------------------
# 🔗 Llamar la función para autenticar y obtener el cliente
cliente = autenticacion_google_sheets()

# 📄 Reemplaza con tu Sheet ID obtenido de la URL de Google Sheets
SHEET_ID = "1bbzGDZxsppCplXh7A1OEOAH1rVMXbk6sfCEYkNVrMoQ"

# 🔍 Acceder a la primera hoja del archivo
worksheet = cliente.open_by_key(SHEET_ID).sheet1

# 📥 Cargar datos de Google Sheets en un DataFrame
def cargar_datos():
    data = worksheet.get_all_records()
    return pd.DataFrame(data)

df = cargar_datos()

# 📋 Mostrar tabla editable en Streamlit
edited_df = st.data_editor(df, num_rows="dynamic")
#----------------------------------------------------------------------------------------






# Suponiendo que 'edited_df' es el DataFrame con los datos editados
# Y 'worksheet' es el objeto de la hoja de Google Sheets

def actualizar_datos_modificados(worksheet, edited_df):
    # Leer los datos actuales desde Google Sheets
    data_actual = worksheet.get_all_values()

    # Comparar los datos y encontrar las celdas modificadas
    rows_to_update = []
    for i, row in enumerate(edited_df.values.tolist()):
        for j, new_value in enumerate(row):
            # Si el valor en la hoja de Google Sheets es diferente del valor en 'edited_df', se actualizará
            if data_actual[i + 1][j] != str(new_value):  # i + 1 porque los datos de Google Sheets empiezan en la fila 2
                rows_to_update.append((i + 2, j + 1, new_value))  # Guardar la fila y columna para actualizar

    # Actualizar las celdas modificadas
    for row in rows_to_update:
        row_index, col_index, new_value = row
        worksheet.update_cell(row_index, col_index, new_value)

    st.success(f"Se han actualizado {len(rows_to_update)} celdas en Google Sheets.")


# Botón de actualización en Streamlit
if st.button("Actualizar datos en Google Sheets"):
    actualizar_datos_modificados(worksheet, edited_df)









# Detectar cambios
#if st.button("Guardar cambios"):
    # Elimina los NaN en el DataFrame
    #data_actualizado = [[cell if not (isinstance(cell, float) and np.isnan(cell)) else "" for cell in row] for row in data_actualizado]

    # Convierte el DataFrame a lista de listas
    #data_actualizado = [edited_df.columns.values.tolist()] + edited_df.values.tolist()

    # Determina el rango que se va a actualizar (A1 hasta la última celda de datos)
    #range_ = f"A1:{chr(65 + len(edited_df.columns))}{len(edited_df)}"

    # Actualiza el rango de la hoja sin borrar los datos previos
    #worksheet.update(range_, data_actualizado)

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
    
    st.success("Registros agregados correctamente a Google Sheets con ID consecutivo.")

#--------------------------------------------------------------------------------------------------------------

# Inicializar una lista vacía para almacenar los registros
# Inicializar variables en session_state si no existen
if "registros" not in st.session_state:
    st.session_state.registros = []
if "descripcion" not in st.session_state:
    st.session_state.descripcion = ""
if "monto" not in st.session_state:
    st.session_state.monto = 0.0  # Asegurar que es float
if "tasa_cambio" not in st.session_state:
    st.session_state.tasa_cambio = "1.0"
#---------------------------------------------------------------------------------------
# Actualizar el valor de st.session_state.monto antes de la creación del widget
if 'monto' in st.session_state:
    monto = st.session_state.monto
else:
    monto = 0.01  # Valor predeterminado si no está en session_state
#-------------------------------------------------------------------------------------------------
# DEFINIR VARIABLE ELIMINAR REGISTRO
# Función para eliminar un registro
def eliminar_registro(index):
    if 0 <= index < len(st.session_state.registros):
        del st.session_state.registros[index]
        st.success("Registro eliminado con éxito.")
        #st.rerun()
#----------------------------------------------------------------------------------------------
# Función para agregar un nuevo registro
# DEFINICION DE VARIABLES PARA NUEVO REGISTRO

if "registros" not in st.session_state:
        st.session_state.registros = []  # Asegurarse de que la lista esté inicializada


def agregar_registro(fecha, categoria, descripcion, monto, tipo_pago, tasa_cambio=None, subcategoria=None, responsable=None):
    
    
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
    
    if (tipo_pago == "BSF" or tipo_pago == "BSF Transfer") and not tasa_cambio:
        st.warning("Por favor, ingrese la tasa de cambio si paga en BSF.")
        return

    # Validar la tasa de cambio
    if (tipo_pago == "BSF" or tipo_pago == "BSF Transfer") and tasa_cambio:
        try: 
            tasa_cambio = float(tasa_cambio)
            if tasa_cambio <= 0:
                st.warning("La tasa de cambio debe ser un número positivo.")
                return
        except ValueError:
            st.warning("La tasa de cambio debe ser un número válido.")
            return

    # Si la validación pasa, agregar el registro a la tabla resumen en streamlit
    registro = {
        "Fecha": fecha.strftime("%Y-%m-%d"),  # ✅ Convertir fecha a cadena se necesita para google sheet
        "Categoría": categoria,
        "Subcategoría": subcategoria if subcategoria else "No especificado",  # Valor predeterminado si es None
        "Responsable": responsable if responsable else "No especificado",  # Valor predeterminado si es None
        "Descripción": descripcion,
        "Monto": monto,
        "Tipo de pago": tipo_pago,
        "Tasa de cambio": tasa_cambio if tipo_pago == "BSF" or tipo_pago == "BSF Transfer" else None
    }

    
# Agregar el registro a la lista
    st.session_state.registros.append(registro)

# Intentar guardar en Google Sheets
    try:
        cargar_registros_a_google_sheets([registro], "BD DE REGISTROS FINANCIEROS")
        st.success("¡Registro agregado exitosamente!")
        
        # Limpiar los campos después de agregar el registro
        limpiar_campos()  # Limpiar los campos del formulario

    except Exception as e:
        st.error(f"Hubo un problema al guardar el registro en Google Sheets: {e}")


 # Función para limpiar los campos después de agregar un registro
def limpiar_campos():
    
    st.session_state["descripcion"] = ""
    st.session_state["monto"] = 0.0
    st.session_state["tasa_cambio"] = 0.0       



#---------------------------------------------------------------------------------------------------
# Agregar opción de EDITAR

# EN ESTA SECCION NOS ASEGURAMOS DE QUE EL NUMERO DE RESISTRO EXISTA Y ESTE DENTRO DE LA LISTA
# QUE SE HA CREADO, LUEGO SE DEFINEN LAS VARIABLES PARA ESPECIFICAR QUE EL MONTO DEBE SER NEGATIVO

def editar_registro(index, fecha, categoria, descripcion, monto, tipo_pago, tasa_cambio, subcategoria, responsable):
    # Si la categoría es "Gasto", hacer el monto negativo
    
        
    if categoria == "Gasto" and monto >0:
        monto = -abs(monto) # Asegura que el monto siempre sea negativo para gastos
         
        # Aquí podrías ajustar el monto si es necesario
        monto = abs(monto)  # Esto asegura que el monto sea positivo
    elif categoria == "Ingreso" and monto < 0:
          monto = abs(monto)
 
    
    # Validación antes de actualizar el registro
    if categoria == "Ingreso" and monto <= 0:
        st.warning("El monto debe ser un número positivo para ingresos.")
        return
    elif categoria == "Gasto" and monto >= 0:
        st.warning("El monto debe ser un número negativo para gastos.")
        return

    # Validar tasa de cambio si el pago es en BSF
    if tipo_pago == "BSF" and tasa_cambio:
        try:
            tasa_cambio = float(tasa_cambio)
            if tasa_cambio <= 0:
                st.warning("La tasa de cambio debe ser un número positivo.")
                return
        except ValueError:
            st.warning("La tasa de cambio debe ser un número válido.")
            return

    st.session_state.registros[index] = {
        "Fecha": fecha,
        "Categoría": categoria,
        "Subcategoría": subcategoria if subcategoria else "No especificado",
        "Responsable": responsable if responsable else "No especificado",
        "Descripción": descripcion,
        "Monto": monto,
        "Tipo de pago": tipo_pago,
        "Tasa de cambio": tasa_cambio if tipo_pago == "BSF" else None
    }

  
    st.success("Registro editado con éxito!")

 # Limpiar los campos del formulario, pero sin vaciar la lista de la tabla
    limpiar_campos()     
   
 # Esperar 0.5 segundos para que el usuario vea el mensaje
    time.sleep(0.5)

    # **Forzar la recarga de la app para reflejar los cambios de inmediato**
    st.rerun()
    
#------------------------------------------------------------------------------------
# Interfaz de usuario SECCION DONDE SE CARGAN LOS DATOS (WIDGETS) (formulario)
st.title("Control de Ingresos y Gastos")



# Ingreso de datos
fecha = st.date_input("Fecha de la transacción", value=datetime.today().date(), key="fecha")
categoria = st.selectbox("Selecciona la categoría", ["Ingreso", "Gasto"], key="categoria")


# Subcategorías para gastos
subcategorias_gasto_fijo = ["Alquiler", "Nómina", "Servicios", "Gas", "Piscina", "Contadora", "SEMAT", "SENIAT", "Patente", "Viáticos", "Comida", "Mantenimiento"]
subcategorias_gasto_variable = ["Publicidad", "Comisiones", "Transporte", "Otros"]

# Subcategorías para ingresos
subcategorias_ingreso = ["Ventas Saha", "Ventas Netlink", "Alquiler", "Aporte de Capital", "Otros Ingresos"]

subcategoria = None
responsable = None
if categoria == "Gasto":
    subcategoria_tipo = st.selectbox("Selecciona el tipo de gasto", ["Gasto fijo", "Gasto variable"], key="subcategoria_tipo")
    
    if subcategoria_tipo == "Gasto fijo":
        subcategoria = st.selectbox("Selecciona la subcategoría de gasto fijo", subcategorias_gasto_fijo, key="subcategoria_fijo")
    elif subcategoria_tipo == "Gasto variable":
        subcategoria = st.selectbox("Selecciona la subcategoría de gasto variable", subcategorias_gasto_variable, key="subcategoria_variable")
    
    # Selección del responsable
    responsable = st.selectbox("¿A quién corresponde el gasto?", ["SAHA", "AMINE", "Gabriel" , "NETLINK"], key="responsable")

elif categoria == "Ingreso":
    subcategoria = st.selectbox("Selecciona la subcategoría de ingreso", subcategorias_ingreso, key="subcategoria_ingreso")
    responsable = st.selectbox("¿A quién corresponde el ingreso?", ["SAHA", "AMINE", "Gabriel"], key="responsable_ingreso")

descripcion = st.text_input("Descripción", value=st.session_state.get("descripcion", ""))

monto = st.number_input("Ingrese el monto", value=float(st.session_state.monto), step=0.01, format="%.2f")
st.session_state.monto = monto


# Opciones de pago
tipo_pago = st.selectbox("Selecciona el tipo de pago", ["Dólares", "Zelle", "BSF", "BSF Transfer"], key="tipo_pago")

# Si el pago es en BSF, solicitar la tasa de cambio
tasa_cambio = None
if tipo_pago == "BSF" or tipo_pago == "BSF Transfer":
    # Widget de entrada numérica
    tasa_cambio = st.number_input("Ingrese la tasa de cambio",value=float(st.session_state.tasa_cambio),  # Asegurar que sea un float 
                                   step=0.01,)
                            
     # Al guardar o procesar el registro, puedes almacenar el valor actualizado en session_state
    st.session_state.tasa_cambio = tasa_cambio                          
    
#-------------------------------------------------------------------------------------------

# SE CREA EL BOTON DE REGISTRAR
# Botón para agregar el registro
if st.button("Agregar registro"):
    agregar_registro(fecha, categoria, descripcion, monto, tipo_pago, tasa_cambio, subcategoria, responsable)
#---------------------------------------------------------------------------------------
# ACA SE CREA LA TABLA CON LOS REGISTROS INTRODUCIDOS 
# Mostrar los registros guardados (solo si existen)
if st.session_state.registros:
    df = pd.DataFrame(st.session_state.registros)
    st.subheader("Registros de transacciones")
    st.dataframe(df) 

# Agregar un espacio adicional entre la tabla y la seccion de editar registros
st.markdown("<br><br>", unsafe_allow_html=True)

#---------------------------------------------------------------------------------------

# Asegurarse de que edit_index esté dentro del rango de los registros

if st.session_state.registros:
    # Usar un valor predeterminado para edit_index si no se ha ingresado
    edit_index = st.number_input("Número de registro a editar", min_value=0, max_value=len(st.session_state.registros)-1, step=1, key="edit_index", value=0)

    # Verificar que edit_index es válido antes de continuar
    if 0 <= edit_index < len(st.session_state.registros):
        # Cargar los datos del registro a editar
        registro_a_editar = st.session_state.registros[edit_index]

    
    fecha = st.date_input("Fecha de la transacción", value=registro_a_editar["Fecha"], key="fecha_editar")
    categoria = st.selectbox("Selecciona la categoría", ["Ingreso", "Gasto"], 
                             index=["Ingreso", "Gasto"].index(registro_a_editar["Categoría"]), 
                             key="categoria_editar")
#--------------------------------------------------------------------------------------------------------
    # Aquí se evalúa si el tipo de categoría cambia
    # Definir monto ANTES de la verificación para evitar errores
    # Inicializar el monto en session_state si no existe

    if "monto_editar" not in st.session_state:
      st.session_state.monto_editar = registro_a_editar["Monto"]
 
    # Evaluar si la categoría cambia y actualizar el monto en session_state
    if registro_a_editar["Categoría"] == "Gasto" and categoria == "Ingreso" and st.session_state.monto_editar < 0:
      st.session_state.monto_editar = abs(st.session_state.monto_editar)
      st.warning("Estás cambiando un gasto a un ingreso. Asegúrate de que el monto sea positivo.")
    
    
    # Definir límites según la categoría
    if categoria == "Ingreso":
        min_val, max_val = 0.01, None  # Solo positivos
        if st.session_state.monto_editar < 0:
            st.session_state.monto_editar = 0.01  # Corrige valores negativos
    else:
        min_val, max_val = -1000000.0, -0.01  # Solo negativos
        if st.session_state.monto_editar > 0:
            st.session_state.monto_editar = -0.01  # Corrige valores positivos

   # Usar el valor de session_state en el número input
    monto = st.number_input("Monto", min_value=min_val, max_value=max_val, step=0.01, 
                        value=st.session_state.monto_editar)  
#-----------------------------------------------------------------------------------------

    subcategoria = None
    responsable = None
    
    if categoria == "Gasto":
        subcategoria_tipo = st.selectbox("Selecciona el tipo de gasto", ["Gasto fijo", "Gasto variable"], key="subcategoria_tipo_editar")
        
        if subcategoria_tipo == "Gasto fijo":
            subcategoria = st.selectbox("Selecciona la subcategoría de gasto fijo", subcategorias_gasto_fijo, 
                                        index=subcategorias_gasto_fijo.index(registro_a_editar["Subcategoría"]), 
                                        key="subcategoria_fijo_editar")
        elif subcategoria_tipo == "Gasto variable":
            subcategoria = st.selectbox("Selecciona la subcategoría de gasto variable", subcategorias_gasto_variable, 
                                        index=subcategorias_gasto_variable.index(registro_a_editar["Subcategoría"]), 
                                        key="subcategoria_variable_editar")
        
        responsable = st.selectbox("¿A quién corresponde el gasto?", ["SAHA", "AMINE", "Gabriel", "NETLINK"], 
                                   index=["SAHA", "AMINE", "Gabriel", "NETLINK"].index(registro_a_editar["Responsable"]), 
                                   key="responsable_editar")
        
        # Permitir números negativos para EDITAR Gastos
        #monto = st.number_input("Monto", min_value=-10000.0, max_value=-0.01, step=0.01, 
                                #value=registro_a_editar["Monto"], key="monto_editar")

    elif categoria == "Ingreso":

# Ingresos solo permiten números positivos
        #monto = st.number_input("Monto", min_value=0.01, step=0.01, 
                                #value=registro_a_editar["Monto"], key="monto_editar")

        subcategoria = st.selectbox("Selecciona la subcategoría de ingreso", subcategorias_ingreso, 
                                    index=subcategorias_ingreso.index(registro_a_editar["Subcategoría"]), 
                                    key="subcategoria_ingreso_editar")
        responsable = st.selectbox("¿A quién corresponde el ingreso?", ["SAHA", "AMINE", "Gabriel"], 
                                   index=["SAHA", "AMINE", "Gabriel"].index(registro_a_editar["Responsable"]), 
                                   key="responsable_ingreso_editar")

        

    descripcion = st.text_input("Descripción de la transacción", 
                                value=registro_a_editar["Descripción"], key="descripcion_editar")

    tipo_pago = st.selectbox("Selecciona el tipo de pago", ["Dólares", "Zelle", "BSF","BSF Transfer"], 
                             index=["Dólares", "Zelle", "BSF","BSF Transfer"].index(registro_a_editar["Tipo de pago"]), 
                             key="tipo_pago_editar")

    # Si el pago es en BSF, solicitar la tasa de cambio
    tasa_cambio = None
    if tipo_pago == "BSF" or tipo_pago == "BSF Transfer":
        tasa_cambio = st.text_input("Tasa de cambio del día (si aplica)", 
                                    value=registro_a_editar["Tasa de cambio"] if registro_a_editar["Tasa de cambio"] else "", 
                                    key="tasa_cambio_editar")
#-----------------------------------------------------------------------------------------------
# SE CREA EL BOTON DE ACTUALIZAR LO EDITADO

    # Mostrar el botón de actualización siempre
    if st.button("Actualizar registro"):
        editar_registro(edit_index, fecha, categoria, descripcion, monto, tipo_pago, tasa_cambio, subcategoria, responsable)

# Agregar un espacio adicional entre los botones
st.markdown("<br><br>", unsafe_allow_html=True)

#-------------------------------------------------------------------------------------------------
# Verificar si hay registros
#ACA SE CREA EL BOTON DE ELIMINAR REGISTROS
if len(st.session_state.registros) > 0:
    # Seleccionar el índice del registro a eliminar
    delete_index = st.number_input("Número de registro a eliminar", min_value=0, max_value=len(st.session_state.registros)-1, step=1, key="delete_index")

    # Verificar si el índice de eliminación es válido
    if 0 <= delete_index < len(st.session_state.registros):
        # Pregunta de confirmación antes de eliminar
        if st.button(f"¿Estás seguro de eliminar el registro #{delete_index}?"):
            eliminar_registro(delete_index)
    else:
        st.warning("Selecciona un registro válido para eliminar.")
else:
    st.warning("No hay registros para eliminar.")
#-----------------------------------------------------------------------------------------------------------------


