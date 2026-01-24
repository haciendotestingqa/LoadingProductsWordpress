#!/usr/bin/env python3
"""
Script wrapper para descargar múltiples colecciones de Yupoo en paralelo
Uso: python3 download_multiple_collections.py
"""

import subprocess
import sys
import time
import re
import requests
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urlparse

# Configuración de colecciones a descargar
# Cada colección puede tener una 'password' opcional para páginas protegidas
# Ejemplo de colección con contraseña:
# {
#     'url': 'https://wholesale4shoesbags.x.yupoo.com/categories/5009203',
#     'name': None,
#     'start_page': 1,
#     'end_page': 1,
#     'password': '214911',  # Contraseña para páginas protegidas (opcional)
# }
COLLECTIONS = [
    {
         'url': 'https://yitian333.x.yupoo.com/categories/4259937',  # BROKEN PLANET系列
         'name': None,  # Se extraerá automáticamente
         'start_page': 1,
         'end_page': 2,
         # 'password': None,  # Sin contraseña (página pública)
     },
    {
        'url': 'https://yitian333.x.yupoo.com/categories/4473868',  # AMIRI系列
        'name': None,  # Se extraerá automáticamente
        'start_page': 1,
        'end_page': 2,
    },
    {
        'url': 'https://yitian333.x.yupoo.com/categories/4811432',  # ow off系列
        'name': None,  # Se extraerá automáticamente
        'start_page': 1,
        'end_page': 1,
    },
    {
        'url': 'https://yitian333.x.yupoo.com/categories/4149449',  # REP系列
        'name': None,  # Se extraerá automáticamente
        'start_page': 1,
        'end_page': 1,
    },
    {
        'url': 'https://yitian333.x.yupoo.com/categories/4511096',  # ADWYSD系列
        'name': None,  # Se extraerá automáticamente
        'start_page': 1,
        'end_page': 1,
    },
    {
        'url': 'https://yitian333.x.yupoo.com/categories/4559369',  # WARREN LOTAS系列
        'name': None,  # Se extraerá automáticamente
        'start_page': 1,
        'end_page': 1,
    },    
    {
        'url': 'https://yitian333.x.yupoo.com/categories/4545050',  # HACULLA系列
        'name': None,  # Se extraerá automáticamente
        'start_page': 1,
        'end_page': 1,
    },
        {
        'url': 'https://yitian333.x.yupoo.com/categories/4284281',  # MARNI系列
        'name': None,  # Se extraerá automáticamente
        'start_page': 1,
        'end_page': 1,
    },    
]

def sanitize_filename(filename):
    """Limpia el nombre de archivo solo de caracteres problemáticos del sistema de archivos"""
    filename = str(filename)
    # Solo reemplaza caracteres que causan problemas en sistemas de archivos
    filename = filename.replace('/', '-').replace('\\', '-')
    filename = filename.replace('\0', '')
    # Limita la longitud solo si es extremadamente larga
    if len(filename) > 200:
        filename = filename[:200]
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
        return False

def extract_category_name_fast(url, password=None):
    """Extrae rápidamente el nombre de la categoría desde la URL"""
    try:
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
            if not authenticate_if_needed(session, url, password):
                return None
        
        # Extraer ID de categoría de la URL
        category_id = url.split('/')[-1]
        
        # Hacer petición rápida solo para extraer el nombre
        response = session.get(f"{url}?page=1", timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Método 1: Buscar en el texto que dice "分类"X系列"下的相册" o "分类"X"下的相册" (MÁS CONFIABLE)
        page_text = soup.get_text()
        # Buscar patrón: 分类"nombre"下的相册 (puede tener 系列 o no)
        match = re.search(r'分类["\']([^"\']+)["\']下的相册', page_text)
        if match:
            category_name = match.group(1).strip()
            # Filtrar nombres inválidos
            invalid_names = ['简体中文', 'english', '繁體中文', 'español', 'portugues', 'Français', 'Deutsch', 'Русский']
            if category_name and category_name not in invalid_names:
                return category_name
        
        # También buscar en el título de la página
        title_tag = soup.find('title')
        if title_tag:
            title_text = title_tag.get_text()
            match = re.search(r'分类["\']([^"\']+)["\']下的相册', title_text)
            if match:
                category_name = match.group(1).strip()
                invalid_names = ['简体中文', 'english', '繁體中文', 'español', 'portugues', 'Français', 'Deutsch', 'Русский']
                if category_name and category_name not in invalid_names:
                    return category_name
        
        # Método 2: Buscar en breadcrumbs - solo enlaces que apunten a esta categoría específica
        category_links = soup.find_all('a', href=lambda x: x and f'/categories/{category_id}' in str(x))
        for link in category_links:
            text = link.text.strip()
            href = link.get('href', '')
            # Filtrar enlaces de idioma (tienen parámetros ?page=1 o son solo idiomas)
            invalid_names = ['简体中文', 'english', '繁體中文', 'español', 'portugues', 'Français', 'Deutsch', 'Русский', 
                           '登录', '注册', 'Home', 'All categories', 'Yupoo', 'search', 'QR code']
            is_language_link = (text in invalid_names or 
                               text.lower() in ['english', '简体中文', '繁體中文', 'español', 'portugues', 
                                               'français', 'deutsch', 'русский'] or
                               '?page=' in href or
                               len(text) < 3)
            if text and not is_language_link and text not in invalid_names:
                # Aceptar cualquier nombre que no sea de idioma, no necesita tener "系列"
                return text
        
        # Método 3: Buscar en títulos que contengan "系列"
        for tag in ['h1', 'h2', 'h3']:
            titles = soup.find_all(tag)
            for title in titles:
                text = title.text.strip()
                if '系列' in text:
                    # Extraer la parte que contiene "系列"
                    match = re.search(r'([^\s]+系列)', text)
                    if match:
                        category_name = match.group(1)
                        # Filtrar nombres inválidos
                        invalid_names = ['简体中文', 'english', '繁體中文']
                        if category_name not in invalid_names:
                            return category_name
        
        # Método 4: Buscar en la lista de categorías del menú lateral
        # Buscar enlaces en listas que contengan el ID de categoría
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            href = link.get('href', '')
            # Buscar enlaces que apunten exactamente a esta categoría (sin parámetros de idioma)
            if f'/categories/{category_id}' in href and '?page=' not in href:
                text = link.text.strip()
                # Filtrar nombres inválidos y de idioma
                invalid_names = ['简体中文', 'english', '繁體中文', 'español', 'portugues', 'Français', 'Deutsch', 'Русский',
                               '登录', '注册', 'Home', 'All categories', 'Yupoo', 'search', 'QR code']
                is_language = text.lower() in ['english', '简体中文', '繁體中文', 'español', 'portugues', 
                                               'français', 'deutsch', 'русский'] or text in invalid_names
                if text and not is_language and len(text) > 2:
                    return text
        
        return None
    except Exception:
        return None

def get_category_name(collection):
    """Obtiene el nombre de la categoría (de configuración o extrayéndolo)"""
    # Si está especificado en la configuración, usarlo
    if collection.get('name'):
        return collection['name']
    
    # Intentar extraerlo de la URL (pasar contraseña si existe)
    password = collection.get('password')
    category_name = extract_category_name_fast(collection['url'], password)
    if category_name:
        return category_name
    
    # Si no se puede extraer, usar el ID como respaldo
    category_id = collection['url'].split('/')[-1]
    return f"Categoria_{category_id}"

def main():
    """Ejecuta múltiples colecciones en paralelo"""
    script_path = Path(__file__).parent / 'download_yupoo_category.py'
    
    if not script_path.exists():
        print(f"❌ Error: No se encuentra el script {script_path}")
        sys.exit(1)
    
    print("="*70)
    print("Descargador Múltiple de Colecciones Yupoo")
    print("="*70)
    print(f"Colecciones a descargar: {len(COLLECTIONS)}")
    print("="*70)
    print()
    
    # Crear carpeta de logs
    logs_dir = Path(__file__).parent / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    processes = []
    
    try:
        # Primero, extraer nombres de todas las categorías
        print("Extrayendo nombres de categorías...")
        category_names = {}
        for idx, collection in enumerate(COLLECTIONS, 1):
            category_id = collection['url'].split('/')[-1]
            print(f"  [{idx}/{len(COLLECTIONS)}] Extrayendo nombre para categoría {category_id}...", end=' ', flush=True)
            category_name = get_category_name(collection)
            category_names[category_id] = category_name
            print(f"✓ {category_name}")
        print()
        
        # Ejecutar cada colección en paralelo
        for idx, collection in enumerate(COLLECTIONS, 1):
            category_id = collection['url'].split('/')[-1]
            category_name = category_names[category_id]
            
            print(f"[{idx}/{len(COLLECTIONS)}] Preparando colección: {category_name}")
            print(f"  URL: {collection['url']}")
            
            # Construir comando con -u para unbuffered output
            cmd = [sys.executable, '-u', str(script_path), '--url', collection['url']]
            
            if collection['name']:
                cmd.extend(['--name', collection['name']])
            
            # Pasar contraseña si está configurada
            if collection.get('password'):
                cmd.extend(['--password', collection['password']])
            
            cmd.extend(['--start', str(collection['start_page'])])
            cmd.extend(['--end', str(collection['end_page'])])
            
            # Crear archivo de log con nombre de categoría
            sanitized_name = sanitize_filename(category_name)
            log_file = logs_dir / f"{sanitized_name}_{category_id}.log"
            
            # Abrir archivo de log directamente en modo texto con line buffering
            # Esto permite escritura inmediata sin necesidad de threads
            log_handle = open(log_file, 'w', encoding='utf-8', buffering=1)
            
            # Ejecutar en segundo plano redirigiendo directamente al archivo
            # Usar -u para unbuffered output en Python
            process = subprocess.Popen(
                cmd,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                cwd=Path(__file__).parent
            )
            
            # No necesitamos thread ya que la salida va directamente al archivo
            processes.append({
                'process': process,
                'url': collection['url'],
                'log_file': log_file,
                'log_handle': log_handle,  # Guardar el handle para cerrarlo después
                'category_id': category_id,
                'category_name': category_name
            })
            print(f"  ✓ Iniciado (PID: {process.pid})")
            print(f"  📝 Log: {log_file}")
        
        print(f"\n{'='*70}")
        print(f"Ejecutando {len(processes)} colecciones en paralelo...")
        print(f"📁 Logs guardados en: {logs_dir.absolute()}")
        print("Presiona Ctrl+C para detener todas las descargas")
        print(f"{'='*70}\n")
        
        # Esperar a que todos los procesos terminen
        while processes:
            for proc_info in processes[:]:
                if proc_info['process'].poll() is not None:
                    # Proceso terminado - cerrar el archivo de log
                    if 'log_handle' in proc_info:
                        try:
                            proc_info['log_handle'].flush()
                            proc_info['log_handle'].close()
                        except (IOError, OSError):
                            pass
                    
                    # Proceso terminado
                    return_code = proc_info['process'].returncode
                    category_name = proc_info.get('category_name', proc_info['category_id'])
                    if return_code == 0:
                        print(f"✓ {category_name} completada")
                        print(f"  📝 Log: {proc_info['log_file']}")
                    else:
                        print(f"✗ {category_name} terminó con error (código: {return_code})")
                        print(f"  📝 Log: {proc_info['log_file']}")
                    processes.remove(proc_info)
            
            if processes:
                time.sleep(1)  # Esperar un segundo antes de verificar de nuevo
        
        print(f"\n{'='*70}")
        print("Todas las descargas completadas")
        print(f"📁 Todos los logs están en: {logs_dir.absolute()}")
        print(f"{'='*70}")
        
    except KeyboardInterrupt:
        print("\n\n⚠ Deteniendo todas las descargas...")
        for proc_info in processes:
            if proc_info['process'].poll() is None:
                category_name = proc_info.get('category_name', proc_info['category_id'])
                proc_info['process'].terminate()
                print(f"  Deteniendo: {category_name} (PID: {proc_info['process'].pid})")
        
        # Esperar un poco y luego forzar si es necesario
        time.sleep(2)
        for proc_info in processes:
            if proc_info['process'].poll() is None:
                category_name = proc_info.get('category_name', proc_info['category_id'])
                proc_info['process'].kill()
                print(f"  Forzado a detener: {category_name}")
        
        # Cerrar todos los archivos de log
        for proc_info in processes:
            if 'log_handle' in proc_info:
                try:
                    proc_info['log_handle'].flush()
                    proc_info['log_handle'].close()
                except (IOError, OSError):
                    pass

if __name__ == "__main__":
    main()
