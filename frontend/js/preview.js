/**
 * Lógica de la página de preview.
 */

/**
 * Carga y renderiza el preview de productos.
 */
function loadPreview() {
    const previewContent = document.getElementById('preview-content');
    
    // Obtener datos desde sessionStorage
    const previewDataStr = sessionStorage.getItem('previewData');
    if (!previewDataStr) {
        previewContent.innerHTML = '<p>No hay datos de preview disponibles.</p>';
        return;
    }
    
    const previewData = JSON.parse(previewDataStr);
    
    if (previewData.length === 0) {
        previewContent.innerHTML = '<p>No hay productos para mostrar.</p>';
        return;
    }
    
    // Renderizar cada producto
    previewContent.innerHTML = '';
    
    previewData.forEach((product, index) => {
        const productCard = document.createElement('div');
        productCard.className = 'preview-product-card';
        
        // Título combinado
        const title = document.createElement('h2');
        title.className = 'preview-product-title';
        title.textContent = `${product.title} - ${product.color}`;
        productCard.appendChild(title);
        
        // Imagen de producto (P)
        if (product.productImage) {
            const productImageDiv = document.createElement('div');
            productImageDiv.className = 'preview-image-section';
            
            const label = document.createElement('p');
            label.className = 'image-label';
            label.textContent = 'Imagen de Producto:';
            productImageDiv.appendChild(label);
            
            const img = document.createElement('img');
            img.src = `/${product.productImage}`;
            img.alt = 'Imagen de producto';
            img.className = 'preview-image';
            productImageDiv.appendChild(img);
            
            productCard.appendChild(productImageDiv);
        }
        
        // Imágenes de galería (G)
        if (product.galleryImages && product.galleryImages.length > 0) {
            const galleryDiv = document.createElement('div');
            galleryDiv.className = 'preview-gallery-section';
            
            const label = document.createElement('p');
            label.className = 'image-label';
            label.textContent = 'Galería de Productos:';
            galleryDiv.appendChild(label);
            
            const galleryContainer = document.createElement('div');
            galleryContainer.className = 'preview-gallery-container';
            
            product.galleryImages.forEach(imagePath => {
                const img = document.createElement('img');
                img.src = `/${imagePath}`;
                img.alt = 'Imagen de galería';
                img.className = 'preview-image preview-gallery-image';
                galleryContainer.appendChild(img);
            });
            
            galleryDiv.appendChild(galleryContainer);
            productCard.appendChild(galleryDiv);
        }
        
        previewContent.appendChild(productCard);
    });
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
