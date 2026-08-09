import math

import pandas as pd
import numpy as np

def build_results(forecast, inventory, orders, ingredients):
    df = forecast.merge(inventory, on=['sucursal', 'ingrediente_id'], how='left')
    df = df.merge(orders, on=['sucursal', 'ingrediente_id'], how='left')
    df = df.merge(ingredients, on='ingrediente_id', how='left')    

    df['stock_actual_unidad_base'] = df['stock_actual_unidad_base'].fillna(0)
    df['consumo_proyectado'] = df['consumo_proyectado'].fillna(0)
    df['unidad_base_por_formato'] = df['unidad_base_por_formato'].fillna(0)
    df['pedido_no_incluido'] = df['cantidad_formatos'].isna()
    df['cantidad_formatos'] = df['cantidad_formatos'].fillna(0)

    df['necesidad_real'] = df['consumo_proyectado'] - df['stock_actual_unidad_base']
    df['cantidad_unidad_base_equivalente'] = df['cantidad_formatos'] * df['unidad_base_por_formato']

    def calcular_pedido_sugerido(row):  
        necesidad = row['necesidad_real']
        formato = row['unidad_base_por_formato']
        if pd.isna(formato) or formato <= 0:
            return 0
        return max(math.ceil(necesidad / formato), 0) 

    
    df['pedido_sugerido_formatos'] = df.apply(calcular_pedido_sugerido, axis=1)
    df['pedido_sugerido_unidad_base'] = df['pedido_sugerido_formatos'] * df['unidad_base_por_formato']
    df['diferencia_formatos'] = df['cantidad_formatos'] - df['pedido_sugerido_formatos']
    df['cantidad_ordenada_unidad_base'] = (
        df['cantidad_formatos'] * df['unidad_base_por_formato']
    )

    return df


                                                   