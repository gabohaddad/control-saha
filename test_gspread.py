import streamlit as st
from gspread_pandas import Spread

def prueba_gspread_pandas():
    try:
        spread = Spread("BD DE REGISTROS FINANCIEROS")
        df_cuentas = spread.sheet_to_df(sheet="Cuentas", index=None)
        st.write("Datos de la hoja 'Cuentas':")
        st.dataframe(df_cuentas)
    except Exception as e:
        st.error(f"Error al conectar o leer la hoja: {e}")

if __name__ == "__main__":
    prueba_gspread_pandas()
