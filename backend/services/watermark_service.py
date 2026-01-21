"""
Servicio para aplicar marca de agua a imágenes usando ffmpeg.
"""
import subprocess
import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def apply_watermark(input_image_path: str, output_image_path: str) -> bool:
    """
    Aplica marca de agua a una imagen usando ffmpeg.
    
    Args:
        input_image_path: Ruta completa de la imagen de entrada
        output_image_path: Ruta completa de la imagen de salida con marca de agua
        
    Returns:
        bool: True si se aplicó correctamente, False en caso contrario
    """
    # Validar que el archivo de entrada exista
    if not os.path.exists(input_image_path):
        logger.error(f"Archivo de entrada no existe: {input_image_path}")
        return False
    
    # Crear directorio de salida si no existe
    output_dir = Path(output_image_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Verificar que ffmpeg esté disponible
    try:
        subprocess.run(['ffmpeg', '-version'], 
                      capture_output=True, 
                      check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.error("ffmpeg no está instalado o no está en el PATH")
        return False
    
    # Construir comando ffmpeg
    # Usar variables dinámicas para input y output
    font_path = "/usr/share/fonts/truetype/msttcorefonts/Verdana_Bold.ttf"
    
    # Verificar que la fuente exista, si no, usar fuente del sistema
    if not os.path.exists(font_path):
        logger.warning(f"Fuente no encontrada en {font_path}, usando fuente del sistema")
        font_path = "Verdana-Bold"
    
    cmd = [
        'ffmpeg',
        '-i', input_image_path,
        '-vf', (
            f"drawtext=text='VALENCIADRIP.COM':"
            f"fontfile={font_path}:"
            f"fontsize=30:"
            f"fontcolor=white@0.4:"
            f"shadowcolor=gray@0.9:"
            f"shadowx=1:"
            f"shadowy=1:"
            f"x=(w-text_w)/2:"
            f"y=(h-text_h)/2"
        ),
        '-frames:v', '1',
        '-q:v', '2',
        output_image_path
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        logger.info(f"Marca de agua aplicada exitosamente: {output_image_path}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error al ejecutar ffmpeg: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"Error inesperado al aplicar marca de agua: {str(e)}")
        return False
