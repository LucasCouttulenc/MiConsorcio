// ==========================================
// CONSTANTES Y HELPERS GENERALES
// ==========================================
const mesesNombres = {
    "01": "Enero", "02": "Febrero", "03": "Marzo", "04": "Abril",
    "05": "Mayo", "06": "Junio", "07": "Julio", "08": "Agosto",
    "09": "Septiembre", "10": "Octubre", "11": "Noviembre", "12": "Diciembre"
};

let contadorFilas = 0;

function setValorInput(id, val) {
    const el = document.getElementById(id);
    if (!el) return;
    const limpio = (val === null || val === undefined) ? '' : String(val).trim();
    el.value = (limpio !== '') ? limpio : '-';
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

function calcularAnchosColumnas(numColumnas) {
    const totalCols = Math.max(1, numColumnas);
    const pesoTotal = 2 + totalCols; 
    
    const anchoConcepto = ((2 / pesoTotal) * 100).toFixed(2) + '%';
    const anchoColumna = ((1 / pesoTotal) * 100).toFixed(2) + '%';

    return { anchoConcepto, anchoColumna };
}

// ==========================================
// CREACIÓN Y ELIMINACIÓN DE SUBTIPOS
// ==========================================
function crearSubtipo() {
    const consorcioId = getConsorcioActualId();
    if (!consorcioId) {
        alert("Por favor, seleccione primero un consorcio.");
        return;
    }

    const input = document.getElementById('input-nuevo-subtipo');
    const nombre = input ? input.value.trim().toUpperCase() : '';
    if (!nombre) {
        alert("Ingrese un nombre para el subtipo.");
        return;
    }

    window.subtiposPorConsorcio = window.subtiposPorConsorcio || {};
    if (!window.subtiposPorConsorcio[consorcioId]) {
        window.subtiposPorConsorcio[consorcioId] = [];
    }

    if (window.subtiposPorConsorcio[consorcioId].includes(nombre)) {
        alert(`El subtipo "${nombre}" ya existe.`);
        return;
    }

    window.subtiposPorConsorcio[consorcioId].push(nombre);
    input.value = '';

    renderizarListasGestion();
    sincronizarVistaPrevia();
}

function eliminarSubtipo(index) {
    const consorcioId = getConsorcioActualId();
    if (!consorcioId || !window.subtiposPorConsorcio || !window.subtiposPorConsorcio[consorcioId]) return;

    window.subtiposPorConsorcio[consorcioId].splice(index, 1);
    renderizarListasGestion();
    sincronizarVistaPrevia();
}

// ==========================================
// CREACIÓN Y ELIMINACIÓN DE COLUMNAS / GRUPOS
// ==========================================
function crearGrupo() {
    const consorcioId = getConsorcioActualId();
    if (!consorcioId) {
        alert("Por favor, seleccione primero un consorcio.");
        return;
    }

    const input = document.getElementById('input-nuevo-grupo');
    const nombre = input ? input.value.trim().toUpperCase() : '';
    if (!nombre) {
        alert("Ingrese un nombre para la columna.");
        return;
    }

    window.gruposPorConsorcio = window.gruposPorConsorcio || {};
    if (!window.gruposPorConsorcio[consorcioId]) {
        window.gruposPorConsorcio[consorcioId] = [];
    }

    const existe = window.gruposPorConsorcio[consorcioId].some(g => g.nombre.toUpperCase() === nombre);
    if (existe) {
        alert(`La columna "${nombre}" ya existe.`);
        return;
    }

    
    const val = 'NUEVO:' + nombre;

    window.gruposPorConsorcio[consorcioId].push({ val: val, nombre: nombre });
    input.value = '';

    renderizarListasGestion();
    sincronizarVistaPrevia();
}

function eliminarGrupo(index) {
    const consorcioId = getConsorcioActualId();
    if (!consorcioId || !window.gruposPorConsorcio || !window.gruposPorConsorcio[consorcioId]) return;

    window.gruposPorConsorcio[consorcioId].splice(index, 1);
    renderizarListasGestion();
    sincronizarVistaPrevia();
}

// ==========================================
// CREACIÓN Y ELIMINACIÓN DE FILAS DE GASTO
// ==========================================
function agregarFilaGasto(concepto = '', tipo = 'ordinario', subtipoSel = '', grupoSel = '', monto = '') {
    const tbody = document.getElementById('body-gastos');
    const consorcioId = getConsorcioActualId();
    const grupos = (consorcioId && window.gruposPorConsorcio && window.gruposPorConsorcio[consorcioId]) ? window.gruposPorConsorcio[consorcioId] : [];
    const subtipos = (consorcioId && window.subtiposPorConsorcio && window.subtiposPorConsorcio[consorcioId]) ? window.subtiposPorConsorcio[consorcioId] : [];

    let opcionesGrupos = '<option value="">-- Seleccionar --</option>';
    grupos.forEach(g => {
        const selected = String(g.val) === String(grupoSel) ? 'selected' : '';
        opcionesGrupos += `<option value="${g.val}" ${selected}>${g.nombre}</option>`;
    });

    let opcionesSubtipos = '<option value="">-- Seleccionar --</option>';
    subtipos.forEach(st => {
        const selected = String(st) === String(subtipoSel) ? 'selected' : '';
        opcionesSubtipos += `<option value="${st}" ${selected}>${st}</option>`;
    });

    const filaId = `gasto-${contadorFilas}`;
    const tr = document.createElement('tr');
    tr.id = filaId;
    tr.innerHTML = `
        <td>
            <input type="text" name="gastos_concepto[]" class="gl-input input-concepto" value="${concepto}" required>
        </td>
        <td>
            <select name="gastos_tipo[]" class="gl-select select-tipo" required>
                <option value="ordinario" ${tipo === 'ordinario' ? 'selected' : ''}>Ordinario</option>
                <option value="extraordinario" ${tipo === 'extraordinario' ? 'selected' : ''}>Extraordinario</option>
            </select>
        </td>
        <td>
            <select name="gastos_subtipo[]" class="gl-select select-subtipo" required>
                ${opcionesSubtipos}
            </select>
        </td>
        <td>
            <select name="gastos_grupo[]" class="gl-select select-grupo" required>
                ${opcionesGrupos}
            </select>
        </td>
        <td>
            <input type="text" inputmode="decimal" min="0" name="gastos_monto[]" class="gl-input input-monto" placeholder="0.00" value="${monto}" required>
        </td>
        <td class="text-center">
            <button type="button" class="gl-btn gl-btn-danger-outline gl-btn-sm" onclick="eliminarFila('${filaId}')">✕</button>
        </td>
    `;

    tbody.appendChild(tr);
    contadorFilas++;
    sincronizarVistaPrevia();
}

function eliminarFila(id) {
    const fila = document.getElementById(id);
    if (fila) fila.remove();
    sincronizarVistaPrevia();
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

    // Cierre: día 30 (o el último día del mes si tiene menos, como febrero)
    const diaCierre = Math.min(30, ultimoDia);
    document.getElementById('fecha_cierre').value = `${anioInt}-${mesStr}-${diaCierre.toString().padStart(2, '0')}`;

    // Vencimiento: día 10 del mes siguiente
    let mesSig = mesInt + 1;
    let anioSig = anioInt;
    if (mesSig > 12) {
        mesSig = 1;
        anioSig += 1;
    }
    const mesSigStr = mesSig.toString().padStart(2, '0');
    document.getElementById('fecha_vencimiento_1').value = `${anioSig}-${mesSigStr}-10`;
}

function actualizarFechasYVista() {
    calcularFechasSugeridas();
    sincronizarVistaPrevia();
}