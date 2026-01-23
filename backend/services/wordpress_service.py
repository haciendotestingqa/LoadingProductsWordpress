"""
Servicio para integración con WordPress Media Library y WooCommerce API.
"""
import os
import time
import logging
import requests
from pathlib import Path
from typing import Optional, List, Dict
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración
logger = logging.getLogger(__name__)

WP_BASE_URL = os.getenv("WC_BASE_URL", "https://valenciadrip.com")
WORDPRESS_USER = "Editor"
WORDPRESS_PASS = os.getenv("WORDPRESS_PASS", "")
CONSUMER_KEY = os.getenv("CONSUMER_KEY", "")
CONSUMER_SECRET = os.getenv("CONSUMER_SECRET", "")
MAX_RETRIES = 3
RETRY_DELAY = 2.0


def upload_image_to_media(image_path: str, filename: str) -> Optional[int]:
    """
    Sube una imagen al Media Library de WordPress.
    
    Args:
        image_path: Ruta absoluta a la imagen con marca de agua
        filename: Nombre del archivo a subir
    
    Returns:
        ID del attachment en WordPress Media Library o None si falla
    """
    if not WORDPRESS_PASS:
        logger.error("WORDPRESS_PASS no está configurado en .env")
        return None
    
    url = f"{WP_BASE_URL.rstrip('/')}/wp-json/wp/v2/media?author=4"
    
    # Verificar que el archivo existe
    if not Path(image_path).exists():
        logger.error(f"Archivo no encontrado: {image_path}")
        return None
    
    headers = {
        'Content-Disposition': f'attachment; filename={filename}',
        'Content-Type': 'image/jpeg'
    }
    
    auth = HTTPBasicAuth(WORDPRESS_USER, WORDPRESS_PASS)
    
    # Reintentos con backoff exponencial
    for attempt in range(MAX_RETRIES):
        try:
            with open(image_path, 'rb') as img_file:
                response = requests.post(
                    url,
                    headers=headers,
                    data=img_file,
                    auth=auth,
                    timeout=60
                )
            
            if response.status_code == 201:
                data = response.json()
                attachment_id = data.get('id')
                source_url = data.get('source_url')
                logger.info(f"Imagen subida exitosamente: {filename} -> {source_url} (ID: {attachment_id})")
                return attachment_id
            else:
                logger.warning(f"Error al subir imagen (intento {attempt + 1}/{MAX_RETRIES}): {response.status_code} - {response.text[:200]}")
                
                if attempt < MAX_RETRIES - 1:
                    wait_time = RETRY_DELAY * (2 ** attempt)
                    time.sleep(wait_time)
                else:
                    logger.error(f"Falló la subida de imagen después de {MAX_RETRIES} intentos")
                    return None
                    
        except requests.exceptions.RequestException as e:
            logger.error(f"Error de conexión al subir imagen (intento {attempt + 1}/{MAX_RETRIES}): {str(e)}")
            
            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_DELAY * (2 ** attempt)
                time.sleep(wait_time)
            else:
                logger.error(f"Falló la subida de imagen después de {MAX_RETRIES} intentos")
                return None
        except Exception as e:
            logger.error(f"Error inesperado al subir imagen: {str(e)}")
            return None
    
    return None


def link_image_to_product(attachment_id: int, product_id: int) -> bool:
    """
    Vincula una imagen (attachment) a un producto actualizando su post_parent.
    Esto hace que la imagen aparezca como "vinculada" en la Media Library de WordPress.
    
    Args:
        attachment_id: ID del attachment (imagen) en WordPress
        product_id: ID del producto al que vincular la imagen
    
    Returns:
        True si se vinculó exitosamente, False en caso contrario
    """
    if not WORDPRESS_PASS:
        logger.error("WORDPRESS_PASS no está configurado en .env")
        return False
    
    url = f"{WP_BASE_URL.rstrip('/')}/wp-json/wp/v2/media/{attachment_id}"
    auth = HTTPBasicAuth(WORDPRESS_USER, WORDPRESS_PASS)
    
    payload = {"post": product_id}
    headers = {'Content-Type': 'application/json'}
    
    try:
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            auth=auth,
            timeout=30
        )
        
        if response.status_code == 200:
            return True
        else:
            logger.warning(f"No se pudo vincular imagen {attachment_id}: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"Error al vincular imagen {attachment_id}: {str(e)}")
        return False


def duplicate_product(product_id: int) -> Optional[int]:
    """
    Duplica un producto en WooCommerce con reintentos automáticos para errores 500.
    
    Args:
        product_id: ID del producto base a duplicar
    
    Returns:
        ID del producto duplicado o None si falla
    """
    if not CONSUMER_KEY or not CONSUMER_SECRET:
        logger.error("CONSUMER_KEY o CONSUMER_SECRET no están configurados en .env")
        return None
    
    url = f"{WP_BASE_URL.rstrip('/')}/wp-json/wc/v3/products/{product_id}/duplicate"
    auth = HTTPBasicAuth(CONSUMER_KEY, CONSUMER_SECRET)
    
    # Reintentos con backoff para errores 500 de servidor
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(url, auth=auth, timeout=60)
            
            if response.status_code == 200 or response.status_code == 201:
                data = response.json()
                new_product_id = data.get('id')
                logger.info(f"Producto duplicado exitosamente: {product_id} -> {new_product_id}")
                return new_product_id
            
            elif response.status_code == 500:
                logger.warning(f"Error 500 al duplicar producto {product_id} (intento {attempt + 1}/{MAX_RETRIES})")
                
                if attempt < MAX_RETRIES - 1:
                    wait_time = RETRY_DELAY * (2 ** attempt)
                    time.sleep(wait_time)
                else:
                    logger.error(f"Falló la duplicación después de {MAX_RETRIES} intentos con error 500")
                    return None
            
            else:
                logger.error(f"Error al duplicar producto {product_id}: {response.status_code} - {response.text[:200]}")
                return None
                
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout al duplicar producto {product_id} (intento {attempt + 1}/{MAX_RETRIES})")
            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_DELAY * (2 ** attempt)
                time.sleep(wait_time)
            else:
                logger.error(f"Falló la duplicación después de {MAX_RETRIES} intentos (timeout)")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error de conexión al duplicar producto {product_id}: {str(e)}")
            return None
            
        except Exception as e:
            logger.error(f"Error inesperado al duplicar producto {product_id}: {str(e)}")
            return None
    
    return None


def update_product(product_id: int, name: str, images: List[Dict[str, int]]) -> Optional[str]:
    """
    Actualiza un producto en WooCommerce con nombre, estado e imágenes.
    
    Args:
        product_id: ID del producto a actualizar
        name: Nombre del producto en formato "TITULO - COLOR"
        images: Lista de diccionarios con formato [{"id": attachment_id}, ...]
                El primer elemento es la imagen principal, el resto son galería
    
    Returns:
        Permalink del producto actualizado o None si falla
    """
    if not CONSUMER_KEY or not CONSUMER_SECRET:
        logger.error("CONSUMER_KEY o CONSUMER_SECRET no están configurados en .env")
        return None
    
    url = f"{WP_BASE_URL.rstrip('/')}/wp-json/wc/v3/products/{product_id}"
    auth = HTTPBasicAuth(CONSUMER_KEY, CONSUMER_SECRET)
    
    payload = {
        "name": name,
        "status": "publish",
        "images": images
    }
    
    headers = {'Content-Type': 'application/json'}
    
    try:
        response = requests.put(
            url,
            json=payload,
            headers=headers,
            auth=auth,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            permalink = data.get('permalink')
            logger.info(f"Producto actualizado exitosamente: {product_id} -> {permalink}")
            return permalink
        else:
            logger.error(f"Error al actualizar producto {product_id}: {response.status_code} - {response.text[:200]}")
            return None
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Error de conexión al actualizar producto {product_id}: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error inesperado al actualizar producto {product_id}: {str(e)}")
        return None


def process_product_publication(
    product_base_id: int,
    titulo: str,
    color: str,
    imagen_principal_path: str,
    imagenes_galeria_paths: List[str]
) -> Dict[str, any]:
    """
    Procesa la publicación completa de un producto:
    1. Sube imágenes al Media Library
    2. Duplica el producto base
    3. Actualiza el producto con título, imágenes y estado
    4. Vincula las imágenes al producto (para que aparezcan en Media Library)
    
    Args:
        product_base_id: ID del producto base en WooCommerce
        titulo: Título del producto
        color: Color del producto
        imagen_principal_path: Ruta a la imagen principal con marca de agua
        imagenes_galeria_paths: Lista de rutas a imágenes de galería con marca de agua
    
    Returns:
        Dict con keys: success (bool), url (str), error (str)
    """
    try:
        # 1. Subir imagen principal
        filename_principal = Path(imagen_principal_path).name
        attachment_id_principal = upload_image_to_media(imagen_principal_path, filename_principal)
        
        if not attachment_id_principal:
            return {
                "success": False,
                "url": None,
                "error": "Error al subir imagen principal"
            }
        
        # 2. Subir imágenes de galería
        attachment_ids_galeria = []
        for galeria_path in imagenes_galeria_paths:
            filename_galeria = Path(galeria_path).name
            attachment_id_galeria = upload_image_to_media(galeria_path, filename_galeria)
            
            if attachment_id_galeria:
                attachment_ids_galeria.append(attachment_id_galeria)
            else:
                logger.warning(f"No se pudo subir imagen de galería: {galeria_path}")
        
        # 3. Construir array de imágenes para WooCommerce usando IDs
        images = [{"id": attachment_id_principal}]
        for attachment_id_galeria in attachment_ids_galeria:
            images.append({"id": attachment_id_galeria})
        
        # 4. Duplicar producto base
        new_product_id = duplicate_product(product_base_id)
        
        if not new_product_id:
            return {
                "success": False,
                "url": None,
                "error": "Error al duplicar producto base"
            }
        
        # 5. Actualizar producto duplicado
        product_name = f"{titulo} - {color}"
        permalink = update_product(new_product_id, product_name, images)
        
        if not permalink:
            return {
                "success": False,
                "url": None,
                "error": "Error al actualizar producto duplicado"
            }
        
        # 6. Vincular todas las imágenes al producto para que aparezcan en Media Library
        link_image_to_product(attachment_id_principal, new_product_id)
        for attachment_id_galeria in attachment_ids_galeria:
            link_image_to_product(attachment_id_galeria, new_product_id)
        
        return {
            "success": True,
            "url": permalink,
            "error": None
        }
        
    except Exception as e:
        logger.error(f"Error en process_product_publication: {str(e)}", exc_info=True)
        return {
            "success": False,
            "url": None,
            "error": f"Error inesperado: {str(e)}"
        }
