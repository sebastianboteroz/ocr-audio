import os
import time
import glob
import re
import cv2
import numpy as np
import pytesseract
from PIL import Image
import streamlit as st
from gtts import gTTS
from googletrans import Translator

# ---------- Configuración de Página ----------
st.set_page_config(
    page_title="OCR & Traductor de Voz",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------- Estilos Personalizados (Fondo Blanco + Accesibilidad) ----------
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    :root {
        --bg-main: #FFFFFF;
        --bg-sidebar: #F8FAFC;
        --border-color: #E2E8F0;
        --accent-blue: #0284C7;
        --accent-hover: #0369A1;
        --text-primary: #0F172A;
        --text-secondary: #475569;
    }

    .stApp {
        background-color: var(--bg-main) !important;
        color: var(--text-primary);
        font-family: 'Inter', sans-serif;
    }

    section[data-testid="stSidebar"] {
        background-color: var(--bg-sidebar) !important;
        border-right: 1px solid var(--border-color) !important;
    }

    h1, h2, h3, h4, h5, h6, p, label, .stMarkdown, div[data-testid="stMarkdownContainer"] {
        color: var(--text-primary) !important;
    }

    .hero-tag {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        background: #F0F9FF;
        border: 1px solid #BAE6FD;
        color: var(--accent-blue) !important;
        padding: 0.35rem 0.85rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        margin-bottom: 0.8rem;
    }

    .hero-title {
        font-size: clamp(2rem, 4vw, 2.8rem);
        font-weight: 700;
        letter-spacing: -0.02em;
        line-height: 1.2;
        margin-bottom: 0.5rem;
    }

    .hero-subtitle {
        font-size: 1.05rem;
        color: var(--text-secondary) !important;
        max-width: 65ch;
        line-height: 1.5;
        margin-bottom: 1.5rem;
    }

    .card-header {
        font-size: 0.9rem;
        font-weight: 600;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        color: var(--accent-blue) !important;
        margin-bottom: 0.8rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .stButton>button {
        border-radius: 8px !important;
        border: 1px solid var(--accent-blue) !important;
        background: var(--accent-blue) !important;
        color: #FFFFFF !important;
        font-weight: 600 !important;
        padding: 0.6rem 1.2rem !important;
        transition: all 0.2s ease-in-out !important;
        width: 100%;
    }

    .stButton>button:hover {
        background: var(--accent-hover) !important;
        border-color: var(--accent-hover) !important;
        box-shadow: 0 4px 12px rgba(2, 132, 199, 0.2) !important;
    }

    textarea, input {
        border-radius: 8px !important;
        border: 1px solid var(--border-color) !important;
        background-color: #FFFFFF !important;
        color: var(--text-primary) !important;
    }

    button:focus-visible, input:focus-visible, textarea:focus-visible {
        outline: 2px solid var(--accent-blue) !important;
        outline-offset: 2px;
    }
    </style>
""", unsafe_allow_html=True)

# ---------- Diccionarios de Idiomas y Acentos ----------
IDIOMAS = {
    "Español": "es",
    "Inglés": "en",
    "Italiano": "it",
    "Francés": "fr",
    "Alemán": "de",
    "Japonés": "ja",
    "Coreano": "ko",
    "Mandarín": "zh-cn",
    "Bengalí": "bn"
}

ACENTOS = {
    "Por defecto": "com",
    "México / Latam": "com.mx",
    "Reino Unido": "co.uk",
    "Estados Unidos": "com",
    "Canadá": "ca",
    "Australia": "com.au",
    "Irlanda": "ie",
    "Sudáfrica": "co.za",
    "India": "co.in"
}

# ---------- Funciones Auxiliares ----------
def limpiar_archivos_antiguos(dias=7):
    if not os.path.exists("temp"):
        os.makedirs("temp")
    archivos = glob.glob("temp/*.mp3")
    ahora = time.time()
    limite = dias * 86400
    for f in archivos:
        if os.stat(f).st_mtime < ahora - limite:
            try:
                os.remove(f)
            except OSError:
                pass

limpiar_archivos_antiguos(7)

def text_to_speech(src_lang, dest_lang, text_data, tld_code):
    translator = Translator()
    translation = translator.translate(text_data, src=src_lang, dest=dest_lang)
    trans_text = translation.text
    
    tts = gTTS(trans_text, lang=dest_lang, tld=tld_code, slow=False)
    
    safe_prefix = re.sub(r'[^a-zA-Z0-9]', '', text_data[:15]).strip()
    if not safe_prefix:
        safe_prefix = "audio"
    
    filename = f"{safe_prefix}_{int(time.time())}.mp3"
    filepath = os.path.join("temp", filename)
    tts.save(filepath)
    return filepath, trans_text

# ---------- Encabezado Principal ----------
st.markdown('<div class="hero-tag">✨ OCR & Traducción por Voz</div>', unsafe_allow_html=True)
st.markdown('<h1 class="hero-title">Escanea texto y escúchalo traducido</h1>', unsafe_allow_html=True)
st.markdown('<p class="hero-subtitle">Captura texto desde tu cámara o sube un archivo de imagen. El sistema extraerá las palabras automáticamente para que puedas traducirlas y generarlas en audio.</p>', unsafe_allow_html=True)

# ---------- Barra Lateral (Configuración) ----------
with st.sidebar:
    # Carga de la imagen personalizada traductor2.png
    if os.path.exists("traductor2.png"):
        st.image("traductor2.png", width=140)
    else:
        st.info("🖼️ Guarda tu archivo como 'traductor2.png' en la misma carpeta del script.")

    st.header("🛠️ Configuración")
    
    st.subheader("1. Fuente de Imagen")
    metodo = st.radio(
        "Selecciona el origen:",
        ("📁 Cargar imagen", "📷 Usar cámara"),
        help="Elige si deseas subir un archivo existente o tomar una fotografía en vivo."
    )
    
    st.markdown("---")
    st.subheader("2. Filtros de Procesamiento")
    aplicar_filtro = st.checkbox("Invertir colores (Alto contraste)", help="Utilízalo si la imagen tiene texto claro sobre un fondo muy oscuro.")
    
    st.markdown("---")
    st.subheader("3. Parámetros de Traducción")
    in_lang_name = st.selectbox("Idioma de origen (Imagen):", list(IDIOMAS.keys()), index=0)
    out_lang_name = st.selectbox("Idioma de destino (Traducción):", list(IDIOMAS.keys()), index=2)  # Italiano
    accent_name = st.selectbox("Acento de audio:", list(ACENTOS.keys()), index=0)
    
    display_output_text = st.checkbox("Mostrar texto traducido", value=True)

# ---------- Captura y Carga de Imagen ----------
img_rgb = None

if metodo == "📷 Usar cámara":
    img_buffer = st.camera_input("Toma una fotografía para escanear:")
    if img_buffer is not None:
        bytes_data = img_buffer.getvalue()
        cv2_img = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)
        if aplicar_filtro:
            cv2_img = cv2.bitwise_not(cv2_img)
        img_rgb = cv2.cvtColor(cv2_img, cv2.COLOR_BGR2RGB)
else:
    uploaded_file = st.file_uploader("Selecciona un archivo de imagen (PNG, JPG, JPEG):", type=["png", "jpg", "jpeg"])
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        img_np = np.array(image)
        
        if len(img_np.shape) == 3 and img_np.shape[2] == 4:
            img_np = cv2.cvtColor(img_np, cv2.COLOR_RGBA2RGB)
            
        if aplicar_filtro:
            img_np = cv2.bitwise_not(img_np)
            
        img_rgb = img_np

# ---------- Procesamiento y Resultados ----------
if img_rgb is not None:
    col1, col2 = st.columns([1, 1], gap="medium")
    
    with col1:
        st.markdown('<div class="card-header">🖼️ Imagen procesada</div>', unsafe_allow_html=True)
        st.image(img_rgb, use_container_width=True, caption="Vista previa de la imagen analizada.")
        
    with col2:
        st.markdown('<div class="card-header">📝 Texto detectado (OCR)</div>', unsafe_allow_html=True)
        
        try:
            with st.spinner("Extrayendo texto de la imagen..."):
                ocr_lang_code = IDIOMAS[in_lang_name]
                tess_lang = "chi_sim" if ocr_lang_code == "zh-cn" else ocr_lang_code
                
                texto_extraido = pytesseract.image_to_string(img_rgb, lang=tess_lang)

            if texto_extraido.strip():
                st.text_area(
                    label="Resultado del escaneo:",
                    value=texto_extraido,
                    height=180,
                    help="Puedes editar el texto si requiere correcciones antes de traducir."
                )
                
                st.markdown("---")
                
                if st.button("🔊 Traducir y Generar Audio"):
                    with st.spinner("Traduciendo y convirtiendo a voz..."):
                        audio_path, texto_traducido = text_to_speech(
                            IDIOMAS[in_lang_name],
                            IDIOMAS[out_lang_name],
                            texto_extraido,
                            ACENTOS[accent_name]
                        )
                        
                        st.markdown("### 🎧 Audio Generado")
                        with open(audio_path, "rb") as audio_file:
                            st.audio(audio_file.read(), format="audio/mp3", start_time=0)
                            
                        if display_output_text:
                            st.markdown("### 🌐 Texto Traducido")
                            st.success(texto_traducido)
            else:
                st.warning("🔍 No se detectó texto claro en la imagen. Intenta mejorar el encuadre, la iluminación o cambiar los filtros en el menú lateral.")

        except pytesseract.TesseractNotFoundError:
            st.error("⚠️ No se encontró la instalación de Tesseract OCR en el sistema.")
        except Exception as e:
            st.error(f"Ocurrió un error inesperado al procesar la solicitud: {e}")

else:
    st.info("👋 **¡Bienvenido!** Selecciona una imagen desde tu equipo o activa la cámara en el menú lateral para comenzar.")
