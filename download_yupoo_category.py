#!/usr/bin/env python3
"""
Script para descargar todas las imágenes de productos de una categoría Yupoo
Estructura: Categoria/Pagina/Producto/imagenes.jpg
"""

import os
import re
import requests
from pathlib import Path
import time
from urllib.parse import urlparse, parse_qs, urljoin
from bs4 import BeautifulSoup

# Configuración
BASE_URL = "https://yitian333.x.yupoo.com/categories/4135412"
START_PAGE = 2
END_PAGE = 4
MAX_RETRIES = 3
DELAY_BETWEEN_REQUESTS = 0.5
DELAY_BETWEEN_IMAGES = 0.3

# Headers para las peticiones
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Referer': 'https://yitian333.x.yupoo.com/',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
}

def sanitize_filename(filename):
    """Limpia el nombre de archivo de caracteres problemáticos, pero mantiene los originales"""
    # Solo reemplaza caracteres que pueden causar problemas en el sistema de archivos
    filename = str(filename)
    filename = filename.replace('/', '-').replace('\\', '-')
    filename = filename.replace('\0', '')
    # Limita la longitud del nombre de archivo
    if len(filename) > 200:
        filename = filename[:200]
    return filename.strip()

def download_image(url, filepath, retries=3):
    """Descarga una imagen con reintentos"""
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=HEADERS, timeout=30)
            response.raise_for_status()
            
            # Verificar que es una imagen
            content_type = response.headers.get('content-type', '').lower()
            if 'image' not in content_type and len(response.content) < 100:
                # Si la URL original falla, intentar con medium
                if '/original.jpeg' in url:
                    url_alt = url.replace('/original.jpeg', '/medium.jpeg')
                    response = requests.get(url_alt, headers=HEADERS, timeout=30)
                    response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            return True
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(1 * (attempt + 1))  # Espera incremental
            else:
                return False
    return False

def extract_category_name(soup):
    """Extrae el nombre de la categoría"""
    # Buscar en breadcrumbs o título
    breadcrumb = soup.find('a', href=lambda x: x and '/categories/' in x)
    if breadcrumb and breadcrumb.text.strip():
        return breadcrumb.text.strip()
    
    title = soup.find('h2')
    if title:
        text = title.text.strip()
        if '系列' in text or 'Trapstar' in text:
            return text.split()[0] if text.split() else "Trapstar系列"
    
    return "Trapstar系列"

def extract_products_from_page(soup, base_url):
    """Extrae información de productos de la página usando BeautifulSoup"""
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
            container_text = parent.get_text(separator='\n', strip=True)
            lines = [l.strip() for l in container_text.split('\n') if l.strip()]
            
            # El nombre del producto es la línea que NO es solo un número
            # y que tiene más de 1 carácter
            for line in reversed(lines):  # Empezar desde el final
                if line and not re.match(r'^\d+$', line) and len(line) > 1:
                    # Verificar que no sea texto de navegación
                    invalid_names = ['登录', '注册', 'Home', 'album', 'All categories', 'Yupoo', 'search', 'QR code']
                    if line not in invalid_names and not line.startswith('http'):
                        product_name = line
                        break
            
            # Si no encontramos, buscar en headings dentro del contenedor
            if not product_name:
                headings = parent.find_all(['h2', 'h3', 'h4'])
                for heading in headings:
                    text = heading.get_text(strip=True)
                    if text and not re.match(r'^\d+$', text) and len(text) > 1:
                        link_text = link.get_text(strip=True)
                        if text != link_text and text not in ['登录', '注册', 'Home', 'album']:
                            product_name = text
                            break
        
        # Si aún no tenemos nombre, usar el texto del enlace como último recurso
        if not product_name:
            link_text = link.get_text(strip=True)
            # Solo usar si no es solo un número y tiene sentido
            if link_text and not re.match(r'^\d+$', link_text) and len(link_text) > 2:
                product_name = link_text
        
        # Filtrar nombres inválidos y verificar que tenga sentido
        # Solo agregar si encontramos un nombre válido (no solo números)
        if product_name and len(product_name) >= 2:
            # Filtrar nombres de navegación y URLs
            invalid = ['登录', '注册', 'Home', 'album', 'All categories', 'Yupoo', 'search', 'QR code', '简体中文', 'english']
            # Verificar que el nombre no sea solo números y que no esté en la lista de inválidos
            if (product_name not in invalid and 
                not product_name.startswith('http') and 
                not re.match(r'^\d+$', product_name) and
                len(product_name.strip()) >= 2):
                seen_album_ids.add(album_id)
                seen_urls.add(full_url)
                products.append({
                    'url': full_url,
                    'name': product_name.strip()
                })
    
    # Eliminar duplicados por nombre (por si acaso)
    seen_names = set()
    unique_products = []
    for product in products:
        if product['name'] not in seen_names:
            seen_names.add(product['name'])
            unique_products.append(product)
    
    return unique_products

def extract_images_from_product(soup, product_url):
    """Extrae URLs de imágenes de la página de un producto"""
    images = []
    
    # Buscar todas las imágenes
    img_tags = soup.find_all('img')
    
    seen_hashes = set()
    image_hashes_to_names = {}
    
    for img in img_tags:
        src = img.get('src', '') or img.get('data-src', '') or img.get('data-original', '')
        if not src or 'photo.yupoo.com' not in src:
            continue
        
        # Extraer el hash de la URL
        match = re.search(r'/yitian333/([a-f0-9]+)/', src)
        if match:
            hash_id = match.group(1)
            if hash_id not in seen_hashes:
                seen_hashes.add(hash_id)
                
                # Construir URL original
                original_url = f"https://photo.yupoo.com/yitian333/{hash_id}/original.jpeg"
                images.append({
                    'url': original_url,
                    'hash': hash_id
                })
                
                # Buscar nombre de archivo asociado
                # Buscar heading cercano que pueda tener el nombre
                parent = img.find_parent(['div', 'article', 'section'])
                if parent:
                    heading = parent.find(['h2', 'h3', 'h4'])
                    if heading:
                        filename = heading.get_text(strip=True)
                        if filename and ('.jpg' in filename.lower() or '.jpeg' in filename.lower() or '.png' in filename.lower()):
                            image_hashes_to_names[hash_id] = filename
    
    # También buscar en headings directamente
    headings = soup.find_all(['h2', 'h3', 'h4'])
    for heading in headings:
        text = heading.get_text(strip=True)
        if text and ('.jpg' in text.lower() or '.jpeg' in text.lower() or '.png' in text.lower()):
            # Buscar imagen cercana
            parent = heading.find_parent(['div', 'article', 'section'])
            if parent:
                img_tag = parent.find('img')
                if img_tag:
                    src = img_tag.get('src', '') or img_tag.get('data-src', '')
                    match = re.search(r'/yitian333/([a-f0-9]+)/', src)
                    if match:
                        hash_id = match.group(1)
                        image_hashes_to_names[hash_id] = text
    
    # Combinar imágenes con nombres
    result = []
    for img_info in images:
        hash_id = img_info['hash']
        filename = image_hashes_to_names.get(hash_id, f"{hash_id}.jpg")
        result.append({
            'url': img_info['url'],
            'filename': filename
        })
    
    return result

def download_product_images(product_url, product_name, output_dir, retries=MAX_RETRIES):
    """Descarga todas las imágenes de un producto con reintentos"""
    success_count = 0
    failed_count = 0
    
    for attempt in range(retries):
        try:
            # Obtener la página del producto
            response = requests.get(product_url, headers=HEADERS, timeout=30)
            response.raise_for_status()
            
            # Parsear HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extraer imágenes
            images = extract_images_from_product(soup, product_url)
            
            if not images:
                if attempt < retries - 1:
                    time.sleep(2 * (attempt + 1))
                    continue
                return False, 0, 0
            
            # Descargar cada imagen
            downloaded_filenames = set()  # Para evitar duplicados
            for img_info in images:
                filename = sanitize_filename(img_info['filename'])
                filepath = output_dir / filename
                
                # Evitar descargas duplicadas
                if filename in downloaded_filenames or filepath.exists():
                    continue
                
                if download_image(img_info['url'], filepath):
                    success_count += 1
                    downloaded_filenames.add(filename)
                    time.sleep(DELAY_BETWEEN_IMAGES)
                else:
                    # Intentar con URL alternativa
                    alt_url = img_info['url'].replace('/original.jpeg', '/medium.jpeg')
                    if download_image(alt_url, filepath):
                        success_count += 1
                        downloaded_filenames.add(filename)
                        failed_count -= 1
                    else:
                        failed_count += 1
                
                time.sleep(DELAY_BETWEEN_IMAGES)
            
            if success_count > 0:
                return True, success_count, failed_count
            
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2 * (attempt + 1))
            else:
                return False, success_count, failed_count
    
    return False, success_count, failed_count

def main():
    """Función principal"""
    print("="*70)
    print("Descargador de imágenes Yupoo por categoría")
    print("="*70)
    print(f"Categoría: Trapstar系列")
    print(f"Páginas: {START_PAGE} a {END_PAGE}")
    print(f"URL base: {BASE_URL}")
    print("="*70)
    print()
    
    # Directorio base
    base_dir = Path("yupoo_downloads") / "Trapstar系列"
    base_dir.mkdir(parents=True, exist_ok=True)
    
    total_products = 0
    total_success = 0
    total_failed = 0
    total_images = 0
    
    # Procesar cada página
    for page_num in range(START_PAGE, END_PAGE + 1):
        print(f"\n{'='*70}")
        print(f"Procesando página {page_num}...")
        print(f"{'='*70}")
        
        page_url = f"{BASE_URL}?page={page_num}"
        page_dir = base_dir / str(page_num)
        page_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Obtener la página
            response = requests.get(page_url, headers=HEADERS, timeout=30)
            response.raise_for_status()
            
            # Parsear HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extraer productos
            products = extract_products_from_page(soup, BASE_URL)
            
            if not products:
                print(f"⚠ No se encontraron productos en la página {page_num}")
                continue
            
            print(f"Encontrados {len(products)} productos en página {page_num}\n")
            
            # Procesar cada producto
            for idx, product in enumerate(products, 1):
                product_name = sanitize_filename(product['name'])
                product_url = product['url']
                
                print(f"[{idx}/{len(products)}] Producto: {product_name}")
                print(f"  URL: {product_url}")
                
                product_dir = page_dir / product_name
                product_dir.mkdir(parents=True, exist_ok=True)
                
                success, img_success, img_failed = download_product_images(
                    product_url, product_name, product_dir, MAX_RETRIES
                )
                
                total_products += 1
                total_images += img_success
                
                if success and img_success > 0:
                    total_success += 1
                    print(f"  ✓ Descargadas {img_success} imágenes")
                    if img_failed > 0:
                        print(f"  ⚠ {img_failed} imágenes fallaron")
                else:
                    total_failed += 1
                    print(f"  ✗ Falló (descargadas: {img_success}, fallidas: {img_failed})")
                
                time.sleep(DELAY_BETWEEN_REQUESTS)
            
        except Exception as e:
            print(f"✗ Error procesando página {page_num}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    # Resumen final
    print(f"\n{'='*70}")
    print("RESUMEN FINAL")
    print(f"{'='*70}")
    print(f"Total productos procesados: {total_products}")
    print(f"  ✓ Exitosos: {total_success}")
    print(f"  ✗ Fallidos: {total_failed}")
    print(f"Total imágenes descargadas: {total_images}")
    print(f"📁 Ubicación: {base_dir.absolute()}")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()
