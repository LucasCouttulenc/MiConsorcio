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
// CREACIÓN Y ELIMINACIÓN DE FILAS DE GASTO
// ==========================================
function escaparHtml(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function construirChecklistUF(consorcioId, seleccionadas) {
    const ufs = (consorcioId && window.ufsPorConsorcio && window.ufsPorConsorcio[consorcioId]) ? window.ufsPorConsorcio[consorcioId] : [];
    if (!ufs.length) {
        return '<div class="rec-vacio">Seleccioná un consorcio con unidades funcionales cargadas.</div>';
    }
    const sel = new Set((seleccionadas || []).map(String));
    return ufs.map(uf => {
        const checked = sel.has(String(uf.id)) ? 'checked' : '';
        return `<label class="uf-chip"><input type="checkbox" class="uf-check" data-uf="${uf.id}" ${checked}><span>${escaparHtml(uf.label)}</span></label>`;
    }).join('');
}

function cambioModo(filaId, seleccionadasForzadas) {
    const fila = document.getElementById(filaId);
    const rec = document.getElementById(`${filaId}-rec`);
    if (!fila || !rec) return;
    const select = fila.querySelector('.select-grupo');
    const modo = select ? select.value : 'general';

    select.classList.remove('modo-particular', 'modo-parcial');
    if (modo === 'particular') select.classList.add('modo-particular');
    if (modo === 'parcial') select.classList.add('modo-parcial');

    if (modo === 'particular' || modo === 'parcial') {
        let seleccionadas = seleccionadasForzadas;
        if (!seleccionadas) {
            seleccionadas = [...rec.querySelectorAll('.uf-check:checked')].map(ch => ch.dataset.uf);
        }
        const consorcioId = getConsorcioActualId();
        const panel = rec.querySelector('.rec-panel');
        const titulo = rec.querySelector('.rec-title');
        panel.classList.remove('modo-particular', 'modo-parcial');
        panel.classList.add(modo === 'particular' ? 'modo-particular' : 'modo-parcial');
        titulo.innerHTML = modo === 'particular'
            ? 'Gasto <b>Particular</b> — elegí las UF que <b>pagan</b> este gasto:'
            : 'Gasto <b>Parcial</b> — marcá las UF que quedan <b>afuera</b> (no lo pagan):';
        rec.querySelector('.rec-grid').innerHTML = construirChecklistUF(consorcioId, seleccionadas);
        rec.style.display = '';
    } else {
        rec.style.display = 'none';
    }
}

function refrescarRecuadros() {
    document.querySelectorAll('#body-gastos tr.fila-gasto').forEach(fila => cambioModo(fila.id));
}

function agregarFilaGasto(concepto = '', tipo = 'ordinario', subtipoSel = '', modoSel = 'general', monto = '', ufsSel = []) {
    const tbody = document.getElementById('body-gastos');
    const consorcioId = getConsorcioActualId();
    const grupos = (consorcioId && window.gruposPorConsorcio && window.gruposPorConsorcio[consorcioId]) ? window.gruposPorConsorcio[consorcioId] : [];
    const subtipos = (consorcioId && window.subtiposPorConsorcio && window.subtiposPorConsorcio[consorcioId]) ? window.subtiposPorConsorcio[consorcioId] : [];

    const modoActual = modoSel || 'general';
    let opcionesGrupos = '';
    (grupos.length ? grupos : [{val:'general',nombre:'General'},{val:'parcial',nombre:'Parcial'},{val:'particular',nombre:'Particular'}]).forEach(g => {
        const selected = String(g.val) === String(modoActual) ? 'selected' : '';
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
            <select name="gastos_subtipo[]" class="gl-select select-subtipo" required>
                ${opcionesSubtipos}
            </select>
        </td>
        <td>
            <select name="gastos_grupo[]" class="gl-select select-grupo" onchange="cambioModo('${filaId}')" required>
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

    const recTr = document.createElement('tr');
    recTr.id = `${filaId}-rec`;
    recTr.className = 'fila-rec';
    recTr.style.display = 'none';
    recTr.innerHTML = `
        <td colspan="6" class="rec-cell">
            <div class="rec-panel">
                <div class="rec-title"></div>
                <div class="rec-grid"></div>
            </div>
        </td>
    `;
    tbody.appendChild(recTr);

    contadorFilas++;
    cambioModo(filaId, (ufsSel && ufsSel.length) ? ufsSel : null);
    sincronizarVistaPrevia();
}

function eliminarFila(id) {
    const fila = document.getElementById(id);
    if (fila) fila.remove();
    const rec = document.getElementById(`${id}-rec`);
    if (rec) rec.remove();
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