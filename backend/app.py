"""
Aplicación Flask principal para el registro de productos Yupoo.
"""
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from pathlib import Path
import logging
import os

from services.csv_service import load_titles
from services.image_service import get_collections, get_products
from services.watermark_service import apply_watermark

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Permitir CORS para el frontend

# Obtener la ruta del proyecto
PROJECT_ROOT = Path(__file__).parent.parent


@app.route('/')
def index():
    """Redirigir a la página principal del frontend."""
    return send_from_directory(str(PROJECT_ROOT / 'frontend'), 'index.html')


@app.route('/preview.html')
def preview():
    """Servir la página de preview."""
    return send_from_directory(str(PROJECT_ROOT / 'frontend'), 'preview.html')


@app.route('/api/titles', methods=['GET'])
def api_titles():
    """Retorna lista de títulos desde CSV."""
    try:
        titles = load_titles()
        return jsonify({"success": True, "titles": titles}), 200
    except Exception as e:
        logger.error(f"Error al cargar títulos: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/collections', methods=['GET'])
def api_collections():
    """Retorna lista de colecciones disponibles."""
    try:
        collections = get_collections()
        return jsonify({"success": True, "collections": collections}), 200
    except Exception as e:
        logger.error(f"Error al obtener colecciones: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/products', methods=['GET'])
def api_products():
    """Retorna todos los productos de una colección."""
    collection_name = request.args.get('collection')
    
    if not collection_name:
        return jsonify({"success": False, "error": "Parámetro 'collection' requerido"}), 400
    
    try:
        products = get_products(collection_name)
        return jsonify({"success": True, "products": products}), 200
    except Exception as e:
        logger.error(f"Error al obtener productos: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/preview', methods=['POST'])
def api_preview():
    """
    Procesa 25 productos y aplica marca de agua a las imágenes seleccionadas.
    
    Body esperado:
    {
        "products": [
            {
                "collection": "Trapstar系列",
                "page": "3",
                "name": "款号：1006",
                "title": "Camiseta Básica",
                "color": "Rojo",
                "productImage": "09591a65.jpg",  // imagen con checkbox P
                "galleryImages": ["0c2a2ee3.jpg", ...]  // imágenes con checkbox G
            },
            ...
        ]
    }
    """
    try:
        data = request.get_json()
        if not data or 'products' not in data:
            return jsonify({"success": False, "error": "Formato de datos inválido"}), 400
        
        products = data['products']
        processed_products = []
        
        for product_data in products:
            collection = product_data.get('collection')
            page = product_data.get('page')
            product_name = product_data.get('name')
            folder_name = product_data.get('folderName', product_name)  # Usar folderName si existe (para duplicados)
            product_image = product_data.get('productImage')  # Imagen con checkbox P
            gallery_images = product_data.get('galleryImages', [])  # Imágenes con checkbox G
            
            # Validar que los campos requeridos no sean None
            if not collection or not page or not product_name:
                logger.error(f"Campos faltantes en producto: collection={collection}, page={page}, name={product_name}")
                continue
            
            # Construir rutas base
            try:
                input_base = PROJECT_ROOT / "yupoo_downloads" / collection / page / product_name
                output_base = PROJECT_ROOT / "imagenes_marca_agua" / collection / page / folder_name
            except (TypeError, AttributeError) as e:
                logger.error(f"Error al construir rutas para producto {product_name}: {str(e)}")
                continue
            
            processed_product = {
                "collection": collection,
                "page": page,
                "name": product_name,
                "title": product_data.get('title'),
                "color": product_data.get('color'),
                "productImage": None,
                "galleryImages": []
            }
            
            # Procesar imagen de producto (P)
            if product_image and product_image.strip():  # Verificar que no sea None ni vacío
                try:
                    input_path = input_base / product_image
                    output_path = output_base / product_image
                    
                    if input_path.exists():
                        if apply_watermark(str(input_path), str(output_path)):
                            # Ruta relativa para el frontend usando folder_name
                            processed_product["productImage"] = f"imagenes_marca_agua/{collection}/{page}/{folder_name}/{product_image}"
                        else:
                            logger.warning(f"No se pudo aplicar marca de agua a {input_path}")
                    else:
                        logger.warning(f"Imagen no encontrada: {input_path}")
                except Exception as e:
                    logger.error(f"Error al procesar imagen de producto {product_image}: {str(e)}")
            
            # Procesar imágenes de galería (G)
            for gallery_image in gallery_images:
                if not gallery_image or not gallery_image.strip():  # Validar que no sea None ni vacío
                    continue
                try:
                    input_path = input_base / gallery_image
                    output_path = output_base / gallery_image
                    
                    if input_path.exists():
                        if apply_watermark(str(input_path), str(output_path)):
                            processed_product["galleryImages"].append(
                                f"imagenes_marca_agua/{collection}/{page}/{folder_name}/{gallery_image}"
                            )
                        else:
                            logger.warning(f"No se pudo aplicar marca de agua a {input_path}")
                    else:
                        logger.warning(f"Imagen no encontrada: {input_path}")
                except Exception as e:
                    logger.error(f"Error al procesar imagen de galería {gallery_image}: {str(e)}")
                    continue
            
            processed_products.append(processed_product)
        
        return jsonify({"success": True, "products": processed_products}), 200
        
    except Exception as e:
        logger.error(f"Error al procesar preview: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/process', methods=['POST'])
def api_process():
    """
    Endpoint para confirmar el procesamiento de un lote.
    Por ahora solo retorna éxito para mostrar el popup.
    """
    try:
        data = request.get_json()
        # Por ahora solo retornamos éxito
        return jsonify({"success": True, "message": "Lote procesado correctamente"}), 200
    except Exception as e:
        logger.error(f"Error al procesar: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


# Servir archivos estáticos del frontend
@app.route('/<path:filename>')
def serve_static(filename):
    """Servir archivos estáticos del frontend."""
    frontend_path = PROJECT_ROOT / 'frontend'
    file_path = frontend_path / filename
    
    # Verificar que el archivo esté dentro del directorio frontend por seguridad
    try:
        file_path.resolve().relative_to(frontend_path.resolve())
    except ValueError:
        return jsonify({"error": "Acceso denegado"}), 403
    
    if file_path.exists() and file_path.is_file():
        return send_from_directory(str(frontend_path), filename)
    
    return jsonify({"error": "Archivo no encontrado"}), 404


# Servir imágenes con marca de agua
@app.route('/imagenes_marca_agua/<path:filename>')
def serve_watermarked_images(filename):
    """Servir imágenes con marca de agua."""
    image_path = PROJECT_ROOT / 'imagenes_marca_agua' / filename
    
    # Verificar que el archivo esté dentro del directorio imagenes_marca_agua por seguridad
    try:
        image_path.resolve().relative_to((PROJECT_ROOT / 'imagenes_marca_agua').resolve())
    except ValueError:
        return jsonify({"error": "Acceso denegado"}), 403
    
    if image_path.exists() and image_path.is_file():
        return send_from_directory(str(PROJECT_ROOT / 'imagenes_marca_agua'), filename)
    
    return jsonify({"error": "Imagen no encontrada"}), 404


# Servir imágenes originales de yupoo_downloads
@app.route('/yupoo_downloads/<path:filename>')
def serve_original_images(filename):
    """Servir imágenes originales de yupoo_downloads."""
    from urllib.parse import unquote
    
    # Decodificar la ruta para manejar caracteres especiales y chinos
    decoded_filename = unquote(filename)
    
    # Construir la ruta del archivo
    image_path = PROJECT_ROOT / 'yupoo_downloads' / decoded_filename
    
    # Verificar que el archivo esté dentro del directorio yupoo_downloads por seguridad
    try:
        image_path.resolve().relative_to((PROJECT_ROOT / 'yupoo_downloads').resolve())
    except ValueError:
        return jsonify({"error": "Acceso denegado"}), 403
    
    if image_path.exists() and image_path.is_file():
        # Usar la ruta decodificada para servir el archivo
        directory = str(PROJECT_ROOT / 'yupoo_downloads')
        # Necesitamos reconstruir la ruta relativa desde el directorio base
        relative_path = image_path.relative_to(PROJECT_ROOT / 'yupoo_downloads')
        return send_from_directory(directory, str(relative_path))
    
    return jsonify({"error": "Imagen no encontrada"}), 404


if __name__ == '__main__':
    # Crear directorio de imágenes con marca de agua si no existe
    watermark_dir = PROJECT_ROOT / 'imagenes_marca_agua'
    watermark_dir.mkdir(exist_ok=True)
    
    logger.info("Iniciando servidor Flask...")
    logger.info(f"Directorio del proyecto: {PROJECT_ROOT}")
    app.run(debug=True, host='0.0.0.0', port=5000)
