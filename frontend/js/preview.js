/**
 * Lógica de la página de preview.
 */

/**
 * Carga y renderiza el preview de productos en formato tabla.
 */
function loadPreview() {
    const previewTbody = document.getElementById('preview-tbody');
    
    // Obtener datos desde sessionStorage
    const previewDataStr = sessionStorage.getItem('previewData');
    if (!previewDataStr) {
        previewTbody.innerHTML = '<tr><td colspan="4">No hay datos de preview disponibles.</td></tr>';
        return;
    }
    
    const previewData = JSON.parse(previewDataStr);
    
    if (previewData.length === 0) {
        previewTbody.innerHTML = '<tr><td colspan="4">No hay productos para mostrar.</td></tr>';
        return;
    }
    
    // Limpiar tabla
    previewTbody.innerHTML = '';
    
    // Renderizar cada producto como fila de tabla
    previewData.forEach((product, index) => {
        const tr = document.createElement('tr');
        
        // Agregar clase para filas alternadas
        if (index % 2 === 0) {
            tr.classList.add('row-even');
        } else {
            tr.classList.add('row-odd');
        }
        
        // Columna Item
        const tdItem = document.createElement('td');
        tdItem.textContent = index + 1;
        tr.appendChild(tdItem);
        
        // Columna Título - Color
        const tdTitle = document.createElement('td');
        tdTitle.textContent = `${product.title} - ${product.color}`;
        tr.appendChild(tdTitle);
        
        // Columna Imagen de Producto
        const tdProductImage = document.createElement('td');
        tdProductImage.className = 'preview-images-cell';
        if (product.productImage) {
            const img = document.createElement('img');
            img.src = `/${product.productImage}`;
            img.alt = 'Imagen de producto';
            img.className = 'preview-thumbnail';
            img.addEventListener('click', () => openImageModal(img.src));
            tdProductImage.appendChild(img);
        } else {
            tdProductImage.textContent = '-';
        }
        tr.appendChild(tdProductImage);
        
        // Columna Galería de Productos
        const tdGallery = document.createElement('td');
        tdGallery.className = 'preview-images-cell';
        if (product.galleryImages && product.galleryImages.length > 0) {
            const galleryContainer = document.createElement('div');
            galleryContainer.className = 'preview-gallery-mini';
            product.galleryImages.forEach(imagePath => {
                const img = document.createElement('img');
                img.src = `/${imagePath}`;
                img.alt = 'Imagen de galería';
                img.className = 'preview-thumbnail';
                img.addEventListener('click', () => openImageModal(img.src));
                galleryContainer.appendChild(img);
            });
            tdGallery.appendChild(galleryContainer);
        } else {
            tdGallery.textContent = '-';
        }
        tr.appendChild(tdGallery);
        
        previewTbody.appendChild(tr);
    });
}

/**
 * Abre el modal con la imagen ampliada (reutilizar función de main.js si es posible).
 */
function openImageModal(imageSrc) {
    // Crear modal si no existe
    let modal = document.getElementById('image-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'image-modal';
        modal.className = 'image-modal';
        modal.style.display = 'none';
        
        const closeBtn = document.createElement('span');
        closeBtn.className = 'image-modal-close';
        closeBtn.innerHTML = '&times;';
        closeBtn.addEventListener('click', () => closeImageModal());
        
        const img = document.createElement('img');
        img.id = 'modal-image';
        img.className = 'modal-image-content';
        
        modal.appendChild(closeBtn);
        modal.appendChild(img);
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                closeImageModal();
            }
        });
        
        document.body.appendChild(modal);
    }
    
    const modalImg = document.getElementById('modal-image');
    modalImg.src = imageSrc;
    modal.style.display = 'block';
}

/**
 * Cierra el modal de imagen.
 */
function closeImageModal() {
    const modal = document.getElementById('image-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}

/**
 * Maneja el clic en el botón Procesar.
 */
async function handleProcess() {
    try {
        const response = await fetch('/api/process', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ processed: true })
        });
        
        const data = await response.json();
        if (data.success) {
            // Mostrar modal con mensaje
            showModal('Lote de 25 imágenes procesado');
            
            // Después de 2 segundos, navegar a la siguiente página
            setTimeout(() => {
                // Calcular siguiente página desde sessionStorage
                const savedPage = parseInt(sessionStorage.getItem('currentPage')) || 1;
                const totalPages = Math.ceil(parseInt(sessionStorage.getItem('totalProducts') || 0) / 25);
                const nextPage = savedPage < totalPages ? savedPage + 1 : savedPage;
                
                // Limpiar datos de preview
                sessionStorage.removeItem('previewData');
                
                // Navegar de vuelta a index.html con parámetro de página
                window.location.href = `/?page=${nextPage}`;
            }, 2000);
        } else {
            alert('Error al procesar: ' + (data.error || 'Error desconocido'));
        }
    } catch (error) {
        console.error('Error al procesar:', error);
        alert('Error al procesar. Por favor, intenta de nuevo.');
    }
}

/**
 * Muestra un modal con un mensaje.
 */
function showModal(message) {
    const modal = document.getElementById('modal');
    const modalMessage = document.getElementById('modal-message');
    modalMessage.textContent = message;
    modal.style.display = 'block';
    
    // Cerrar modal al hacer clic en X
    const closeBtn = document.querySelector('.close');
    closeBtn.onclick = () => {
        modal.style.display = 'none';
    };
    
    // Cerrar modal al hacer clic fuera
    window.onclick = (event) => {
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    };
}

// Event listeners
document.addEventListener('DOMContentLoaded', () => {
    loadPreview();
    
    document.getElementById('process-btn').addEventListener('click', handleProcess);
});
