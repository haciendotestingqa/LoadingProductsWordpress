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
 * Obtiene los datos actuales del reporte para exportar.
 */
async function getReporteDataForExport() {
    try {
        const response = await fetch('/api/reporte-data');
        const data = await response.json();
        
        if (data.success) {
            return data.productos;
        }
        return [];
    } catch (error) {
        console.error('Error al obtener datos para exportar:', error);
        return [];
    }
}

/**
 * Exporta el reporte como PDF con formato profesional.
 */
async function exportToPDF() {
    const btnExport = document.getElementById('btn-export-pdf');
    btnExport.disabled = true;
    btnExport.querySelector('span:last-child').textContent = 'Generando...';
    
    try {
        // Obtener datos actuales
        const productos = await getReporteDataForExport();
        
        if (!productos || productos.length === 0) {
            alert('No hay productos para exportar');
            btnExport.disabled = false;
            btnExport.querySelector('span:last-child').textContent = 'Exportar PDF';
            return;
        }
        
        // Calcular estadísticas
        const total = productos.length;
        const exitosos = productos.filter(p => p.estado === 'exitoso').length;
        const errores = productos.filter(p => p.estado === 'error').length;
        
        // Crear instancia de jsPDF
        const { jsPDF } = window.jspdf;
        const doc = new jsPDF({
            orientation: 'landscape',
            unit: 'mm',
            format: 'a4'
        });
        
        // Configurar fuentes
        doc.setFont('helvetica');
        
        // ===== ENCABEZADO =====
        // Título principal
        doc.setFontSize(20);
        doc.setTextColor(102, 126, 234); // Color morado
        doc.text('Reporte de Productos Procesados', 15, 20);
        
        // Fecha de generación
        const now = new Date();
        const dateString = now.toLocaleDateString('es-ES', { 
            year: 'numeric', 
            month: 'long', 
            day: 'numeric' 
        });
        const timeString = now.toLocaleTimeString('es-ES');
        doc.setFontSize(10);
        doc.setTextColor(100, 100, 100);
        doc.text(`Generado el ${dateString} a las ${timeString}`, 15, 27);
        
        // ===== ESTADÍSTICAS =====
        doc.setFontSize(12);
        doc.setTextColor(0, 0, 0);
        
        // Cajas de estadísticas
        const statsY = 35;
        const boxWidth = 60;
        const boxHeight = 18;
        const gap = 10;
        
        // Total
        doc.setFillColor(102, 126, 234);
        doc.roundedRect(15, statsY, boxWidth, boxHeight, 3, 3, 'F');
        doc.setTextColor(255, 255, 255);
        doc.setFontSize(10);
        doc.text('Total Procesados', 17, statsY + 6);
        doc.setFontSize(16);
        doc.setFont('helvetica', 'bold');
        doc.text(total.toString(), 17, statsY + 14);
        
        // Exitosos
        doc.setFillColor(40, 167, 69);
        doc.roundedRect(15 + boxWidth + gap, statsY, boxWidth, boxHeight, 3, 3, 'F');
        doc.setTextColor(255, 255, 255);
        doc.setFontSize(10);
        doc.setFont('helvetica', 'normal');
        doc.text('Exitosos', 17 + boxWidth + gap, statsY + 6);
        doc.setFontSize(16);
        doc.setFont('helvetica', 'bold');
        doc.text(exitosos.toString(), 17 + boxWidth + gap, statsY + 14);
        
        // Errores
        doc.setFillColor(220, 53, 69);
        doc.roundedRect(15 + (boxWidth + gap) * 2, statsY, boxWidth, boxHeight, 3, 3, 'F');
        doc.setTextColor(255, 255, 255);
        doc.setFontSize(10);
        doc.setFont('helvetica', 'normal');
        doc.text('Errores', 17 + (boxWidth + gap) * 2, statsY + 6);
        doc.setFontSize(16);
        doc.setFont('helvetica', 'bold');
        doc.text(errores.toString(), 17 + (boxWidth + gap) * 2, statsY + 14);
        
        // ===== TABLA DE PRODUCTOS =====
        doc.setFont('helvetica', 'normal');
        doc.setTextColor(0, 0, 0);
        
        // Preparar datos para la tabla (ordenar por número descendente)
        const productosOrdenados = [...productos].sort((a, b) => b.numero - a.numero);
        
        // Mantener referencia a las URLs completas para los hipervínculos
        const tableData = productosOrdenados.map(p => [
            p.numero.toString(),
            p.titulo,
            p.url, // URL completa sin recortar
            p.fecha || '-',
            p.estado === 'exitoso' ? 'Exitoso' : 'Error'
        ]);
        
        doc.autoTable({
            startY: statsY + boxHeight + 10,
            head: [['#', 'Título - Color', 'URL del Producto', 'Fecha', 'Estado']],
            body: tableData,
            theme: 'striped',
            headStyles: {
                fillColor: [102, 126, 234],
                textColor: 255,
                fontStyle: 'bold',
                halign: 'left'
            },
            columnStyles: {
                0: { cellWidth: 15, halign: 'center', fontStyle: 'bold' },
                1: { cellWidth: 55 },
                2: { cellWidth: 95, fontSize: 7, textColor: [102, 126, 234] }, // URL completa, azul
                3: { cellWidth: 38, halign: 'center' },
                4: { cellWidth: 25, halign: 'center' }
            },
            bodyStyles: {
                fontSize: 9,
                cellPadding: 3
            },
            alternateRowStyles: {
                fillColor: [245, 245, 245]
            },
            didParseCell: function(data) {
                // Colorear la columna de estado
                if (data.column.index === 4 && data.section === 'body') {
                    const estado = data.cell.raw;
                    if (estado === 'Exitoso') {
                        data.cell.styles.textColor = [21, 87, 36];
                        data.cell.styles.fillColor = [212, 237, 218];
                        data.cell.styles.fontStyle = 'bold';
                    } else {
                        data.cell.styles.textColor = [114, 28, 36];
                        data.cell.styles.fillColor = [248, 215, 218];
                        data.cell.styles.fontStyle = 'bold';
                    }
                }
                
                // Estilo para URLs en la columna 2
                if (data.column.index === 2 && data.section === 'body') {
                    const url = data.cell.raw;
                    // Solo aplicar estilo de link si es una URL exitosa
                    if (url && url.startsWith('http') && !url.startsWith('ERROR')) {
                        data.cell.styles.textColor = [102, 126, 234]; // Azul
                        data.cell.styles.fontStyle = 'italic';
                    } else {
                        data.cell.styles.textColor = [114, 28, 36]; // Rojo para errores
                    }
                }
            },
            didDrawCell: function(data) {
                // Agregar hipervínculo clickeable a las URLs exitosas
                if (data.column.index === 2 && data.section === 'body') {
                    const url = data.cell.raw;
                    if (url && url.startsWith('http') && !url.startsWith('ERROR')) {
                        // Agregar link clickeable
                        doc.link(
                            data.cell.x,
                            data.cell.y,
                            data.cell.width,
                            data.cell.height,
                            { url: url }
                        );
                    }
                }
            },
            margin: { left: 15, right: 15 },
            tableWidth: 'auto'
        });
        
        // ===== FOOTER =====
        const pageCount = doc.internal.getNumberOfPages();
        for (let i = 1; i <= pageCount; i++) {
            doc.setPage(i);
            
            // Línea separadora
            doc.setDrawColor(200, 200, 200);
            doc.line(15, 200, 282, 200);
            
            // Texto del footer
            doc.setFontSize(8);
            doc.setTextColor(100, 100, 100);
            doc.text('ValenciaDrip - Sistema de Gestión de Productos', 15, 205);
            doc.text(`Página ${i} de ${pageCount}`, 260, 205);
        }
        
        // ===== GUARDAR PDF =====
        const fileName = `reporte_productos_${now.getFullYear()}_${(now.getMonth()+1).toString().padStart(2,'0')}_${now.getDate().toString().padStart(2,'0')}.pdf`;
        doc.save(fileName);
        
    } catch (error) {
        console.error('Error al generar PDF:', error);
        alert('Error al generar el PDF. Por favor, intenta de nuevo.');
    } finally {
        btnExport.disabled = false;
        btnExport.querySelector('span:last-child').textContent = 'Exportar PDF';
    }
}

/**
 * Configura el botón de exportar PDF.
 */
function setupExportButton() {
    const btnExport = document.getElementById('btn-export-pdf');
    
    btnExport.addEventListener('click', () => {
        exportToPDF();
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
    
    // Configurar botón de exportar PDF
    setupExportButton();
});
