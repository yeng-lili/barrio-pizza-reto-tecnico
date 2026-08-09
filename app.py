import streamlit as st
import plotly.express as px 
import pandas as pd 
import io 
import zipfile

from data_loader import load_files
from preprocess import (clean_ingredients, clean_consumption, clean_inventory, clean_orders)
from forecasting import forecast_consumption
from metrics import build_results
from alerts import classify_alerts, detect_anomalies
from chat_data import preguntar

#Configuracion del inicio del dashboard
st.set_page_config(
    page_title="BarrioPizzaStock IA", 
    layout="wide")

COLORES_ALERTAS = {
    'PEDIDO ADECUADO': "#4C8F67",
    "SOBREPEDIDO": "#E9B266",
    "SUBPEDIDO": "#E06464",
}

#Estado de la aplicacion del dashboard
if 'results' not in st.session_state:
    st.session_state.results = None
if 'consumo' not in st.session_state:
    st.session_state.consumo = None
if 'analizado' not in st.session_state:
    st.session_state.analizado = False
if 'sucursal_actual' not in st.session_state:
    st.session_state.sucursal_actual = None
if 'ingrediente_actual' not in st.session_state:
    st.session_state.ingrediente_actual = None

#Encabezado del dashboard
col_logo, col_titulo = st.columns ([1, 6])
with col_logo:
    st.image('assets/logo_barrio_pizza.png', width = 180)
    st.markdown("""
    <style>
    [data-testid="column"] {
    display: flex;
    align-items: center;}</style>
    """, unsafe_allow_html=True)

with col_titulo:
    st.title('BarrioPizzaStock IA')
    st.subheader('Sistema inteligente para planificar el abastecimiento de ingredientes')

#Carga y analisis de archivos

with st.expander(
    '1. Cargar archivos',
    expanded = not st.session_state.analizado,
):
    with st.form('form_archivos'):
        consumo_file = st.file_uploader("Adjunta el archivo consumo_historico", type=["csv"])
        ingredientes_file = st.file_uploader("Adjunta el archivo ingredientes", type=["csv"])
        inventario_file = st.file_uploader("Adjunta el archivo inventario_actual", type=["csv"])
        orden_file = st.file_uploader("Adjunta el archivo orden_compra_semana", type=["csv"])
        analizar = st.form_submit_button (
            'Analizar archivos', type = 'primary',
        )

    if analizar:
        archivos = [
            consumo_file,
            ingredientes_file,
            inventario_file,
            orden_file,
        ]

        if not all (archivo is not None for archivo in archivos):
            st.error (
                'Debes adjuntar los cuatros archivos CSV antes de realizar el ánalisis.'
            )
        else:
            try:
                ingredientes, consumo, inventario, ordenes = load_files (
                    ingredientes_file,
                    consumo_file,
                    inventario_file,
                    orden_file,
                )

                consumo = clean_consumption(consumo)
                ingredientes = clean_ingredients(ingredientes)
                inventario = clean_inventory(inventario)
                ordenes = clean_orders(ordenes)

                forecast = forecast_consumption(consumo)

                results = build_results (
                    forecast, inventario, ordenes, ingredientes,
                )

                results = classify_alerts(results)
                results = detect_anomalies (results)

                st.session_state.results = results
                st.session_state.consumo = consumo
                st.session_state.ingredientes = ingredientes
                st.session_state.inventario = inventario
                st.session_state.ordenes = ordenes
                st.session_state.forecast = forecast
                st.session_state.analizado = True

                st.success('Análisis completado correctamente.')

            except Exception as error:
                st.session_state.results = None
                st.session_state.consumo = None
                st.session_state.analizado = False
                st.error ( f'No se pudo completar el análisis: {error}')

#Funcion de detener la app si no hay datos
if (
    not st.session_state.analizado
    or st.session_state.results is None
):
    st.info (
        'Adjunta los archivos correspondiente y presiona «Analizar archivos» para comenzar el análisis. '
    )
    st.stop()

results = st.session_state.results.copy()
consumo = st.session_state.consumo.copy()


#Validacion de columnas

columnas_requeridas = {
    'sucursal',
    'ingrediente_id',
    'consumo_proyectado',
    'cantidad_formatos',
    'pedido_sugerido_formatos',
    'alerta'
}

columnas_faltantes = (
    columnas_requeridas  - set(results.columns)
)

if columnas_faltantes:
    st.error ('Faltan estas columnas en results: ' + ', '.join(sorted(columnas_faltantes)))
    st.stop()

# Usamos el nombre visible del ingrediente
# Si no existe, usamos ingrediente_id
columna_ingrediente = (
    "nombre"
    if "nombre" in results.columns
    else "ingrediente_id")

#Listas para los filtros

sucursales = sorted (
    results['sucursal'].dropna().unique().tolist()
)

ingredientes = sorted (
    results[columna_ingrediente].dropna().unique().tolist()
)

if not sucursales or not ingredientes:
    st.error(
        'No se encontraron sucursales o ingredientes en los resultados.'
    )
    st.stop()

if (
    st.session_state.sucursal_actual not in sucursales):
    st.session_state.sucursal_actual = sucursales [0]

if (
    st.session_state.ingrediente_actual not in ingredientes):
    st.session_state.ingrediente_actual = ingredientes [0]


#Pestañas

tab_resumen,  tab_alertas, tab_ordenes, tab_proyeccion, tab_chat = st.tabs (
    [
        'Resumen',
        "Alertas y anomalías",
        'Órdenes de compra',
        'Proyección y necesidad',
        'Chat con los datos',
       
    ]
)

#Resumen General 

with tab_resumen:
    st.header ('Resumen General')
    st.caption("Vista consolidada del estado de las órdenes.")
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1: 
        st.metric(
            'Total de órdenes',
            len(results),
        )

    with col2:
        st.metric(
            "Riesgo de quiebre",
            int (
                (
                    results['alerta'] == 'SUBPEDIDO'
                ).sum()
            ),
        )

    with col3:
        st.metric (
            'Sobrepedidos',
            int (
                (
                    results['alerta'] == 'SOBREPEDIDO'
                ).sum()
            ),
        )

    with col4:
        st.metric (
            'Pedidos adecuados',
            int (
                (
                    results['alerta'] == 'PEDIDO ADECUADO'
                ).sum()
            ),
        )

    with col5:
        st.metric(
            'No incluido en la orden',
            int (
                results.get(
                    'pedido_no_incluido',
                    pd.Series(dtype=bool),
                ).sum()
            ),
        )

    st.subheader('Estado de las órdenes')
    resumen_alertas = (
        results ['alerta'].value_counts().reindex(
            [
                'PEDIDO ADECUADO',
                'SOBREPEDIDO',
                'SUBPEDIDO',
            ],
            fill_value= 0,
        )
        .rename_axis('estado')
        .reset_index(name = 'cantidad')
    )
    
    fig_alertas = px.bar(
        resumen_alertas,
        x = 'estado',
        y = 'cantidad',
        color = 'estado',
        text = 'cantidad',
        color_discrete_map = COLORES_ALERTAS,
        category_orders = {
            'estado': [
                'PEDIDO ADECUADO',
                'SOBREPEDIDO',
                'SUBPEDIDO',
                ]
            },
        )
    
    fig_alertas.update_layout (
        height=400,
        showlegend=False,
        xaxis_title=None,
        yaxis_title="Cantidad de órdenes",
        margin=dict(
            l=20,
            r=20,
            t=30,
            b=30,
            ),
        )
    
    fig_alertas.update_traces (
        textposition = 'outside'
        )
    
    st.plotly_chart (
        fig_alertas,
         use_container_width = True,
    )
    
    st.subheader ('Alertas por sucursal')
    
    resumen_sucursal = (
        results.groupby(['sucursal', 'alerta']).size().reset_index(name = 'cantidad')
    )
    
    
    fig_sucursal = px.bar(
        resumen_sucursal,
        x="sucursal",
        y="cantidad",
        color="alerta",
        barmode="group",
        color_discrete_map=COLORES_ALERTAS,
        category_orders={
            "alerta": [
                "PEDIDO ADECUADO",
                "SOBREPEDIDO",
                "SUBPEDIDO",
            ]
        },
        labels={
            "sucursal": "Sucursal",
            "cantidad": "Cantidad de órdenes",
            "alerta": "Estado",
        },
    )

    fig_sucursal.update_layout (
        height=380,
        xaxis_title='Cantidad de órdenes',
        yaxis_title=None,
        legend_title=None,
        margin=dict(
            l=20,
            r=20,
            t=30,
            b=30,
        ),
    )
    
    fig_sucursal.update_xaxes(
        tickangle = -25
    )

    st.plotly_chart(
        fig_sucursal, use_container_width= True,
    )

#Pestaña Alertas
with tab_alertas:

    st.subheader("Alertas y acciones recomendadas")

    resultados_actuales = st.session_state.results.copy()

    if (
        'es_perecedero' not in resultados_actuales.columns and 
        'ingredientes' in st.session_state and
        st.session_state.ingredientes is not None and
        'es_perecedero' in st.session_state.ingredientes.columns
    ):
        resultados_actuales = resultados_actuales.merge(
            st.session_state.ingredientes[
                ['ingrediente_id', 'es_perecedero']
            ],
            on ='ingrediente_id', how = 'left',
        )

    alertas = resultados_actuales[
        resultados_actuales["alerta"] != "PEDIDO ADECUADO"
    ].copy()

    if 'es_perecedero' in alertas.columns:
        alertas['_es_perecedero_bool'] = (
            alertas['es_perecedero']
            .astype(str)
            .str.strip()
            .str.lower()
            .isin(['si', "sí", "true", "1", "yes"])
        )
    else:
        alertas['_es_perecedero_bool']= False

    alertas['_no_incluido_bool'] = alertas.get(
        'pedido_no_incluido', False
    ).fillna(False).astype(bool)

    alertas['_perecedero_urgente'] = (
        (alertas['alerta'] == 'SOBREPEDIDO') & 
        alertas ['_es_perecedero_bool']
    )

    alertas['_magnitud'] = alertas['diferencia_formatos'].abs()

    def rango_prioridad(fila):
        if fila['_no_incluido_bool']:
            return 0
        if fila['alerta'] == 'SUBPEDIDO':
            return 1
        if fila['_perecedero_urgente']:
            return 2
        return 3

    alertas['_rango_prioridad'] = alertas.apply(rango_prioridad, axis=1)

    alertas = alertas.sort_values(
        ['_rango_prioridad', '_magnitud'],
        ascending=[True, False],
    )

    if alertas.empty:
        st.success(
            "Todos los pedidos están dentro "
            "de lo proyectado."
        )
    else:

        st.warning(
            f"Se detectaron {len(alertas)} "
            "órdenes que requieren revisión."
        )

        st.subheader('Alertas detectadas')

        for _, fila in alertas.iterrows():
            mensaje = fila.get('mensaje_alerta')

            if pd.isna(mensaje) or not mensaje:
                mensaje = (
                    f"{fila['sucursal']} debe revisar el pedido de"
                    f"{fila.get('nombre', fila['ingrediente_id'])}."
                )

            no_incluido = bool(fila.get('_no_incluido_bool', False))
            es_perecedero_urgente = bool(
                fila.get('_perecedero_urgente', False)
            )

            if no_incluido:
                mensaje = f'NO PEDIDO — {mensaje}'
            elif es_perecedero_urgente:
                mensaje = f'URGENTE (perecedero) — {mensaje}'

            if fila['alerta'] == 'SUBPEDIDO':
                st.error(mensaje)
            elif fila ['alerta'] == 'SOBREPEDIDO':
                st.warning(mensaje)

        st.divider ()

        st.subheader(
            "Resumen de pedidos que requieren atención"
        )

        columnas_alertas = [
            columna
            for columna in [
                "sucursal",
                "nombre",
                "cantidad_formatos",
                "pedido_sugerido_formatos",
                "alerta",
            ]
            if columna in alertas.columns
        ]

        tabla_alertas = alertas[
            columnas_alertas
        ].rename(
            columns={
                "sucursal": "Sucursal",
                "nombre": "Ingrediente",
                "cantidad_formatos": (
                    "Pedido actual"
                ),
                "pedido_sugerido_formatos": (
                    "Pedido sugerido"
                ),
                "alerta": "Estado",
            }
        )

        st.dataframe(
            tabla_alertas,
            use_container_width=True,
            hide_index=True,
        )

        st.divider()

        st.subheader( "Pedidos atípicos por sucursal")
        if "pedido_atipico" in resultados_actuales.columns:
            pedido_atipico = resultados_actuales[
                 resultados_actuales["pedido_atipico"] == True
            ].copy()
        else: 
            pedido_atipico = resultados_actuales.iloc[0:0]

        if pedido_atipico.empty:
            st.info(
                "No se detectaron pedidos atípicos "
                "entre las sucursales."
        )

        else:
            st.warning(
                f"Se detectaron {len(pedido_atipico)} "
                "pedidos atípicos."
            )

            columnas_raras = [
                columna
                for columna in [
                    "sucursal",
                    "nombre",
                    "cantidad_ordenada_unidad_base",
                    'motivo_atipico',
                ]
                if columna in pedido_atipico.columns
            ]

            tabla_atipicos = pedido_atipico[columnas_raras].rename(columns={
                "sucursal": "Sucursal",
                "nombre": "Ingrediente",
                "cantidad_ordenada_unidad_base": "Cantidad pedida",
                "motivo_atipico": "Motivo",
            })

            st.dataframe(
                tabla_atipicos,
                use_container_width=True,
                hide_index=True,
            )
    

@st.fragment
def mostrar_ordenes(
    results,
    ingredientes,
    inventario,
    forecast,
):
    st.header("Órdenes de compra")

    st.caption(
        "Puedes cargar otro archivo o modificar "
        "las cantidades directamente."
    )

    nuevo_archivo_ordenes = st.file_uploader(
        "Reemplazar archivo de órdenes",
        type=["csv"],
        key="nuevo_archivo_ordenes",
    )

    if nuevo_archivo_ordenes is not None:
        ordenes_nuevas = pd.read_csv(
            nuevo_archivo_ordenes
        )

        ordenes_nuevas = clean_orders(
            ordenes_nuevas
        )

        st.session_state.ordenes = (
            ordenes_nuevas
        )

        st.rerun(scope="app")

    ordenes_actuales = (
        st.session_state.ordenes.copy()
    )

    st.subheader("Editar cantidades")

    columnas_editor = [
        columna
        for columna in [
            "sucursal",
            "ingrediente_id",
            "cantidad_formatos",
        ]
        if columna in ordenes_actuales.columns
    ]

    ordenes_para_editar = (
        ordenes_actuales[columnas_editor].copy()
    )

    ordenes_editadas = st.data_editor(
        ordenes_para_editar,
        use_container_width=True,
        hide_index=True,
        disabled=[
            columna
            for columna in columnas_editor
            if columna != "cantidad_formatos"
        ],
        key="editor_ordenes",
    )

    if st.button(
        "Actualizar alertas",
        type="primary",
        key="actualizar_alertas",
    ):
        ordenes_editadas = (
            ordenes_editadas.copy()
        )

        ordenes_editadas[
            "cantidad_formatos"
        ] = pd.to_numeric(
            ordenes_editadas[
                "cantidad_formatos"
            ],
            errors="coerce",
        ).fillna(0)

        resultados_actualizados = build_results(
            forecast,
            inventario,
            ordenes_editadas,
            ingredientes,
        )

        resultados_actualizados = classify_alerts(
            resultados_actualizados
        )

        resultados_actualizados = detect_anomalies(
            resultados_actualizados
        )

        st.session_state.ordenes = (
            ordenes_editadas
        )

        st.session_state.results = (
            resultados_actualizados
        )

        st.success(
            "Órdenes actualizadas y alertas recalculadas."
        )

        

        st.rerun(scope='app')

        # No uses st.rerun() aquí.
        # El fragmento ya se actualiza por el botón.

    st.divider()

    st.subheader(
        "Órdenes agrupadas por proveedor"
    )

    resultados_actuales = (
        st.session_state.results
    )

    columnas_proveedor = [
        columna
        for columna in [
            "proveedor",
            "sucursal",
            "nombre",
            "formato_compra",
            "cantidad_formatos",
            "pedido_sugerido_formatos",
            "alerta",
        ]
        if columna in resultados_actuales.columns
    ]

    tabla_proveedores = (
        resultados_actuales[columnas_proveedor]
        .sort_values(
            [
                "proveedor",
                "sucursal",
            ]
        )
    )

    buffer_zip = io.BytesIO()
    with zipfile.ZipFile(buffer_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
        for proveedor, grupo in tabla_proveedores.groupby('proveedor'):
            csv_bytes = (
                grupo.drop(columns=['proveedor'])
                .to_csv(index=False)
                .encode('utf-8-sig')
            )
            zf.writestr(f'orden_{proveedor}.csv', csv_bytes)

    st.download_button(
        label = 'Descargar todas las órdenes por proveedor (.zip)',
        data= buffer_zip.getvalue(),
        file_name='ordenes_por_proveedor.zip',
        mime='application/zip',
        key='descargar_todo_zip',
    )

    for proveedor, grupo in (
        tabla_proveedores.groupby("proveedor")
    ):
        with st.expander(
            f"Proveedor: {proveedor}"
        ):
            st.dataframe(
                grupo.drop(
                    columns=["proveedor"]
                ),
                use_container_width=True,
                hide_index=True,
            )

            csv_proveedor = grupo.to_csv(
                index=False
            ).encode("utf-8-sig")

            st.download_button(
                label=(
                    f"Descargar orden de "
                    f"{proveedor}"
                ),
                data=csv_proveedor,
                file_name=(
                    f"orden_{proveedor}.csv"
                ),
                mime="text/csv",
                key=f"descargar_{proveedor}",
            )

@st.fragment
def mostrar_proyeccion(
    results,
    consumo,
    sucursales,
    ingredientes,
    columna_ingrediente,
):
    st.header("Proyección y necesidad")

    st.caption(
        "Consulta el consumo histórico, la proyección, "
        "el inventario y el pedido sugerido."
    )

    if (
        st.session_state.sucursal_actual
        not in sucursales
    ):
        st.session_state.sucursal_actual = sucursales[0]

    if (
        st.session_state.ingrediente_actual
        not in ingredientes
    ):
        st.session_state.ingrediente_actual = ingredientes[0]

    with st.form("form_filtros"):

        col1, col2 = st.columns(2)

        with col1:
            sucursal_seleccionada = st.selectbox(
                "Selecciona una sucursal",
                sucursales,
                index=sucursales.index(
                    st.session_state.sucursal_actual
                ),
                key="filtro_sucursal",
            )

        with col2:
            ingrediente_seleccionado = st.selectbox(
                "Selecciona un ingrediente",
                ingredientes,
                index=ingredientes.index(
                    st.session_state.ingrediente_actual
                ),
                key="filtro_ingrediente",
            )

        aplicar_filtros = st.form_submit_button(
            "Aplicar filtros",
            type="primary",
        )

    # Este bloque debe estar FUERA del form
    if aplicar_filtros:
        st.session_state.sucursal_actual = (
            sucursal_seleccionada
        )

        st.session_state.ingrediente_actual = (
            ingrediente_seleccionado
        )

    sucursal_actual = (
        st.session_state.sucursal_actual
    )

    ingrediente_actual = (
        st.session_state.ingrediente_actual
    )

    detalle = results[
        (
            results["sucursal"]
            == sucursal_actual
        )
        & (
            results[columna_ingrediente]
            == ingrediente_actual
        )
    ]

    st.markdown(
        f"**Mostrando:** "
        f"{ingrediente_actual} · "
        f"{sucursal_actual}"
    )

    if detalle.empty:
        st.warning(
            "No existe información para "
            "la selección realizada."
        )
        return

    ingrediente_id = (
        detalle.iloc[0]["ingrediente_id"]
    )

    historico = consumo[
        (
            consumo["sucursal"]
            == sucursal_actual
        )
        & (
            consumo["ingrediente_id"]
            == ingrediente_id
        )
    ].copy()

    if not historico.empty:

        historico["semana_num"] = pd.to_numeric(
            historico["semana"]
            .astype(str)
            .str.extract(r"(\d+)")[0],
            errors="coerce",
        )

        historico = historico.sort_values(
            "semana_num"
        )

        fig_historico = px.line(
            historico,
            x="semana",
            y="consumo_unidad_base",
            markers=True,
            title="Consumo histórico",
            labels={
                "semana": "Semana",
                "consumo_unidad_base": (
                    "Consumo en unidad base"
                ),
            },
        )

        fig_historico.update_layout(
            height=400,
            xaxis_title=None,
            yaxis_title="Consumo",
        )

        st.plotly_chart(
            fig_historico,
            use_container_width=True,
        )

    columnas_detalle = [
        columna
        for columna in [
            "sucursal",
            "nombre",
            "unidad_base",
            "consumo_proyectado",
            "stock_actual_unidad_base",
            "necesidad_real",
            "cantidad_formatos",
            "pedido_sugerido_formatos",
            "alerta",
            
        ]
        if columna in detalle.columns
    ]

    st.subheader(
        "Detalle de proyección y necesidad"
    )

    st.dataframe(
        detalle[columnas_detalle],
        use_container_width=True,
        hide_index=True,
    )

    st.divider()

    with st.expander("Comparativo semanal por sucursal"):
        ingredientes_disponibles = sorted(
            results[columna_ingrediente].dropna().unique().tolist()
        )

        ingrediente_comparar = st.selectbox(
            "Selecciona un ingrediente para comparar entre sucursales",
            ingredientes_disponibles,
            index=ingredientes_disponibles.index(ingrediente_actual)
            if ingrediente_actual in ingredientes_disponibles else 0,
            key="ingrediente_comparativo_semanal",
        )

        ingrediente_id_comparar = results.loc[
            results[columna_ingrediente] == ingrediente_comparar, "ingrediente_id"
            ].iloc[0]

        # Histórico semanal de ese ingrediente en todas las sucursales
        consumo_ingrediente = consumo[
            consumo["ingrediente_id"] == ingrediente_id_comparar
            ].copy()

        consumo_ingrediente["semana_num"] = pd.to_numeric(
            consumo_ingrediente["semana"].astype(str).str.extract(r"(\d+)")[0],
            errors="coerce",
        )

        orden_semanas = (
            consumo_ingrediente.drop_duplicates("semana")
            .sort_values("semana_num")["semana"]
            .tolist()
        )

        pivote = consumo_ingrediente.pivot_table(
            index="sucursal",
            columns="semana",
            values="consumo_unidad_base",
            aggfunc="sum",
            )[orden_semanas]

        # Se agrega la proyección (S7) como columna de referencia
        proyeccion_ingrediente = results[
            results[columna_ingrediente] == ingrediente_comparar
            ][["sucursal", "consumo_proyectado"]].set_index("sucursal")

        pivote = pivote.join(
            proyeccion_ingrediente.rename(
                columns={"consumo_proyectado": "Proyectado (S7)"}
            )
        )

        st.caption(
            f"Consumo semanal de {ingrediente_comparar} por sucursal, con la proyección para la próxima semana.")

        st.dataframe(pivote, use_container_width=True)

        fig_comparativo = px.line(
            consumo_ingrediente.sort_values("semana_num"),
            x="semana",
            y="consumo_unidad_base",
            color="sucursal",
            markers=True,
            title=f"Consumo histórico de {ingrediente_comparar} por sucursal",
        )

        fig_comparativo.update_layout(height=380, xaxis_title=None, yaxis_title="Consumo")
        st.plotly_chart(fig_comparativo, use_container_width=True)




with tab_ordenes:
    mostrar_ordenes(
        results=st.session_state.results,
        ingredientes=st.session_state.ingredientes,
        inventario=st.session_state.inventario,
        forecast=st.session_state.forecast,
    )


with tab_proyeccion:
    mostrar_proyeccion(
        results=st.session_state.results,
        consumo=st.session_state.consumo,
        sucursales=sucursales,
        ingredientes=ingredientes,
        columna_ingrediente=columna_ingrediente,
    )

with tab_chat:
    st.header("Chat con los datos")

    if "chat_historial" not in st.session_state:
        st.session_state.chat_historial = []

    for contenido in st.session_state.chat_historial:
        texto_partes = "".join(
            parte.text for parte in contenido.parts
            if getattr(parte, "text", None)
        )
        if not texto_partes:
            continue  # se salta llamadas/resultados de función, no son para mostrar

        if contenido.role == "user":
            with st.chat_message("user"):
                st.write(texto_partes)
        elif contenido.role == "model":
            with st.chat_message("assistant"):
                st.write(texto_partes)

    pregunta = st.chat_input("Pregunta sobre tus pedidos, por ejemplo: ¿qué sucursal está pidiendo demasiado queso?")

    if pregunta:
        with st.chat_message("user"):
            st.write(pregunta)
        with st.spinner("Consultando..."):
            texto, st.session_state.chat_historial = preguntar(
                pregunta, results, st.session_state.chat_historial
            )
        with st.chat_message("assistant"):
            st.write(texto)

