/**
 * Lógica principal de la página de registro de productos.
 */

// Estado global
let allProducts = [];
let allTitles = [];
let allCollections = [];
let selectedCollection = null;
let currentPage = 1;
const PRODUCTS_PER_PAGE = 25;
let productStates = {}; // Estado de cada producto: {title, color, checkboxes}
let duplicateCounters = {}; // Contador de duplicados por producto original: {productKey: count}

// Colores predefinidos
const COLORS = [
    'Rojo', 'Azul', 'Verde', 'Negro', 'Blanco', 'Gris', 
    'Amarillo', 'Naranja', 'Rosa', 'Morado', 'Marrón', 'Beige'
];

/**
 * Inicializa la aplicación al cargar la página.
 */
async function init() {
    try {
        // 1. Cargar títulos desde API
        await loadTitles();
        
        // 2. Cargar colecciones desde API
        await loadCollections();
        
        // 3. Si hay múltiples colecciones, mostrar dropdown
        if (allCollections.length > 1) {
            setupCollectionSelector();
        } else if (allCollections.length === 1) {
            selectedCollection = allCollections[0];
            await loadProducts(selectedCollection);
        }
        
        // 4. Restaurar estado desde LocalStorage
        restoreState();
        
        // 4.5. Cargar contadores de duplicados
        loadDuplicateCounters();
        
        // 5. Obtener página desde URL o usar 1
        const urlParams = new URLSearchParams(window.location.search);
        const pageFromUrl = parseInt(urlParams.get('page')) || 1;
        
        // Guardar total de productos para cálculo de páginas
        if (allProducts.length > 0) {
            sessionStorage.setItem('totalProducts', allProducts.length.toString());
        }
        
        // 6. Renderizar página
        renderPage(pageFromUrl);
        
    } catch (error) {
        console.error('Error al inicializar:', error);
        alert('Error al cargar los datos. Por favor, recarga la página.');
    }
}

/**
 * Carga los títulos desde la API.
 */
async function loadTitles() {
    try {
        const response = await fetch('/api/titles');
        const data = await response.json();
        if (data.success) {
            allTitles = data.titles;
        } else {
            throw new Error(data.error || 'Error al cargar títulos');
        }
    } catch (error) {
        console.error('Error al cargar títulos:', error);
        throw error;
    }
}

/**
 * Carga las colecciones desde la API.
 */
async function loadCollections() {
    try {
        const response = await fetch('/api/collections');
        const data = await response.json();
        if (data.success) {
            allCollections = data.collections;
        } else {
            throw new Error(data.error || 'Error al cargar colecciones');
        }
    } catch (error) {
        console.error('Error al cargar colecciones:', error);
        throw error;
    }
}

/**
 * Configura el selector de colección.
 */
function setupCollectionSelector() {
    const selector = document.getElementById('collection-selector');
    const dropdown = document.getElementById('collection-dropdown');
    
    selector.style.display = 'block';
    
    // Limpiar opciones existentes
    dropdown.innerHTML = '<option value="">Seleccionar colección...</option>';
    
    // Añadir colecciones
    allCollections.forEach(collection => {
        const option = document.createElement('option');
        option.value = collection;
        option.textContent = collection;
        dropdown.appendChild(option);
    });
    
    // Restaurar selección guardada
    const savedCollection = loadSelectedCollection();
    if (savedCollection && allCollections.includes(savedCollection)) {
        dropdown.value = savedCollection;
        selectedCollection = savedCollection;
        loadProducts(selectedCollection);
    }
    
    // Event listener para cambio de colección
    dropdown.addEventListener('change', async (e) => {
        selectedCollection = e.target.value;
        if (selectedCollection) {
            saveSelectedCollection(selectedCollection);
            // Limpiar lista guardada al cambiar de colección
            localStorage.removeItem('yupoo_products_list');
            await loadProducts(selectedCollection);
            currentPage = 1;
            renderPage(1);
        }
    });
}

/**
 * Carga los productos de una colección.
 */
async function loadProducts(collectionName) {
    try {
        const response = await fetch(`/api/products?collection=${encodeURIComponent(collectionName)}`);
        const data = await response.json();
        if (data.success) {
            // Cargar productos base desde API
            const baseProducts = data.products;
            
            // Intentar restaurar lista con duplicados desde LocalStorage
            const savedProductsList = loadProductsList();
            if (savedProductsList && savedProductsList.length > 0) {
                // Verificar que la colección coincida
                if (savedProductsList[0] && savedProductsList[0].collection === collectionName) {
                    allProducts = savedProductsList;
                    console.log('Productos con duplicados restaurados desde LocalStorage');
                } else {
                    // Si la colección cambió, usar productos base
                    allProducts = baseProducts;
                    saveProductsList(allProducts);
                }
            } else {
                // Si no hay lista guardada, usar productos base
                allProducts = baseProducts;
                saveProductsList(allProducts);
            }
            
            // Guardar total de productos
            sessionStorage.setItem('totalProducts', allProducts.length.toString());
            // Restaurar estado guardado
            restoreState();
            // Obtener página desde URL o usar 1
            const urlParams = new URLSearchParams(window.location.search);
            const pageFromUrl = parseInt(urlParams.get('page')) || 1;
            renderPage(pageFromUrl);
        } else {
            throw new Error(data.error || 'Error al cargar productos');
        }
    } catch (error) {
        console.error('Error al cargar productos:', error);
        alert('Error al cargar los productos. Por favor, intenta de nuevo.');
    }
}

/**
 * Restaura el estado desde LocalStorage.
 */
function restoreState() {
    const savedState = loadState();
    if (savedState && savedState.products) {
        productStates = savedState.products;
    } else {
        productStates = {};
    }
}

/**
 * Renderiza una página específica de productos.
 */
function renderPage(pageNum) {
    if (!selectedCollection || allProducts.length === 0) {
        return;
    }
    
    currentPage = pageNum;
    const startIndex = (pageNum - 1) * PRODUCTS_PER_PAGE;
    const endIndex = Math.min(startIndex + PRODUCTS_PER_PAGE, allProducts.length);
    const pageProducts = allProducts.slice(startIndex, endIndex);
    
    const tbody = document.getElementById('products-tbody');
    tbody.innerHTML = '';
    
    pageProducts.forEach((product, index) => {
        const globalIndex = startIndex + index;
        const row = createProductRow(product, globalIndex);
        // Agregar clase para filas alternadas (zebra striping)
        if (index % 2 === 0) {
            row.classList.add('row-even');
        } else {
            row.classList.add('row-odd');
        }
        tbody.appendChild(row);
    });
    
    // Actualizar controles de paginación
    updatePagination();
    
    // Actualizar botón Preview y footer
    updatePreviewButton();
}

/**
 * Crea una fila de producto en la tabla.
 */
function createProductRow(product, globalIndex) {
    const tr = document.createElement('tr');
    tr.dataset.productIndex = globalIndex;
    
    // Columna Item
    const tdItem = document.createElement('td');
    tdItem.textContent = globalIndex + 1;
    tr.appendChild(tdItem);
    
    // Columna Título
    const tdTitle = document.createElement('td');
    const titleSelect = document.createElement('select');
    titleSelect.className = 'title-select';
    titleSelect.dataset.productIndex = globalIndex;
    titleSelect.innerHTML = '<option value="">Seleccionar título...</option>';
    allTitles.forEach(title => {
        const option = document.createElement('option');
        option.value = title.id;
        option.textContent = title.titulo;
        titleSelect.appendChild(option);
    });
    
    // Restaurar título guardado
    const savedState = productStates[globalIndex];
    if (savedState && savedState.title) {
        titleSelect.value = savedState.title;
    }
    
    titleSelect.addEventListener('change', (e) => {
        if (!productStates[globalIndex]) {
            productStates[globalIndex] = {};
        }
        productStates[globalIndex].title = e.target.value;
        saveProductState(globalIndex, productStates[globalIndex]);
        updatePreviewButton();
    });
    
    tdTitle.appendChild(titleSelect);
    tr.appendChild(tdTitle);
    
    // Columna Color
    const tdColor = document.createElement('td');
    const colorSelect = document.createElement('select');
    colorSelect.className = 'color-select';
    colorSelect.dataset.productIndex = globalIndex;
    colorSelect.innerHTML = '<option value="">Seleccionar color...</option>';
    COLORS.forEach(color => {
        const option = document.createElement('option');
        option.value = color;
        option.textContent = color;
        colorSelect.appendChild(option);
    });
    
    // Restaurar color guardado
    if (savedState && savedState.color) {
        colorSelect.value = savedState.color;
    }
    
    colorSelect.addEventListener('change', (e) => {
        if (!productStates[globalIndex]) {
            productStates[globalIndex] = {};
        }
        productStates[globalIndex].color = e.target.value;
        saveProductState(globalIndex, productStates[globalIndex]);
        updatePreviewButton();
    });
    
    tdColor.appendChild(colorSelect);
    tr.appendChild(tdColor);
    
    // Columna Imágenes
    const tdImages = document.createElement('td');
    tdImages.className = 'images-cell';
    
    const imagesContainer = document.createElement('div');
    imagesContainer.className = 'images-container';
    
    product.images.forEach((imageName, imageIndex) => {
        const imageWrapper = document.createElement('div');
        imageWrapper.className = 'image-wrapper';
        
        const img = document.createElement('img');
        // Construir la ruta codificando cada segmento correctamente
        // Flask maneja automáticamente la decodificación, pero necesitamos codificar cada parte
        const pathParts = [
            'yupoo_downloads',
            product.collection,
            product.page,
            product.name,
            imageName
        ];
        // Codificar cada parte y unir con /
        const encodedPath = pathParts.map(part => encodeURIComponent(part)).join('/');
        img.src = `/${encodedPath}`;
        img.alt = imageName;
        img.className = 'product-thumbnail';
        img.dataset.fullImage = img.src; // Guardar URL completa para el modal
        // Event listener para abrir modal al hacer click
        img.addEventListener('click', () => openImageModal(img.src));
        imageWrapper.appendChild(img);
        
        const checkboxesContainer = document.createElement('div');
        checkboxesContainer.className = 'checkboxes-container';
        
        // Checkbox P (Producto)
        const checkboxP = document.createElement('input');
        checkboxP.type = 'checkbox';
        checkboxP.id = `p-${globalIndex}-${imageIndex}`;
        checkboxP.className = 'checkbox-p';
        checkboxP.dataset.productIndex = globalIndex;
        checkboxP.dataset.imageIndex = imageIndex;
        
        // Restaurar estado del checkbox P
        if (savedState && savedState.checkboxesP && savedState.checkboxesP.includes(imageIndex)) {
            checkboxP.checked = true;
        }
        
        checkboxP.addEventListener('change', (e) => {
            if (e.target.checked) {
                // Si se marca P, desmarcar G de la misma imagen
                const checkboxG = document.getElementById(`g-${globalIndex}-${imageIndex}`);
                if (checkboxG && checkboxG.checked) {
                    checkboxG.checked = false;
                    handleCheckboxG(globalIndex, imageIndex, false);
                }
            }
            handleCheckboxP(globalIndex, imageIndex, e.target.checked);
        });
        
        const labelP = document.createElement('label');
        labelP.htmlFor = checkboxP.id;
        labelP.textContent = 'P';
        
        checkboxesContainer.appendChild(checkboxP);
        checkboxesContainer.appendChild(labelP);
        
        // Checkbox G (Galería)
        const checkboxG = document.createElement('input');
        checkboxG.type = 'checkbox';
        checkboxG.id = `g-${globalIndex}-${imageIndex}`;
        checkboxG.className = 'checkbox-g';
        checkboxG.dataset.productIndex = globalIndex;
        checkboxG.dataset.imageIndex = imageIndex;
        
        // Restaurar estado del checkbox G
        if (savedState && savedState.checkboxesG && savedState.checkboxesG.includes(imageIndex)) {
            checkboxG.checked = true;
        }
        
        checkboxG.addEventListener('change', (e) => {
            if (e.target.checked) {
                // Si se marca G, desmarcar P de la misma imagen
                const checkboxP = document.getElementById(`p-${globalIndex}-${imageIndex}`);
                if (checkboxP && checkboxP.checked) {
                    checkboxP.checked = false;
                    handleCheckboxP(globalIndex, imageIndex, false);
                }
            }
            handleCheckboxG(globalIndex, imageIndex, e.target.checked);
        });
        
        const labelG = document.createElement('label');
        labelG.htmlFor = checkboxG.id;
        labelG.textContent = 'G';
        
        checkboxesContainer.appendChild(checkboxG);
        checkboxesContainer.appendChild(labelG);
        
        imageWrapper.appendChild(checkboxesContainer);
        imagesContainer.appendChild(imageWrapper);
    });
    
    tdImages.appendChild(imagesContainer);
    tr.appendChild(tdImages);
    
    // Columna Acciones
    const tdActions = document.createElement('td');
    tdActions.className = 'actions-cell';
    
    const btnDuplicate = document.createElement('button');
    btnDuplicate.className = 'btn-duplicate';
    btnDuplicate.textContent = 'Duplicar';
    btnDuplicate.addEventListener('click', () => handleDuplicate(globalIndex));
    
    const btnDelete = document.createElement('button');
    btnDelete.className = 'btn-delete';
    btnDelete.textContent = 'Borrar';
    btnDelete.addEventListener('click', () => handleDelete(globalIndex));
    
    tdActions.appendChild(btnDuplicate);
    tdActions.appendChild(btnDelete);
    tr.appendChild(tdActions);
    
    return tr;
}

/**
 * Maneja el cambio de checkbox P (solo uno permitido por fila).
 */
function handleCheckboxP(productIndex, imageIndex, checked) {
    if (!productStates[productIndex]) {
        productStates[productIndex] = {};
    }
    
    if (!productStates[productIndex].checkboxesP) {
        productStates[productIndex].checkboxesP = [];
    }
    
    if (checked) {
        // Desmarcar otros checkboxes P de la misma fila
        const row = document.querySelector(`tr[data-product-index="${productIndex}"]`);
        const otherCheckboxesP = row.querySelectorAll('.checkbox-p');
        otherCheckboxesP.forEach(cb => {
            if (cb.dataset.imageIndex != imageIndex) {
                cb.checked = false;
                const idx = productStates[productIndex].checkboxesP.indexOf(parseInt(cb.dataset.imageIndex));
                if (idx > -1) {
                    productStates[productIndex].checkboxesP.splice(idx, 1);
                }
            }
        });
        
        // Añadir este checkbox
        if (!productStates[productIndex].checkboxesP.includes(imageIndex)) {
            productStates[productIndex].checkboxesP.push(imageIndex);
        }
    } else {
        // Remover este checkbox
        const idx = productStates[productIndex].checkboxesP.indexOf(imageIndex);
        if (idx > -1) {
            productStates[productIndex].checkboxesP.splice(idx, 1);
        }
    }
    
    saveProductState(productIndex, productStates[productIndex]);
    updatePreviewButton();
}

/**
 * Maneja el cambio de checkbox G (múltiples permitidos).
 */
function handleCheckboxG(productIndex, imageIndex, checked) {
    if (!productStates[productIndex]) {
        productStates[productIndex] = {};
    }
    
    if (!productStates[productIndex].checkboxesG) {
        productStates[productIndex].checkboxesG = [];
    }
    
    if (checked) {
        if (!productStates[productIndex].checkboxesG.includes(imageIndex)) {
            productStates[productIndex].checkboxesG.push(imageIndex);
        }
    } else {
        const idx = productStates[productIndex].checkboxesG.indexOf(imageIndex);
        if (idx > -1) {
            productStates[productIndex].checkboxesG.splice(idx, 1);
        }
    }
    
    saveProductState(productIndex, productStates[productIndex]);
    updatePreviewButton();
}

/**
 * Genera una clave única para un producto basado en su información original.
 */
function getProductKey(product) {
    return `${product.collection}|${product.page}|${product.name}`;
}

/**
 * Obtiene el contador de duplicados para un producto.
 */
function getDuplicateCount(product) {
    const key = getProductKey(product);
    return duplicateCounters[key] || 0;
}

/**
 * Incrementa el contador de duplicados para un producto.
 */
function incrementDuplicateCount(product) {
    const key = getProductKey(product);
    if (!duplicateCounters[key]) {
        duplicateCounters[key] = 0;
    }
    duplicateCounters[key]++;
    // Guardar contadores en LocalStorage
    saveDuplicateCounters();
    return duplicateCounters[key];
}

/**
 * Guarda los contadores de duplicados en LocalStorage.
 */
function saveDuplicateCounters() {
    try {
        localStorage.setItem('yupoo_duplicate_counters', JSON.stringify(duplicateCounters));
    } catch (e) {
        console.error('Error al guardar contadores de duplicados:', e);
    }
}

/**
 * Carga los contadores de duplicados desde LocalStorage.
 */
function loadDuplicateCounters() {
    try {
        const stored = localStorage.getItem('yupoo_duplicate_counters');
        duplicateCounters = stored ? JSON.parse(stored) : {};
    } catch (e) {
        console.error('Error al cargar contadores de duplicados:', e);
        duplicateCounters = {};
    }
}

/**
 * Duplica una fila de producto.
 */
function handleDuplicate(productIndex) {
    // Insertar el mismo producto después del actual
    const product = allProducts[productIndex];
    const duplicatedProduct = {...product}; // Copia del producto
    
    // Incrementar contador de duplicados para este producto original
    const duplicateCount = incrementDuplicateCount(product);
    
    // Guardar el contador de duplicados en el producto duplicado
    duplicatedProduct._duplicateCount = duplicateCount;
    duplicatedProduct._originalKey = getProductKey(product);
    
    allProducts.splice(productIndex + 1, 0, duplicatedProduct);
    
    // Guardar la lista completa de productos (incluyendo duplicados)
    saveProductsList(allProducts);
    
    // Actualizar índices de estados
    const newStates = {};
    Object.keys(productStates).forEach(key => {
        const idx = parseInt(key);
        if (idx > productIndex) {
            newStates[idx + 1] = productStates[key];
        } else {
            newStates[key] = productStates[key];
        }
    });
    
    // La nueva fila no tiene estado (todo en blanco)
    productStates = newStates;
    
    // Guardar estado completo
    const state = loadState() || {};
    state.products = productStates;
    saveState(state);
    
    // Actualizar total de productos
    sessionStorage.setItem('totalProducts', allProducts.length.toString());
    
    // Re-renderizar página actual
    renderPage(currentPage);
}

/**
 * Elimina una fila de producto.
 */
function handleDelete(productIndex) {
    if (confirm('¿Estás seguro de que deseas eliminar este producto?')) {
        // Eliminar producto
        allProducts.splice(productIndex, 1);
        
        // Guardar la lista completa de productos actualizada
        saveProductsList(allProducts);
        
        // Actualizar índices de estados
        const newStates = {};
        Object.keys(productStates).forEach(key => {
            const idx = parseInt(key);
            if (idx < productIndex) {
                newStates[key] = productStates[key];
            } else if (idx > productIndex) {
                newStates[idx - 1] = productStates[key];
            }
            // idx === productIndex se omite (se elimina)
        });
        
        productStates = newStates;
        
        // Guardar estado completo
        const state = loadState() || {};
        state.products = productStates;
        saveState(state);
        
        // Actualizar total de productos
        sessionStorage.setItem('totalProducts', allProducts.length.toString());
        
        // Re-renderizar página actual
        renderPage(currentPage);
    }
}

/**
 * Actualiza los controles de paginación.
 */
function updatePagination() {
    const totalPages = Math.ceil(allProducts.length / PRODUCTS_PER_PAGE);
    const pageInfo = document.getElementById('page-info');
    pageInfo.textContent = `Página ${currentPage} de ${totalPages}`;
    
    const prevBtn = document.getElementById('prev-page');
    const nextBtn = document.getElementById('next-page');
    
    prevBtn.disabled = currentPage === 1;
    nextBtn.disabled = currentPage >= totalPages;
    
    prevBtn.onclick = () => {
        if (currentPage > 1) {
            renderPage(currentPage - 1);
        }
    };
    
    nextBtn.onclick = () => {
        if (currentPage < totalPages) {
            renderPage(currentPage + 1);
        }
    };
}

/**
 * Actualiza el estado del botón Preview y muestra items incompletos.
 */
function updatePreviewButton() {
    const previewBtn = document.getElementById('preview-btn');
    const startIndex = (currentPage - 1) * PRODUCTS_PER_PAGE;
    const endIndex = Math.min(startIndex + PRODUCTS_PER_PAGE, allProducts.length);
    
    // Validar que todos los productos tengan título, color y al menos un checkbox
    const incompleteItems = [];
    
    for (let i = startIndex; i < endIndex; i++) {
        const state = productStates[i];
        const itemNumber = i + 1;
        const missingFields = [];
        
        if (!state || !state.title) {
            missingFields.push('título');
        }
        if (!state || !state.color) {
            missingFields.push('color');
        }
        const hasCheckbox = (state && state.checkboxesP && state.checkboxesP.length > 0) ||
                          (state && state.checkboxesG && state.checkboxesG.length > 0);
        if (!hasCheckbox) {
            missingFields.push('imagen seleccionada');
        }
        
        if (missingFields.length > 0) {
            incompleteItems.push({
                item: itemNumber,
                fields: missingFields
            });
        }
    }
    
    const isValid = incompleteItems.length === 0;
    previewBtn.disabled = !isValid;
    
    // Mostrar/ocultar footer con items incompletos
    const footer = document.getElementById('incomplete-items-footer');
    const footerText = document.getElementById('incomplete-items-text');
    
    if (incompleteItems.length > 0) {
        const itemsText = incompleteItems.map(item => {
            return `Item ${item.item} (${item.fields.join(', ')})`;
        }).join(', ');
        footerText.textContent = `Faltan completar: ${itemsText}`;
        footer.style.display = 'block';
    } else {
        footer.style.display = 'none';
    }
}

/**
 * Muestra la barra de progreso.
 */
function showProgressBar() {
    const progressContainer = document.getElementById('progress-bar-container');
    const progressFill = document.getElementById('progress-bar-fill');
    const progressPercentage = document.getElementById('progress-percentage');
    progressContainer.style.display = 'block';
    progressFill.style.width = '0%';
    progressPercentage.textContent = '0%';
}

/**
 * Actualiza la barra de progreso.
 */
function updateProgressBar(percentage) {
    const progressFill = document.getElementById('progress-bar-fill');
    const progressPercentage = document.getElementById('progress-percentage');
    progressFill.style.width = percentage + '%';
    progressPercentage.textContent = Math.round(percentage) + '%';
}

/**
 * Oculta la barra de progreso.
 */
function hideProgressBar() {
    const progressContainer = document.getElementById('progress-bar-container');
    progressContainer.style.display = 'none';
}

/**
 * Maneja el clic en el botón Preview.
 */
async function handlePreview() {
    const startIndex = (currentPage - 1) * PRODUCTS_PER_PAGE;
    const endIndex = Math.min(startIndex + PRODUCTS_PER_PAGE, allProducts.length);
    const pageProducts = allProducts.slice(startIndex, endIndex);
    
    // Preparar datos para el preview
    const previewData = [];
    
    for (let i = startIndex; i < endIndex; i++) {
        const product = allProducts[i];
        const state = productStates[i];
        
        if (!state || !state.title || !state.color) {
            alert('Por favor, completa todos los campos (título y color) para todos los productos.');
            return;
        }
        
        // Obtener título completo
        const titleObj = allTitles.find(t => t.id == state.title);
        const titleName = titleObj ? titleObj.titulo : '';
        
        // Obtener imagen de producto (P)
        let productImage = null;
        if (state.checkboxesP && state.checkboxesP.length > 0) {
            const imageIndex = state.checkboxesP[0];
            productImage = product.images[imageIndex];
        }
        
        // Obtener imágenes de galería (G)
        const galleryImages = [];
        if (state.checkboxesG && state.checkboxesG.length > 0) {
            state.checkboxesG.forEach(imageIndex => {
                galleryImages.push(product.images[imageIndex]);
            });
        }
        
        // Validar que los datos del producto estén completos
        if (!product.collection || !product.page || !product.name) {
            console.error(`Producto en índice ${i} tiene datos incompletos:`, product);
            alert(`Error: El producto en la posición ${i + 1} tiene datos incompletos. Por favor, verifica los datos.`);
            return;
        }
        
        // Determinar el nombre de la carpeta para duplicados
        let folderName = product.name;
        if (product._duplicateCount) {
            // Si es un duplicado, agregar sufijo
            if (product._duplicateCount === 1) {
                folderName = product.name + '_copy';
            } else {
                folderName = product.name + '_copy' + product._duplicateCount;
            }
        }
        
        previewData.push({
            collection: product.collection,
            page: product.page,
            name: product.name,
            folderName: folderName,  // Nombre de carpeta con sufijo si es duplicado
            title: titleName,
            color: state.color,
            productImage: productImage || null,
            galleryImages: galleryImages || []
        });
    }
    
    // Calcular total de imágenes a procesar para la barra de progreso
    let totalImages = 0;
    previewData.forEach(product => {
        if (product.productImage) totalImages++;
        totalImages += product.galleryImages.length;
    });
    
    // Mostrar barra de progreso
    showProgressBar();
    
    // Deshabilitar botón Preview
    const previewBtn = document.getElementById('preview-btn');
    previewBtn.disabled = true;
    
    // Simular progreso mientras se procesa
    let processedImages = 0;
    const progressInterval = setInterval(() => {
        // Simular progreso (no es real, pero da feedback visual)
        if (processedImages < totalImages * 0.9) {
            processedImages += 2;
            const percentage = (processedImages / totalImages) * 100;
            updateProgressBar(Math.min(percentage, 90));
        }
    }, 100);
    
    // Enviar al backend para procesar marca de agua
    try {
        const response = await fetch('/api/preview', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ products: previewData })
        });
        
        clearInterval(progressInterval);
        updateProgressBar(100);
        
        const data = await response.json();
        if (data.success) {
            // Esperar un momento para que se vea el 100%
            setTimeout(() => {
                hideProgressBar();
                previewBtn.disabled = false;
                
                // Guardar datos en sessionStorage para la página de preview
                sessionStorage.setItem('previewData', JSON.stringify(data.products));
                // Guardar página actual
                sessionStorage.setItem('currentPage', currentPage.toString());
                // Navegar a preview.html
                window.location.href = '/preview.html';
            }, 500);
        } else {
            hideProgressBar();
            previewBtn.disabled = false;
            alert('Error al procesar el preview: ' + (data.error || 'Error desconocido'));
        }
    } catch (error) {
        clearInterval(progressInterval);
        hideProgressBar();
        previewBtn.disabled = false;
        console.error('Error al enviar preview:', error);
        alert('Error al procesar el preview. Por favor, intenta de nuevo.');
    }
}

/**
 * Abre el modal con la imagen ampliada.
 */
function openImageModal(imageSrc) {
    const modal = document.getElementById('image-modal');
    const modalImg = document.getElementById('modal-image');
    modalImg.src = imageSrc;
    modal.style.display = 'block';
}

/**
 * Cierra el modal de imagen.
 */
function closeImageModal() {
    const modal = document.getElementById('image-modal');
    modal.style.display = 'none';
}

// Event listeners
document.addEventListener('DOMContentLoaded', () => {
    init();
    
    // Event listener para botón Preview
    const previewBtn = document.getElementById('preview-btn');
    if (previewBtn) {
        previewBtn.addEventListener('click', handlePreview);
    }
    
    // Event listeners para modal de imagen
    const imageModal = document.getElementById('image-modal');
    const closeBtn = document.querySelector('.image-modal-close');
    
    if (closeBtn) {
        closeBtn.addEventListener('click', closeImageModal);
    }
    
    if (imageModal) {
        imageModal.addEventListener('click', (e) => {
            if (e.target === imageModal) {
                closeImageModal();
            }
        });
    }
    
    // Cerrar modal con tecla ESC
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeImageModal();
        }
    });
});
