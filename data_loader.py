import pandas as pd
def load_files(ing_file, cons_file, inv_file, ord_file):
    """
    Load the CSV files into pandas DataFrames.

    Parameters:
    ing_file (UploadedFile): The uploaded ingredients CSV file.
    cons_file (UploadedFile): The uploaded consumption CSV file.
    inv_file (UploadedFile): The uploaded inventory CSV file.
    ord_file (UploadedFile): The uploaded order CSV file.

    Returns:
    tuple: A tuple containing the loaded DataFrames for ingredients, consumption, inventory, and orders.
    """
    ingredientes = pd.read_csv(ing_file)
    consumo = pd.read_csv(cons_file)
    inventario = pd.read_csv(inv_file)
    orden = pd.read_csv(ord_file)

    return ingredientes, consumo, inventario, orden
