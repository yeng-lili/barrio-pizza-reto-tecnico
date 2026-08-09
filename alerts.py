import pandas as pd
import numpy as np

def numero(valor, default = 0):
    '''
    Convierte valores vacios o texto a numero.
    '''
    valor = pd.to_numeric(valor, errors='coerce')

    if pd.isna(valor):
        return default
    return float(valor)

def _formatear_numero(valor):
    '''
    Evita mostrar numeros como 2.0 o nan.
    '''
    if pd.isna(valor):
        return '0'
    valor = float(valor)

    if valor.is_integer():
        return str(int(valor))
    return f'{valor:.2f}'.rstrip('0').rstrip('.')

def classify_alerts(df):
    df = df.copy()

    def classify(row):
        actual = row['cantidad_formatos']
        sugerido = row['pedido_sugerido_formatos']

        if actual < sugerido:
            return 'SUBPEDIDO'
        elif actual > sugerido:
            return 'SOBREPEDIDO'
        return 'PEDIDO ADECUADO'

    def build_message (row):
        sucursal = row.get("sucursal", "Sucursal desconocida")
        ingrediente = row.get("nombre", "Ingrediente")
        unidad = row.get('unidad_base', '')

        actual = numero(row.get("cantidad_ordenada_unidad_base"))
        sugerido = numero(row.get("pedido_sugerido_unidad_base"))

        if row["alerta"] == "SUBPEDIDO":
            faltante = sugerido - actual
            faltante_texto = _formatear_numero(faltante)

            return (
                f"Alerta: {sucursal} está pidiendo "
                f"{faltante_texto} {unidad} de {ingrediente} "
                "menos que lo proyectado → riesgo de quiebre."
            )

        if row["alerta"] == "SOBREPEDIDO":
            exceso = actual - sugerido
            exceso_texto = _formatear_numero(exceso)

            return (
                f"Alerta: {sucursal} está pidiendo "
                f"{exceso_texto} {unidad} de {ingrediente} "
                "más que lo proyectado → posible sobrepedido."
            )

        return f"Pedido adecuado de {ingrediente}."

    df["alerta"] = df.apply(classify, axis=1)
    df["mensaje_alerta"] = df.apply(build_message, axis=1)

    return df

def detect_anomalies(df):
    df = df.copy()

    if 'cantidad_ordenada_unidad_base' in df.columns:
        columna_pedido = 'cantidad_ordenada_unidad_base'
    elif 'cantidad_unidad_base_equivalencia' in df.columns:
        columna_pedido = 'cantidad_unidad_base_equivalencia'

    else:
        raise KeyError (
            'No se encontró una columna con la cantidad'
            'ordenada en unidad base.'
        )

    df ['ratio_pedido_consumo'] = np.where (
        df ['consumo_proyectado'] > 0, 
        df[columna_pedido] / df['consumo_proyectado'],
        0
    )

    """
    Mediana del ratio para cada ingrediente
    """

    mediana_por_ingrediente = (
        df.groupby('ingrediente_id') [
            'ratio_pedido_consumo'
        ]. transform('median')
    )

    """
    Desviacion absoluta respecto a la mediana
    """

    desviacion = (
        df ['ratio_pedido_consumo'] - mediana_por_ingrediente
    ).abs()

    '''
    MAD : desviacion absoluta mediana
    '''
    mad_por_ingrediente = (
        desviacion.groupby (
            df['ingrediente_id']
        ).transform('median')
    )

    '''
    Si MAD es 0, marcar como atipico si se aleja mas de 50%
    '''

    df['pedido_atipico'] = np.where(
        mediana_por_ingrediente == 0,
        desviacion > 0.50,
        desviacion > 3 * mad_por_ingrediente
    )

    df['pedido_atipico'] = (
        df['pedido_atipico'].fillna(False).astype(bool)
    )

    df['mediana_ratio_sucursal'] = mediana_por_ingrediente
    df['desviacion_vs_mediana'] = desviacion

    def _motivo(row):
        if not row['pedido_atipico']:
            return ''
        ratio = row['ratio_pedido_consumo']
        mediana = row['mediana_ratio_sucursal']
        if mediana and mediana > 0:
            veces = ratio / mediana
            veces_texto = _formatear_numero(veces)
            if ratio > mediana:
                return f'Pide {veces_texto}x lo habitual de esa sucursal'
            return 'Pide muy por debajo de lo habitual de esa sucursal'
        return 'Pide muy por encima de lo habitual de esa sucursal'
    
    df['motivo_atipico'] = df.apply(_motivo, axis=1)

    return df