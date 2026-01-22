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
    Solo procesa imágenes nuevas y elimina las descartadas.
    
    Body esperado:
    {
        "products": [
            {
                "collection": "Trapstar系列",
                "page": "3",
                "name": "款号：1006",
                "title": "Camiseta Básica",
                "color": "Rojo",
                "productImage": "09591a65.jpg",
                "galleryImages": ["0c2a2ee3.jpg", ...],
                "hasChanges": true,
                "imagesToAdd": ["09591a65.jpg", ...],
                "imagesToRemove": ["old_image.jpg", ...]
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
            folder_name = product_data.get('folderName', product_name)
            product_image = product_data.get('productImage')
            gallery_images = product_data.get('galleryImages', [])
            has_changes = product_data.get('hasChanges', False)
            images_to_add = product_data.get('imagesToAdd', [])
            images_to_remove = product_data.get('imagesToRemove', [])
            
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
            
            # Si hay cambios, procesar
            if has_changes:
                # Eliminar imágenes descartadas
                for image_to_remove in images_to_remove:
                    if image_to_remove and image_to_remove.strip():
                        try:
                            output_path = output_base / image_to_remove
                            if output_path.exists():
                                output_path.unlink()
                                logger.info(f"Imagen eliminada: {output_path}")
                        except Exception as e:
                            logger.error(f"Error al eliminar imagen {image_to_remove}: {str(e)}")
                
                # Procesar solo imágenes nuevas
                for image_to_add in images_to_add:
                    if not image_to_add or not image_to_add.strip():
                        continue
                    try:
                        input_path = input_base / image_to_add
                        output_path = output_base / image_to_add
                        
                        if input_path.exists():
                            if apply_watermark(str(input_path), str(output_path)):
                                logger.info(f"Marca de agua aplicada a: {output_path}")
                            else:
                                logger.warning(f"No se pudo aplicar marca de agua a {input_path}")
                        else:
                            logger.warning(f"Imagen no encontrada: {input_path}")
                    except Exception as e:
                        logger.error(f"Error al procesar imagen {image_to_add}: {str(e)}")
            
            # Construir las rutas finales para el frontend
            if product_image and product_image.strip():
                processed_product["productImage"] = f"imagenes_marca_agua/{collection}/{page}/{folder_name}/{product_image}"
            
            for gallery_image in gallery_images:
                if gallery_image and gallery_image.strip():
                    processed_product["galleryImages"].append(
                        f"imagenes_marca_agua/{collection}/{page}/{folder_name}/{gallery_image}"
                    )
            
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


@app.route('/api/delete-product-folder', methods=['POST'])
def api_delete_product_folder():
    """
    Elimina la carpeta de un producto en imagenes_marca_agua/.
    
    Body esperado:
    {
        "collection": "Trapstar系列",
        "page": "3",
        "folderName": "款号：1006"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "Formato de datos inválido"}), 400
        
        collection = data.get('collection')
        page = data.get('page')
        folder_name = data.get('folderName')
        
        if not collection or not page or not folder_name:
            return jsonify({"success": False, "error": "Faltan parámetros requeridos"}), 400
        
        # Construir la ruta de la carpeta a eliminar
        import shutil
        folder_path = PROJECT_ROOT / "imagenes_marca_agua" / collection / page / folder_name
        
        if folder_path.exists() and folder_path.is_dir():
            try:
                shutil.rmtree(folder_path)
                logger.info(f"Carpeta eliminada: {folder_path}")
                return jsonify({"success": True, "message": "Carpeta eliminada correctamente"}), 200
            except Exception as e:
                logger.error(f"Error al eliminar carpeta {folder_path}: {str(e)}")
                return jsonify({"success": False, "error": f"Error al eliminar carpeta: {str(e)}"}), 500
        else:
            # No existe la carpeta, pero retornamos éxito igualmente
            logger.info(f"Carpeta no existe (probablemente nunca fue procesada): {folder_path}")
            return jsonify({"success": True, "message": "Carpeta no existe"}), 200
            
    except Exception as e:
        logger.error(f"Error al eliminar carpeta de producto: {str(e)}")
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
