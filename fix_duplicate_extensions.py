#!/usr/bin/env python3
"""
Script para corregir duplicados de extensiones .jpg/.jpeg
Verifica la extensión original en línea y elimina la versión incorrecta
"""

import requests
from pathlib import Path
from collections import defaultdict
import time
import sys

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://yitian333.x.yupoo.com/',
}

def get_real_extension_from_url(image_id):
    """
    Intenta determinar la extensión correcta desde Yupoo
    Prueba ambas URLs (large.jpg y large.jpeg) y verifica cuál existe
    """
    base_url = f"https://photo.yupoo.com/yitian333/{image_id}/large"
    
    # Primero intentar con .jpeg (más común en Yupoo)
    for ext in ['.jpeg', '.jpg']:
        url = base_url + ext
        try:
            response = requests.head(url, headers=HEADERS, timeout=5, allow_redirects=True)
            if response.status_code == 200:
                # Verificar el Content-Type para confirmar
                content_type = response.headers.get('Content-Type', '').lower()
                if 'image' in content_type:
                    return ext
        except Exception:
            continue
    
    # Si no se puede determinar, usar .jpeg como predeterminado (más común)
    return '.jpeg'

def find_duplicates(base_dir):
    """Encuentra todos los pares de duplicados .jpg/.jpeg"""
    duplicates = defaultdict(list)
    
    for img_file in base_dir.rglob("*"):
        if img_file.is_file() and img_file.suffix.lower() in ['.jpg', '.jpeg']:
            base_name = img_file.stem
            parent = img_file.parent
            key = (parent, base_name)
            duplicates[key].append(img_file)
    
    # Filtrar solo los que tienen duplicados
    return {k: v for k, v in duplicates.items() if len(v) > 1}

def fix_duplicates(base_dir, dry_run=False):
    """
    Corrige los duplicados eliminando la versión con extensión incorrecta
    """
    print("="*70)
    print("Corrector de Extensiones Duplicadas")
    print("="*70)
    print(f"Directorio: {base_dir}")
    print(f"Modo: {'DRY RUN (simulación)' if dry_run else 'REAL (eliminará archivos)'}")
    print("="*70)
    print()
    sys.stdout.flush()
    
    print("🔍 Buscando duplicados...")
    sys.stdout.flush()
    duplicates = find_duplicates(base_dir)
    
    if not duplicates:
        print("✓ No se encontraron duplicados")
        return
    
    print(f"✓ Encontrados {len(duplicates)} pares de duplicados")
    print()
    sys.stdout.flush()
    
    deleted_count = 0
    kept_count = 0
    errors = []
    
    # Agrupar por ID para hacer menos peticiones
    unique_ids = set()
    for (parent, base_name), files in duplicates.items():
        unique_ids.add(base_name)
    
    print(f"IDs únicos a verificar: {len(unique_ids)}")
    print("Verificando extensiones originales en línea...")
    print()
    
    # Crear un mapa de ID -> extensión correcta
    extension_map = {}
    batch_size = 50
    ids_list = list(unique_ids)
    total_batches = (len(ids_list) - 1) // batch_size + 1
    
    print("📡 Verificando extensiones originales en línea...")
    print(f"   Total de IDs a verificar: {len(ids_list)}")
    print(f"   Procesando en {total_batches} lotes de {batch_size}...")
    print()
    sys.stdout.flush()
    
    for i in range(0, len(ids_list), batch_size):
        batch = ids_list[i:i+batch_size]
        batch_num = i // batch_size + 1
        print(f"  ⏳ Lote {batch_num}/{total_batches} ({i+1}-{min(i+batch_size, len(ids_list))} de {len(ids_list)})...", end=' ')
        sys.stdout.flush()
        
        for image_id in batch:
            correct_ext = get_real_extension_from_url(image_id)
            extension_map[image_id] = correct_ext
            time.sleep(0.05)  # Pequeña pausa para no saturar el servidor
        
        print("✓")
        sys.stdout.flush()
    
    print()
    print("🗑️  Procesando duplicados...")
    print()
    sys.stdout.flush()
    
    for idx, ((parent, base_name), files) in enumerate(duplicates.items(), 1):
        if idx % 50 == 0:
            print(f"  ⏳ Procesados {idx}/{len(duplicates)} pares... ({idx*100//len(duplicates)}%)")
            sys.stdout.flush()
        
        # Obtener la extensión correcta
        correct_ext = extension_map.get(base_name, '.jpeg')
        
        # Separar archivos por extensión
        files_by_ext = {f.suffix.lower(): f for f in files}
        
        # Determinar qué archivo mantener y cuál eliminar
        if correct_ext in files_by_ext:
            # Mantener el archivo con la extensión correcta
            wrong_ext = '.jpg' if correct_ext == '.jpeg' else '.jpeg'
            delete_file = files_by_ext.get(wrong_ext)
        else:
            # Si no está la correcta, mantener la primera y eliminar la segunda
            delete_file = files[1] if len(files) > 1 else None
        
        if delete_file and delete_file.exists():
            try:
                if not dry_run:
                    delete_file.unlink()
                deleted_count += 1
            except Exception as e:
                errors.append((delete_file, str(e)))
        
        kept_count += 1
    
    print()
    print("="*70)
    print("📊 RESUMEN")
    print("="*70)
    print(f"Pares de duplicados procesados: {len(duplicates)}")
    print(f"Archivos mantenidos: {kept_count}")
    print(f"Archivos {'que se eliminarían' if dry_run else 'eliminados'}: {deleted_count}")
    
    if errors:
        print(f"\n⚠️  Errores encontrados: {len(errors)}")
        for file, error in errors[:10]:
            print(f"  - {file}: {error}")
    
    if dry_run:
        print("\n⚠️  ESTO FUE UNA SIMULACIÓN. Los archivos NO fueron eliminados.")
        print("   Ejecuta de nuevo sin --dry-run para eliminar realmente.")
    else:
        print("\n✅ Corrección completada.")
    
    print("="*70)
    
    # Calcular espacio liberado
    if deleted_count > 0:
        space_mb = deleted_count * 500 / 1024
        print(f"\n💾 Espacio {'que se liberaría' if dry_run else 'liberado'}: ~{space_mb:.1f} MB")
        print("   (estimación basada en ~500KB por imagen)")
    
    sys.stdout.flush()

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Corrige duplicados de extensiones .jpg/.jpeg verificando el origen"
    )
    parser.add_argument(
        '--dir',
        type=str,
        default='yupoo_downloads',
        help='Directorio base a procesar (default: yupoo_downloads)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Modo simulación: muestra qué se haría sin eliminar archivos'
    )
    
    args = parser.parse_args()
    
    base_dir = Path(args.dir)
    
    if not base_dir.exists():
        print(f"❌ Error: El directorio {base_dir} no existe")
        sys.exit(1)
    
    # Confirmar si no es dry-run
    if not args.dry_run:
        print("⚠️  ADVERTENCIA: Este script ELIMINARÁ archivos duplicados.")
        print("   Se recomienda hacer una copia de seguridad primero.")
        print()
        response = input("¿Continuar? (escribe 'SI' para confirmar): ")
        if response != 'SI':
            print("Operación cancelada.")
            sys.exit(0)
        print()
    
    fix_duplicates(base_dir, dry_run=args.dry_run)

if __name__ == "__main__":
    main()
