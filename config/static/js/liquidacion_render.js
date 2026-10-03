// ==========================================
// RENDERIZADO DE TAGS Y SELECTORES
// ==========================================
function renderizarListaSubtipos() {
    const consorcioId = getConsorcioActualId();
    const contenedor = document.getElementById('lista-subtipos-tags');
    if (!contenedor) return;

    contenedor.innerHTML = '';
    const lista = (consorcioId && window.subtiposPorConsorcio[consorcioId]) ? window.subtiposPorConsorcio[consorcioId] : [];

    lista.forEach((subtipo, idx) => {
        const tag = document.createElement('span');
        tag.className = 'badge bg-secondary';
        tag.innerHTML = `
            ${subtipo}
            <button type="button" class="btn-close" onclick="eliminarSubtipo(${idx})">✕</button>
        `;
        contenedor.appendChild(tag);
    });
}

function actualizarSelectoresSubtipos() {
    const consorcioId = getConsorcioActualId();
    const lista = (consorcioId && window.subtiposPorConsorcio[consorcioId]) ? window.subtiposPorConsorcio[consorcioId] : [];
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

function renderizarListaGrupos() {
    const consorcioId = getConsorcioActualId();
    const contenedor = document.getElementById('lista-grupos-tags');
    if (!contenedor) return;

    contenedor.innerHTML = '';
    const lista = (consorcioId && window.gruposPorConsorcio[consorcioId]) ? window.gruposPorConsorcio[consorcioId] : [];

    lista.forEach((grupo, idx) => {
        const tag = document.createElement('span');
        tag.className = 'badge';
        tag.style.backgroundColor = '#6f42c1';
        tag.innerHTML = `
            ${grupo.nombre}
            <button type="button" class="btn-close" onclick="eliminarGrupo(${idx})">✕</button>
        `;
        contenedor.appendChild(tag);
    });
}

function actualizarSelectoresGrupos() {
    const consorcioId = getConsorcioActualId();
    let lista = (consorcioId && window.gruposPorConsorcio[consorcioId]) ? window.gruposPorConsorcio[consorcioId] : [];
    if (!lista.length) lista = [{val:'general',nombre:'General'},{val:'parcial',nombre:'Parcial'},{val:'particular',nombre:'Particular'}];
    const selects = document.querySelectorAll('.select-grupo');

    selects.forEach(select => {
        const valActual = select.value || 'general';
        let html = '';
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
// RENDERIZADO Y SINCRONIZACIÓN DE VISTA PREVIA
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
        const val = document.getElementById(inputId).value.trim();
        document.getElementById(lblId).textContent = val !== '' ? val : '-';
    });

    sincronizarTablaGastosVistaPrevia();
}

function alSeleccionarConsorcio(consorcioId) {
    renderizarListasGestion();

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

    refrescarRecuadros();
    sincronizarVistaPrevia();
}

function sincronizarTablaGastosVistaPrevia() {
    const consorcioId = getConsorcioActualId();
    const filas = document.querySelectorAll('#body-gastos tr');
    const contenedorMatriz = document.getElementById('pv-tabla-gastos-matriz');
    
    if (!contenedorMatriz) return;

    const gruposConsorcio = (consorcioId && window.gruposPorConsorcio[consorcioId]) ? window.gruposPorConsorcio[consorcioId] : [];

    if (!consorcioId) {
        const { anchoConcepto, anchoColumna } = calcularAnchosColumnas(1);
        contenedorMatriz.innerHTML = `
            <table class="table table-bordered mb-0" style="width: 100% !important; table-layout: fixed;">
                <thead class="table-secondary">
                    <tr>
                        <th class="text-start" style="width: ${anchoConcepto};">Concepto / Detalle</th>
                        <th class="text-center" style="width: ${anchoColumna};">Monto ($)</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td colspan="2" class="text-center text-muted py-3">
                            Seleccione un consorcio para ver las columnas
                        </td>
                    </tr>
                </tbody>
            </table>
        `;
        return;
    }

    // 1. Agrupar gastos cargados por Subtipo
    const gastosPorSubtipo = {};

   filas.forEach(fila => {
        const concepto = fila.querySelector('.input-concepto')?.value || '';
        const subtipoSelect = fila.querySelector('.select-subtipo');
        const subtipoVal = subtipoSelect?.value || '';
        const subtipo = subtipoVal.trim() !== '' ? subtipoVal.trim().toUpperCase() : 'GASTOS GENERALES';
        const grupoSelect = fila.querySelector('.select-grupo');
        const grupoVal = grupoSelect?.value;
        
        // Soporte para comas y puntos en el monto
        const montoRaw = fila.querySelector('.input-monto')?.value || '0';
        const monto = parseFloat(montoRaw.replace(',', '.')) || 0;

        if (concepto.trim() !== '' || monto > 0) {
            if (!gastosPorSubtipo[subtipo]) {
                gastosPorSubtipo[subtipo] = [];
            }
            gastosPorSubtipo[subtipo].push({ concepto, grupoVal, monto });
        }
    });

    let htmlContenedor = '';
    let hayGastos = false;
    const totalesGeneralesPorGrupo = {};

    // 2. Generar cada Subtipo como una TABLA INDEPENDIENTE adaptativa
    for (const [subtipo, listaGastos] of Object.entries(gastosPorSubtipo)) {
        hayGastos = true;

        const gruposUsadosKeys = new Set(
            listaGastos.map(item => item.grupoVal).filter(Boolean)
        );

        let gruposDelSubtipo = [];
        if (gruposUsadosKeys.size > 0) {
            gruposDelSubtipo = gruposConsorcio.filter(g => gruposUsadosKeys.has(g.val));
        } else {
            gruposDelSubtipo = [...gruposConsorcio];
        }

        const tieneColumnas = gruposDelSubtipo.length > 0;
        const colCount = tieneColumnas ? gruposDelSubtipo.length : 1;

        const { anchoConcepto, anchoColumna } = calcularAnchosColumnas(colCount);

        const subtotalesSubtipo = {};
        if (tieneColumnas) {
            gruposDelSubtipo.forEach(g => subtotalesSubtipo[g.val] = 0);
        } else {
            subtotalesSubtipo['default'] = 0;
        }

        htmlContenedor += `
            <table class="table table-bordered mb-3 align-middle" style="width: 100% !important; table-layout: fixed;">
                <thead>
                    <tr style="background-color: var(--gl-blue-header, #1b365d); color: #ffffff;">
                        <th colspan="${colCount + 1}" class="text-center text-uppercase fw-bold py-1">
                            ${subtipo}
                        </th>
                    </tr>
                    <tr class="table-secondary text-center small">
                        <th class="text-start" style="width: ${anchoConcepto};">Concepto / Detalle</th>`;

        if (tieneColumnas) {
            gruposDelSubtipo.forEach(g => {
                htmlContenedor += `<th class="text-center" style="width: ${anchoColumna};">${g.nombre}</th>`;
            });
        } else {
            htmlContenedor += `<th class="text-center" style="width: ${anchoColumna};">Monto ($)</th>`;
        }

        htmlContenedor += `</tr></thead><tbody>`;

        // Filas del subtipo
        listaGastos.forEach(item => {
            htmlContenedor += `<tr><td class="text-start ps-3 text-truncate" style="width: ${anchoConcepto};" title="${item.concepto}">${item.concepto || '<em>(Sin concepto)</em>'}</td>`;
            
            if (tieneColumnas) {
                gruposDelSubtipo.forEach(g => {
                    if (item.grupoVal === g.val) {
                        subtotalesSubtipo[g.val] += item.monto;
                        totalesGeneralesPorGrupo[g.val] = (totalesGeneralesPorGrupo[g.val] || 0) + item.monto;
                        htmlContenedor += `<td class="text-end fw-bold text-dark" style="width: ${anchoColumna};">$ ${item.monto.toLocaleString('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>`;
                    } else {
                        htmlContenedor += `<td class="text-center text-muted small" style="width: ${anchoColumna};">-</td>`;
                    }
                });
            } else {
                subtotalesSubtipo['default'] += item.monto;
                totalesGeneralesPorGrupo['default'] = (totalesGeneralesPorGrupo['default'] || 0) + item.monto;
                htmlContenedor += `<td class="text-end fw-bold text-dark" style="width: ${anchoColumna};">$ ${item.monto.toLocaleString('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>`;
            }
            
            htmlContenedor += `</tr>`;
        });

        // Subtotal del Subtipo
        htmlContenedor += `
            <tr class="fw-bold table-active" style="background-color: #f8f9fa;">
                <td class="text-start ps-3" style="width: ${anchoConcepto};">SUBTOTAL ${subtipo}:</td>`;

        if (tieneColumnas) {
            gruposDelSubtipo.forEach(g => {
                const subTot = subtotalesSubtipo[g.val] || 0;
                htmlContenedor += `<td class="text-end" style="width: ${anchoColumna};">$ ${subTot.toLocaleString('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>`;
            });
        } else {
            const subTot = subtotalesSubtipo['default'] || 0;
            htmlContenedor += `<td class="text-end" style="width: ${anchoColumna};">$ ${subTot.toLocaleString('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>`;
        }

        htmlContenedor += `</tr></tbody></table>`;
    }

    if (!hayGastos) {
        const colCount = gruposConsorcio.length > 0 ? gruposConsorcio.length : 1;
        const { anchoConcepto, anchoColumna } = calcularAnchosColumnas(colCount);

        htmlContenedor = `
            <table class="table table-bordered mb-0" style="width: 100% !important; table-layout: fixed;">
                <thead class="table-secondary">
                    <tr>
                        <th class="text-start" style="width: ${anchoConcepto};">Concepto / Detalle</th>`;
        if (gruposConsorcio.length > 0) {
            gruposConsorcio.forEach(g => {
                htmlContenedor += `<th class="text-center" style="width: ${anchoColumna};">${g.nombre}</th>`;
            });
        } else {
            htmlContenedor += `<th class="text-center" style="width: ${anchoColumna};">Monto ($)</th>`;
        }
        htmlContenedor += `</tr></thead>
            <tbody>
                <tr>
                    <td colspan="${colCount + 1}" class="text-center text-muted py-3">
                        Sin gastos ingresados
                    </td>
                </tr>
            </tbody>
        </table>`;
    } else {
        // 3. Tabla para TOTAL ESTIMADO GENERAL
        const gruposGlobalesActivos = gruposConsorcio.filter(g => totalesGeneralesPorGrupo[g.val] !== undefined);
        const colCountGlobal = gruposGlobalesActivos.length > 0 ? gruposGlobalesActivos.length : 1;
        const { anchoConcepto, anchoColumna } = calcularAnchosColumnas(colCountGlobal);

        if (gruposGlobalesActivos.length > 0) {
            htmlContenedor += `
                <table class="table table-bordered mb-0" style="width: 100% !important; table-layout: fixed;">
                    <thead>
                        <tr class="fw-bold table-active border-2" style="background-color: #e9ecef;">
                            <th class="text-start" style="width: ${anchoConcepto};">TOTAL ESTIMADO GENERAL:</th>`;
            
            gruposGlobalesActivos.forEach(g => {
                const tot = totalesGeneralesPorGrupo[g.val] || 0;
                htmlContenedor += `<th class="text-end" style="width: ${anchoColumna};">$ ${tot.toLocaleString('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</th>`;
            });

            htmlContenedor += `</tr></thead></table>`;
        } else if (totalesGeneralesPorGrupo['default'] !== undefined) {
            htmlContenedor += `
                <table class="table table-bordered mb-0" style="width: 100% !important; table-layout: fixed;">
                    <thead>
                        <tr class="fw-bold table-active border-2" style="background-color: #e9ecef;">
                            <th class="text-start" style="width: ${anchoConcepto};">TOTAL ESTIMADO GENERAL:</th>
                            <th class="text-end" style="width: ${anchoColumna};">$ ${totalesGeneralesPorGrupo['default'].toLocaleString('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</th>
                        </tr>
                    </thead>
                </table>`;
        }
    }

    contenedorMatriz.innerHTML = htmlContenedor;
}

// ==========================================
// INICIALIZACIÓN DE EVENTOS
// ==========================================
document.addEventListener('DOMContentLoaded', () => {
    const formLiquidacion = document.getElementById('form-liquidacion');
    const selectConsorcio = document.getElementById('select-consorcio');

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
        if (e.target.matches('.select-tipo, .select-subtipo, .select-grupo, #fecha_cierre, #fecha_vencimiento_1')) {
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