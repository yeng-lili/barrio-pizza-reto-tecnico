import numpy as np
import pandas as pd

def forecast_consumption(consumo):
    resultados = []

    for (sucursal, ingrediente_id), grupo in consumo.groupby(['sucursal', 'ingrediente_id']):
        grupo = grupo.copy()

        grupo['semana_num'] = (
            grupo['semana'].astype(str).str.extract(r'(\d+)').astype(float)
        )

        grupo = grupo.sort_values('semana_num')

        valores = grupo['consumo_unidad_base'].dropna()

        if len(valores) == 0:
            continue

     
        #Detectar valores atipicos usando el rango intercuartilico (IQR)
        

        q1 = valores.quantile(0.25)
        q3 = valores.quantile(0.75)
        iqr = q3 - q1

        limite_inferior = q1 - 1.5 * iqr
        limite_superior = q3 + 1.5 * iqr

        grupo_limpio = grupo[
            grupo['consumo_unidad_base']. between
            (limite_inferior,
            limite_superior)
            
        ]

       
        #Si quedan poco datos, usar todo los datos historicos 
        

        if len(grupo_limpio) < 3:
            grupo_limpio = grupo

        x = grupo_limpio['semana_num'].to_numpy()
        y = grupo_limpio['consumo_unidad_base'].to_numpy()

        if len(x) >= 3 and len(np.unique(x)) >=2:
            pendiente, intercepto = np.polyfit(x, y, 1)

            """
            Siguiente semana despues de S6
            """

            proyeccion = pendiente * 7 + intercepto
            metodo = 'Proyección basada en tendencia'

        else:
            proyeccion = np.mean(y) if len(y) > 0 else 0
            metodo = 'Promedio simple'

        resultados.append({
            'sucursal': sucursal,
            'ingrediente_id': ingrediente_id,
            'consumo_proyectado': max(float(proyeccion), 0),
            'metodo_proyeccion': metodo
        })

    return pd.DataFrame(resultados)
