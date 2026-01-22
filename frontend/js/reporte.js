/**
 * Lógica de la página de reporte.
 */

let autoRefreshInterval = null;

/**
 * Carga los datos del reporte desde el backend.
 */
async function loadReporteData() {
    try {
        const response = await fetch('/api/reporte-data');
        const data = await response.json();
        
        if (data.success) {
            renderReporte(data.productos);
            updateStats(data.productos);
            updateLastUpdate();
        } else {
            console.error('Error al cargar reporte:', data.error);
            showError('Error al cargar el reporte');
        }
        
    } catch (error) {
        console.error('Error al cargar reporte:', error);
        showError('Error de conexión al cargar el reporte');
    }
}

/**
 * Renderiza la tabla del reporte con los productos.
 */
function renderReporte(productos) {
    const loadingContainer = document.getElementById('loading-container');
    const noDataContainer = document.getElementById('no-data-container');
    const reporteTable = document.getElementById('reporte-table');
    const tbody = document.getElementById('reporte-tbody');
    
    // Ocultar loading
    loadingContainer.style.display = 'none';
    
    if (!productos || productos.length === 0) {
        // Mostrar mensaje de "sin datos"
        noDataContainer.style.display = 'block';
        reporteTable.style.display = 'none';
        return;
    }
    
    // Mostrar tabla
    noDataContainer.style.display = 'none';
    reporteTable.style.display = 'table';
    
    // Limpiar tbody
    tbody.innerHTML = '';
    
    // Ordenar productos por número (descendente, más reciente primero)
    const productosOrdenados = [...productos].sort((a, b) => b.numero - a.numero);
    
    // Renderizar cada producto
    productosOrdenados.forEach(producto => {
        const tr = document.createElement('tr');
        
        // Columna Número
        const tdNumero = document.createElement('td');
        tdNumero.textContent = producto.numero;
        tdNumero.style.fontWeight = 'bold';
        tr.appendChild(tdNumero);
        
        // Columna Título - Color
        const tdTitulo = document.createElement('td');
        tdTitulo.textContent = producto.titulo;
        tr.appendChild(tdTitulo);
        
        // Columna URL
        const tdUrl = document.createElement('td');
        if (producto.estado === 'exitoso' && producto.url && !producto.url.startsWith('ERROR')) {
            const link = document.createElement('a');
            link.href = producto.url;
            link.textContent = producto.url;
            link.className = 'product-url';
            link.target = '_blank';
            link.rel = 'noopener noreferrer';
            tdUrl.appendChild(link);
        } else {
            const span = document.createElement('span');
            span.textContent = producto.url;
            span.className = 'error-message';
            tdUrl.appendChild(span);
        }
        tr.appendChild(tdUrl);
        
        // Columna Fecha
        const tdFecha = document.createElement('td');
        tdFecha.textContent = producto.fecha || '-';
        tr.appendChild(tdFecha);
        
        // Columna Estado
        const tdEstado = document.createElement('td');
        const badge = document.createElement('span');
        badge.className = `status-badge status-${producto.estado}`;
        badge.textContent = producto.estado === 'exitoso' ? 'Exitoso' : 'Error';
        tdEstado.appendChild(badge);
        tr.appendChild(tdEstado);
        
        tbody.appendChild(tr);
    });
}

/**
 * Actualiza las estadísticas en el header.
 */
function updateStats(productos) {
    if (!productos) {
        return;
    }
    
    const total = productos.length;
    const exitosos = productos.filter(p => p.estado === 'exitoso').length;
    const errores = productos.filter(p => p.estado === 'error').length;
    
    document.getElementById('stat-total').textContent = total;
    document.getElementById('stat-exitosos').textContent = exitosos;
    document.getElementById('stat-errores').textContent = errores;
}

/**
 * Actualiza el timestamp de última actualización.
 */
function updateLastUpdate() {
    const now = new Date();
    const timeString = now.toLocaleTimeString('es-ES');
    const dateString = now.toLocaleDateString('es-ES');
    
    const lastUpdateElement = document.getElementById('last-update');
    lastUpdateElement.textContent = `Última actualización: ${dateString} ${timeString}`;
}

/**
 * Muestra un mensaje de error.
 */
function showError(message) {
    const loadingContainer = document.getElementById('loading-container');
    loadingContainer.innerHTML = `
        <div style="color: #dc3545;">
            <p>⚠️ ${message}</p>
            <button onclick="loadReporteData()" class="btn-refresh">Reintentar</button>
        </div>
    `;
}

/**
 * Configura el auto-refresh.
 */
function setupAutoRefresh() {
    const autoRefreshCheckbox = document.getElementById('auto-refresh');
    
    const startAutoRefresh = () => {
        if (autoRefreshInterval) {
            clearInterval(autoRefreshInterval);
        }
        autoRefreshInterval = setInterval(() => {
            loadReporteData();
        }, 10000); // 10 segundos
    };
    
    const stopAutoRefresh = () => {
        if (autoRefreshInterval) {
            clearInterval(autoRefreshInterval);
            autoRefreshInterval = null;
        }
    };
    
    autoRefreshCheckbox.addEventListener('change', (e) => {
        if (e.target.checked) {
            startAutoRefresh();
        } else {
            stopAutoRefresh();
        }
    });
    
    // Iniciar auto-refresh si el checkbox está marcado
    if (autoRefreshCheckbox.checked) {
        startAutoRefresh();
    }
}

/**
 * Configura el botón de refresh manual.
 */
function setupRefreshButton() {
    const btnRefresh = document.getElementById('btn-refresh');
    
    btnRefresh.addEventListener('click', async () => {
        btnRefresh.disabled = true;
        btnRefresh.querySelector('span:last-child').textContent = 'Actualizando...';
        
        await loadReporteData();
        
        btnRefresh.disabled = false;
        btnRefresh.querySelector('span:last-child').textContent = 'Actualizar';
    });
}

/**
 * Inicializa la página.
 */
document.addEventListener('DOMContentLoaded', () => {
    // Cargar datos iniciales
    loadReporteData();
    
    // Configurar auto-refresh
    setupAutoRefresh();
    
    // Configurar botón de refresh
    setupRefreshButton();
});
