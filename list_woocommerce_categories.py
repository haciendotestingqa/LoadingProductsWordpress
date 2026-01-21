#!/usr/bin/env python3
"""
Script para listar todas las categorías de productos de WooCommerce
usando la API REST (solo lectura, no hace cambios en WordPress).
"""

import sys
import os
import time
import json
import requests
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

# Cargar variables de entorno desde el archivo .env
load_dotenv()

# ================== CONFIGURACIÓN ==================
# Las variables se cargan desde el archivo .env
WC_BASE_URL = os.getenv("WC_BASE_URL", "")
CONSUMER_KEY = os.getenv("CONSUMER_KEY", "")
CONSUMER_SECRET = os.getenv("CONSUMER_SECRET", "")
PER_PAGE = int(os.getenv("PER_PAGE", "100"))
HIDE_EMPTY = os.getenv("HIDE_EMPTY", "False").lower() == "true"
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
RETRY_DELAY = float(os.getenv("RETRY_DELAY", "2.0"))
# ===================================================

# Headers para simular un navegador real y evitar bloqueos
# Nota: requests maneja automáticamente la descompresión gzip/deflate
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json',
    'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',  # El servidor puede comprimir, requests descomprime automáticamente
    'Connection': 'keep-alive',
    'Cache-Control': 'no-cache',
}


def make_wc_request(url, params=None, use_basic_auth=False):
    """
    Realiza una petición a la API de WooCommerce con reintentos.
    Intenta primero con parámetros de query, luego con autenticación básica HTTP.
    """
    for attempt in range(MAX_RETRIES):
        try:
            if use_basic_auth:
                # Usar autenticación básica HTTP (algunos servidores la prefieren)
                auth = HTTPBasicAuth(CONSUMER_KEY, CONSUMER_SECRET)
                resp = requests.get(url, params=params, headers=HEADERS, auth=auth, timeout=30)
            else:
                # Usar parámetros de query (método estándar de WooCommerce)
                resp = requests.get(url, params=params, headers=HEADERS, timeout=30)
            
            # Si obtenemos un 503, esperar un poco más antes de reintentar
            if resp.status_code == 503:
                if attempt < MAX_RETRIES - 1:
                    wait_time = RETRY_DELAY * (2 ** attempt)  # Backoff exponencial
                    print(f"⚠️ Servidor ocupado (503). Reintentando en {wait_time:.1f}s... (intento {attempt + 1}/{MAX_RETRIES})")
                    time.sleep(wait_time)
                    continue
                else:
                    resp.raise_for_status()
            
            resp.raise_for_status()
            return resp
            
        except requests.exceptions.Timeout:
            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_DELAY * (attempt + 1)
                print(f"⚠️ Timeout. Reintentando en {wait_time:.1f}s... (intento {attempt + 1}/{MAX_RETRIES})")
                time.sleep(wait_time)
            else:
                raise
        except requests.exceptions.HTTPError as e:
            if attempt < MAX_RETRIES - 1 and resp.status_code in [503, 502, 504]:
                wait_time = RETRY_DELAY * (2 ** attempt)
                print(f"⚠️ Error HTTP {resp.status_code}. Reintentando en {wait_time:.1f}s... (intento {attempt + 1}/{MAX_RETRIES})")
                time.sleep(wait_time)
            else:
                raise
        except requests.exceptions.RequestException as e:
            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_DELAY * (attempt + 1)
                print(f"⚠️ Error de conexión: {e}. Reintentando en {wait_time:.1f}s... (intento {attempt + 1}/{MAX_RETRIES})")
                time.sleep(wait_time)
            else:
                raise
    
    return None


def get_wc_categories():
    """
    Obtiene TODAS las categorías de productos de WooCommerce
    usando la API REST (solo lectura).
    """
    all_categories = []
    page = 1

    # Verificar primero si la URL base es accesible
    print("Verificando conexión con el servidor...")
    try:
        test_url = f"{WC_BASE_URL.rstrip('/')}/wp-json/"
        test_resp = requests.get(test_url, headers=HEADERS, timeout=10)
        
        # Verificar si el sitio está en mantenimiento
        if test_resp.status_code == 503:
            content_type = test_resp.headers.get('content-type', '').lower()
            if 'html' in content_type or test_resp.text.strip().startswith('<!DOCTYPE'):
                response_lower = test_resp.text.lower()
                if 'mantenimiento' in response_lower or 'maintenance' in response_lower:
                    print(f"⚠️ El sitio está en MODO DE MANTENIMIENTO")
                    print(f"   Código de estado: {test_resp.status_code}")
                    print(f"   El servidor está temporalmente fuera de servicio.")
                    print(f"   Por favor, intenta nuevamente más tarde.\n")
                    return []
        
        if test_resp.status_code == 200:
            print(f"✓ Conexión establecida correctamente")
        else:
            print(f"⚠️ Conexión establecida pero con código: {test_resp.status_code}")
    except Exception as e:
        print(f"⚠️ Advertencia: No se pudo verificar la conexión base: {e}")
        print("Continuando de todas formas...\n")

    while True:
        url = f"{WC_BASE_URL.rstrip('/')}/wp-json/wc/v3/products/categories"
        params = {
            "consumer_key": CONSUMER_KEY,
            "consumer_secret": CONSUMER_SECRET,
            "per_page": PER_PAGE,
            "page": page,
            "hide_empty": str(HIDE_EMPTY).lower(),
        }

        try:
            # Intentar primero con parámetros de query
            resp = make_wc_request(url, params=params, use_basic_auth=False)
            
            # Si falla con 401 o 403, intentar con autenticación básica HTTP
            if resp is None or resp.status_code in [401, 403]:
                print(f"⚠️ Autenticación por query falló. Intentando con autenticación básica HTTP...")
                # Remover las credenciales de los params para usar auth básica
                params_auth = {k: v for k, v in params.items() if k not in ['consumer_key', 'consumer_secret']}
                resp = make_wc_request(url, params=params_auth, use_basic_auth=True)
            
            if resp is None:
                print(f"✗ No se pudo obtener la página {page} después de {MAX_RETRIES} intentos")
                break

            # Verificar si la respuesta es HTML en lugar de JSON (sitio en mantenimiento, etc.)
            content_type = resp.headers.get('content-type', '').lower()
            if 'html' in content_type or resp.text.strip().startswith('<!DOCTYPE') or resp.text.strip().startswith('<html'):
                # Buscar indicadores de mantenimiento en la respuesta
                response_lower = resp.text.lower()
                if 'mantenimiento' in response_lower or 'maintenance' in response_lower:
                    print(f"\n⚠️ El sitio está en MODO DE MANTENIMIENTO")
                    print(f"   El servidor está temporalmente fuera de servicio.")
                    print(f"   Por favor, intenta nuevamente más tarde.\n")
                    return []
                else:
                    print(f"\n⚠️ El servidor devolvió HTML en lugar de JSON")
                    print(f"   Esto puede indicar que el sitio está en mantenimiento o hay un problema de configuración.")
                    print(f"   Respuesta recibida (primeros 300 caracteres):")
                    print(f"   {resp.text[:300]}...\n")
                    return []
            
            # Manejar la descompresión de la respuesta
            # requests normalmente descomprime automáticamente, pero verificamos el Content-Encoding
            content_encoding = resp.headers.get('content-encoding', '').lower()
            
            try:
                # Intentar parsear JSON directamente (requests debería haber descomprimido)
                categories = resp.json()
            except (ValueError, json.JSONDecodeError) as e:
                # Si falla, puede que la respuesta esté comprimida y requests no la haya descomprimido
                print(f"⚠️ Error al parsear JSON. Verificando compresión...")
                print(f"  Content-Encoding: {content_encoding if content_encoding else 'none'}")
                
                # Intentar descomprimir manualmente si está comprimida
                if 'br' in content_encoding or 'brotli' in content_encoding:
                    try:
                        import brotli
                        print(f"  Intentando descomprimir respuesta Brotli...")
                        decompressed = brotli.decompress(resp.content).decode('utf-8')
                        categories = json.loads(decompressed)
                        print(f"✓ Descompresión Brotli exitosa")
                    except ImportError:
                        print(f"✗ Error: Se requiere la librería 'brotli'. Instálala con: pip install brotli")
                        break
                    except Exception as decompress_error:
                        print(f"✗ Error al descomprimir Brotli: {decompress_error}")
                        print(f"  Tamaño de respuesta: {len(resp.content)} bytes")
                        break
                elif 'gzip' in content_encoding or resp.content[:2] == b'\x1f\x8b':  # Magic number de gzip
                    import gzip
                    try:
                        print(f"  Intentando descomprimir respuesta gzip...")
                        decompressed = gzip.decompress(resp.content).decode('utf-8')
                        categories = json.loads(decompressed)
                        print(f"✓ Descompresión gzip exitosa")
                    except Exception as decompress_error:
                        print(f"✗ Error al descomprimir gzip: {decompress_error}")
                        print(f"  Tamaño de respuesta: {len(resp.content)} bytes")
                        print(f"  Primeros bytes (hex): {resp.content[:20].hex()}")
                        break
                elif 'deflate' in content_encoding:
                    import zlib
                    try:
                        print(f"  Intentando descomprimir respuesta deflate...")
                        decompressed = zlib.decompress(resp.content).decode('utf-8')
                        categories = json.loads(decompressed)
                        print(f"✓ Descompresión deflate exitosa")
                    except Exception as decompress_error:
                        print(f"✗ Error al descomprimir deflate: {decompress_error}")
                        break
                else:
                    # No está comprimida, mostrar el error original
                    print(f"✗ Error al parsear la respuesta JSON en la página {page}: {e}")
                    print(f"  Content-Type recibido: {content_type}")
                    print(f"  Tamaño de respuesta: {len(resp.content)} bytes")
                    
                    # Intentar mostrar la respuesta como texto si es posible
                    try:
                        response_text = resp.text
                        if response_text:
                            print(f"  Respuesta recibida (primeros 300 caracteres): {response_text[:300]}...")
                        else:
                            print(f"  Respuesta vacía o binaria (primeros 100 bytes en hex): {resp.content[:100].hex()}...")
                    except:
                        print(f"  Respuesta binaria (primeros 100 bytes en hex): {resp.content[:100].hex()}...")
                    break

            # Si no vienen más resultados, salimos del bucle
            if not categories:
                break

            print(f"✓ Página {page}: {len(categories)} categorías obtenidas")
            all_categories.extend(categories)
            page += 1
            
            # Pequeña pausa entre páginas para no sobrecargar el servidor
            if page > 1:
                time.sleep(0.5)

        except requests.exceptions.HTTPError as e:
            print(f"✗ Error HTTP al obtener la página {page}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                status_code = e.response.status_code
                print(f"  Código de estado: {status_code}")
                
                # Verificar si la respuesta es HTML (mantenimiento)
                response_text = e.response.text
                if response_text.strip().startswith('<!DOCTYPE') or response_text.strip().startswith('<html'):
                    response_lower = response_text.lower()
                    if 'mantenimiento' in response_lower or 'maintenance' in response_lower:
                        print(f"\n⚠️ El sitio está en MODO DE MANTENIMIENTO")
                        print(f"   El servidor está temporalmente fuera de servicio.")
                        print(f"   Por favor, intenta nuevamente más tarde.\n")
                        return []
                    else:
                        print(f"  Respuesta HTML recibida (primeros 300 caracteres):")
                        print(f"  {response_text[:300]}...")
                else:
                    print(f"  Respuesta: {response_text[:200]}...")
            break
        except requests.exceptions.RequestException as e:
            print(f"✗ Error al conectar con la API de WooCommerce en la página {page}: {e}")
            break

    return all_categories


def print_categories(categories):
    """Muestra por consola un listado legible de las categorías."""
    if not categories:
        print("No se encontraron categorías.")
        return

    print("=" * 70)
    print("RESUMEN DE CATEGORÍAS ENCONTRADAS")
    print("=" * 70)
    print(f"Total de categorías encontradas: {len(categories)}\n")
    
    # Separar categorías principales (sin padre) y subcategorías (con padre)
    main_categories = []
    subcategories = []
    
    for cat in categories:
        if cat.get("parent", 0) == 0:
            main_categories.append(cat)
        else:
            subcategories.append(cat)
    
    print(f"📁 Categorías principales: {len(main_categories)}")
    print(f"📂 Subcategorías: {len(subcategories)}\n")
    
    # Mostrar lista de nombres de categorías principales
    if main_categories:
        print("=" * 70)
        print("LISTA DE CATEGORÍAS PRINCIPALES:")
        print("=" * 70)
        for idx, cat in enumerate(main_categories, 1):
            name = cat.get("name", "Sin nombre")
            count = cat.get("count", 0)
            cat_id = cat.get("id", "N/A")
            print(f"{idx:4d}. {name:<50} (ID: {cat_id}, Productos: {count})")
        print()
    
    # Mostrar detalles completos si el usuario quiere
    print("=" * 70)
    print("DETALLES COMPLETOS DE TODAS LAS CATEGORÍAS:")
    print("=" * 70)
    print()
    
    for idx, cat in enumerate(categories, 1):
        cat_id = cat.get("id")
        name = cat.get("name")
        slug = cat.get("slug")
        parent = cat.get("parent")
        count = cat.get("count")
        
        # Indicar si es categoría principal o subcategoría
        category_type = "📁 Principal" if parent == 0 else f"📂 Subcategoría (Padre ID: {parent})"
        
        print(f"[{idx}/{len(categories)}] {category_type}")
        print(f"  ID: {cat_id}")
        print(f"  Nombre: {name}")
        print(f"  Slug: {slug}")
        print(f"  Nº productos asignados: {count}")
        print("-" * 70)


def main():
    # Validar que las variables de entorno estén configuradas
    if not WC_BASE_URL or not CONSUMER_KEY or not CONSUMER_SECRET:
        print("⚠️ Error: Faltan variables de configuración en el archivo .env")
        print("\nPor favor, asegúrate de que el archivo .env contenga:")
        print("   - WC_BASE_URL (URL de tu WordPress)")
        print("   - CONSUMER_KEY (Clave de consumidor de WooCommerce)")
        print("   - CONSUMER_SECRET (Clave secreta de WooCommerce)")
        print("   - PER_PAGE (opcional, por defecto 100)")
        print("   - HIDE_EMPTY (opcional, por defecto False)")
        print("   - MAX_RETRIES (opcional, por defecto 3)")
        print("   - RETRY_DELAY (opcional, por defecto 2.0 segundos)")
        sys.exit(1)

    print("=" * 70)
    print("Obteniendo categorías de productos desde WooCommerce")
    print("=" * 70)
    print(f"URL: {WC_BASE_URL}")
    print(f"Páginas por solicitud: {PER_PAGE}")
    print(f"Reintentos máximos: {MAX_RETRIES}")
    print("=" * 70)
    print()
    
    categories = get_wc_categories()
    
    if categories:
        print(f"\n✓ Proceso completado exitosamente")
        print(f"  Total de categorías obtenidas: {len(categories)}\n")
    else:
        print(f"\n⚠️ No se obtuvieron categorías\n")
    
    print_categories(categories)


if __name__ == "__main__":
    main()

