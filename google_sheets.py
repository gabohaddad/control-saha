import gspread
from google.oauth2.service_account import Credentials

# Rutas y configuración para la autenticación
# FUNCION PARA OBTENER REGISTROS DESDE GOOGLE SHEET EN FORMA DE DICCIONARIO PARA 
# MANEJO DE DATOS, REPORTES ETC

def obtener_registros(BD_DE_REGISTROS_FINANCIEROS):
    # Cargar las credenciales desde el archivo .json

# Define los alcances necesarios
    SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    
    # Cargar las credenciales con los alcances
    credenciales = Credentials.from_service_account_file(
        r'C:\Users\USUARIO\Documents\Proyecto python finanzas personales\coastal-range-452621-e4-14db891d7262.json',
        scopes=SCOPES
    )

    # Conectarse a Google Sheets usando gspread
    gc = gspread.authorize(credenciales)

    # Abrir la hoja de Google Sheets
    sheet = gc.open("BD DE REGISTROS FINANCIEROS").sheet1

    # Obtener todos los registros
    registros = sheet.get_all_records()

    return registros
#--------------------------------------------------------------------------------------


    #for registro in registros:
        # Ajusta los campos según la estructura de tus datos
        #sheet.append_row([registro["campo1"], registro["campo2"], registro["campo3"]])  # Asegúrate de que estos campos existan en tu estructura de datos

    #print("Registros cargados correctamente")

#---------------------------------------------------------------------------------------------    
# FUNCION PARA Agregar registros a la hoja DE GOOGLE SHEET DESDE EL FORMULARIO
# Función para cargar registros a Google Sheets
def cargar_registros_a_google_sheets(registros, BD_DE_REGISTROS_FINANCIEROS):
    # Define los alcances necesarios
    SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    
    # Cargar las credenciales con los alcances
    credenciales = Credentials.from_service_account_file(
        r'C:\Users\USUARIO\Documents\Proyecto python finanzas personales\coastal-range-452621-e4-14db891d7262.json',
        scopes=SCOPES
    )

    # Conectarse a Google Sheets usando gspread
    gc = gspread.authorize(credenciales)

    # Abrir la hoja de Google Sheets
    sheet = gc.open("BD DE REGISTROS FINANCIEROS").sheet1

    # Agregar registros a la hoja
    
    for registro in registros:
    # Ajusta los campos según la estructura de tus datos
    # Aquí estoy suponiendo que los registros tienen estos campos: "FECHA", "CATEGORIA", etc.
    # Cambia estos nombres de campo según la estructura de tus registros
       sheet.append_row([
          registro["FECHA"], 
          registro["CATEGORIA"], 
          registro["SUB-CATEGORIA"],
          registro["RESPONSABLE"], 
          registro["DESCRIPCION"], 
          registro["MONTO"],
          registro["TIPO DE PAGO"],
          registro["TASA DE CAMBIO"]
    ])

    print("Registros cargados correctamente")


