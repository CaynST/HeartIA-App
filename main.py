import streamlit as st
from streamlit_autorefresh import st_autorefresh
import pandas as pd
import numpy as np
import time
import joblib
import random
import threading
import os
from twilio.rest import Client

# Carga modelo (ajusta ruta)
modelo = joblib.load("modelo_ia_lightgbm.pkl")



account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
client = Client(account_sid, auth_token)

st.set_page_config(page_title="Monitor Cardiaco", layout="centered")

if "modo_emergencia" not in st.session_state:
    st.session_state.modo_emergencia = False

# --- Funciones ---
def simular_presion(ap_hi, ap_lo):
    ap_hi = max(90, min(160, int(ap_hi + random.randint(-3, 3))))
    ap_lo = max(60, min(100, int(ap_lo + random.randint(-3, 3))))
    return ap_hi, ap_lo

def hacer_llamada(from_number, to_number):
    client = Client(account_sid, auth_token)

    llamada = client.calls.create(
        twiml='<Response><Say voice="alice">Se ha detectado una emergencia cardíaca. Por favor contacte al usuario de inmediato.</Say></Response>',
        to=to_number,
        from_=from_number
    )

    return llamada.sid


def simular_ritmo_cardiaco():
    return random.randint(90, 100)

def clasificar_riesgo(prob):
    if prob < 0.5:
        return "Todo bien", "green"
    elif prob < 0.6:
        return "Riesgo bajo", "yellow"
    elif prob < 0.85:
        return "Riesgo medio", "orange"
    else:
        return "Riesgo alto", "red"

def clasificar_presion(ap_hi, ap_lo):
    if ap_hi < 90 or ap_lo < 60:
        return "Presión baja", "blue"
    elif ap_hi > 120 or ap_lo > 80:
        return "Presión alta", "red"
    else:
        return "Presión normal", "green"

# --- Formulario Inicio ---
if "form_data" not in st.session_state:
    st.session_state.form_data = None

with st.sidebar:
    st.header("Configuración")
    pagina = st.radio("Navegación", ["Inicio", "Contacto de emergencia", "Monitorización"])

# Página Inicio: Formulario
if pagina == "Inicio":
    st.title("Registro inicial del usuario")
    with st.form("form_usuario"):
        age = st.number_input("Edad (años)", min_value=1, max_value=120, value=30)
        gender = st.selectbox("Género", options=[1, 2], format_func=lambda x: "Mujer" if x == 1 else "Hombre")
        height = st.number_input("Altura (cm)", min_value=100, max_value=250, value=170)
        weight = st.number_input("Peso (kg)", min_value=30, max_value=200, value=70)
        smoke = st.selectbox("¿Fuma?", [0, 1], format_func=lambda x: "No" if x == 0 else "Sí")
        alco = st.selectbox("¿Consume alcohol?", [0, 1], format_func=lambda x: "No" if x == 0 else "Sí")
        active = st.selectbox("¿Es activo físicamente?", [0, 1], format_func=lambda x: "No" if x == 0 else "Sí")
        
        submitted = st.form_submit_button("Guardar datos")
        if submitted:
            st.session_state.form_data = {
                "age": int(age * 365),  # convertir años a días
                "gender": gender,
                "height": height,
                "weight": weight,
                "smoke": smoke,
                "alco": alco,
                "active": active,
            }
            st.success("Datos guardados correctamente")

# Página Contacto emergencia
elif pagina == "Contacto de emergencia":
    st.title("Configuración de contacto de emergencia")
    with st.form("form_contacto"):
        user_phone = st.text_input("Número telefónico del usuario")
        emergency_phone = st.text_input("Número telefónico de contacto de emergencia")
        submitted = st.form_submit_button("Guardar números")
        if submitted:
            st.session_state.user_phone = user_phone
            st.session_state.emergency_phone = emergency_phone
            st.success("Números guardados")

# Página Monitorización
elif pagina == "Monitorización":
    st.title("Monitorización cardíaca en tiempo real")
    
    if not st.session_state.get("form_data", None):
        st.warning("Por favor completa el formulario inicial primero.")
    else:
        datos = st.session_state.form_data

        # Variables iniciales
        if "ap_hi" not in st.session_state:
            st.session_state.ap_hi = 100
        if "ap_lo" not in st.session_state:
            st.session_state.ap_lo = 70
        if "ritmo_cardiaco" not in st.session_state:
            st.session_state.ritmo_cardiaco = 75

        # Botones para simular riesgo
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("Simular Riesgo Medio"):
                st.session_state.ap_hi = 145
                st.session_state.ap_lo = 95
                st.session_state.ritmo_cardiaco = 95
        with col2:
            if st.button("Simular Riesgo Alto"):
                st.session_state.ap_hi = 160
                st.session_state.ap_lo = 100
                st.session_state.ritmo_cardiaco = 110
        with col3:
            if st.button("Simular Ataque Cardíaco"):
                st.session_state.ap_hi = 180
                st.session_state.ap_lo = 110
                st.session_state.ritmo_cardiaco = 130
                st.session_state.modo_emergencia = True
        with st.container():
            if st.button("Normalizar Signos Vitales"):
                st.session_state.ap_hi = 110
                st.session_state.ap_lo = 70
                st.session_state.ritmo_cardiaco = 75
                st.success("Signos vitales normalizados")
                st.session_state.modo_emergencia = False


        # Simular presión y ritmo con pequeña variación
        ap_hi, ap_lo = simular_presion(st.session_state.ap_hi, st.session_state.ap_lo)
        ritmo = simular_ritmo_cardiaco()

        st.session_state.ap_hi = ap_hi
        st.session_state.ap_lo = ap_lo
        st.session_state.ritmo_cardiaco = ritmo

        # Preparar datos para modelo
        df = pd.DataFrame([{
        "age": datos["age"],
        "gender": datos["gender"],
        "height": datos["height"],
        "weight": datos["weight"],
        "ap_hi": st.session_state.ap_hi,
        "ap_lo": st.session_state.ap_lo,
        "smoke": datos["smoke"],
        "alco": datos["alco"],
        "active": datos["active"]
            }])

        # Obtener probabilidad riesgo
        riesgo_prob = modelo.predict_proba(df)[:, 1][0]

        # Mostrar estado riesgo
        estado_riesgo, color_riesgo = clasificar_riesgo(riesgo_prob)
        st.markdown(f"<h2 style='color:{color_riesgo}'>Riesgo: {estado_riesgo} ({riesgo_prob*100:.1f}%)</h2>", unsafe_allow_html=True)

        # Mostrar estado presión
        estado_presion, color_presion = clasificar_presion(ap_hi, ap_lo)
        st.markdown(f"<h3 style='color:{color_presion}'>Presión arterial: {estado_presion} ({ap_hi}/{ap_lo} mmHg)</h3>", unsafe_allow_html=True)

        # Mostrar ritmo cardíaco
        st.metric("Ritmo cardíaco (bpm)", ritmo)

        # Gráfica de ritmo cardíaco (últimos 20 segundos)
        if "hist_ritmo" not in st.session_state:
            st.session_state.hist_ritmo = []

        st.session_state.hist_ritmo.append(ritmo)
        if len(st.session_state.hist_ritmo) > 20:
            st.session_state.hist_ritmo.pop(0)

        st.line_chart(st.session_state.hist_ritmo)

        if st.session_state.modo_emergencia:
            st.error("⚠️ ¡Modo de emergencia activado!")

            user = st.session_state.get("user_phone", "No definido")
            contacto = st.session_state.get("emergency_phone", "No definido")

            st.markdown(f"📞 Llamando desde **{user}** a contacto de emergencia **{contacto}**...")

            try:
                sid = hacer_llamada(from_number=user, to_number=contacto)
                st.success(f"✅ Llamada iniciada con SID: {sid}")
            except Exception as e:
                st.error(f"❌ No se pudo realizar la llamada: {e}")
           


        # Esperar 1 segundo para refrescar
        time.sleep(1)
        st_autorefresh(interval=1000, key="auto-refresh")
