// ==========================================
// VISTA PREVIA EN TIEMPO REAL
// ==========================================

function sincronizarVistaPrevia() {
    const mes = document.getElementById('select-mes').value;
    const anio = document.getElementById('select-anio').value;
    const cierre = document.getElementById('fecha_cierre').value;
    const venc = document.getElementById('fecha_vencimiento_1').value;

    document.getElementById('lbl-periodo').textContent = `${mesesNombres[mes]} ${anio}`;
    document.getElementById('lbl-cierre').textContent = formatearFechaAR(cierre);
    document.getElementById('lbl-vencimiento').textContent = formatearFechaAR(venc);

    const camposAdmin = [
        ['admin_razon', 'lbl-admin-razon'], ['admin_nombre', 'lbl-admin-nombre'],
        ['admin_domicilio', 'lbl-admin-domicilio'], ['admin_fiscal', 'lbl-admin-fiscal'],
        ['admin_cuit', 'lbl-admin-cuit'], ['admin_rpa', 'lbl-admin-rpa'],
        ['admin_telefono', 'lbl-admin-telefono'], ['admin_mail', 'lbl-admin-mail'],
    ];
    camposAdmin.forEach(([inputId, lblId]) => {
        const el = document.getElementById(inputId);
        const lbl = document.getElementById(lblId);
        if (el && lbl) {
            const val = el.value.trim();
            lbl.textContent = val !== '' ? val : '-';
        }
    });

    sincronizarTablaGastosVistaPrevia();
}

function alSeleccionarConsorcio(consorcioId) {
    actualizarSelectoresRubros();
    autoGenerarFilasPersonal(consorcioId);


    const info = window.datosConsorcios[consorcioId];
    if (info) {
        document.getElementById('lbl-consorcio-nombre').textContent = info.nombre;
        document.getElementById('lbl-consorcio-localidad').textContent = info.localidad;
        document.getElementById('lbl-consorcio-cuit').textContent = info.cuit;
        document.getElementById('lbl-consorcio-suterh').textContent = info.suterh;
        document.getElementById('lbl-consorcio-horario').textContent = info.horario_atencion;

        setValorInput('admin_razon', info.admin_razon);
        setValorInput('admin_nombre', info.admin_nombre);
        setValorInput('admin_domicilio', info.admin_domicilio);
        setValorInput('admin_fiscal', info.admin_fiscal);
        setValorInput('admin_cuit', info.admin_cuit);
        setValorInput('admin_rpa', info.admin_rpa);
        setValorInput('admin_telefono', info.admin_telefono);
        setValorInput('admin_mail', info.admin_mail);
    } else {
        document.getElementById('lbl-consorcio-nombre').textContent = '--';
        document.getElementById('lbl-consorcio-localidad').textContent = '--';
        document.getElementById('lbl-consorcio-cuit').textContent = '--';
        document.getElementById('lbl-consorcio-suterh').textContent = '--';
        document.getElementById('lbl-consorcio-horario').textContent = '-';

        ['admin_razon', 'admin_nombre', 'admin_domicilio', 'admin_fiscal',
         'admin_cuit', 'admin_rpa', 'admin_telefono', 'admin_mail'].forEach(id => {
            setValorInput(id, '-');
        });
    }

    sincronizarVistaPrevia();
}

function sincronizarTablaGastosVistaPrevia() {
    const consorcioId = getConsorcioActualId();
    const filas = document.querySelectorAll('#body-gastos tr.fila-gasto');
    const contenedorMatriz = document.getElementById('pv-tabla-gastos-matriz');

    if (!contenedorMatriz) return;

    if (!consorcioId) {
        contenedorMatriz.innerHTML = `
            <table class="table table-bordered mb-0" style="width: 100%; table-layout: fixed;">
                <thead class="table-secondary">
                    <tr>
                        <th class="text-center">Concepto / Detalle</th>
                        <th class="text-center">Monto ($)</th>
                    </tr>
                </thead>
                <tbody>
                    <tr><td colspan="2" class="text-center text-muted py-3">Seleccione un consorcio</td></tr>
                </tbody>
            </table>
        `;
        return;
    }

    // Agrupar gastos por RUBRO (nombre)
    const gastosPorRubro = {};
    const columnasPorRubro = {}; // { rubroNombre: Set(columnaId) }

    filas.forEach(fila => {
        const concepto = fila.querySelector('.input-concepto')?.value || '';
        const rubroSelect = fila.querySelector('.select-rubro');
        const rubroVal = rubroSelect?.value || '';
        const rubroNombre = rubroSelect?.selectedOptions?.[0]?.textContent?.trim() || '';
        const columnaSelect = fila.querySelector('.select-grupo');
        const columnaVal = columnaSelect?.value || '';
        const columnaNombre = columnaSelect?.selectedOptions?.[0]?.textContent?.trim() || '';
        const montoRaw = fila.querySelector('.input-monto')?.value || '0';
        const monto = parseFloat(montoRaw.replace(',', '.')) || 0;

        if ((concepto.trim() !== '' || monto > 0) && rubroVal) {
            if (!gastosPorRubro[rubroNombre]) {
                gastosPorRubro[rubroNombre] = [];
                columnasPorRubro[rubroNombre] = new Set();
            }
            gastosPorRubro[rubroNombre].push({ concepto, columnaVal, columnaNombre, monto });
            if (columnaVal) columnasPorRubro[rubroNombre].add(columnaVal);
        }
    });

    // Si no hay rubros asignados, mostramos un mensaje simple
    if (Object.keys(gastosPorRubro).length === 0) {
        contenedorMatriz.innerHTML = `
            <table class="table table-bordered mb-0" style="width: 100%;">
                <tbody>
                    <tr><td class="text-center text-muted py-3">Sin gastos ingresados</td></tr>
                </tbody>
            </table>
        `;
        return;
    }

    let html = '';
    const totalesGeneralesPorColumna = {};

    for (const [rubroNombre, listaGastos] of Object.entries(gastosPorRubro)) {
        const columnaIds = Array.from(columnasPorRubro[rubroNombre]);
        // Usamos los datos de la columna desde window.columnasPorRubro para tener el nombre
        const columnaLookup = {};
        Object.values(window.columnasPorRubro || {}).forEach(cols => {
            cols.forEach(c => { columnaLookup[c.val] = c; });
        });

        const colCount = columnaIds.length || 1;
        const { anchoConcepto, anchoColumna } = calcularAnchosColumnas(colCount);

        const subtotales = {};
        columnaIds.forEach(cid => subtotales[cid] = 0);
        let subtotalSinCol = 0;

        html += `
            <table class="table table-bordered mb-3 align-middle" style="width: 100%; table-layout: fixed;">
                <thead>
                    <tr style="background-color: var(--gl-blue-header, #1b365d); color: #ffffff;">
                        <th colspan="${colCount + 1}" class="text-center text-uppercase fw-bold py-1">
                            ${rubroNombre}
                        </th>
                    </tr>
                    <tr class="table-secondary text-center small">
                        <th class="text-center" style="width: ${anchoConcepto};">Concepto / Detalle</th>`;

        if (columnaIds.length > 0) {
            columnaIds.forEach(cid => {
                const nombre = columnaLookup[cid]?.codigo || 'Col.';
                html += `<th class="text-center" style="width: ${anchoColumna};">${nombre}</th>`;
            });
        } else {
            html += `<th class="text-center" style="width: ${anchoColumna};">Monto ($)</th>`;
        }
        html += `</tr></thead><tbody>`;

        listaGastos.forEach(item => {
            html += `<tr><td class="text-center text-truncate" title="${item.concepto}">${item.concepto || '<em>(Sin concepto)</em>'}</td>`;
            if (columnaIds.length > 0) {
                columnaIds.forEach(cid => {
                    if (item.columnaVal === cid) {
                        subtotales[cid] += item.monto;
                        totalesGeneralesPorColumna[cid] = (totalesGeneralesPorColumna[cid] || 0) + item.monto;
                        html += `<td class="text-center fw-bold">$ ${item.monto.toLocaleString('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>`;
                    } else {
                        html += `<td class="text-center text-muted small">-</td>`;
                    }
                });
            } else {
                subtotalSinCol += item.monto;
                totalesGeneralesPorColumna['default'] = (totalesGeneralesPorColumna['default'] || 0) + item.monto;
                html += `<td class="text-center fw-bold">$ ${item.monto.toLocaleString('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>`;
            }
            html += `</tr>`;
        });

        // Subtotal del rubro
        html += `<tr class="fw-bold table-active" style="background-color: #f8f9fa;">
            <td class="text-center">SUBTOTAL ${rubroNombre}:</td>`;
        if (columnaIds.length > 0) {
            columnaIds.forEach(cid => {
                html += `<td class="text-center">$ ${(subtotales[cid] || 0).toLocaleString('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>`;
            });
        } else {
            html += `<td class="text-center">$ ${subtotalSinCol.toLocaleString('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>`;
        }
        html += `</tr></tbody></table>`;
    }

    // Total general
    const columnaLookupGlobal = {};
    Object.values(window.columnasPorRubro || {}).forEach(cols => {
        cols.forEach(c => { columnaLookupGlobal[c.val] = c; });
    });
    const colsGlobales = Object.keys(totalesGeneralesPorColumna).filter(k => k !== 'default');
    if (colsGlobales.length > 0) {
        const { anchoConcepto, anchoColumna } = calcularAnchosColumnas(colsGlobales.length);
        html += `
            <table class="table table-bordered mb-0" style="width: 100%; table-layout: fixed;">
                <thead>
                    <tr class="fw-bold table-active border-2" style="background-color: #e9ecef;">
                        <th class="text-center" style="width: ${anchoConcepto};">TOTAL ESTIMADO GENERAL:</th>`;
        colsGlobales.forEach(cid => {
            html += `<th class="text-center" style="width: ${anchoColumna};">$ ${(totalesGeneralesPorColumna[cid] || 0).toLocaleString('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</th>`;
        });
        html += `</tr></thead></table>`;
    } else if (totalesGeneralesPorColumna['default'] !== undefined) {
        html += `
            <table class="table table-bordered mb-0" style="width: 100%;">
                <thead>
                    <tr class="fw-bold table-active border-2" style="background-color: #e9ecef;">
                        <th class="text-center">TOTAL ESTIMADO GENERAL:</th>
                        <th class="text-center">$ ${totalesGeneralesPorColumna['default'].toLocaleString('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</th>
                    </tr>
                </thead>
            </table>`;
    }

    contenedorMatriz.innerHTML = html;
}

// ==========================================
// INICIALIZACIÓN DE EVENTOS
// ==========================================
document.addEventListener('DOMContentLoaded', () => {
    const formLiquidacion = document.getElementById('form-liquidacion');
    const selectConsorcio = document.getElementById('select-consorcio');
    if (!formLiquidacion || !selectConsorcio) return;

    calcularFechasSugeridas();

    if (selectConsorcio.value) {
        alSeleccionarConsorcio(selectConsorcio.value);
    } else {
        ['admin_razon', 'admin_nombre', 'admin_domicilio', 'admin_fiscal',
         'admin_cuit', 'admin_rpa', 'admin_telefono', 'admin_mail'].forEach(id => {
            setValorInput(id, '-');
        });
        sincronizarVistaPrevia();
    }

    agregarFilaGasto();

    formLiquidacion.addEventListener('input', (e) => {
        if (e.target.matches('.input-concepto, .input-monto, #fecha_cierre, #fecha_vencimiento_1, #admin_razon, #admin_nombre, #admin_domicilio, #admin_fiscal, #admin_cuit, #admin_rpa, #admin_telefono, #admin_mail')) {
            sincronizarVistaPrevia();
        }
    });

    formLiquidacion.addEventListener('change', (e) => {
        if (e.target.matches('.select-tipo, .select-rubro, .select-grupo, #fecha_cierre, #fecha_vencimiento_1')) {
            sincronizarVistaPrevia();
        }
    });

    selectConsorcio.addEventListener('change', (e) => alSeleccionarConsorcio(e.target.value));
    document.getElementById('select-mes').addEventListener('change', actualizarFechasYVista);
    document.getElementById('select-anio').addEventListener('change', actualizarFechasYVista);
    ['fecha_cierre', 'fecha_vencimiento_1'].forEach(id => {
        const el = document.getElementById(id);
        el.addEventListener('input', sincronizarVistaPrevia);
        el.addEventListener('change', sincronizarVistaPrevia);
    });
});



function autoGenerarFilasPersonal(consorcioId) {
    const tbody = document.getElementById('body-gastos');
    if (!tbody) return false;

    const nuevoId = String(consorcioId);

    // --- 1. Si venimos de otro consorcio auto-generado, evaluar si hay que preguntar ---
    if (window._autogenConsorcio && window._autogenConsorcio !== nuevoId) {
        const filas = tbody.querySelectorAll('tr.fila-gasto');
        const tieneDatos = Array.from(filas).some(f =>
            (f.querySelector('.input-monto')?.value || '').trim() !== '' ||
            (f.querySelector('.select-grupo')?.value || '') !== ''
        );

        if (tieneDatos) {
            const ok = confirm(
                'Vas a cambiar de consorcio y se van a perder los gastos que cargaste. ¿Continuar?'
            );
            if (!ok) {
                // Revertimos el select al consorcio anterior
                document.getElementById('select-consorcio').value = window._autogenConsorcio;
                return false;
            }
        }

        // El usuario aceptó o no había datos: borramos y seguimos
        tbody.replaceChildren();
        window._autogenConsorcio = null;
    }

    // --- 2. Ahora generamos las filas del nuevo consorcio ---
    const data = (window.personalPorConsorcio || {})[nuevoId];
    if (!data || !data.items || !data.items.length || !data.rubro_id) {
        return false;
    }

    tbody.replaceChildren();
    data.items.forEach(item => {
        agregarFilaGasto(item.concepto, item.tipo, data.rubro_id, '', '');
    });
    window._autogenConsorcio = nuevoId;
    return true;
}