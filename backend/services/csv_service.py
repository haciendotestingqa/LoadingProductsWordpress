"""
Servicio para leer y procesar el archivo CSV de títulos.
"""
import csv
import os
from pathlib import Path


def load_titles():
    """
    Lee el archivo input.csv desde la raíz del proyecto.
    
    Returns:
        list: Lista de diccionarios con formato [{"id": 1, "titulo": "..."}, ...]
    """
    # Obtener la ruta del proyecto (subir dos niveles desde este archivo)
    project_root = Path(__file__).parent.parent.parent
    csv_path = project_root / "input.csv"
    
    if not csv_path.exists():
        raise FileNotFoundError(f"No se encontró el archivo input.csv en {csv_path}")
    
    titles = []
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                titles.append({
                    "id": int(row['id']),
                    "titulo": row['titulo'].strip()
                })
    except Exception as e:
        raise Exception(f"Error al leer input.csv: {str(e)}")
    
    return titles
