import json
 
import pandas as pd
import streamlit as st
from google import genai
from google.genai import types
 
MODEL = "gemini-3.5-flash"
 
# Se lee la API key desde st.secrets (recomendado) o variable de entorno.
# En Streamlit Cloud / local: crea .streamlit/secrets.toml con:
#   GEMINI_API_KEY = "AIza..."
_api_key = st.secrets.get("GEMINI_API_KEY") if hasattr(st, "secrets") else None
client = genai.Client(api_key=_api_key) if _api_key else genai.Client()
 
# Whitelist de columnas: evita que el modelo pida columnas inexistentes
# o intente algo fuera del alcance de la función.
COLUMNAS_PERMITIDAS = {
    "sucursal", "nombre", "ingrediente_id", "unidad_base", "alerta",
    "consumo_proyectado", "stock_actual_unidad_base", "necesidad_real",
    "cantidad_formatos", "pedido_sugerido_formatos", "diferencia_formatos",
    "cantidad_ordenada_unidad_base", "pedido_sugerido_unidad_base",
    "pedido_atipico", "metodo_proyeccion", "pedido_no_incluido",
}
 
CONSULTAR_DATOS_DECLARACION = {
    "name": "consultar_datos",
    "description": (
        "Consulta la tabla de resultados de pedidos de ingredientes. "
        "Permite filtrar por sucursal, ingrediente o tipo de alerta, "
        "y agrupar/sumar columnas numéricas. Úsala siempre antes de "
        "dar cifras concretas: nunca inventes números."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "filtro_sucursal": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Nombres exactos de sucursales a incluir.",
            },
            "filtro_ingrediente": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Nombres exactos de ingredientes a incluir.",
            },
            "filtro_alerta": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["SUBPEDIDO", "SOBREPEDIDO", "PEDIDO ADECUADO"],
                },
                "description": "Tipos de alerta a incluir.",
            },
            "agrupar_por": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Columnas por las que agrupar, ej. ['sucursal'] o "
                    "['sucursal', 'nombre']."
                ),
            },
            "columnas_a_sumar": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Columnas numéricas a sumar al agrupar, ej. "
                    "['diferencia_formatos']."
                ),
            },
            "ordenar_por": {
                "type": "string",
                "description": "Columna por la que ordenar el resultado.",
            },
            "orden_descendente": {
                "type": "boolean",
                "description": "true para descendente, false para ascendente.",
            },
            "limite_filas": {
                "type": "integer",
                "description": "Máximo de filas a devolver (por defecto 20, tope 50).",
            },
        },
    },
}
 
TOOLS = [types.Tool(function_declarations=[CONSULTAR_DATOS_DECLARACION])]
 
SYSTEM_PROMPT = (
    "Eres el asistente de datos de BarrioPizzaStock IA. Respondes en "
    "español, de forma breve y directa, sobre pedidos, stock e "
    "ingredientes de una cadena de pizzerías. SIEMPRE usa la función "
    "consultar_datos antes de dar una cifra concreta: nunca inventes "
    "números. Si la pregunta es ambigua, responde con la interpretación "
    "más razonable en vez de pedir aclaración. Si los datos consultados "
    "no contienen lo que se pregunta, dilo claramente en vez de suponer."
)
 
 
def ejecutar_consulta(df: pd.DataFrame, params: dict) -> list[dict]:
    """
    Ejecuta de forma segura los filtros/agrupaciones que pide el modelo,
    validando columnas contra COLUMNAS_PERMITIDAS.
    """
    data = df.copy()
 
    if params.get("filtro_sucursal"):
        data = data[data["sucursal"].isin(params["filtro_sucursal"])]
 
    columna_ingrediente = "nombre" if "nombre" in data.columns else "ingrediente_id"
    if params.get("filtro_ingrediente"):
        data = data[data[columna_ingrediente].isin(params["filtro_ingrediente"])]
 
    if params.get("filtro_alerta") and "alerta" in data.columns:
        data = data[data["alerta"].isin(params["filtro_alerta"])]
 
    agrupar_por = [
        c for c in params.get("agrupar_por", []) or []
        if c in COLUMNAS_PERMITIDAS and c in data.columns
    ]
    columnas_a_sumar = [
        c for c in params.get("columnas_a_sumar", []) or []
        if c in COLUMNAS_PERMITIDAS and c in data.columns
    ]
 
    if agrupar_por and columnas_a_sumar:
        data = data.groupby(agrupar_por, as_index=False)[columnas_a_sumar].sum()
 
    orden = params.get("ordenar_por")
    if orden and orden in data.columns:
        data = data.sort_values(
            orden, ascending=not params.get("orden_descendente", False)
        )
 
    limite = min(params.get("limite_filas", 20) or 20, 50)
    return data.head(limite).to_dict(orient="records")
 
 
def preguntar(pregunta: str, df: pd.DataFrame, historial: list | None = None):
    """
    Envía la pregunta a Gemini con acceso a la función consultar_datos.
    Devuelve (texto_respuesta, historial_actualizado) para guardar en
    st.session_state y mantener contexto entre preguntas.
    """
    contenidos = (historial or []) + [
        types.Content(role="user", parts=[types.Part(text=pregunta)])
    ]
 
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        tools=TOOLS,
    )
 
    respuesta = client.models.generate_content(
        model=MODEL, contents=contenidos, config=config,
    )
 
    # Mientras el modelo pida usar la función, la ejecutamos y le
    # devolvemos el resultado, hasta que responda con texto final.
    while True:
        llamadas_funcion = [
            parte.function_call
            for parte in respuesta.candidates[0].content.parts
            if parte.function_call is not None
        ]
 
        if not llamadas_funcion:
            break
 
        contenidos.append(respuesta.candidates[0].content)
 
        partes_resultado = []
        for llamada in llamadas_funcion:
            try:
                resultado = ejecutar_consulta(df, dict(llamada.args or {}))
                salida = {"resultado": resultado}
            except Exception as error:
                salida = {"error": str(error)}
 
            partes_resultado.append(
                types.Part.from_function_response(
                    name=llamada.name, response=salida,
                )
            )
 
        contenidos.append(types.Content(role="user", parts=partes_resultado))
 
        respuesta = client.models.generate_content(
            model=MODEL, contents=contenidos, config=config,
        )
 
    contenidos.append(respuesta.candidates[0].content)
    texto = respuesta.text or ""
 
    return texto, contenidos