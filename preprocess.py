import pandas as pd 

def clean_ingredients(ingredientes):
    df = ingredientes.copy()
    df.columns = df.columns.str.strip()
    df['ingrediente_id'] = df['ingrediente_id'].str.strip().str.lower()
    df['es_perecedero'] = df['es_perecedero'].astype(str).str.strip().str.lower().isin(['si', 'sí'])
    return df

def clean_consumption(consumo):
    df = consumo.copy()
    df['sucursal'] = df['sucursal'].str.strip()
    df['ingrediente_id'] = df['ingrediente_id'].str.strip().str.lower()
    df['semana'] = df['semana'].str.strip()
    df['consumo_unidad_base'] = pd.to_numeric(df['consumo_unidad_base'], errors='coerce').fillna(0)
    return df

def clean_inventory(inventario):
    df = inventario.copy()
    df['sucursal'] = df['sucursal'].str.strip()
    df['ingrediente_id'] = df['ingrediente_id'].str.strip().str.lower()
    df['stock_actual_unidad_base'] = pd.to_numeric(df['stock_actual_unidad_base'], errors='coerce')
    return df

def clean_orders(orden):
    df = orden.copy()
    df['sucursal'] = df['sucursal'].str.strip()
    df['ingrediente_id'] = df['ingrediente_id'].str.strip().str.lower()
    df['cantidad_formatos'] = pd.to_numeric(df['cantidad_formatos'], errors='coerce')
    return df
