// config/static/js/liquidacion_preview.js

let contadorFilas = 0;

// Estructuras de datos locales para consorcios
var gruposPorConsorcio = gruposPorConsorcio || {};
var subtiposPorConsorcio = subtiposPorConsorcio || {};

document.addEventListener('DOMContentLoaded', function () {
    const formLiquidacion = document.getElementById('form-liquidacion');
    const selectConsorcio = document.getElementById('select-consorcio');

    if (selectConsorcio) {
        selectConsorcio.addEventListener('change', function () {
            renderizarListasGestion();
            sincronizarVistaPrevia();
        });
    }

    if (formLiquidacion) {
        formLiquidacion.addEventListener('input', function (e) {
            if (e.target.matches('.input-concepto, .input-monto')) {
                sincronizarVistaPrevia();
            }
        });

        formLiquidacion.addEventListener('change', function (e) {
            if (e.target.matches('.select-tipo, .select-subtipo, .select-grupo')) {
                sincronizarVistaPrevia();
            }
        });
    }

    renderizarListasGestion();
    sincronizarVistaPrevia();
});

function getConsorcioActualId() {
    const select = document.getElementById('select-consorcio');
    return select ? select.value : null;
}

// ==========================================
// GESTIÓN DE SUBTIPOS / RUBROS
// ==========================================

function crearSubtipo() {
    const consorcioId = getConsorcioActualId();
    if (!consorcioId) {
        alert("Por favor, seleccione primero un consorcio.");
        return;
    }

    const input = document.getElementById('input-nuevo-subtipo');
    if (!input) return;

    const nombre = input.value.trim().toUpperCase();
    if (!nombre) {
        alert("Ingrese un nombre para el subtipo.");
        return;
    }

    if (!subtiposPorConsorcio[consorcioId]) {
        subtiposPorConsorcio[consorcioId] = [];
    }

    // Validación de Duplicados
    if (subtiposPorConsorcio[consorcioId].includes(nombre)) {
        alert(`El subtipo "${nombre}" ya existe.`);
        return;
    }

    subtiposPorConsorcio[consorcioId].push(nombre);
    input.value = '';

    renderizarListaSubtipos();
    actualizarSelectoresSubtipos();
    sincronizarVistaPrevia();
}

function eliminarSubtipo(index) {
    const consorcioId = getConsorcioActualId();
    if (!consorcioId || !subtiposPorConsorcio[consorcioId]) return;

    subtiposPorConsorcio[consorcioId].splice(index, 1);

    renderizarListaSubtipos();
    actualizarSelectoresSubtipos();
    sincronizarVistaPrevia();
}

function renderizarListaSubtipos() {
    const consorcioId = getConsorcioActualId();
    const contenedor = document.getElementById('lista-subtipos-tags');
    if (!contenedor) return;

    contenedor.innerHTML = '';
    const lista = (consorcioId && subtiposPorConsorcio[consorcioId]) ? subtiposPorConsorcio[consorcioId] : [];

    lista.forEach((subtipo, idx) => {
        const tag = document.createElement('span');
        tag.className = 'badge bg-secondary d-inline-flex align-items-center gap-1 p-2 fs-7';
        tag.innerHTML = `
            ${subtipo}
            <button type="button" class="btn-close btn-close-white" style="font-size: 0.5rem;" onclick="eliminarSubtipo(${idx})"></button>
        `;
        contenedor.appendChild(tag);
    });
}

function actualizarSelectoresSubtipos() {
    const consorcioId = getConsorcioActualId();
    const lista = (consorcioId && subtiposPorConsorcio[consorcioId]) ? subtiposPorConsorcio[consorcioId] : [];
    const selects = document.querySelectorAll('.select-subtipo');

    selects.forEach(select => {
        const valActual = select.value;
        let html = '<option value="">-- Seleccionar --</option>';
        lista.forEach(st => {
            const selected = st === valActual ? 'selected' : '';
            html += `<option value="${st}" ${selected}>${st}</option>`;
        });
        select.innerHTML = html;
    });
}

// ==========================================
// GESTIÓN DE COLUMNAS / GRUPOS
// ==========================================

function crearGrupo() {
    const consorcioId = getConsorcioActualId();
    if (!consorcioId) {
        alert("Por favor, seleccione primero un consorcio.");
        return;
    }

    const input = document.getElementById('input-nuevo-grupo');
    if (!input) return;

    const nombre = input.value.trim().toUpperCase();
    if (!nombre) {
        alert("Ingrese un nombre para la columna.");
        return;
    }

    if (!gruposPorConsorcio[consorcioId]) {
        gruposPorConsorcio[consorcioId] = [];
    }

    // Validación de Duplicados
    const existe = gruposPorConsorcio[consorcioId].some(g => g.nombre.toUpperCase() === nombre);
    if (existe) {
        alert(`La columna "${nombre}" ya existe.`);
        return;
    }

    const val = 'grupo_' + Date.now();
    gruposPorConsorcio[consorcioId].push({ val: val, nombre: nombre });
    input.value = '';

    renderizarListaGrupos();
    actualizarSelectoresGrupos();
    sincronizarVistaPrevia();
}

function eliminarGrupo(index) {
    const consorcioId = getConsorcioActualId();
    if (!consorcioId || !gruposPorConsorcio[consorcioId]) return;

    gruposPorConsorcio[consorcioId].splice(index, 1);

    renderizarListaGrupos();
    actualizarSelectoresGrupos();
    sincronizarVistaPrevia();
}

function renderizarListaGrupos() {
    const consorcioId = getConsorcioActualId();
    const contenedor = document.getElementById('lista-grupos-tags');
    if (!contenedor) return;

    contenedor.innerHTML = '';
    const lista = (consorcioId && gruposPorConsorcio[consorcioId]) ? gruposPorConsorcio[consorcioId] : [];

    lista.forEach((grupo, idx) => {
        const tag = document.createElement('span');
        tag.className = 'badge bg-success d-inline-flex align-items-center gap-1 p-2 fs-7';
        tag.innerHTML = `
            ${grupo.nombre}
            <button type="button" class="btn-close btn-close-white" style="font-size: 0.5rem;" onclick="eliminarGrupo(${idx})"></button>
        `;
        contenedor.appendChild(tag);
    });
}

function actualizarSelectoresGrupos() {
    const consorcioId = getConsorcioActualId();
    const lista = (consorcioId && gruposPorConsorcio[consorcioId]) ? gruposPorConsorcio[consorcioId] : [];
    const selects = document.querySelectorAll('.select-grupo');

    selects.forEach(select => {
        const valActual = select.value;
        let html = '<option value="">-- Seleccionar --</option>';
        lista.forEach(g => {
            const selected = g.val === valActual ? 'selected' : '';
            html += `<option value="${g.val}" ${selected}>${g.nombre}</option>`;
        });
        select.innerHTML = html;
    });
}

function renderizarListasGestion() {
    renderizarListaSubtipos();
    renderizarListaGrupos();
    actualizarSelectoresSubtipos();
    actualizarSelectoresGrupos();
}

// ==========================================
// FILAS DE GASTO Y VISTA PREVIA
// ==========================================

function agregarFilaGasto(concepto = '', tipo = 'ordinario', subtipoSel = '', grupoSel = '', monto = '') {
    const tbody = document.getElementById('body-gastos');
    if (!tbody) return;

    const consorcioId = getConsorcioActualId();
    const grupos = (consorcioId && gruposPorConsorcio[consorcioId]) ? gruposPorConsorcio[consorcioId] : [];
    const subtipos = (consorcioId && subtiposPorConsorcio[consorcioId]) ? subtiposPorConsorcio[consorcioId] : [];

    let opcionesGrupos = '<option value="">-- Seleccionar --</option>';
    grupos.forEach(g => {
        opcionesGrupos += `<option value="${g.val}" ${g.val === grupoSel ? 'selected' : ''}>${g.nombre}</option>`;
    });

    let opcionesSubtipos = '<option value="">-- Seleccionar --</option>';
    subtipos.forEach(st => {
        opcionesSubtipos += `<option value="${st}" ${st === subtipoSel ? 'selected' : ''}>${st}</option>`;
    });

    const filaId = `gasto-${contadorFilas}`;
    const tr = document.createElement('tr');
    tr.id = filaId;
    tr.innerHTML = `
        <td>
            <input type="text" name="gastos_concepto[]" class="form-control input-concepto" placeholder="Ej: Sueldo Básico" value="${concepto}" required>
        </td>
        <td>
            <select name="gastos_tipo[]" class="form-select select-tipo" required>
                <option value="ordinario" ${tipo === 'ordinario' ? 'selected' : ''}>Ordinario</option>
                <option value="extraordinario" ${tipo === 'extraordinario' ? 'selected' : ''}>Extraordinario</option>
            </select>
        </td>
        <td>
            <select name="gastos_subtipo[]" class="form-select select-subtipo" required>
                ${opcionesSubtipos}
            </select>
        </td>
        <td>
            <select name="gastos_grupo[]" class="form-select select-grupo" required>
                ${opcionesGrupos}
            </select>
        </td>
        <td>
            <input type="text" inputmode="decimal" min="0" name="gastos_monto[]" class="form-control input-monto" placeholder="0.00" value="${monto}" required>
        </td>
        <td class="text-center">
            <button type="button" class="btn btn-outline-danger btn-sm" onclick="eliminarFila('${filaId}')">✕</button>
        </td>
    `;

    tbody.appendChild(tr);
    contadorFilas++;
    sincronizarVistaPrevia();
}

function eliminarFila(filaId) {
    const fila = document.getElementById(filaId);
    if (fila) {
        fila.remove();
        sincronizarVistaPrevia();
    }
}

function sincronizarVistaPrevia() {
    sincronizarTablaGastosVistaPrevia();
}

function sincronizarTablaGastosVistaPrevia() {
    const consorcioId = getConsorcioActualId();
    const filas = document.querySelectorAll('#body-gastos tr');
    const tablaMatriz = document.getElementById('pv-tabla-gastos-matriz');

    if (!tablaMatriz) return;

    const gruposConsorcio = (consorcioId && gruposPorConsorcio[consorcioId]) ? gruposPorConsorcio[consorcioId] : [];

    if (!consorcioId || gruposConsorcio.length === 0) {
        tablaMatriz.innerHTML = `
            <thead class="table-secondary">
                <tr>
                    <th class="text-start">Concepto / Detalle</th>
                    <th class="text-center">Monto ($)</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td colspan="2" class="text-center text-muted">Seleccione un consorcio y agregue al menos una columna para visualizarlas</td>
                </tr>
            </tbody>
        `;
        return;
    }

    const gastosPorSubtipo = {};

    filas.forEach(fila => {
        const concepto = fila.querySelector('.input-concepto')?.value || '';
        const subtipoVal = fila.querySelector('.select-subtipo')?.value || '';
        const subtipo = subtipoVal.trim() !== '' ? subtipoVal.trim().toUpperCase() : 'GASTOS GENERALES';
        const grupoSelect = fila.querySelector('.select-grupo');
        const grupoVal = grupoSelect?.value;
        const monto = parseFloat(fila.querySelector('.input-monto')?.value) || 0;

        if (concepto.trim() !== '' || monto > 0) {
            if (!gastosPorSubtipo[subtipo]) {
                gastosPorSubtipo[subtipo] = [];
            }
            gastosPorSubtipo[subtipo].push({ concepto, grupoVal, monto });
        }
    });

    let htmlMatriz = '';
    let totalesPorColumna = new Array(gruposConsorcio.length).fill(0);
    let hayGastos = false;

    for (const [subtipo, listaGastos] of Object.entries(gastosPorSubtipo)) {
        hayGastos = true;

        htmlMatriz += `
            <thead class="border-top">
                <tr style="background-color: #1c7c6d; color: #ffffff;">
                    <th colspan="${gruposConsorcio.length + 1}" class="text-center text-uppercase fw-bold py-1 fs-6">
                        ${subtipo}
                    </th>
                </tr>
                <tr class="table-secondary text-center align-middle small">
                    <th class="text-start" style="min-width: 140px;">Concepto / Detalle</th>`;

        gruposConsorcio.forEach(g => {
            htmlMatriz += `<th class="text-center" style="min-width: 80px;">${g.nombre}</th>`;
        });

        htmlMatriz += `</tr></thead><tbody>`;

        listaGastos.forEach(item => {
            htmlMatriz += `<tr><td class="text-start ps-3">${item.concepto || '<em>(Sin concepto)</em>'}</td>`;

            gruposConsorcio.forEach((g, idx) => {
                if (item.grupoVal === g.val) {
                    totalesPorColumna[idx] += item.monto;
                    htmlMatriz += `<td class="text-end fw-bold text-dark">$ ${item.monto.toLocaleString('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>`;
                } else {
                    htmlMatriz += `<td class="text-center text-muted small">-</td>`;
                }
            });

            htmlMatriz += `</tr>`;
        });

        htmlMatriz += `</tbody>`;
    }

    if (!hayGastos) {
        htmlMatriz = `
            <thead class="table-secondary">
                <tr>
                    <th class="text-start">Concepto / Detalle</th>`;
        gruposConsorcio.forEach(g => {
            htmlMatriz += `<th class="text-center">${g.nombre}</th>`;
        });
        htmlMatriz += `</tr></thead>
            <tbody>
                <tr>
                    <td colspan="${gruposConsorcio.length + 1}" class="text-center text-muted py-3">
                        Sin gastos ingresados
                    </td>
                </tr>
            </tbody>`;
    } else {
        htmlMatriz += `
            <tfoot>
                <tr class="fw-bold table-active border-top border-2">
                    <td class="text-start">TOTAL ESTIMADO:</td>`;

        totalesPorColumna.forEach(tot => {
            htmlMatriz += `<td class="text-end">$ ${tot.toLocaleString('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>`;
        });

        htmlMatriz += `</tr></tfoot>`;
    }

    tablaMatriz.innerHTML = htmlMatriz;
}