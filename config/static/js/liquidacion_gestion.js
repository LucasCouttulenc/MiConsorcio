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

function opcionesRubrosHTML(rubroSeleccionado = '') {
    let html = '<option value="">-- Seleccionar --</option>';
    getRubrosDelConsorcio().forEach(r => {
        const sel = String(r.val) === String(rubroSeleccionado) ? 'selected' : '';
        html += `<option value="${r.val}" ${sel}>${r.nombre}</option>`;
    });
    return html;
}

function opcionesColumnasHTML(rubroId, columnaSeleccionada = '') {
    let html = '<option value="">-- Seleccionar --</option>';
    getColumnasDelRubro(rubroId).forEach(c => {
        const sel = String(c.val) === String(columnaSeleccionada) ? 'selected' : '';
        html += `<option value="${c.val}" ${sel}>${c.codigo} - ${c.nombre}</option>`;
    });
    return html;
}

function actualizarSelectoresRubros() {
    document.querySelectorAll('.select-rubro').forEach(sel => {
        const actual = sel.value;
        sel.innerHTML = opcionesRubrosHTML(actual);
    });
}

function onCambiarRubro(selectRubro) {
    const fila = selectRubro.closest('tr');
    const selectGrupo = fila.querySelector('.select-grupo');
    selectGrupo.innerHTML = opcionesColumnasHTML(selectRubro.value);
    sincronizarVistaPrevia();
}

// ==========================================
// CREACIÓN Y ELIMINACIÓN DE FILAS DE GASTO
// ==========================================
function agregarFilaGasto(concepto = '', tipo = 'ordinario', rubroSel = '', grupoSel = '', monto = '') {
    const tbody = document.getElementById('body-gastos');

    const filaId = `gasto-${contadorFilas}`;
    const tr = document.createElement('tr');
    tr.id = filaId;
    tr.className = 'fila-gasto';
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
            <select name="gastos_rubro[]" class="gl-select select-rubro" onchange="onCambiarRubro(this)" required>
                ${opcionesRubrosHTML(rubroSel)}
            </select>
        </td>
        <td>
            <select name="gastos_grupo[]" class="gl-select select-grupo" required>
                ${opcionesColumnasHTML(rubroSel, grupoSel)}
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

    const diaCierre = Math.min(30, ultimoDia);
    document.getElementById('fecha_cierre').value = `${anioInt}-${mesStr}-${diaCierre.toString().padStart(2, '0')}`;

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