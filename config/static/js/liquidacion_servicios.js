// ==========================================
// SERVICIOS RECURRENTES
// Propone como filas los servicios que corresponden al consorcio y período
// elegidos (ej: fumigación trimestral). El admin los confirma, edita o borra.
// ==========================================

function periodoAMeses(periodo) {
    const [anio, mes] = periodo.split('-').map(Number);
    return anio * 12 + mes - 1;
}

// Misma regla que ServicioRecurrente.corresponde_en en gastos/models.py
function servicioCorrespondeEn(servicio, periodo) {
    const actual = periodoAMeses(periodo);
    const inicio = periodoAMeses(servicio.inicio);
    if (actual < inicio) return false;
    if (servicio.fin && actual > periodoAMeses(servicio.fin)) return false;
    return (actual - inicio) % servicio.frecuencia === 0;
}

function sincronizarServiciosRecurrentes() {
    const tbody = document.getElementById('body-gastos');
    const consorcioId = document.getElementById('select-consorcio')?.value;
    const mes = document.getElementById('select-mes')?.value;
    const anio = document.getElementById('select-anio')?.value;
    if (!tbody) return;

    const periodo = consorcioId && mes && anio ? `${anio}-${String(mes).padStart(2, '0')}` : '';
    const servicios = periodo ? ((window.serviciosPorConsorcio || {})[consorcioId] || []) : [];
    const corresponden = servicios.filter(s => servicioCorrespondeEn(s, periodo));
    const ids = new Set(corresponden.map(s => String(s.id)));

    // Saca las filas propuestas que ya no corresponden (cambió el consorcio o el período)
    tbody.querySelectorAll('tr.fila-gasto[data-servicio]').forEach(fila => {
        if (!ids.has(fila.dataset.servicio)) fila.remove();
    });

    // Agrega las que faltan, sin duplicar
    corresponden.forEach(s => {
        if (tbody.querySelector(`tr.fila-gasto[data-servicio="${s.id}"]`)) return;
        // Si solo hay una fila vacía (la inicial), se reemplaza
        const filas = tbody.querySelectorAll('tr.fila-gasto');
        if (filas.length === 1 && !filas[0].dataset.servicio &&
            !filas[0].querySelector('.input-concepto-hidden').value.trim() &&
            !filas[0].querySelector('.input-monto-hidden').value.trim()) {
            filas[0].remove();
        }

        agregarFilaGasto(s.concepto, s.tipo, s.rubro_id, s.columna_id, s.monto, String(s.id));
    });

    if (typeof sincronizarVistaPrevia === 'function') sincronizarVistaPrevia();
}
