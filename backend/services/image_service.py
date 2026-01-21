"""
Servicio para escanear y leer la estructura de carpetas de imágenes.
"""
import os
from pathlib import Path
from typing import List, Dict


def get_collections() -> List[str]:
    """
    Escanea yupoo_downloads/ y retorna los nombres de carpetas de nivel 1 (colecciones).
    
    Returns:
        list: Lista de nombres de colecciones, ej: ["Trapstar系列"]
    """
    project_root = Path(__file__).parent.parent.parent
    yupoo_dir = project_root / "yupoo_downloads"
    
    if not yupoo_dir.exists():
        return []
    
    collections = []
    for item in yupoo_dir.iterdir():
        if item.is_dir():
            collections.append(item.name)
    
    return sorted(collections)


def get_products(collection_name: str) -> List[Dict]:
    """
    Escanea yupoo_downloads/{collection}/ y retorna todos los productos.
    
    Args:
        collection_name: Nombre de la colección a escanear
        
    Returns:
        list: Lista de diccionarios con información de productos:
        {
            "collection": "Trapstar系列",
            "page": "3",
            "name": "款号：1006",
            "images": ["09591a65.jpg", ...],
            "image_paths": ["yupoo_downloads/Trapstar系列/3/款号：1006/09591a65.jpg", ...]
        }
    """
    project_root = Path(__file__).parent.parent.parent
    collection_dir = project_root / "yupoo_downloads" / collection_name
    
    if not collection_dir.exists():
        return []
    
    products = []
    
    # Escanear cada página (carpetas numéricas)
    for page_dir in sorted(collection_dir.iterdir(), key=lambda x: x.stat().st_mtime):
        if not page_dir.is_dir():
            continue
        
        page_name = page_dir.name
        
        # Escanear cada producto dentro de la página
        # Ordenar por fecha de modificación (más antigua primero)
        product_dirs = sorted(
            [d for d in page_dir.iterdir() if d.is_dir()],
            key=lambda x: x.stat().st_mtime
        )
        
        for product_dir in product_dirs:
            product_name = product_dir.name
            
            # Obtener todas las imágenes del producto
            # Ordenar por fecha de modificación (mtime ascendente)
            image_files = sorted(
                [f for f in product_dir.iterdir() if f.is_file() and f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.webp']],
                key=lambda x: x.stat().st_mtime
            )
            
            images = [f.name for f in image_files]
            # Rutas relativas desde la raíz del proyecto para el frontend
            image_paths = [f"yupoo_downloads/{collection_name}/{page_name}/{product_name}/{f.name}" for f in image_files]
            
            products.append({
                "collection": collection_name,
                "page": page_name,
                "name": product_name,
                "images": images,
                "image_paths": image_paths
            })
    
    return products
