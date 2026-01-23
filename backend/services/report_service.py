"""
Servicio para gestión de reportes de productos procesados.
"""
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from threading import RLock

logger = logging.getLogger(__name__)

# Obtener la ruta del proyecto
PROJECT_ROOT = Path(__file__).parent.parent.parent
REPORT_FILE = PROJECT_ROOT / "reporte.json"

# RLock (Reentrant Lock) para evitar deadlocks cuando load_report llama a save_report
report_lock = RLock()


def load_report() -> Dict:
    """
    Carga el reporte desde el archivo JSON.
    Si el archivo no existe o está vacío, crea uno nuevo con estructura inicial.
    
    Returns:
        Dict con estructura: {"productos": [...]}
    """
    with report_lock:
        if not REPORT_FILE.exists():
            logger.info(f"Archivo de reporte no existe. Creando nuevo en: {REPORT_FILE}")
            initial_data = {"productos": []}
            save_report(initial_data)
            return initial_data
        
        # Verificar si el archivo está vacío
        if REPORT_FILE.stat().st_size == 0:
            logger.info(f"Archivo de reporte está vacío. Inicializando con estructura correcta.")
            initial_data = {"productos": []}
            save_report(initial_data)
            return initial_data
        
        try:
            with open(REPORT_FILE, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                
                # Si el contenido está vacío o solo tiene espacios
                if not content:
                    logger.info(f"Archivo de reporte tiene contenido vacío. Inicializando.")
                    initial_data = {"productos": []}
                    save_report(initial_data)
                    return initial_data
                
                # Intentar parsear el JSON
                data = json.loads(content)
                logger.info(f"Reporte cargado exitosamente. Total productos: {len(data.get('productos', []))}")
                return data
                
        except json.JSONDecodeError as e:
            logger.error(f"Error al decodificar JSON del reporte: {str(e)}")
            # Solo crear backup si el archivo tiene contenido (no está vacío)
            if REPORT_FILE.stat().st_size > 0:
                backup_path = REPORT_FILE.with_suffix('.json.backup')
                import shutil
                shutil.copy(REPORT_FILE, backup_path)
                logger.warning(f"Archivo de reporte corrupto. Backup creado en: {backup_path}")
            
            # Inicializar con estructura correcta
            initial_data = {"productos": []}
            save_report(initial_data)
            return initial_data
            
        except Exception as e:
            logger.error(f"Error inesperado al cargar reporte: {str(e)}")
            initial_data = {"productos": []}
            save_report(initial_data)
            return initial_data


def save_report(data: Dict) -> bool:
    """
    Guarda el reporte en el archivo JSON.
    
    Args:
        data: Dict con estructura: {"productos": [...]}
    
    Returns:
        True si se guardó exitosamente, False en caso contrario
    """
    with report_lock:
        try:
            with open(REPORT_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"Reporte guardado exitosamente. Total productos: {len(data.get('productos', []))}")
            return True
        except Exception as e:
            logger.error(f"Error al guardar reporte: {str(e)}")
            return False


def add_product_to_report(
    titulo: str,
    url: str,
    estado: str = "exitoso"
) -> bool:
    """
    Agrega un producto al reporte.
    El número de item se calcula automáticamente como el siguiente disponible.
    
    Args:
        titulo: Título del producto en formato "TITULO - COLOR"
        url: URL del producto publicado o mensaje de error si falló
        estado: Estado del producto ("exitoso" o "error")
    
    Returns:
        True si se agregó exitosamente, False en caso contrario
    """
    try:
        # Cargar reporte actual
        data = load_report()
        
        # Calcular siguiente número
        productos = data.get("productos", [])
        if productos:
            ultimo_numero = max(p.get("numero", 0) for p in productos)
            siguiente_numero = ultimo_numero + 1
        else:
            siguiente_numero = 1
        
        # Crear nuevo producto
        fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        nuevo_producto = {
            "numero": siguiente_numero,
            "titulo": titulo,
            "url": url,
            "fecha": fecha_actual,
            "estado": estado
        }
        
        # Agregar a la lista
        productos.append(nuevo_producto)
        data["productos"] = productos
        
        # Guardar
        success = save_report(data)
        
        if success:
            logger.info(f"Producto agregado al reporte: #{siguiente_numero} - {titulo}")
        
        return success
        
    except Exception as e:
        logger.error(f"Error al agregar producto al reporte: {str(e)}")
        return False


def get_report_summary() -> Dict:
    """
    Obtiene un resumen del reporte.
    
    Returns:
        Dict con: total, exitosos, errores, ultimo_procesado
    """
    try:
        data = load_report()
        productos = data.get("productos", [])
        
        total = len(productos)
        exitosos = sum(1 for p in productos if p.get("estado") == "exitoso")
        errores = sum(1 for p in productos if p.get("estado") == "error")
        
        ultimo_procesado = None
        if productos:
            ultimo = max(productos, key=lambda p: p.get("numero", 0))
            ultimo_procesado = ultimo.get("fecha")
        
        return {
            "total": total,
            "exitosos": exitosos,
            "errores": errores,
            "ultimo_procesado": ultimo_procesado
        }
        
    except Exception as e:
        logger.error(f"Error al obtener resumen del reporte: {str(e)}")
        return {
            "total": 0,
            "exitosos": 0,
            "errores": 0,
            "ultimo_procesado": None
        }


def clear_report() -> bool:
    """
    Limpia el reporte (útil para testing o reset).
    Crea un backup antes de limpiar.
    
    Returns:
        True si se limpió exitosamente, False en caso contrario
    """
    try:
        # Crear backup si existe el archivo
        if REPORT_FILE.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = REPORT_FILE.parent / f"reporte_backup_{timestamp}.json"
            import shutil
            shutil.copy(REPORT_FILE, backup_path)
            logger.info(f"Backup del reporte creado en: {backup_path}")
        
        # Limpiar reporte
        initial_data = {"productos": []}
        success = save_report(initial_data)
        
        if success:
            logger.info("Reporte limpiado exitosamente")
        
        return success
        
    except Exception as e:
        logger.error(f"Error al limpiar reporte: {str(e)}")
        return False
