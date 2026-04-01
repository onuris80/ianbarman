import streamlit as st
import google.generativeai as genai
import requests
import json
import os

# --- 1. CONFIGURACIÓN DE PÁGINA (DEBE SER LA PRIMERA LÍNEA) ---
st.set_page_config(page_title="Barman Audiovisual", page_icon="🥃", layout="wide")

# --- CONFIGURACIÓN DE LAS APIs ---
# Las llaves deben estar configuradas como variables de entorno
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyBd8uWOkNjNki0_bgCTzVyZNjn6m5oRmDk")
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "2e5d945e329362c2c3563514dc377708")

genai.configure(api_key=GEMINI_API_KEY)

# --- 2. FUNCIONES DE APOYO ---

@st.cache_data
def obtener_paises_soportados():
    """Obtiene la lista de países con datos de streaming en TMDB."""
    url = f"https://api.themoviedb.org/3/watch/providers/regions?api_key={TMDB_API_KEY}"
    try:
        res = requests.get(url).json()
        # Creamos un diccionario: {"España": "ES", "Japan": "JP", "United States of America": "US"...}
        paises = {item["native_name"]: item["iso_3166_1"] for item in res.get("results", [])}
        return paises if paises else {"España": "ES", "México": "MX"}
    except:
        return {"España": "ES", "México": "MX", "Estados Unidos": "US"} # Fallback si falla

def obtener_info_completa_tmdb(titulo, tipo_media, region):
    """Busca el poster y las plataformas de streaming en una región específica."""
    search_url = f"https://api.themoviedb.org/3/search/{tipo_media}?api_key={TMDB_API_KEY}&query={titulo}"
    info = {"poster": None, "plataformas": "No disponible en suscripción."}
    try:
        search_res = requests.get(search_url).json()
        if not search_res.get("results"):
            return info
        
        res = search_res["results"][0]
        tmdb_id = res["id"]
        
        if res.get("poster_path"):
            info["poster"] = f"https://image.tmdb.org/t/p/w500{res['poster_path']}"
        
        prov_url = f"https://api.themoviedb.org/3/{tipo_media}/{tmdb_id}/watch/providers?api_key={TMDB_API_KEY}"
        prov_res = requests.get(prov_url).json()
        reg_data = prov_res.get("results", {}).get(region, {})
        
        plat = [p["provider_name"] for p in reg_data.get("flatrate", [])]
        if plat:
            info["plataformas"] = ", ".join(plat)
        return info
    except:
        return info

def extraer_json(texto):
    """Limpia el texto y extrae el bloque JSON."""
    try:
        inicio = texto.find("[")
        fin = texto.rfind("]") + 1
        if inicio != -1 and fin != 0:
            json_str = texto[inicio:fin]
            return json.loads(json_str)
        return None
    except:
        return None

def limpiar_chat():
    """Reinicia la sesión."""
    if "mensajes" in st.session_state:
        del st.session_state.mensajes
    if "chat_session" in st.session_state:
        del st.session_state.chat_session

# --- 3. SIDEBAR ---
paises_dict = obtener_paises_soportados()
lista_nombres = sorted(list(paises_dict.keys()))

with st.sidebar:
    st.title("🥃 Barman Lounge")
    
    def_idx = lista_nombres.index("España") if "España" in lista_nombres else 0
    pais_sel = st.selectbox("Ubicación del cliente:", lista_nombres, index=def_idx, on_change=limpiar_chat)
    cod_pais = paises_dict[pais_sel]
    
    st.markdown("---")
    st.subheader("📝 Tomar Nota")
    
    with st.expander("Abrir Carta", expanded=False):
        f_ene = st.radio("Energía:", ["Adrenalina y tensión", "Sosiego y calma", "Euforia", "Melancolía"], key="f_ene")
        f_pal = st.radio("Paladar:", ["Clásico con solera", "Estreno", "Indie", "Comercial"], key="f_pal")
        f_pro = st.radio("Profundidad:", ["Ligero", "Evasión", "Desafío", "Impacto", "Reflexión"], key="f_pro")
        f_for = st.radio("Formato:", ["Película", "Serie", "Miniserie"], key="f_for")
        f_extra = st.text_input("Nota adicional:", placeholder="Ej: Algún actor o tema...", key="f_extra")
        
        btn_ficha = st.button("Enviar Pedido a la Barra 🥃")

    if st.button("🔄 Reiniciar Conversación"):
        limpiar_chat()
        st.rerun()

# --- 4. CONFIGURACIÓN DEL MODELO IA ---
instrucciones_bot = f"""
Eres 'IAN Barman Audiovisual', barman profesional en {pais_sel}. Tu servicio es directo, educado y eficaz.

PROTOCOLO DE CATA BINARIA (Obligatorio):
1. RECEPCIÓN: Salude brevemente y pregunte por el estado de ánimo del cliente.

MODOS DE TRABAJO:
1. FICHA DE CATA: Sirve MÁXIMO 3 opciones en formato JSON.
2. CATEGORÍAS DE CATA:
   - Energía: Adrenalina y tensión, Sosiego y calma, Euforia, Melancolía.
   - Paladar: Clásico con solera, Estreno, Indie, Comercial.
   - Profundidad: Ligero, Evasión, Desafío, Impacto, Reflexión.
   - Formato: Película, Serie, Miniserie.
3. PRIORIDAD DE BODEGA: Debes priorizar títulos disponibles en plataformas populares (Netflix, Disney+, Max, Amazon Prime Video, Apple TV+).
4. TEXTO NORMAL: Responde como un barman humano. Charla o ajusta recomendaciones.

REGLA DE ORO: Máximo 3 recomendaciones por petición.
JSON Estructura:
[
  {{"titulo": "Nombre Original", "tipo": "movie/tv", "analisis": "Nota emocional", "ambiente": "Maridaje"}}
]
"""

if "chat_session" not in st.session_state:
    model = genai.GenerativeModel('gemini-2.5-flash', system_instruction=instrucciones_bot)
    st.session_state.chat_session = model.start_chat(history=[])
    st.session_state.mensajes = []
    
    with st.spinner("Preparando la cristalería..."):
        res_ini = st.session_state.chat_session.send_message(
            f"Salúdeme profesionalmente como BarmIAn en {pais_sel} y pregúnteme por mi jornada."
        )
        st.session_state.mensajes.append({"role": "assistant", "content": res_ini.text.strip(), "type": "text"})

# --- 5. CUERPO PRINCIPAL ---
st.title("🥃 IAN su Barman Audiovisual")

for msg in st.session_state.mensajes:
    with st.chat_message(msg["role"]):
        if msg["type"] == "text":
            st.markdown(msg["content"])
        elif msg["type"] == "recommendations":
            cols = st.columns(3)
            for idx, rec in enumerate(msg["data"]):
                with cols[idx]:
                    if rec.get("poster"):
                        st.image(rec["poster"], use_container_width=True)
                    with st.expander(f"📋 Nota del Barman"):
                        st.write(f"**{rec.get('titulo', 'Sin título')}**")
                        st.write(f"💡 {rec.get('analisis', 'Sin análisis')}")
                        st.caption(f"🏠 {rec.get('ambiente', 'Cualquier ambiente')}")
                        st.info(f"📺 {rec.get('plataformas', 'No disponible')}")

# --- 6. PROCESAMIENTO ---

def procesar_respuesta_ia(texto_entrada):
    with st.chat_message("assistant"):
        with st.spinner("IAN está agitando la coctelera..."):
            response = st.session_state.chat_session.send_message(texto_entrada)
            raw_text = response.text.strip()
            datos_json = extraer_json(raw_text)
            
            if datos_json:
                # Limitamos a 3 por seguridad del frontend aunque la IA ya tiene la instrucción
                datos_json = datos_json[:3]
                for rec in datos_json:
                    # Ajustamos el tipo de medio si es miniserie (tratada como tv en TMDB)
                    media_type = "tv" if rec.get("tipo") in ["tv", "serie", "miniserie"] else "movie"
                    info = obtener_info_completa_tmdb(rec.get("titulo", ""), media_type, cod_pais)
                    rec.update(info)
                st.session_state.mensajes.append({"role": "assistant", "type": "recommendations", "data": datos_json})
            else:
                st.session_state.mensajes.append({"role": "assistant", "type": "text", "content": raw_text})
    st.rerun()

if btn_ficha:
    comanda = f"""
    [PETICIÓN DE FICHA DE CATA]
    - Energía: {f_ene}
    - Estilo: {f_pal}
    - Profundidad: {f_pro}
    - Formato: {f_for}
    - Notas extra: {f_extra}
    Por favor, sirva 3 opciones acorde a este perfil, priorizando plataformas populares.
    """
    st.session_state.mensajes.append({"role": "user", "type": "text", "content": "*(He enviado una nueva ficha de cata)*"})
    procesar_respuesta_ia(comanda)

if prompt := st.chat_input("Dígame algo más..."):
    st.session_state.mensajes.append({"role": "user", "type": "text", "content": prompt})
    procesar_respuesta_ia(prompt)