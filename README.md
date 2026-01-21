# Aplicación de Registro de Productos Yupoo

Aplicación full-stack para registrar, organizar y previsualizar productos con marca de agua desde imágenes descargadas de Yupoo.

## Estructura del Proyecto

```
LoadingProductsWordpress/
├── input.csv                    # Archivo CSV con títulos (id, titulo)
├── backend/
│   ├── app.py                   # Servidor Flask principal
│   ├── services/
│   │   ├── csv_service.py       # Lectura de CSV
│   │   ├── image_service.py     # Escaneo de carpetas de imágenes
│   │   └── watermark_service.py  # Aplicación de marca de agua con ffmpeg
│   └── requirements.txt         # Dependencias del backend
├── frontend/
│   ├── index.html               # Página principal
│   ├── preview.html             # Página de preview
│   ├── css/
│   │   └── styles.css           # Estilos de la aplicación
│   └── js/
│       ├── main.js              # Lógica principal
│       ├── storage.js           # Gestión de LocalStorage
│       └── preview.js           # Lógica de preview
├── yupoo_downloads/             # Imágenes originales (estructura: coleccion/pagina/producto/)
├── imagenes_marca_agua/         # Imágenes con marca de agua (se crea automáticamente)
└── requirements.txt             # Dependencias generales del proyecto
```

## Requisitos Previos

1. **Python 3.8+** instalado
2. **ffmpeg** instalado en el sistema
   - Ubuntu/Debian: `sudo apt install ffmpeg`
   - macOS: `brew install ffmpeg`
   - Windows: Descargar desde https://ffmpeg.org/

3. **Estructura de imágenes**:
   - Las imágenes deben estar en `yupoo_downloads/coleccion/pagina/producto/`
   - Esta estructura se genera automáticamente por `download_yupoo_category.py`

## Instalación

1. **Activar el entorno virtual** (si ya existe):
```bash
source venv/bin/activate
```

2. **Instalar dependencias**:
```bash
# Instalar dependencias generales
pip install -r requirements.txt

# Instalar dependencias del backend
pip install -r backend/requirements.txt
```

## Configuración

1. **Archivo input.csv**:
   - Debe estar en la raíz del proyecto
   - Formato: `id,titulo`
   - Ejemplo:
   ```csv
   id,titulo
   1,Camiseta Básica
   2,Pantalón Deportivo
   3,Chaqueta Trapstar
   ```

2. **Fuente para marca de agua**:
   - Por defecto busca: `/usr/share/fonts/truetype/msttcorefonts/Verdana_Bold.ttf`
   - Si no existe, usa la fuente del sistema
   - Para instalar la fuente en Ubuntu/Debian:
     ```bash
     sudo apt install ttf-mscorefonts-installer
     ```

## Ejecución

1. **Iniciar el servidor Flask**:
```bash
cd backend
python app.py
```

2. **Abrir en el navegador**:
   - Navegar a: `http://localhost:5000/`
   - La aplicación se cargará automáticamente

## Uso de la Aplicación

### 1. Selección de Colección
- Si hay múltiples colecciones, aparecerá un dropdown para seleccionar
- Si hay una sola colección, se carga automáticamente

### 2. Registro de Productos
- **Item**: Numeración automática (1, 2, 3...)
- **Título**: Seleccionar desde el dropdown (cargado desde `input.csv`)
- **Color**: Seleccionar color predefinido
- **Imágenes**: 
  - Se muestran como miniaturas
  - Marcar checkbox **P** para Imagen de Producto (solo 1 por fila)
  - Marcar checkbox **G** para Imágenes de Galería (múltiples permitidas)
- **Acciones**:
  - **Duplicar**: Crea una nueva fila vacía debajo
  - **Borrar**: Elimina la fila

### 3. Paginación
- Se muestran 25 productos por página
- Usar controles de paginación para navegar

### 4. Preview
- Al hacer clic en "Preview":
  - Se procesan las 25 imágenes seleccionadas
  - Se aplica marca de agua con ffmpeg
  - Se muestra la página de preview con todas las imágenes
- El formato de título es: `{Título} - {Color}`

### 5. Procesar
- Al hacer clic en "Procesar":
  - Muestra popup: "Lote de 25 imágenes procesado"
  - Regresa a la siguiente página de registro

## Características

- ✅ Carga automática de títulos desde CSV
- ✅ Detección automática de colecciones
- ✅ Paginación (25 productos por página)
- ✅ Duplicación y eliminación de filas
- ✅ Validación: solo 1 checkbox P por fila
- ✅ Persistencia en LocalStorage (sobrevive recargas)
- ✅ Aplicación de marca de agua con ffmpeg
- ✅ Preview de imágenes procesadas
- ✅ Diseño responsive y moderno

## API Endpoints

- `GET /api/titles` - Obtener lista de títulos desde CSV
- `GET /api/collections` - Obtener lista de colecciones
- `GET /api/products?collection={name}` - Obtener productos de una colección
- `POST /api/preview` - Procesar imágenes con marca de agua
- `POST /api/process` - Confirmar procesamiento de lote

## Estructura de Datos

### Producto
```json
{
  "collection": "Trapstar系列",
  "page": "3",
  "name": "款号：1006",
  "images": ["09591a65.jpg", "0c2a2ee3.jpg"],
  "image_paths": ["yupoo_downloads/Trapstar系列/3/款号：1006/09591a65.jpg"]
}
```

### Estado de Producto (LocalStorage)
```json
{
  "title": "1",
  "color": "Rojo",
  "checkboxesP": [0],
  "checkboxesG": [1, 2]
}
```

## Solución de Problemas

### Error: "ffmpeg no está instalado"
- Instalar ffmpeg según tu sistema operativo (ver Requisitos Previos)

### Error: "No se encontró el archivo input.csv"
- Asegúrate de que `input.csv` esté en la raíz del proyecto
- Verifica el formato del CSV (id,titulo)

### Las imágenes no se cargan
- Verifica que la estructura de carpetas sea correcta: `yupoo_downloads/coleccion/pagina/producto/`
- Verifica permisos de lectura en las carpetas

### La marca de agua no se aplica
- Verifica que ffmpeg esté instalado: `ffmpeg -version`
- Revisa los logs del servidor Flask para ver errores específicos
- Verifica que la fuente exista o que el sistema tenga una fuente alternativa

## Notas Técnicas

- **Orden de productos**: Se ordenan por fecha de modificación (más antigua primero)
- **Orden de imágenes**: Dentro de cada producto, se ordenan por mtime ascendente
- **Caracteres especiales**: Se manejan correctamente nombres con caracteres chinos
- **Rutas**: El backend usa rutas absolutas desde la raíz del proyecto
- **CORS**: Configurado para permitir requests desde el frontend
- **Servidor estático**: Flask sirve archivos estáticos y las imágenes procesadas

## Desarrollo

Para desarrollo, el servidor Flask se ejecuta en modo debug:
- Cambios en código se recargan automáticamente
- Errores se muestran en el navegador
- Logs detallados en la consola

## Licencia

Este proyecto es de uso interno.
