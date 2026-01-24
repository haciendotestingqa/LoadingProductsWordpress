#!/usr/bin/env python3
"""
Script para analizar productos repetidos y comparar con lo disponible en línea
Compara lo descargado localmente con lo que hay en el sitio web
"""

from pathlib import Path
from collections import Counter
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import sys

# Importar configuración de colecciones
try:
    sys.path.insert(0, str(Path(__file__).parent))
    from download_multiple_collections import COLLECTIONS, extract_category_name_fast, sanitize_filename, is_password_protected, authenticate_if_needed
except ImportError:
    print("❌ Error: No se puede importar la configuración de colecciones")
    sys.exit(1)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Referer': 'https://yitian333.x.yupoo.com/',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
}

def get_total_products_online(url, max_pages_to_check=10, session=None, password=None):
    """Obtiene el total de productos disponibles en línea para una categoría"""
    try:
        # Usar sesión si está disponible, sino crear una nueva
        if session is None:
            session = requests.Session()
            session.headers.update(HEADERS)
            # Autenticar si es necesario
            if password:
                if not authenticate_if_needed(session, url, password):
                    return None
        
        # Primero intentar obtener el total desde la primera página
        page_url = f"{url}?page=1" if '?' not in url else f"{url}&page=1"
        response = session.get(page_url, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Verificar si requiere autenticación
        if password and is_password_protected(soup):
            if not authenticate_if_needed(session, url, password):
                return None
            # Reintentar
            response = session.get(page_url, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
        
        # Buscar en elementos con clase que contenga "total"
        # El texto suele ser "en total X álbumes" en español
        total_elements = soup.select('[class*="total"]')
        for elem in total_elements:
            text = elem.get_text()
            # Buscar patrones en español e inglés
            patterns = [
                r'en total (\d+) álbumes',  # español
                r'total (\d+) albums',  # inglés
                r'(\d+)\s+albums? total',  # variación
                r'共(\d+)个相册',  # chino
                r'共\s*(\d+)\s*个相册',  # chino con espacios
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    return int(match.group(1))
        
        # Buscar en todo el texto de la página
        page_text = soup.get_text()
        for pattern in [r'en total (\d+) álbumes', r'total (\d+) albums', r'共(\d+)个相册']:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                return int(match.group(1))
        
        # Si no se encuentra, intentar contar todas las páginas disponibles
        # Buscar "共X页" o "X páginas"
        page_patterns = [r'共(\d+)页', r'(\d+)\s+páginas', r'(\d+)\s+pages']
        for pattern in page_patterns:
            page_match = re.search(pattern, page_text, re.IGNORECASE)
            if page_match:
                total_pages = int(page_match.group(1))
                # Contar productos únicos de todas las páginas
                all_products = set()
                for page_num in range(1, min(total_pages + 1, max_pages_to_check + 1)):
                    products = get_products_from_page_online(url, page_num, session, password)
                    for p in products:
                        all_products.add(p['album_id'])  # Usar album_id para evitar duplicados
                return len(all_products)
        
        return None
    except Exception:
        return None

def extract_products_from_page_online(soup, base_url, include_duplicates=False):
    """Extrae productos de una página en línea usando la estructura real del sitio
    
    Args:
        soup: BeautifulSoup object
        base_url: URL base
        include_duplicates: Si True, incluye todos los productos aunque tengan el mismo nombre
    """
    products = []
    seen_album_ids = set()
    
    # Buscar contenedores de productos con la clase correcta
    product_containers = soup.find_all('div', class_='categories__children')
    
    for container in product_containers:
        # Buscar el enlace al álbum dentro del contenedor
        link = container.find('a', href=lambda x: x and '/albums/' in x)
        if not link:
            continue
        
        href = link.get('href', '')
        album_id_match = re.search(r'/albums/(\d+)', href)
        if not album_id_match:
            continue
        
        album_id = album_id_match.group(1)
        if album_id in seen_album_ids:
            continue
        
        # El nombre del producto está en el texto del contenedor
        # El formato suele ser: "número_fotos|nombre_producto"
        container_text = container.get_text(separator='|', strip=True)
        parts = [p.strip() for p in container_text.split('|') if p.strip()]
        
        product_name = None
        # El primer elemento suele ser el número de fotos, el segundo el nombre del producto
        # Algunos productos se nombran solo con números, así que no podemos filtrarlos todos
        if len(parts) >= 2:
            # Tomar el segundo elemento como nombre (el primero es el conteo de fotos)
            product_name = parts[1]
        elif len(parts) == 1:
            # Si solo hay un elemento y no es solo un número pequeño (< 100), usarlo
            if not (re.match(r'^\d+$', parts[0]) and len(parts[0]) <= 2):
                product_name = parts[0]
        
        if product_name:
            invalid = ['登录', '注册', 'Home', 'album', 'All categories', 'Yupoo', 'search', 'QR code', '简体中文', 'english']
            if (product_name not in invalid and 
                not product_name.startswith('http') and 
                len(product_name.strip()) >= 2):
                seen_album_ids.add(album_id)
                products.append({
                    'name': sanitize_filename(product_name.strip()),
                    'album_id': album_id
                })
    
    # Si no encontramos productos con la clase específica, usar el método anterior
    if not products:
        album_links = soup.find_all('a', href=lambda x: x and '/albums/' in x)
        
        for link in album_links:
            href = link.get('href', '')
            if not href:
                continue
            
            if '?uid=' not in href and '&isSubCate=' not in href:
                parent = link.find_parent(['nav', 'header', 'footer'])
                if parent:
                    continue
            
            album_id_match = re.search(r'/albums/(\d+)', href)
            if not album_id_match:
                continue
            
            album_id = album_id_match.group(1)
            if album_id in seen_album_ids:
                continue
            
            product_name = None
            parent = link.find_parent(['div', 'article', 'section', 'li'])
            
            if parent:
                container_text = parent.get_text(separator='\n', strip=True)
                lines = [l.strip() for l in container_text.split('\n') if l.strip()]
                
                # Buscar el nombre del producto (puede ser un número)
                for line in reversed(lines):
                    if line and len(line) > 0:
                        invalid_names = ['登录', '注册', 'Home', 'album', 'All categories', 'Yupoo', 'search', 'QR code']
                        # Ignorar solo números muy pequeños (1-99) que son probablemente conteos
                        is_small_number = re.match(r'^\d{1,2}$', line)
                        if (line not in invalid_names and 
                            not line.startswith('http') and 
                            not is_small_number):
                            product_name = line
                            break
            
            if product_name and len(product_name) >= 2:
                invalid = ['登录', '注册', 'Home', 'album', 'All categories', 'Yupoo', 'search', 'QR code', '简体中文', 'english']
                if (product_name not in invalid and 
                    not product_name.startswith('http') and 
                    not re.match(r'^\d+$', product_name) and
                    len(product_name.strip()) >= 2):
                    seen_album_ids.add(album_id)
                    products.append({
                        'name': sanitize_filename(product_name.strip()),
                        'album_id': album_id
                    })
    
    return products

def get_products_from_page_online(url, page_num, session=None, password=None):
    """Obtiene todos los productos de una página específica en línea"""
    try:
        # Usar sesión si está disponible, sino crear una nueva
        if session is None:
            session = requests.Session()
            session.headers.update(HEADERS)
            # Autenticar si es necesario
            if password:
                if not authenticate_if_needed(session, url, password):
                    return []
        
        page_url = f"{url}?page={page_num}"
        response = session.get(page_url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Verificar si requiere autenticación
        if password and is_password_protected(soup):
            if not authenticate_if_needed(session, url, password):
                return []
            # Reintentar
            response = session.get(page_url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
        
        return extract_products_from_page_online(soup, url)
    except Exception as e:
        return []

def analyze_collection_online_vs_local(collection_config):
    """Analiza una colección comparando lo que hay en línea vs lo descargado"""
    url = collection_config['url']
    start_page = collection_config['start_page']
    end_page = collection_config['end_page']
    password = collection_config.get('password')
    
    # Crear sesión para mantener cookies de autenticación
    session = requests.Session()
    session.headers.update(HEADERS)
    
    # Autenticar si es necesario
    if password:
        if not authenticate_if_needed(session, url, password):
            print(f"  ✗ Error: No se pudo autenticar para {url}")
            return None
    
    # Obtener nombre de categoría - primero intentar desde la configuración
    category_name = collection_config.get('name')
    
    # Si no está en la configuración, intentar extraerlo
    if not category_name:
        category_name = extract_category_name_fast(url, password)
    
    # Si aún no se puede extraer, buscar en las carpetas locales existentes
    if not category_name or category_name.startswith('Categoria_'):
        # Buscar carpeta que coincida con el ID de categoría
        category_id = url.split('/')[-1]
        base_dir = Path("yupoo_downloads")
        if base_dir.exists():
            for folder in base_dir.iterdir():
                if folder.is_dir():
                    # Verificar si el nombre contiene el ID o si hay una carpeta con ese patrón
                    if category_id in folder.name or folder.name.endswith(f"_{category_id}"):
                        # Intentar extraer el nombre real
                        if not category_name or category_name.startswith('Categoria_'):
                            category_name = folder.name.split('_')[0] if '_' in folder.name else folder.name
        
        # Si aún no se encuentra, usar el ID
        if not category_name or category_name.startswith('Categoria_'):
            category_name = f"Categoria_{category_id}"
    
    category_id = url.split('/')[-1]
    sanitized_name = sanitize_filename(category_name)
    local_dir = Path("yupoo_downloads") / sanitized_name
    
    # Si no existe con ese nombre, buscar por todos los métodos posibles
    if not local_dir.exists():
        base_dir = Path("yupoo_downloads")
        if base_dir.exists():
            # Método 1: Buscar carpeta que termine con el ID
            for folder in base_dir.iterdir():
                if folder.is_dir() and folder.name.endswith(f"_{category_id}"):
                    local_dir = folder
                    category_name = folder.name.rsplit('_', 1)[0]
                    break
            
            # Método 2: Si no se encuentra, buscar carpeta que contenga parte del nombre
            if not local_dir.exists() and category_name != f"Categoria_{category_id}":
                # Intentar buscar por similitud de nombre (sin el ID)
                search_name = category_name.replace(f"_{category_id}", "").lower()
                for folder in base_dir.iterdir():
                    if folder.is_dir() and search_name in folder.name.lower():
                        local_dir = folder
                        category_name = folder.name
                        break
            
            # Método 3: Buscar todas las carpetas y verificar cuál corresponde a esta categoría
            # revisando el contenido o metadatos (último recurso)
            if not local_dir.exists():
                # Intentar extraer el nombre real desde la web y buscar esa carpeta
                real_name = extract_category_name_fast(url)
                if real_name and real_name != f"Categoria_{category_id}":
                    test_dir = base_dir / sanitize_filename(real_name)
                    if test_dir.exists():
                        local_dir = test_dir
                        category_name = real_name
    
    print(f"\n{'='*70}")
    print(f"📦 COLECCIÓN: {category_name}")
    print(f"   URL: {url}")
    print(f"{'='*70}")
    
    # Obtener total de productos en línea
    print("\n  🔍 Consultando información en línea...")
    total_online = get_total_products_online(url, max_pages_to_check=end_page + 5, session=session, password=password)
    if total_online:
        print(f"  📊 Total productos en línea: {total_online}")
    else:
        print(f"  ⚠ No se pudo obtener el total de productos en línea")
        # Intentar contar desde las páginas que vamos a analizar
        print(f"  ℹ Se calculará el total basado en las páginas analizadas")
    
    # Obtener productos descargados localmente
    local_products_by_page = {}
    local_total = 0
    
    if local_dir.exists():
        pages = []
        for item in local_dir.iterdir():
            if item.is_dir() and item.name.isdigit():
                pages.append((int(item.name), item))
        
        pages.sort(key=lambda x: x[0])
        
        for page_num, page_dir in pages:
            products = []
            for item in page_dir.iterdir():
                if item.is_dir() and not item.name.isdigit():
                    products.append(item.name)
            
            local_products_by_page[page_num] = products
            local_total += len(products)
    else:
        print(f"  ⚠ No se encontró la carpeta local: {local_dir}")
    
    print(f"  📁 Total productos descargados: {local_total}")
    
    if total_online:
        difference = total_online - local_total
        if difference > 0:
            print(f"  ⚠ Faltan {difference} productos por descargar")
        elif difference < 0:
            print(f"  ⚠ Hay {abs(difference)} productos más descargados que en línea (posibles duplicados)")
        else:
            print(f"  ✓ Todos los productos están descargados")
    
    # Analizar cada página descargada
    print(f"\n  📄 ANÁLISIS POR PÁGINA:")
    
    online_products_all = []
    local_products_all = []
    
    for page_num in range(start_page, end_page + 1):
        print(f"\n    Página {page_num}:")
        
        # Productos en línea
        online_products = get_products_from_page_online(url, page_num, session, password)
        online_names = [p['name'] for p in online_products]
        online_products_all.extend(online_names)
        
        # Detectar duplicados en línea (mismo nombre, diferentes album_id)
        online_counter = Counter(online_names)
        online_duplicates = {name: count for name, count in online_counter.items() if count > 1}
        total_containers = len(online_products)
        unique_online = len(online_counter)
        
        # Productos descargados
        local_products = local_products_by_page.get(page_num, [])
        local_products_all.extend(local_products)
        
        print(f"      📊 En línea: {total_containers} contenedores, {unique_online} productos únicos")
        if online_duplicates:
            duplicate_count = sum(count - 1 for count in online_duplicates.values())
            print(f"         └─ ⚠ {len(online_duplicates)} productos con nombres duplicados ({duplicate_count} duplicaciones)")
        print(f"      📁 Descargados: {len(local_products)} productos")
        
        # Mostrar productos duplicados en línea
        if online_duplicates:
            print(f"\n      🔄 PRODUCTOS DUPLICADOS EN LÍNEA (mismo nombre, diferentes álbumes):")
            for name, count in sorted(online_duplicates.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"        • '{name}': aparece {count} veces")
            if len(online_duplicates) > 5:
                print(f"        ... y {len(online_duplicates) - 5} productos más con duplicados")
            print(f"      ℹ Nota: Solo se descarga la primera ocurrencia de cada nombre")
        
        # Encontrar productos repetidos en lo descargado
        counter = Counter(local_products)
        repeated = {name: count for name, count in counter.items() if count > 1}
        
        if repeated:
            print(f"\n      🔴 Productos repetidos en descarga: {len(repeated)}")
            for name, count in sorted(repeated.items(), key=lambda x: x[1], reverse=True):
                print(f"        • {name}: aparece {count} veces")
        else:
            print(f"\n      ✓ No hay productos repetidos en descarga")
        
        # Comparar productos en línea vs descargados
        online_set = set(online_names)
        local_set = set(local_products)
        
        missing = online_set - local_set
        extra = local_set - online_set
        
        if missing:
            print(f"      ⚠ Faltan {len(missing)} productos (en línea pero no descargados)")
            if len(missing) <= 10:
                for name in sorted(missing):
                    print(f"        - {name}")
            else:
                for name in sorted(list(missing))[:10]:
                    print(f"        - {name}")
                print(f"        ... y {len(missing) - 10} más")
        
        if extra:
            print(f"      ⚠ Hay {len(extra)} productos extra (descargados pero no en línea)")
            if len(extra) <= 10:
                for name in sorted(extra):
                    print(f"        + {name}")
            else:
                for name in sorted(list(extra))[:10]:
                    print(f"        + {name}")
                print(f"        ... y {len(extra) - 10} más")
    
    # Resumen general de la colección
    online_unique = len(set(online_products_all))
    local_unique = len(set(local_products_all))
    total_online_containers = len(online_products_all)
    
    # Detectar duplicados en todas las páginas analizadas
    online_all_counter = Counter(online_products_all)
    online_all_duplicates = {name: count for name, count in online_all_counter.items() if count > 1}
    total_duplicate_count = sum(count - 1 for count in online_all_duplicates.values())
    
    print(f"\n  📊 RESUMEN DE LA COLECCIÓN:")
    print(f"    Contenedores en línea (páginas {start_page}-{end_page}): {total_online_containers}")
    print(f"    Productos únicos en línea: {online_unique}")
    if online_all_duplicates:
        print(f"    └─ Productos con nombres duplicados: {len(online_all_duplicates)} ({total_duplicate_count} duplicaciones)")
    print(f"    Total descargados: {local_unique} productos únicos")
    
    # Verificar que coincidan productos únicos
    if online_unique == local_unique:
        print(f"    ✅ PERFECTO: Todos los productos únicos fueron descargados correctamente")
    elif local_unique < online_unique:
        diff = online_unique - local_unique
        print(f"    ⚠ Faltan {diff} productos únicos por descargar")
    else:
        diff = local_unique - online_unique
        print(f"    ⚠ Hay {diff} productos más descargados que únicos en línea")
    
    # Si tenemos el total en línea, mostrar la diferencia
    if total_online:
        if total_online > online_unique:
            print(f"\n    ℹ Información adicional:")
            print(f"    Total absoluto en la categoría: {total_online} productos")
            print(f"    Productos en otras páginas: {total_online - online_unique}")
        difference = total_online - local_unique
        if difference > 0 and total_online > online_unique:
            print(f"    └─ De los cuales {difference} no están en las páginas configuradas")
    
    # Productos repetidos en todas las páginas descargadas
    all_local_counter = Counter(local_products_all)
    all_repeated = {name: count for name, count in all_local_counter.items() if count > 1}
    
    if all_repeated:
        print(f"    🔴 Productos repetidos en todas las páginas: {len(all_repeated)}")
        for name, count in sorted(all_repeated.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"      • {name}: aparece {count} veces")
        if len(all_repeated) > 10:
            print(f"      ... y {len(all_repeated) - 10} más")
    
    return {
        'category_name': category_name,
        'total_online': total_online,
        'total_local': len(set(local_products_all)),
        'repeated_count': len(all_repeated)
    }

def main():
    """Función principal"""
    print("="*70)
    print("Análisis Comparativo: En Línea vs Descargado")
    print("="*70)
    print()
    
    if not COLLECTIONS:
        print("❌ No hay colecciones configuradas")
        return
    
    results = []
    
    for idx, collection in enumerate(COLLECTIONS, 1):
        print(f"\n[{idx}/{len(COLLECTIONS)}] Analizando colección...")
        try:
            result = analyze_collection_online_vs_local(collection)
            results.append(result)
        except Exception as e:
            print(f"  ❌ Error analizando colección: {e}")
            import traceback
            traceback.print_exc()
    
    # Resumen general
    print(f"\n{'='*70}")
    print("📊 RESUMEN GENERAL")
    print(f"{'='*70}")
    
    total_online = sum(r.get('total_online', 0) or 0 for r in results)
    total_local = sum(r.get('total_local', 0) for r in results)
    total_repeated = sum(r.get('repeated_count', 0) for r in results)
    
    print(f"Total colecciones analizadas: {len(results)}")
    print(f"Total productos en línea: {total_online}")
    print(f"Total productos descargados (únicos): {total_local}")
    print(f"Total productos repetidos: {total_repeated}")
    
    if total_online > 0:
        difference = total_online - total_local
        if difference > 0:
            print(f"⚠ Faltan {difference} productos por descargar en total")
        elif difference < 0:
            print(f"⚠ Hay {abs(difference)} productos más descargados que en línea")
        else:
            print(f"✓ Todos los productos están descargados")
    
    print(f"{'='*70}")

if __name__ == "__main__":
    main()
