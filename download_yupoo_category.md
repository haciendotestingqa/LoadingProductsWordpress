# Documentación: download_yupoo_category.py

## 📋 Descripción General

Este script de Python está diseñado para descargar automáticamente todas las imágenes de productos de una categoría específica del sitio web Yupoo (específicamente `yitian333.x.yupoo.com`). El script organiza las descargas en una estructura jerárquica de carpetas que refleja la organización del sitio web.

## 🎯 Finalidad

El propósito principal del script es:

1. **Automatizar la descarga masiva** de imágenes de productos desde Yupoo
2. **Organizar las descargas** en una estructura de carpetas lógica: `Categoria/Pagina/Producto/imagenes.jpg`
3. **Mantener los nombres originales** de productos e imágenes para facilitar la identificación
4. **Manejar errores y reintentos** para garantizar la máxima cantidad de descargas exitosas
5. **Evitar duplicados** tanto a nivel de productos como de imágenes

## 📁 Estructura de Carpetas Generada

El script crea la siguiente estructura de directorios:

```
yupoo_downloads/
└── Trapstar系列/          # Nombre de la categoría
    ├── 2/                 # Número de página
    │   ├── 款号：8859/     # Nombre del producto
    │   │   ├── 0E2A9914.jpg
    │   │   ├── 0E2A9913.jpg
    │   │   └── ...
    │   ├── T03# T04#/
    │   │   └── ...
    │   └── ...
    ├── 3/
    │   └── ...
    └── 4/
        └── ...
```

## ⚙️ Configuración

El script tiene las siguientes constantes configurables al inicio:

```python
BASE_URL = "https://yitian333.x.yupoo.com/categories/4135412"  # URL base de la categoría
START_PAGE = 2                                                # Página inicial a procesar
END_PAGE = 4                                                  # Página final a procesar
MAX_RETRIES = 3                                               # Intentos máximos por producto
DELAY_BETWEEN_REQUESTS = 0.5                                  # Segundos entre peticiones de productos
DELAY_BETWEEN_IMAGES = 0.3                                     # Segundos entre descargas de imágenes
```

### Headers HTTP

El script utiliza headers personalizados para simular un navegador real y evitar bloqueos:

- **User-Agent**: Identifica el script como Chrome
- **Referer**: Indica que viene desde el sitio Yupoo
- **Accept**: Especifica tipos de contenido aceptados
- **Accept-Language**: Español e inglés
- **Connection**: keep-alive para mejor rendimiento

## 🔧 Funciones Principales

### 1. `sanitize_filename(filename)`

**Propósito**: Limpia nombres de archivo de caracteres problemáticos para el sistema de archivos.

**Funcionamiento**:
- Reemplaza `/` y `\` por `-`
- Elimina caracteres nulos (`\0`)
- Limita la longitud a 200 caracteres
- Mantiene caracteres especiales como chinos, `#`, espacios, etc.

**Retorna**: String con el nombre sanitizado

### 2. `download_image(url, filepath, retries=3)`

**Propósito**: Descarga una imagen individual con sistema de reintentos.

**Funcionamiento**:
- Intenta descargar la imagen hasta 3 veces
- Si falla con `/original.jpeg`, intenta con `/medium.jpeg` como alternativa
- Verifica que el contenido sea realmente una imagen
- Usa espera incremental entre reintentos (1s, 2s, 3s)

**Parámetros**:
- `url`: URL de la imagen a descargar
- `filepath`: Ruta donde guardar la imagen
- `retries`: Número de intentos (default: 3)

**Retorna**: `True` si se descargó exitosamente, `False` en caso contrario

### 3. `extract_category_name(soup)`

**Propósito**: Extrae el nombre de la categoría desde el HTML parseado.

**Funcionamiento**:
- Busca enlaces con `/categories/` en el breadcrumb
- Si no encuentra, busca en títulos `h2`
- Si no encuentra nada, retorna "Trapstar系列" por defecto

**Retorna**: Nombre de la categoría como string

### 4. `extract_products_from_page(soup, base_url)`

**Propósito**: Extrae información de todos los productos visibles en una página de categoría.

**Funcionamiento**:
1. Busca todos los enlaces que contengan `/albums/` en el HTML
2. Filtra enlaces que no sean productos (navegación, headers, footers)
3. Extrae el ID único del álbum de cada URL
4. **Problema clave resuelto**: El texto del enlace suele ser solo el número de fotos (ej: "25"), no el nombre del producto
5. Busca el nombre real del producto en el contenedor padre:
   - Analiza las líneas de texto del contenedor
   - Identifica la línea que NO es solo un número y tiene más de 1 carácter
   - Si no encuentra, busca en headings (`h2`, `h3`, `h4`)
6. Filtra nombres inválidos (navegación, URLs, etc.)
7. Elimina duplicados por ID de álbum y por nombre

**Retorna**: Lista de diccionarios con `{'url': str, 'name': str}`

**Nota importante**: Esta función es crítica porque debe distinguir entre:
- El número de fotos (ej: "25") que aparece en el enlace
- El nombre real del producto (ej: "款号：8859") que aparece en el contenedor

### 5. `extract_images_from_product(soup, product_url)`

**Propósito**: Extrae todas las URLs de imágenes de alta resolución de una página de producto.

**Funcionamiento**:
1. Busca todas las etiquetas `<img>` en el HTML
2. Filtra imágenes que pertenezcan a `photo.yupoo.com`
3. Extrae el hash único de cada imagen de la URL
4. Construye URLs de alta resolución usando el formato: `https://photo.yupoo.com/yitian333/{hash}/original.jpeg`
5. Intenta asociar nombres de archivo desde headings cercanos que contengan `.jpg`, `.jpeg`, o `.png`
6. Si no encuentra nombre, usa el hash como nombre de archivo

**Retorna**: Lista de diccionarios con `{'url': str, 'filename': str}`

### 6. `download_product_images(product_url, product_name, output_dir, retries=MAX_RETRIES)`

**Propósito**: Descarga todas las imágenes de un producto con sistema de reintentos.

**Funcionamiento**:
1. Intenta hasta `MAX_RETRIES` veces obtener la página del producto
2. Extrae todas las URLs de imágenes
3. Para cada imagen:
   - Sanitiza el nombre del archivo
   - Verifica que no exista ya (evita duplicados)
   - Intenta descargar con URL original
   - Si falla, intenta con URL alternativa (`/medium.jpeg`)
   - Espera `DELAY_BETWEEN_IMAGES` entre descargas
4. Retorna estadísticas de éxito/fallo

**Parámetros**:
- `product_url`: URL de la página del producto
- `product_name`: Nombre del producto (para logging)
- `output_dir`: Directorio donde guardar las imágenes
- `retries`: Número de intentos (default: MAX_RETRIES)

**Retorna**: Tupla `(success: bool, success_count: int, failed_count: int)`

### 7. `main()`

**Propósito**: Función principal que orquesta todo el proceso de descarga.

**Flujo de ejecución**:
1. Crea el directorio base `yupoo_downloads/Trapstar系列/`
2. Itera sobre cada página (desde `START_PAGE` hasta `END_PAGE`)
3. Para cada página:
   - Descarga el HTML de la página
   - Extrae todos los productos
   - Para cada producto:
     - Crea la carpeta del producto
     - Descarga todas sus imágenes
     - Muestra progreso en consola
4. Al finalizar, muestra un resumen con estadísticas

## 🔄 Flujo de Ejecución Completo

```
1. Inicio
   ↓
2. Crear directorio base (yupoo_downloads/Trapstar系列/)
   ↓
3. Para cada página (2, 3, 4):
   ├─ 3.1. Descargar HTML de la página
   ├─ 3.2. Parsear HTML con BeautifulSoup
   ├─ 3.3. Extraer productos (extract_products_from_page)
   │   └─ Para cada producto encontrado:
   │       ├─ 3.3.1. Crear carpeta del producto
   │       ├─ 3.3.2. Descargar HTML del producto
   │       ├─ 3.3.3. Extraer URLs de imágenes
   │       └─ 3.3.4. Descargar cada imagen
   │           ├─ Intentar con /original.jpeg
   │           └─ Si falla, intentar con /medium.jpeg
   └─ 3.4. Esperar DELAY_BETWEEN_REQUESTS
   ↓
4. Mostrar resumen final
```

## 🛡️ Manejo de Errores

El script implementa múltiples capas de manejo de errores:

1. **Reintentos a nivel de producto**: Si falla la descarga de un producto, reintenta hasta 3 veces
2. **Reintentos a nivel de imagen**: Cada imagen tiene hasta 3 intentos
3. **URLs alternativas**: Si falla `/original.jpeg`, intenta `/medium.jpeg`
4. **Verificación de duplicados**: Evita descargar la misma imagen dos veces
5. **Continuación ante errores**: Si un producto falla, continúa con el siguiente
6. **Logging detallado**: Muestra qué productos/imágenes fallaron

## 📊 Estadísticas y Logging

El script proporciona información detallada durante la ejecución:

- **Por página**: Muestra cuántos productos se encontraron
- **Por producto**: Muestra el nombre, URL, y cuántas imágenes se descargaron
- **Resumen final**: Total de productos procesados, exitosos, fallidos, e imágenes descargadas

## 🔍 Detalles Técnicos Importantes

### Extracción de Nombres de Productos

**Problema resuelto**: El texto del enlace HTML suele ser solo el número de fotos (ej: "25"), no el nombre del producto. El script resuelve esto:

1. Busca el contenedor padre del enlace
2. Analiza todas las líneas de texto del contenedor
3. Identifica la línea que NO es solo un número y tiene más de 1 carácter
4. Esa línea es el nombre real del producto

**Ejemplo**:
- HTML muestra: `<a href="...">25</a>` dentro de un contenedor con texto `"25\n\n\n款号：8859"`
- El script extrae: `"款号：8859"` (el nombre real)

### URLs de Imágenes

Las imágenes en Yupoo usan un sistema de hashes:
- URL de thumbnail: `https://photo.yupoo.com/yitian333/{hash}/small.jpeg`
- URL de tamaño medio: `https://photo.yupoo.com/yitian333/{hash}/medium.jpeg`
- URL original: `https://photo.yupoo.com/yitian333/{hash}/original.jpeg`

El script siempre intenta descargar la versión original primero.

### Filtrado de Duplicados

El script evita duplicados en múltiples niveles:
1. **Por ID de álbum**: Usa el ID numérico único de cada álbum
2. **Por URL completa**: Verifica que la URL no se haya procesado antes
3. **Por nombre de archivo**: No descarga la misma imagen dos veces en el mismo producto

## 📦 Dependencias

El script requiere las siguientes librerías Python:

- `requests`: Para hacer peticiones HTTP
- `beautifulsoup4`: Para parsear HTML
- `pathlib`: Para manejo de rutas (incluido en Python 3.4+)

Instalación:
```bash
pip install requests beautifulsoup4
```

## 🚀 Uso

### Ejecución básica:
```bash
python3 download_yupoo_category.py
```

### Ejecución en segundo plano con logging:
```bash
python3 -u download_yupoo_category.py 2>&1 | tee yupoo_download.log &
```

### Ver progreso en tiempo real:
```bash
tail -f yupoo_download.log
```

## ⚠️ Consideraciones

1. **Respeto a los servidores**: El script incluye delays entre peticiones para no sobrecargar el servidor
2. **Tiempo de ejecución**: Puede tardar varias horas dependiendo de la cantidad de productos e imágenes
3. **Espacio en disco**: Asegúrate de tener suficiente espacio antes de ejecutar
4. **Nombres de archivos**: Los nombres se mantienen originales, incluyendo caracteres especiales chinos
5. **Productos duplicados**: El script detecta productos con el mismo nombre pero diferentes IDs y los descarga por separado

## 🔧 Personalización

Para usar el script con otra categoría o rango de páginas, modifica las constantes al inicio:

```python
BASE_URL = "https://yitian333.x.yupoo.com/categories/OTRO_ID"
START_PAGE = 1
END_PAGE = 10
```

## 📝 Notas para IA

Si una IA necesita entender o modificar este script, debe considerar:

1. **Estructura HTML de Yupoo**: El script está específicamente diseñado para la estructura HTML de `yitian333.x.yupoo.com`. Cambios en el HTML del sitio pueden requerir ajustes.

2. **Extracción de nombres**: La lógica de extracción de nombres de productos es crítica y específica para este sitio. El patrón es: número de fotos en el enlace, nombre real en el contenedor.

3. **Sistema de hashes**: Las imágenes usan hashes hexadecimales en las URLs. El script extrae estos hashes y construye URLs de alta resolución.

4. **Manejo de caracteres especiales**: El script preserva caracteres chinos y especiales en nombres de archivos, solo sanitiza caracteres problemáticos del sistema de archivos.

5. **Robustez**: El script está diseñado para ser robusto ante errores de red, cambios temporales en el sitio, y productos con estructuras ligeramente diferentes.
