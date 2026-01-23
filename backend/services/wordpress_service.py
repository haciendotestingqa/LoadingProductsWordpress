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
    logger.info(f"📤 DEBUG upload_image_to_media: INICIO")
    logger.info(f"   - image_path: {image_path}")
    logger.info(f"   - filename: {filename}")
    
    if not WORDPRESS_PASS:
        logger.error("❌ DEBUG: WORDPRESS_PASS no está configurado en .env")
        return None
    
    url = f"{WP_BASE_URL.rstrip('/')}/wp-json/wp/v2/media?author=4"
    logger.info(f"   - URL: {url}")
    
    # Verificar que el archivo existe
    if not Path(image_path).exists():
        logger.error(f"❌ DEBUG: Archivo no encontrado: {image_path}")
        return None
    
    file_size = Path(image_path).stat().st_size
    logger.info(f"   - Tamaño del archivo: {file_size} bytes")
    
    headers = {
        'Content-Disposition': f'attachment; filename={filename}',
        'Content-Type': 'image/jpeg'
    }
    logger.info(f"   - Headers: {headers}")
    
    auth = HTTPBasicAuth(WORDPRESS_USER, WORDPRESS_PASS)
    logger.info(f"   - Usuario: {WORDPRESS_USER}")
    
    # Reintentos con backoff exponencial
    logger.info(f"🔄 DEBUG: Iniciando subida con hasta {MAX_RETRIES} intentos...")
    for attempt in range(MAX_RETRIES):
        try:
            logger.info(f"   🔄 Intento {attempt + 1}/{MAX_RETRIES}...")
            with open(image_path, 'rb') as img_file:
                logger.info(f"   - Enviando petición POST...")
                response = requests.post(
                    url,
                    headers=headers,
                    data=img_file,
                    auth=auth,
                    timeout=60
                )
            
            logger.info(f"   - Status code recibido: {response.status_code}")
            
            if response.status_code == 201:
                data = response.json()
                logger.info(f"   - Respuesta JSON: {data}")
                attachment_id = data.get('id')
                source_url = data.get('source_url')
                logger.info(f"✅ Imagen subida exitosamente: {filename} -> {source_url} (ID: {attachment_id})")
                return attachment_id  # Retornar ID en lugar de URL
            else:
                logger.warning(f"⚠️ Error al subir imagen (intento {attempt + 1}/{MAX_RETRIES}): {response.status_code}")
                logger.warning(f"   - Respuesta: {response.text[:500]}")
                
                if attempt < MAX_RETRIES - 1:
                    wait_time = RETRY_DELAY * (2 ** attempt)
                    logger.info(f"Reintentando en {wait_time} segundos...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Falló la subida de imagen después de {MAX_RETRIES} intentos")
                    return None
                    
        except requests.exceptions.RequestException as e:
            logger.error(f"Error de conexión al subir imagen (intento {attempt + 1}/{MAX_RETRIES}): {str(e)}")
            
            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_DELAY * (2 ** attempt)
                logger.info(f"Reintentando en {wait_time} segundos...")
                time.sleep(wait_time)
            else:
                logger.error(f"Falló la subida de imagen después de {MAX_RETRIES} intentos")
                return None
        except Exception as e:
            logger.error(f"Error inesperado al subir imagen: {str(e)}")
            return None
    
    return None


def duplicate_product(product_id: int) -> Optional[int]:
    """
    Duplica un producto en WooCommerce con reintentos automáticos para errores 500.
    
    Args:
        product_id: ID del producto base a duplicar
    
    Returns:
        ID del producto duplicado o None si falla
    """
    logger.info(f"📦 DEBUG duplicate_product: INICIO")
    logger.info(f"   - product_id: {product_id}")
    
    if not CONSUMER_KEY or not CONSUMER_SECRET:
        logger.error("❌ DEBUG: CONSUMER_KEY o CONSUMER_SECRET no están configurados en .env")
        return None
    
    url = f"{WP_BASE_URL.rstrip('/')}/wp-json/wc/v3/products/{product_id}/duplicate"
    logger.info(f"   - URL: {url}")
    
    auth = HTTPBasicAuth(CONSUMER_KEY, CONSUMER_SECRET)
    
    # Reintentos con backoff para errores 500 de servidor
    for attempt in range(MAX_RETRIES):
        try:
            logger.info(f"   🔄 Intento de duplicación {attempt + 1}/{MAX_RETRIES}...")
            response = requests.post(url, auth=auth, timeout=60)
            logger.info(f"   - Status code recibido: {response.status_code}")
            
            if response.status_code == 200 or response.status_code == 201:
                data = response.json()
                logger.info(f"   - Respuesta JSON (primeros campos): id={data.get('id')}, name={data.get('name')}")
                new_product_id = data.get('id')
                logger.info(f"✅ Producto duplicado exitosamente: {product_id} -> {new_product_id}")
                return new_product_id
            
            elif response.status_code == 500:
                # Error 500 del servidor - puede ser temporal
                logger.warning(f"⚠️ Error 500 al duplicar producto {product_id} (intento {attempt + 1}/{MAX_RETRIES})")
                
                # Intentar extraer mensaje de error del HTML
                error_text = response.text[:1000] if len(response.text) < 1000 else response.text[:1000] + "..."
                if "Fatal error" in response.text or "Maximum execution time" in response.text:
                    logger.error(f"   - Error crítico de WordPress detectado:")
                    logger.error(f"   - {error_text}")
                else:
                    logger.warning(f"   - Respuesta: {error_text}")
                
                # Reintento con backoff exponencial si no es el último intento
                if attempt < MAX_RETRIES - 1:
                    wait_time = RETRY_DELAY * (2 ** attempt)
                    logger.info(f"   - Reintentando en {wait_time} segundos...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"❌ Falló la duplicación después de {MAX_RETRIES} intentos con error 500")
                    return None
            
            else:
                # Otros errores (400, 401, 404, etc.) - no reintentar
                logger.error(f"❌ Error al duplicar producto {product_id}: {response.status_code}")
                try:
                    error_data = response.json()
                    logger.error(f"   - Error JSON: {error_data}")
                except:
                    logger.error(f"   - Respuesta: {response.text[:500]}")
                return None
                
        except requests.exceptions.Timeout:
            logger.warning(f"⚠️ Timeout al duplicar producto {product_id} (intento {attempt + 1}/{MAX_RETRIES})")
            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_DELAY * (2 ** attempt)
                logger.info(f"   - Reintentando en {wait_time} segundos...")
                time.sleep(wait_time)
            else:
                logger.error(f"❌ Falló la duplicación después de {MAX_RETRIES} intentos (timeout)")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error de conexión al duplicar producto {product_id}: {str(e)}")
            logger.error(f"   - Tipo de error: {type(e).__name__}")
            return None
            
        except Exception as e:
            logger.error(f"💥 Error inesperado al duplicar producto {product_id}: {str(e)}")
            logger.error(f"   - Tipo de error: {type(e).__name__}")
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
    logger.info(f"✏️  DEBUG update_product: INICIO")
    logger.info(f"   - product_id: {product_id}")
    logger.info(f"   - name: {name}")
    logger.info(f"   - images: {images}")
    
    if not CONSUMER_KEY or not CONSUMER_SECRET:
        logger.error("❌ DEBUG: CONSUMER_KEY o CONSUMER_SECRET no están configurados en .env")
        return None
    
    url = f"{WP_BASE_URL.rstrip('/')}/wp-json/wc/v3/products/{product_id}"
    logger.info(f"   - URL: {url}")
    
    auth = HTTPBasicAuth(CONSUMER_KEY, CONSUMER_SECRET)
    
    payload = {
        "name": name,
        "status": "publish",
        "images": images
    }
    logger.info(f"   - Payload: {payload}")
    
    headers = {
        'Content-Type': 'application/json'
    }
    
    try:
        logger.info(f"   - Enviando petición PUT para actualizar...")
        response = requests.put(
            url,
            json=payload,
            headers=headers,
            auth=auth,
            timeout=30
        )
        logger.info(f"   - Status code recibido: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"   - Respuesta JSON: {data}")
            permalink = data.get('permalink')
            logger.info(f"✅ Producto actualizado exitosamente: {product_id} -> {permalink}")
            return permalink
        else:
            logger.error(f"❌ Error al actualizar producto {product_id}: {response.status_code}")
            logger.error(f"   - Respuesta: {response.text[:500]}")
            return None
            
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Error de conexión al actualizar producto {product_id}: {str(e)}")
        logger.error(f"   - Tipo de error: {type(e).__name__}")
        return None
    except Exception as e:
        logger.error(f"💥 Error inesperado al actualizar producto {product_id}: {str(e)}")
        logger.error(f"   - Tipo de error: {type(e).__name__}")
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
        logger.info(f"🚀 DEBUG: INICIO process_product_publication")
        logger.info(f"   - product_base_id: {product_base_id}")
        logger.info(f"   - titulo: {titulo}")
        logger.info(f"   - color: {color}")
        logger.info(f"   - imagen_principal_path: {imagen_principal_path}")
        logger.info(f"   - imagenes_galeria_paths: {imagenes_galeria_paths}")
        
        # 1. Subir imagen principal
        logger.info(f"📸 DEBUG: PASO 1 - Subiendo imagen principal...")
        filename_principal = Path(imagen_principal_path).name
        logger.info(f"   - filename_principal: {filename_principal}")
        
        attachment_id_principal = upload_image_to_media(imagen_principal_path, filename_principal)
        logger.info(f"   - attachment_id_principal recibido: {attachment_id_principal}")
        
        if not attachment_id_principal:
            logger.error(f"❌ DEBUG: FALLO en subida de imagen principal")
            return {
                "success": False,
                "url": None,
                "error": "Error al subir imagen principal"
            }
        
        logger.info(f"✅ DEBUG: Imagen principal subida OK - ID: {attachment_id_principal}")
        
        # 2. Subir imágenes de galería
        logger.info(f"🖼️  DEBUG: PASO 2 - Subiendo {len(imagenes_galeria_paths)} imágenes de galería...")
        attachment_ids_galeria = []
        for idx, galeria_path in enumerate(imagenes_galeria_paths, 1):
            filename_galeria = Path(galeria_path).name
            logger.info(f"   - Subiendo galería {idx}/{len(imagenes_galeria_paths)}: {filename_galeria}")
            
            attachment_id_galeria = upload_image_to_media(galeria_path, filename_galeria)
            logger.info(f"   - attachment_id_galeria recibido: {attachment_id_galeria}")
            
            if attachment_id_galeria:
                attachment_ids_galeria.append(attachment_id_galeria)
                logger.info(f"   ✅ Galería {idx} subida OK - ID: {attachment_id_galeria}")
            else:
                logger.warning(f"   ⚠️ No se pudo subir imagen de galería: {galeria_path}")
        
        logger.info(f"🖼️  DEBUG: Total imágenes de galería subidas: {len(attachment_ids_galeria)}")
        logger.info(f"   - IDs de galería: {attachment_ids_galeria}")
        
        # 3. Construir array de imágenes para WooCommerce usando IDs
        logger.info(f"🔧 DEBUG: PASO 3 - Construyendo array de imágenes...")
        images = [{"id": attachment_id_principal}]
        for attachment_id_galeria in attachment_ids_galeria:
            images.append({"id": attachment_id_galeria})
        
        logger.info(f"   - Array de imágenes construido: {images}")
        
        # 4. Duplicar producto base
        logger.info(f"📦 DEBUG: PASO 4 - Duplicando producto base ID: {product_base_id}...")
        new_product_id = duplicate_product(product_base_id)
        logger.info(f"   - new_product_id recibido: {new_product_id}")
        
        if not new_product_id:
            logger.error(f"❌ DEBUG: FALLO en duplicación de producto")
            return {
                "success": False,
                "url": None,
                "error": "Error al duplicar producto base"
            }
        
        logger.info(f"✅ DEBUG: Producto duplicado OK - Nuevo ID: {new_product_id}")
        
        # 5. Actualizar producto duplicado
        product_name = f"{titulo} - {color}"
        logger.info(f"✏️  DEBUG: PASO 5 - Actualizando producto {new_product_id}...")
        logger.info(f"   - product_name: {product_name}")
        logger.info(f"   - images: {images}")
        
        permalink = update_product(new_product_id, product_name, images)
        logger.info(f"   - permalink recibido: {permalink}")
        
        if not permalink:
            logger.error(f"❌ DEBUG: FALLO en actualización de producto")
            return {
                "success": False,
                "url": None,
                "error": "Error al actualizar producto duplicado"
            }
        
        logger.info(f"✅ DEBUG: Producto actualizado OK - URL: {permalink}")
        logger.info(f"🎉 DEBUG: FIN process_product_publication - ÉXITO TOTAL")
        
        return {
            "success": True,
            "url": permalink,
            "error": None
        }
        
    except Exception as e:
        logger.error(f"💥 DEBUG: EXCEPCIÓN en process_product_publication: {str(e)}")
        logger.error(f"DEBUG: Tipo de error: {type(e).__name__}")
        logger.error(f"DEBUG: Traceback completo:", exc_info=True)
        return {
            "success": False,
            "url": None,
            "error": f"Error inesperado: {str(e)}"
        }
