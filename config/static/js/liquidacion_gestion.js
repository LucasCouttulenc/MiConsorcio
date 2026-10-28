// ==========================================
// CONSTANTES Y HELPERS GENERALES
// ==========================================
const mesesNombres = {
    "01": "Enero", "02": "Febrero", "03": "Marzo", "04": "Abril",
    "05": "Mayo", "06": "Junio", "07": "Julio", "08": "Agosto",
    "09": "Septiembre", "10": "Octubre", "11": "Noviembre", "12": "Diciembre"
};

let contadorFilas = 0;
let filaActivaConcepto = null;
let filaActivaRubro = null;
let filaActivaColumna = null;
let filaActivaMonto = null;

function setValorInput(id, val) {
    const el = document.getElementById(id);
    if (!el) return;
    const limpio = (val === null || val === undefined) ? '' : String(val).trim();
    el.value = (limpio !== '' && limpio !== '-') ? limpio : '';
}

function getConsorcioActualId() {
    const select = document.getElementById('select-consorcio');
    return select ? select.value : null;
}

function formatearFechaAR(fechaIso) {
    if (!fechaIso) return '--/--/----';
    const partes = fechaIso.split('-');
    return partes.length === 3 ? `${partes[2]}/${partes[1]}/${partes[0]}` : fechaIso;
}

function formatearMontoVisual(val) {
    if (!val) return 'Monto';
    let num = parseFloat(val.toString().replace(',', '.'));
    if (isNaN(num)) return 'Monto';
    return "$ " + num.toLocaleString('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function calcularAnchosColumnas(numColumnas) {
    const totalCols = Math.max(1, numColumnas);
    const pesoTotal = 2 + totalCols;
    const anchoConcepto = ((2 / pesoTotal) * 100).toFixed(2) + '%';
    const anchoColumna = ((1 / pesoTotal) * 100).toFixed(2) + '%';
    return { anchoConcepto, anchoColumna };
}

// ==========================================
// RUBROS Y COLUMNAS
// ==========================================
function getRubrosDelConsorcio() {
    const cid = getConsorcioActualId();
    return (cid && window.rubrosPorConsorcio && window.rubrosPorConsorcio[cid])
        ? window.rubrosPorConsorcio[cid] : [];
}

function getColumnasDelRubro(rubroId) {
    return (rubroId && window.columnasPorRubro && window.columnasPorRubro[rubroId])
        ? window.columnasPorRubro[rubroId] : [];
}

function getNombreRubro(rubroId) {
    const rubros = getRubrosDelConsorcio();
    const r = rubros.find(r => String(r.val) === String(rubroId));
    return r ? r.nombre : 'Seleccionar Rubro';
}

function getNombreColumna(rubroId, columnaId) {
    const columnas = getColumnasDelRubro(rubroId);
    const c = columnas.find(c => String(c.val) === String(columnaId));
    return c ? c.nombre : 'Seleccionar Columna';
}

// ==========================================
// MODALES
// ==========================================
function abrirModalConcepto(btn) {
    filaActivaConcepto = btn.closest('tr');
    const val = filaActivaConcepto.querySelector('.input-concepto-hidden').value;
    const input = document.getElementById('modal-concepto-input');
    input.value = val;
    document.getElementById('modal-concepto').style.display = 'flex';
    input.focus();
}

function guardarConceptoModal() {
    if (!filaActivaConcepto) return;
    const val = document.getElementById('modal-concepto-input').value.trim();
    filaActivaConcepto.querySelector('.input-concepto-hidden').value = val;
    filaActivaConcepto.querySelector('.btn-concepto .btn-selector-text').textContent = val || 'Concepto...';
    cerrarModal('modal-concepto');
    sincronizarVistaPrevia();
}

function abrirModalRubro(btn) {
    filaActivaRubro = btn.closest('tr');
    const rubros = getRubrosDelConsorcio();
    const lista = document.getElementById('modal-rubro-list');
    lista.innerHTML = '';
    
    const rubroActual = filaActivaRubro.querySelector('.input-rubro-hidden').value;

    if (rubros.length === 0) {
        lista.innerHTML = '<div style="padding: 1rem; color: #666;">No hay rubros configurados.</div>';
    } else {
        rubros.forEach(r => {
            const btnRubro = document.createElement('button');
            btnRubro.type = 'button';
            btnRubro.className = 'gl-modal-item' + (String(r.val) === String(rubroActual) ? ' active' : '');
            btnRubro.textContent = r.nombre;
            btnRubro.onclick = () => seleccionarRubro(r.val, r.nombre);
            lista.appendChild(btnRubro);
        });
    }
    document.getElementById('modal-rubro').style.display = 'flex';
}

function seleccionarRubro(id, nombre) {
    if (!filaActivaRubro) return;
    
    filaActivaRubro.querySelector('.input-rubro-hidden').value = id;
    filaActivaRubro.querySelector('.btn-rubro .btn-selector-text').textContent = nombre;
    
    // Al cambiar de rubro, reseteamos la columna
    filaActivaRubro.querySelector('.input-grupo-hidden').value = '';
    filaActivaRubro.querySelector('.btn-columna .btn-selector-text').textContent = 'Seleccionar Columna';
    
    cerrarModal('modal-rubro');
    sincronizarVistaPrevia();
}

function abrirModalColumna(btn) {
    filaActivaColumna = btn.closest('tr');
    const rubroId = filaActivaColumna.querySelector('.input-rubro-hidden').value;
    
    if (!rubroId) {
        alert("Primero tenés que seleccionar un rubro.");
        return;
    }

    const columnas = getColumnasDelRubro(rubroId);
    const lista = document.getElementById('modal-columna-list');
    lista.innerHTML = '';
    
    const columnaActual = filaActivaColumna.querySelector('.input-grupo-hidden').value;

    if (columnas.length === 0) {
        lista.innerHTML = '<div style="padding: 1rem; color: #666;">No hay columnas en este rubro.</div>';
    } else {
        columnas.forEach(c => {
            const btnCol = document.createElement('button');
            btnCol.type = 'button';
            btnCol.className = 'gl-modal-item' + (String(c.val) === String(columnaActual) ? ' active' : '');
            btnCol.textContent = c.nombre;
            btnCol.onclick = () => seleccionarColumna(c.val, c.nombre);
            lista.appendChild(btnCol);
        });
    }
    document.getElementById('modal-columna').style.display = 'flex';
}

function seleccionarColumna(id, nombre) {
    if (!filaActivaColumna) return;
    filaActivaColumna.querySelector('.input-grupo-hidden').value = id;
    filaActivaColumna.querySelector('.btn-columna .btn-selector-text').textContent = nombre;
    cerrarModal('modal-columna');
    sincronizarVistaPrevia();
}

function abrirModalMonto(btn) {
    filaActivaMonto = btn.closest('tr');
    const montoActual = filaActivaMonto.querySelector('.input-monto-hidden').value;
    const input = document.getElementById('modal-monto-input');
    input.value = montoActual;
    document.getElementById('modal-monto').style.display = 'flex';
    input.focus();
    input.select();
}

function guardarMontoModal() {
    if (!filaActivaMonto) return;
    const val = document.getElementById('modal-monto-input').value;
    const montoLimpio = val ? parseFloat(val).toFixed(2) : '';
    
    filaActivaMonto.querySelector('.input-monto-hidden').value = montoLimpio;
    filaActivaMonto.querySelector('.btn-monto .btn-selector-text').textContent = formatearMontoVisual(montoLimpio);
    
    cerrarModal('modal-monto');
    sincronizarVistaPrevia();
}

function cerrarModal(id) {
    document.getElementById(id).style.display = 'none';
}


// ==========================================
// CREACIÓN Y ELIMINACIÓN DE FILAS DE GASTO
// ==========================================
function agregarFilaGasto(concepto = '', tipo = 'ordinario', rubroSel = '', grupoSel = '', monto = '', servicio = '', origen = '') {
    const tbody = document.getElementById('body-gastos');

    const filaId = `gasto-${contadorFilas}`;
    const esOrdinario = tipo !== 'extraordinario';
    const rubroNombre = rubroSel ? getNombreRubro(rubroSel) : 'Seleccionar Rubro';
    const grupoNombre = (rubroSel && grupoSel) ? getNombreColumna(rubroSel, grupoSel) : 'Seleccionar Columna';
    
    // Lógica para las etiquetas
    let badgeHTML = '';
    if (servicio) {
        badgeHTML = '<span class="badge-servicio" title="Propuesto por un servicio recurrente">Recurrente</span>';
    } else if (origen === 'libro') {
        badgeHTML = '<span class="badge-libro" title="Anotado en el Libro Diario">Libro</span>';
    } else if (origen === 'caja') {
        badgeHTML = '<span class="badge-caja" title="Gasto cerrado en Caja">En Caja</span>';
    }

    const tr = document.createElement('tr');
    tr.id = filaId;
    tr.className = 'fila-gasto';
    if (servicio) tr.dataset.servicio = servicio;
    if (origen) tr.dataset.origen = origen; 
    
    tr.innerHTML = `
        <td>
            <button type="button" class="btn-selector btn-concepto" onclick="abrirModalConcepto(this)">
                <span class="btn-selector-text">${concepto || 'Escribir concepto...'}</span>
                <span class="btn-selector-icon">✎</span>
            </button>
            <input type="hidden" name="gastos_concepto[]" class="input-concepto-hidden" value="${concepto}">
            ${badgeHTML}
        </td>
        <td>
            <div class="tipo-toggle" data-tipo="${esOrdinario ? 'ordinario' : 'extraordinario'}">
                <button type="button" class="tipo-pill tipo-ordinario ${esOrdinario ? 'activo' : ''}" data-tipo="ordinario" onclick="toggleTipoGasto(this)">ORD</button>
                <button type="button" class="tipo-pill tipo-extraordinario ${!esOrdinario ? 'activo' : ''}" data-tipo="extraordinario" onclick="toggleTipoGasto(this)">EXTR</button>
            </div>
            <input type="hidden" name="gastos_tipo[]" class="input-tipo-hidden" value="${esOrdinario ? 'ordinario' : 'extraordinario'}">
        </td>
        <td>
            <button type="button" class="btn-selector btn-rubro" onclick="abrirModalRubro(this)">
                <span class="btn-selector-text">${rubroNombre}</span>
                <span class="btn-selector-icon">▾</span>
            </button>
            <input type="hidden" name="gastos_rubro[]" class="input-rubro-hidden" value="${rubroSel}">
        </td>
        <td>
            <button type="button" class="btn-selector btn-columna" onclick="abrirModalColumna(this)">
                <span class="btn-selector-text">${grupoNombre}</span>
                <span class="btn-selector-icon">▾</span>
            </button>
            <input type="hidden" name="gastos_grupo[]" class="input-grupo-hidden" value="${grupoSel}">
        </td>
        <td>
            <button type="button" class="btn-selector btn-monto" onclick="abrirModalMonto(this)">
                <span class="btn-selector-text">${formatearMontoVisual(monto)}</span>
            </button>
            <input type="hidden" name="gastos_monto[]" class="input-monto-hidden" value="${monto}">
        </td>
        <td class="text-center">
            <button type="button" class="gl-btn gl-btn-danger-outline gl-btn-sm" onclick="eliminarFila('${filaId}')">✕</button>
        </td>
    `;
    tbody.appendChild(tr);
    contadorFilas++;
    sincronizarVistaPrevia();
    return tr;
}

function eliminarFila(id) {
    const fila = document.getElementById(id);
    if (fila) fila.remove();
    sincronizarVistaPrevia();
}

function toggleTipoGasto(btn) {
    const contenedor = btn.closest('.tipo-toggle');
    if (!contenedor) return;
    const nuevoTipo = btn.dataset.tipo;
    contenedor.dataset.tipo = nuevoTipo;
    contenedor.querySelectorAll('.tipo-pill').forEach(b => {
        b.classList.toggle('activo', b.dataset.tipo === nuevoTipo);
    });
    const hidden = contenedor.parentElement.querySelector('.input-tipo-hidden');
    if (hidden) hidden.value = nuevoTipo;
    if (typeof sincronizarVistaPrevia === 'function') sincronizarVistaPrevia();
}

// ==========================================
// CÁLCULO DE FECHAS
// ==========================================
function calcularFechasSugeridas() {
    const mesEl = document.getElementById('select-mes');
    const anioEl = document.getElementById('select-anio');
    if (!mesEl || !anioEl) return;

    const mesInt = parseInt(mesEl.value, 10);
    const anioInt = parseInt(anioEl.value, 10);

    const ultimoDia = new Date(anioInt, mesInt, 0).getDate();
    const mesStr = mesInt.toString().padStart(2, '0');

    const diaCierre = Math.min(30, ultimoDia);
    document.getElementById('fecha_cierre').value = `${anioInt}-${mesStr}-${diaCierre.toString().padStart(2, '0')}`;

    let mesSig = mesInt + 1;
    let anioSig = anioInt;
    if (mesSig > 12) { mesSig = 1; anioSig += 1; }
    const mesSigStr = mesSig.toString().padStart(2, '0');
    document.getElementById('fecha_vencimiento_1').value = `${anioSig}-${mesSigStr}-10`;
}

function actualizarFechasYVista() {
    calcularFechasSugeridas();
    if (typeof sincronizarServiciosRecurrentes === 'function') sincronizarServiciosRecurrentes();
    sincronizarVistaPrevia();
}

// Interceptar la tecla Enter dentro de los modales para que no se envíe el formulario de atrás
document.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && e.target.closest('.gl-modal')) {
        e.preventDefault(); // Evita que el formulario principal se envíe
        
        // Detectamos qué modal está abierto y guardamos
        const modal = e.target.closest('.gl-modal');
        if (modal.id === 'modal-monto') {
            guardarMontoModal();
        } else if (modal.id === 'modal-concepto') {
            // Solo guardamos si no se está usando Shift+Enter (por si quieren hacer saltos de línea)
            if (!e.shiftKey) {
                guardarConceptoModal();
            }
        }
    }
});