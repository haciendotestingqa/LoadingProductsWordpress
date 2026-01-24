#!/usr/bin/env python3
"""
Script para descargar imágenes de productos desde Yupoo por categoría
Organiza las imágenes en: Categoría/Página/Producto/imagen.jpg
"""

import requests
from bs4 import BeautifulSoup
from pathlib import Path
import time
import re
import argparse
from urllib.parse import urljoin, urlparse

# Configuración por defecto (puede ser sobrescrita por argumentos)
BASE_URL = "https://yitian333.x.yupoo.com/categories/4135412"
CATEGORY_NAME = None  # None = extraer automáticamente, o especifica manualmente: "Trapstar系列"
START_PAGE = 1
END_PAGE = 2
MAX_RETRIES = 3
DELAY_BETWEEN_REQUESTS = 0.5
DELAY_BETWEEN_IMAGES = 0.3
PASSWORD = None  # Contraseña para páginas protegidas (opcional)

def sanitize_filename(filename):
    """Limpia el nombre de archivo solo de caracteres problemáticos del sistema de archivos"""
    filename = str(filename)
    # Solo reemplaza caracteres que causan problemas en sistemas de archivos
    filename = filename.replace('/', '-').replace('\\', '-')
    filename = filename.replace('\0', '')
    # Limita la longitud solo si es extremadamente larga
    if len(filename) > 250:
        filename = filename[:250]
    return filename.strip()

def is_password_protected(soup):
    """Detecta si la página requiere contraseña"""
    page_text = soup.get_text().lower()
    html_str = str(soup).lower()
    return (
        'indexlock' in html_str or
        'encrypted' in page_text or
        '请输入密码' in page_text or
        'enter password' in page_text or
        soup.find('div', class_=lambda x: x and 'indexlock' in str(x)) is not None
    )

def authenticate_if_needed(session, base_url, password=None):
    """
    Autentica en una página protegida si es necesario.
    
    Args:
        session: requests.Session object
        base_url: URL base de la categoría
        password: Contraseña para páginas protegidas (opcional)
    
    Returns:
        bool: True si la autenticación fue exitosa o no era necesaria, False si falló
    """
    if not password:
        return True  # No hay contraseña, asumir que no es necesaria
    
    try:
        # Hacer una petición inicial para verificar si necesita autenticación
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': base_url,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
        }
        
        response = session.get(f"{base_url}?page=1", headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Si no requiere contraseña, retornar True
        if not is_password_protected(soup):
            return True
        
        # Extraer el dominio (OWNER) de la URL
        parsed = urlparse(base_url)
        domain_parts = parsed.netloc.split('.')
        if len(domain_parts) >= 2:
            owner = domain_parts[0]  # ej: wholesale4shoesbags de wholesale4shoesbags.x.yupoo.com
        else:
            owner = domain_parts[0]
        
        # Construir URL de autenticación
        # API_ORIGIN es relativo: '/api', así que construimos la URL completa
        api_origin = f"{parsed.scheme}://{parsed.netloc}/api"
        auth_url = f"{api_origin}/web/users/{owner}?password={password}"
        
        # Hacer petición de autenticación
        auth_response = session.get(auth_url, headers=headers, timeout=10)
        auth_response.raise_for_status()
        
        # Verificar si la autenticación fue exitosa
        try:
            auth_data = auth_response.json()
            if auth_data.get('data', {}).get('passwordValid'):
                # Establecer cookie manualmente si no se estableció automáticamente
                # La cookie se llama 'indexlockcode' según el código JavaScript
                # Usar dominio .x.yupoo.com para que funcione en todos los subdominios
                session.cookies.set('indexlockcode', password, domain='.x.yupoo.com', path='/')
                
                # Verificar que ahora podemos acceder al contenido
                test_response = session.get(f"{base_url}?page=1", headers=headers, timeout=10)
                test_soup = BeautifulSoup(test_response.text, 'html.parser')
                if not is_password_protected(test_soup):
                    return True
        except (ValueError, KeyError) as e:
            # Si no es JSON, verificar directamente si podemos acceder
            # Pero primero establecer la cookie
            # Usar dominio .x.yupoo.com para que funcione en todos los subdominios
            session.cookies.set('indexlockcode', password, domain='.x.yupoo.com', path='/')
            
            test_response = session.get(f"{base_url}?page=1", headers=headers, timeout=10)
            test_soup = BeautifulSoup(test_response.text, 'html.parser')
            if not is_password_protected(test_soup):
                return True
        
        return False
        
    except Exception as e:
        print(f"⚠ Error en autenticación: {e}")
        return False

def extract_category_name(soup, base_url):
    """Extrae el nombre de la categoría desde el HTML respetando el nombre original"""
    # Extraer ID de categoría de la URL para búsquedas más precisas
    category_id = None
    if '/categories/' in base_url:
        match = re.search(r'/categories/(\d+)', base_url)
        if match:
            category_id = match.group(1)
    
    # Lista de nombres inválidos a filtrar
    invalid_names = ['简体中文', 'english', '繁體中文', 'español', 'portugues', 'Français', 
                     'Deutsch', 'Русский', '登录', '注册', 'Home', 'All categories', 
                     'Yupoo', 'search', 'QR code']
    
    # Método 1: Buscar en el texto que dice "分类"X系列"下的相册" o "分类"X"下的相册" (MÁS CONFIABLE)
    page_text = soup.get_text()
    # Buscar patrón: 分类"nombre"下的相册 (puede tener 系列 o no)
    match = re.search(r'分类["\']([^"\']+)["\']下的相册', page_text)
    if match:
        category_name = match.group(1).strip()
        # Filtrar nombres inválidos
        if category_name and category_name not in invalid_names:
            return category_name
    
    # También buscar en el título de la página
    title_tag = soup.find('title')
    if title_tag:
        title_text = title_tag.get_text()
        match = re.search(r'分类["\']([^"\']+)["\']下的相册', title_text)
        if match:
            category_name = match.group(1).strip()
            if category_name and category_name not in invalid_names:
                return category_name
    
    # Método 2: Buscar en breadcrumbs - solo enlaces que apunten a esta categoría específica
    if category_id:
        category_links = soup.find_all('a', href=lambda x: x and f'/categories/{category_id}' in str(x))
        for link in category_links:
            text = link.text.strip()
            href = link.get('href', '')
            # Filtrar enlaces de idioma (tienen parámetros ?page=1 o son solo idiomas)
            # Y filtrar nombres de idioma y navegación
            is_language_link = (text in invalid_names or 
                               text.lower() in ['english', '简体中文', '繁體中文', 'español', 'portugues', 
                                               'français', 'deutsch', 'русский'] or
                               '?page=' in href or
                               len(text) < 3)
            if text and not is_language_link and text not in invalid_names:
                # Aceptar cualquier nombre que no sea de idioma, no necesita tener "系列"
                return text
    
    # Método 3: Buscar en títulos h1, h2 que contengan "系列"
    for tag in ['h1', 'h2', 'h3']:
        titles = soup.find_all(tag)
        for title in titles:
            text = title.text.strip()
            if '系列' in text:
                # Extraer la parte completa que contiene "系列"
                match = re.search(r'([^\s]+系列)', text)
                if match:
                    category_name = match.group(1)
                    # Filtrar nombres inválidos
                    if category_name not in invalid_names:
                        return category_name
    
    # Método 4: Buscar en la lista de categorías del menú lateral
    if category_id:
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            href = link.get('href', '')
            # Buscar enlaces que apunten exactamente a esta categoría (sin parámetros de idioma)
            if f'/categories/{category_id}' in href and '?page=' not in href:
                text = link.text.strip()
                # Filtrar nombres inválidos y de idioma
                is_language = text.lower() in ['english', '简体中文', '繁體中文', 'español', 'portugues', 
                                               'français', 'deutsch', 'русский'] or text in invalid_names
                if text and not is_language and len(text) > 2:
                    return text
    
    # Método 5: Buscar en el breadcrumb de navegación (último recurso)
    breadcrumbs = soup.find_all(['nav', 'ol', 'ul'], class_=lambda x: x and 'breadcrumb' in str(x).lower())
    for breadcrumb in breadcrumbs:
        links = breadcrumb.find_all('a', href=lambda x: x and '/categories/' in x)
        for link in links:
            text = link.text.strip()
            # Filtrar nombres inválidos
            if text and text not in invalid_names and '系列' in text:
                return text
    
    return None

def extract_products_from_page(soup, base_url):
    """Extrae información de productos de la página usando BeautifulSoup
    
    Returns:
        tuple: (lista de productos únicos, número de duplicados detectados, lista de duplicados con info)
    """
    products = []
    
    # Buscar todos los enlaces a /albums/
    album_links = soup.find_all('a', href=lambda x: x and '/albums/' in x)
    
    seen_album_ids = set()  # Usar ID del álbum para evitar duplicados
    seen_urls = set()
    
    for link in album_links:
        href = link.get('href', '')
        if not href:
            continue
        
        # Filtrar enlaces que no son productos (navegación, etc.)
        # Los productos tienen parámetros como ?uid=1&isSubCate=false
        if '?uid=' not in href and '&isSubCate=' not in href:
            # Puede ser un producto, pero verificar que no sea navegación
            parent = link.find_parent(['nav', 'header', 'footer'])
            if parent:
                continue
        
        # Extraer ID del álbum de la URL
        album_id_match = re.search(r'/albums/(\d+)', href)
        if not album_id_match:
            continue
        
        album_id = album_id_match.group(1)
        
        # Evitar duplicados por ID
        if album_id in seen_album_ids:
            continue
        
        # Construir URL completa
        if href.startswith('/'):
            full_url = urljoin(base_url, href)
        elif href.startswith('http'):
            full_url = href
        else:
            continue
        
        # Evitar duplicados por URL completa
        if full_url in seen_urls:
            continue
        
        # El texto del enlace suele ser solo el número de fotos (ej: "25")
        # Necesitamos buscar el nombre real en el contenedor padre
        product_name = None
        parent = link.find_parent(['div', 'article', 'section', 'li'])
        
        if parent:
            # Obtener todo el texto del contenedor
            container_text = parent.get_text(separator='|', strip=True)
            parts = [p.strip() for p in container_text.split('|') if p.strip()]
            
            # CORRECCIÓN: Aceptar productos nombrados solo con números
            # El formato suele ser: "número_fotos|nombre_producto"
            if len(parts) >= 2:
                # El primer elemento es el número de fotos, el segundo el nombre del producto
                product_name = parts[1]
            elif len(parts) == 1:
                # Si solo hay un elemento y no es un número muy pequeño (1-99), usarlo
                if not (re.match(r'^\d{1,2}$', parts[0])):
                    product_name = parts[0]
            
            # Si no encontramos con el método anterior, intentar búsqueda en líneas
            if not product_name:
                lines = [text_line.strip() for text_line in container_text.replace('|', '\n').split('\n') if text_line.strip()]
                for line in reversed(lines):  # Empezar desde el final
                    if line and len(line) > 0:
                        # Ignorar solo números muy pequeños (1-99) que son probablemente conteos
                        invalid_names = ['登录', '注册', 'Home', 'album', 'All categories', 'Yupoo', 'search', 'QR code']
                        is_small_number = re.match(r'^\d{1,2}$', line)
                        if (line not in invalid_names and 
                            not line.startswith('http') and 
                            not is_small_number):
                            product_name = line
                            break
            
            # Si no encontramos, buscar en headings dentro del contenedor
            if not product_name:
                headings = parent.find_all(['h2', 'h3', 'h4'])
                for heading in headings:
                    text = heading.get_text(strip=True)
                    if text and len(text) > 0:
                        link_text = link.get_text(strip=True)
                        is_small_number = re.match(r'^\d{1,2}$', text)
                        if text != link_text and text not in ['登录', '注册', 'Home', 'album'] and not is_small_number:
                            product_name = text
                            break
        
        # Si aún no tenemos nombre, usar el texto del enlace como último recurso
        if not product_name:
            link_text = link.get_text(strip=True)
            # Solo usar si no es un número muy pequeño (probablemente es el conteo de fotos)
            if link_text and not re.match(r'^\d{1,2}$', link_text) and len(link_text) > 0:
                product_name = link_text
        
        # Filtrar nombres inválidos y verificar que tenga sentido
        if product_name and len(product_name) >= 1:
            # Filtrar nombres de navegación y URLs
            invalid = ['登录', '注册', 'Home', 'album', 'All categories', 'Yupoo', 'search', 'QR code', '简体中文', 'english']
            # Aceptar cualquier nombre que no esté en la lista de inválidos
            if (product_name not in invalid and 
                not product_name.startswith('http') and 
                len(product_name.strip()) >= 1):
                seen_album_ids.add(album_id)
                seen_urls.add(full_url)
                products.append({
                    'url': full_url,
                    'name': product_name.strip()
                })
    
    # Eliminar duplicados por nombre (por si acaso)
    seen_names = {}  # Cambiar a dict para guardar el primer producto con ese nombre
    unique_products = []
    duplicates_info = []  # Lista de duplicados con información
    
    for product in products:
        product_name = product['name']
        if product_name not in seen_names:
            seen_names[product_name] = product  # Guardar el primer producto con ese nombre
            unique_products.append(product)
        else:
            # Es un duplicado - guardar información
            duplicates_info.append({
                'name': product_name,
                'url': product['url'],
                'first_url': seen_names[product_name]['url']  # URL del primer producto con ese nombre
            })
    
    return (unique_products, len(duplicates_info), duplicates_info)

def get_image_urls_from_product(product_url, session=None):
    """Obtiene las URLs de todas las imágenes de un producto
    
    Returns:
        tuple: (list of image URLs, success: bool) - success es False si hubo un error al obtener las URLs
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://yitian333.x.yupoo.com/',
        }
        
        # Usar sesión si está disponible (para mantener cookies de autenticación)
        if session:
            response = session.get(product_url, headers=headers, timeout=10)
        else:
            response = requests.get(product_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Buscar imágenes en el visor de galería
        image_urls = []
        
        # Método 1: Buscar en elementos de imagen con clases específicas
        img_elements = soup.find_all('img', class_=lambda x: x and ('image__img' in str(x) or 'showalbum__bigimg' in str(x)))
        for img in img_elements:
            src = img.get('src') or img.get('data-src') or img.get('data-original')
            if src:
                # Convertir URLs protocol-relative a https
                if src.startswith('//'):
                    src = 'https:' + src
                # Solo procesar URLs válidas de imágenes de productos
                if src.startswith('http') and 'photo.yupoo.com' in src:
                    # Limpiar parámetros de tamaño para obtener la imagen completa
                    src = re.sub(r'\?.*$', '', src)
                    # Cambiar 'small' por 'large' para mejor calidad
                    src = src.replace('/small.', '/large.')
                    if src not in image_urls:
                        image_urls.append(src)
        
        # Método 2: Buscar en divs con estilos de fondo
        divs_with_bg = soup.find_all('div', style=lambda x: x and 'background-image' in str(x))
        for div in divs_with_bg:
            style = div.get('style', '')
            match = re.search(r'url\(["\']?(https?://[^"\')]+|//[^"\')]+)["\']?\)', style)
            if match:
                url = match.group(1)
                if url.startswith('//'):
                    url = 'https:' + url
                if 'photo.yupoo.com' in url:
                    url = re.sub(r'\?.*$', '', url)
                    url = url.replace('/small.', '/large.')
                    if url not in image_urls:
                        image_urls.append(url)
        
        # Método 3: Buscar todas las imágenes que parezcan ser de productos
        all_imgs = soup.find_all('img')
        for img in all_imgs:
            src = img.get('src') or img.get('data-src') or img.get('data-original')
            if src:
                if src.startswith('//'):
                    src = 'https:' + src
                # Solo imágenes de photo.yupoo.com (productos reales)
                if src.startswith('http') and 'photo.yupoo.com' in src:
                    src = re.sub(r'\?.*$', '', src)
                    src = src.replace('/small.', '/large.')
                    # Filtrar logos, static, website
                    if (src not in image_urls and 
                        '/static/' not in src and 
                        '/website/' not in src and
                        '/icons/' not in src):
                        image_urls.append(src)
        
        return (image_urls, True)  # Retornar tupla: (urls, success)
        
    except Exception as e:
        print(f"  ✗ Error obteniendo imágenes: {e}")
        return ([], False)  # Retornar lista vacía y False (falló)

def download_image(image_url, save_path, retries=MAX_RETRIES, session=None):
    """Descarga una imagen con reintentos y manejo robusto de errores de conexión"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://yitian333.x.yupoo.com/',
    }
    
    for attempt in range(retries):
        try:
            # Usar sesión si está disponible
            if session:
                response = session.get(image_url, headers=headers, timeout=30, stream=True)
            else:
                response = requests.get(image_url, headers=headers, timeout=30, stream=True)
            response.raise_for_status()
            
            # Descargar en chunks con manejo de errores de conexión
            with open(save_path, 'wb') as f:
                try:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                except (requests.exceptions.ChunkedEncodingError, ConnectionError) as chunk_error:
                    # Error durante la descarga de chunks (IncompleteRead, etc.)
                    # Verificar si el archivo tiene contenido válido
                    f.flush()
                    if save_path.exists() and save_path.stat().st_size > 0:
                        # El archivo tiene contenido, puede ser una imagen parcial
                        # Intentar verificar si es válida o reintentar
                        pass
                    raise chunk_error
            
            # Verificar que el archivo se descargó completamente
            if save_path.exists() and save_path.stat().st_size > 0:
                return True
            else:
                raise Exception("Archivo descargado está vacío")
            
        except (requests.exceptions.ChunkedEncodingError, 
                requests.exceptions.ConnectionError,
                ConnectionError,
                requests.exceptions.Timeout) as e:
            # Errores de conexión: reintentar con más tiempo de espera
            if attempt < retries - 1:
                wait_time = (attempt + 1) * 2  # Esperar más tiempo en cada reintento
                time.sleep(wait_time)
                # Eliminar archivo parcial si existe
                if save_path.exists():
                    try:
                        save_path.unlink()
                    except:
                        pass
                continue
            else:
                print(f"  ✗ Error de conexión descargando {image_url}: {e}")
                if save_path.exists():
                    try:
                        save_path.unlink()  # Eliminar archivo parcial
                    except:
                        pass
                return False
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(1)
                # Eliminar archivo parcial si existe
                if save_path.exists():
                    try:
                        save_path.unlink()
                    except:
                        pass
                continue
            else:
                print(f"  ✗ Error descargando {image_url}: {e}")
                if save_path.exists():
                    try:
                        save_path.unlink()  # Eliminar archivo parcial
                    except:
                        pass
                return False
    
    return False

def process_product(product, base_dir, page_num, session=None):
    """Procesa un producto: descarga sus imágenes
    
    Returns:
        tuple: (número de imágenes descargadas, éxito: bool) - éxito es False si falló obtener las URLs
    """
    product_name = sanitize_filename(product['name'])
    product_url = product['url']
    
    # Crear directorio del producto
    product_dir = base_dir / str(page_num) / product_name
    product_dir.mkdir(parents=True, exist_ok=True)
    
    # Obtener URLs de imágenes
    image_urls, success = get_image_urls_from_product(product_url, session)
    
    if not image_urls:
        if not success:
            # Hubo un error al obtener las URLs (timeout, etc.)
            print("  ⚠ No se encontraron imágenes (error al obtener URLs)")
            return (0, False)
        else:
            # No hay imágenes pero no hubo error (producto sin imágenes)
            print("  ⚠ No se encontraron imágenes")
            return (0, True)
    
    # Descargar cada imagen
    downloaded = 0
    for idx, img_url in enumerate(image_urls, 1):
        # Extraer nombre original de la URL
        # URL típica: https://photo.yupoo.com/yitian333/5073f2ba/large.jpeg
        url_parts = img_url.rstrip('/').split('/')
        if len(url_parts) >= 2:
            # Obtener el ID único y el nombre del archivo
            image_id = url_parts[-2]  # ej: 5073f2ba
            original_filename = url_parts[-1]  # ej: large.jpeg
            
            # Extraer extensión del nombre original
            if '.' in original_filename:
                ext = '.' + original_filename.split('.')[-1]
            else:
                ext = '.jpg'
            
            # Usar el ID como nombre (es único y descriptivo)
            filename = image_id + ext
        else:
            # Fallback: usar índice si no se puede extraer
            ext = '.jpg'
            if '.png' in img_url.lower():
                ext = '.png'
            elif '.webp' in img_url.lower():
                ext = '.webp'
            filename = "{}{}".format(idx, ext)
        
        image_path = product_dir / filename
        
        # Verificar si ya existe (con cualquier extensión .jpg/.jpeg)
        if image_path.exists():
            downloaded += 1
            continue
        
        # También verificar la extensión alternativa para evitar duplicados
        if ext.lower() == '.jpeg':
            alt_path = product_dir / (image_id + '.jpg')
        elif ext.lower() == '.jpg':
            alt_path = product_dir / (image_id + '.jpeg')
        else:
            alt_path = None
        
        if alt_path and alt_path.exists():
            # Ya existe con otra extensión, saltar
            downloaded += 1
            continue
        
        # Descargar
        if download_image(img_url, image_path, session=session):
            downloaded += 1
        
        # Pequeña pausa entre imágenes
        time.sleep(DELAY_BETWEEN_IMAGES)
    
    print(f"  ✓ Descargadas {downloaded} imágenes")
    return (downloaded, True)  # Retornar tupla: (imágenes descargadas, éxito)

def main(base_url=None, category_name=None, start_page=None, end_page=None, password=None):
    """Función principal"""
    # Usar argumentos o valores por defecto
    base_url = base_url or BASE_URL
    start_page = start_page or START_PAGE
    end_page = end_page or END_PAGE
    password = password or PASSWORD
    
    print("="*70)
    print("Descargador de imágenes Yupoo por categoría")
    print("="*70)
    print(f"URL base: {base_url}")
    print(f"Páginas: {start_page} a {end_page}")
    if password:
        print(f"Contraseña: {'*' * len(password)} (configurada)")
    print("="*70)
    print()
    
    # Crear sesión para mantener cookies de autenticación
    session = requests.Session()
    
    # Headers para las peticiones
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://yitian333.x.yupoo.com/',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
    }
    session.headers.update(headers)
    
    # Autenticar si es necesario
    if password:
        print("Verificando autenticación...")
        if not authenticate_if_needed(session, base_url, password):
            print("✗ Error: No se pudo autenticar. Verifica la contraseña.")
            return
        print("✓ Autenticación exitosa")
        print()
    
    # Obtener nombre de categoría
    if not category_name:
        print("Extrayendo nombre de categoría...")
        try:
            response = session.get(f"{base_url}?page=1", timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            category_name = extract_category_name(soup, base_url)
            
            if category_name:
                print(f"✓ Categoría detectada: {category_name}")
            else:
                # Usar ID de categoría como respaldo
                match = re.search(r'/categories/(\d+)', base_url)
                if match:
                    category_name = f"Categoria_{match.group(1)}"
                    print(f"⚠ No se pudo extraer nombre, usando: {category_name}")
                else:
                    category_name = "Yupoo_Downloads"
                    print(f"⚠ Usando nombre por defecto: {category_name}")
        except Exception as e:
            print(f"✗ Error extrayendo categoría: {e}")
            category_name = "Yupoo_Downloads"
            print(f"⚠ Usando nombre por defecto: {category_name}")
    
    # Sanitizar nombre de categoría
    category_name_clean = sanitize_filename(category_name)
    
    print()
    print(f"Categoría: {category_name}")
    print("="*70)
    print()
    
    # Crear directorio base
    base_dir = Path("yupoo_downloads") / category_name_clean
    base_dir.mkdir(parents=True, exist_ok=True)
    
    # Estadísticas
    total_products = 0
    total_images = 0
    failed_products = 0
    total_duplicates = 0  # Contador de productos duplicados detectados
    all_duplicates = []  # Lista de todos los duplicados detectados
    cross_page_duplicates = []  # Duplicados entre páginas diferentes
    
    # Rastrear productos ya procesados entre todas las páginas
    processed_products = {}  # {product_name: {'page': page_num, 'dir': Path}}
    
    # Procesar cada página
    for page in range(start_page, end_page + 1):
        print()
        print("="*70)
        print(f"Procesando página {page}...")
        print("="*70)
        
        try:
            # Obtener HTML de la página
            page_url = f"{base_url}?page={page}"
            response = session.get(page_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Verificar si aún requiere autenticación (por si expiró la sesión)
            if password and is_password_protected(soup):
                print("⚠ Sesión expirada, reautenticando...")
                if not authenticate_if_needed(session, base_url, password):
                    print("✗ Error: No se pudo reautenticar")
                    continue
                # Reintentar la petición
                response = session.get(page_url, timeout=10)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extraer productos
            products, duplicates_count, duplicates_info = extract_products_from_page(soup, base_url)
            total_duplicates += duplicates_count
            all_duplicates.extend(duplicates_info)
            if duplicates_count > 0:
                print(f"Encontrados {len(products)} productos únicos en página {page} ({duplicates_count} duplicados detectados y omitidos)")
            else:
                print(f"Encontrados {len(products)} productos en página {page}")
            print()
            
            # Procesar cada producto
            for idx, product in enumerate(products, 1):
                total_products += 1
                product_name = sanitize_filename(product['name'])
                print(f"[{idx}/{len(products)}] Producto: {product['name']}")
                print(f"  URL: {product['url']}")
                
                # Verificar si este producto ya fue procesado en una página anterior
                if product_name in processed_products:
                    prev_info = processed_products[product_name]
                    prev_page = prev_info['page']
                    prev_dir = prev_info['dir']
                    
                    # Verificar si el directorio anterior tiene imágenes
                    if prev_dir.exists() and any(prev_dir.iterdir()):
                        print(f"  🔄 Duplicado detectado: ya descargado en página {prev_page}")
                        print(f"     Consolidando imágenes nuevas en carpeta de página {prev_page}...")
                        
                        # Obtener URLs de imágenes del producto actual
                        image_urls, success = get_image_urls_from_product(product['url'], session)
                        
                        if not success or not image_urls:
                            print(f"     ⚠ No se pudieron obtener imágenes del duplicado, omitiendo")
                            cross_page_duplicates.append({
                                'name': product['name'],
                                'current_page': page,
                                'current_url': product['url'],
                                'previous_page': prev_page,
                                'previous_dir': str(prev_dir),
                                'images_added': 0
                            })
                            continue
                        
                        # Obtener IDs de imágenes ya descargadas
                        existing_image_ids = set()
                        for img_file in prev_dir.glob("*"):
                            if img_file.is_file() and img_file.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp']:
                                existing_image_ids.add(img_file.stem)  # ID sin extensión
                        
                        # Descargar solo imágenes nuevas
                        new_images_count = 0
                        for img_url in image_urls:
                            # Extraer ID de imagen de la URL
                            url_parts = img_url.rstrip('/').split('/')
                            if len(url_parts) >= 2:
                                image_id = url_parts[-2]
                                original_filename = url_parts[-1]
                                
                                if '.' in original_filename:
                                    ext = '.' + original_filename.split('.')[-1]
                                else:
                                    ext = '.jpg'
                                
                                filename = image_id + ext
                            else:
                                continue
                            
                            # Si la imagen ya existe, saltar
                            image_path = prev_dir / filename
                            if image_path.exists():
                                continue
                            
                            # Verificar extensión alternativa
                            if ext.lower() == '.jpeg':
                                alt_path = prev_dir / (image_id + '.jpg')
                            elif ext.lower() == '.jpg':
                                alt_path = prev_dir / (image_id + '.jpeg')
                            else:
                                alt_path = None
                            
                            if alt_path and alt_path.exists():
                                continue
                            
                            # Descargar imagen nueva en la carpeta de la primera página
                            if download_image(img_url, image_path, session=session):
                                new_images_count += 1
                                total_images += 1
                                time.sleep(DELAY_BETWEEN_IMAGES)
                        
                        if new_images_count > 0:
                            print(f"     ✓ Agregadas {new_images_count} imágenes nuevas (total: {len(existing_image_ids) + new_images_count})")
                        else:
                            print(f"     ℹ No hay imágenes nuevas, todas ya están descargadas")
                        
                        cross_page_duplicates.append({
                            'name': product['name'],
                            'current_page': page,
                            'current_url': product['url'],
                            'previous_page': prev_page,
                            'previous_dir': str(prev_dir),
                            'images_added': new_images_count
                        })
                        continue
                
                try:
                    images, success = process_product(product, base_dir, page, session)
                    total_images += images
                    
                    # Registrar este producto como procesado solo si fue exitoso y tiene imágenes
                    if success and images > 0:
                        product_dir = base_dir / str(page) / product_name
                        processed_products[product_name] = {
                            'page': page,
                            'dir': product_dir
                        }
                    
                    if not success:
                        # Falló al obtener las URLs de imágenes (timeout, error de conexión, etc.)
                        failed_products += 1
                except Exception as e:
                    print(f"  ✗ Error procesando producto: {e}")
                    failed_products += 1
                
                # Pausa entre productos
                time.sleep(DELAY_BETWEEN_REQUESTS)
            
        except Exception as e:
            print(f"✗ Error procesando página {page}: {e}")
    
    # Resumen final
    print()
    print("="*70)
    print("RESUMEN FINAL")
    print("="*70)
    print(f"Total productos procesados: {total_products}")
    print(f"  ✓ Exitosos: {total_products - failed_products}")
    print(f"  ✗ Fallidos: {failed_products}")
    if total_duplicates > 0:
        print(f"  🔄 Duplicados en misma página (omitidos): {total_duplicates}")
    if cross_page_duplicates:
        print(f"  🔄 Duplicados entre páginas (omitidos): {len(cross_page_duplicates)}")
    
    # Mostrar detalles de duplicados
    if total_duplicates > 0 or cross_page_duplicates:
        print()
        print("  Productos duplicados:")
        
        # Duplicados en la misma página
        if total_duplicates > 0:
            from collections import defaultdict
            duplicates_by_name = defaultdict(list)
            for dup in all_duplicates:
                duplicates_by_name[dup['name']].append(dup)
            
            for name, dup_list in sorted(duplicates_by_name.items()):
                print(f"    • \"{name}\" (duplicado en misma página):")
                print(f"      - Descargado: {dup_list[0]['first_url']}")
                for dup in dup_list:
                    print(f"      - Omitido: {dup['url']}")
        
        # Duplicados entre páginas
        if cross_page_duplicates:
            from collections import defaultdict
            cross_duplicates_by_name = defaultdict(list)
            for dup in cross_page_duplicates:
                cross_duplicates_by_name[dup['name']].append(dup)
            
            for name, dup_list in sorted(cross_duplicates_by_name.items()):
                print(f"    • \"{name}\" (duplicado entre páginas):")
                # Agrupar por página anterior
                for dup in dup_list:
                    print(f"      - Ya descargado en página {dup['previous_page']}: {dup['previous_dir']}")
                    print(f"      - Omitido en página {dup['current_page']}: {dup['current_url']}")
    
    print()
    print(f"Total imágenes descargadas: {total_images}")
    print(f"📁 Ubicación: {base_dir.absolute()}")
    print("="*70)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Descarga imágenes de una categoría Yupoo.")
    parser.add_argument('--url', type=str, help='URL base de la categoría Yupoo.')
    parser.add_argument('--name', type=str, default=None, help='Nombre de la categoría (opcional, se extraerá si no se especifica).')
    parser.add_argument('--start', type=int, help='Página inicial a procesar.')
    parser.add_argument('--end', type=int, help='Página final a procesar.')
    parser.add_argument('--password', type=str, default=None, help='Contraseña para páginas protegidas (opcional).')
    
    args = parser.parse_args()
    
    main(args.url, args.name, args.start, args.end, args.password)
