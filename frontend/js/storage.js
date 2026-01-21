/**
 * Gestión de LocalStorage para persistir el estado de la aplicación.
 */

const STORAGE_KEY = 'yupoo_products_state';
const STORAGE_COLLECTION_KEY = 'yupoo_selected_collection';
const STORAGE_PRODUCTS_LIST_KEY = 'yupoo_products_list';

/**
 * Guarda el estado completo de la aplicación en LocalStorage.
 * @param {Object} state - Estado a guardar
 */
function saveState(state) {
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch (e) {
        console.error('Error al guardar en LocalStorage:', e);
    }
}

/**
 * Carga el estado guardado desde LocalStorage.
 * @returns {Object|null} Estado guardado o null si no existe
 */
function loadState() {
    try {
        const stored = localStorage.getItem(STORAGE_KEY);
        return stored ? JSON.parse(stored) : null;
    } catch (e) {
        console.error('Error al cargar desde LocalStorage:', e);
        return null;
    }
}

/**
 * Guarda la colección seleccionada.
 * @param {string} collectionName - Nombre de la colección
 */
function saveSelectedCollection(collectionName) {
    try {
        localStorage.setItem(STORAGE_COLLECTION_KEY, collectionName);
    } catch (e) {
        console.error('Error al guardar colección:', e);
    }
}

/**
 * Carga la colección seleccionada.
 * @returns {string|null} Nombre de la colección o null
 */
function loadSelectedCollection() {
    try {
        return localStorage.getItem(STORAGE_COLLECTION_KEY);
    } catch (e) {
        console.error('Error al cargar colección:', e);
        return null;
    }
}

/**
 * Guarda la lista completa de productos (incluyendo duplicados).
 * @param {Array} products - Lista completa de productos
 */
function saveProductsList(products) {
    try {
        localStorage.setItem(STORAGE_PRODUCTS_LIST_KEY, JSON.stringify(products));
    } catch (e) {
        console.error('Error al guardar lista de productos:', e);
    }
}

/**
 * Carga la lista completa de productos guardada.
 * @returns {Array|null} Lista de productos o null si no existe
 */
function loadProductsList() {
    try {
        const stored = localStorage.getItem(STORAGE_PRODUCTS_LIST_KEY);
        return stored ? JSON.parse(stored) : null;
    } catch (e) {
        console.error('Error al cargar lista de productos:', e);
        return null;
    }
}

/**
 * Limpia todo el estado guardado.
 */
function clearState() {
    try {
        localStorage.removeItem(STORAGE_KEY);
        localStorage.removeItem(STORAGE_COLLECTION_KEY);
        localStorage.removeItem(STORAGE_PRODUCTS_LIST_KEY);
    } catch (e) {
        console.error('Error al limpiar LocalStorage:', e);
    }
}

/**
 * Guarda el estado de un producto específico.
 * @param {number} productIndex - Índice del producto
 * @param {Object} productState - Estado del producto (título, color, checkboxes)
 */
function saveProductState(productIndex, productState) {
    const state = loadState() || {};
    if (!state.products) {
        state.products = {};
    }
    state.products[productIndex] = productState;
    saveState(state);
}

/**
 * Carga el estado de un producto específico.
 * @param {number} productIndex - Índice del producto
 * @returns {Object|null} Estado del producto o null
 */
function loadProductState(productIndex) {
    const state = loadState();
    if (state && state.products && state.products[productIndex]) {
        return state.products[productIndex];
    }
    return null;
}
