import streamlit as st
import pandas as pd

st.title("Control Financiero")

# Inicializar la variable en session_state para almacenar los datos
if 'data' not in st.session_state:
    st.session_state.data = []

st.subheader("Ingresar Información Financiera")

# Seleccionar si es Ingreso o Gasto
tipo = st.selectbox("Seleccione el tipo", options=["Ingreso", "Gasto"])

# Mostrar opciones según el tipo seleccionado
if tipo == "Ingreso":
    opciones_ingresos = ["Ventas", "Alquileres", "Aportes de Capital", "Otros"]
    categoria = st.selectbox("Seleccione la categoría de ingreso", opciones_ingresos)
else:
    opciones_gastos = ["Gastos por Ventas", "Gastos Variables", "Gastos Fijos", "Gastos Personales"]
    categoria = st.selectbox("Seleccione la categoría de gasto", opciones_gastos)

# Ingreso del monto
monto = st.number_input("Monto", min_value=0.0, step=0.1)

# Selección del método de pago
metodo_pago = st.selectbox("Seleccione el método de pago", options=["Dólares", "Zelle", "bsF"])

# Si la moneda es bsF, pedir la tasa de cambio
if metodo_pago == "bsF":
    tasa_cambio = st.number_input("Tasa de cambio del día (bsF por Dólar)", min_value=0.0, step=0.1)
else:
    tasa_cambio = None

# Botón para agregar la información
if st.button("Agregar"):
    if monto > 0:
        st.session_state.data.append({
            "Tipo": tipo,
            "Categoría": categoria,
            "Monto": monto,
            "Método de Pago": metodo_pago,
            "Tasa de Cambio": tasa_cambio
        })
        mensaje = f"{tipo} agregado: {categoria} - {monto} ({metodo_pago})"
        if tasa_cambio:
            mensaje += f" (Tasa: {tasa_cambio})"
        st.success(mensaje)
    else:
        st.warning("Por favor, ingrese un monto mayor a 0.")

# Mostrar resumen y gráfico si hay datos
if st.session_state.data:
    st.subheader("Resumen de Ingresos y Gastos")
    df = pd.DataFrame(st.session_state.data)
    st.write(df)
    
    st.subheader("Gráfico de Montos por Categoría")
    resumen = df.groupby("Categoría")["Monto"].sum()
    st.bar_chart(resumen)