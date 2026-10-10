// Conecta el formulario original con el guardado de borradores.
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('form-liquidacion');
    const inicial = JSON.parse(document.getElementById('datos-iniciales').textContent);
    const estado = document.getElementById('estado-guardado');
    const idBorrador = document.getElementById('liquidacion-id');
    let temporizador;
    let guardadoEnCurso;
    let pendiente = false;
    let finalizando = false;

    if (inicial.consorcio) {
        const consorcio = document.getElementById('select-consorcio');
        consorcio.value = inicial.consorcio;
        alSeleccionarConsorcio(consorcio.value);
        document.getElementById('select-mes').value = inicial.mes;
        document.getElementById('select-anio').value = inicial.anio;
        document.getElementById('fecha_cierre').value = inicial.fecha_cierre || '';
        document.getElementById('fecha_vencimiento_1').value = inicial.fecha_vencimiento_1 || '';

        Object.entries(inicial.administracion || {}).forEach(([id, valor]) => {
            const campo = document.getElementById(id);
            if (campo) campo.value = valor;
        });

        document.getElementById('body-gastos').replaceChildren();
        (inicial.gastos || []).forEach(gasto => {
            // Cada gasto guardado tiene: concepto, tipo, rubro, grupo, monto
            agregarFilaGasto(
                gasto.concepto || '',
                gasto.tipo || 'ordinario',
                gasto.rubro || '',
                gasto.grupo || '',
                gasto.monto || ''
            );
        });
        if (!inicial.gastos?.length) agregarFilaGasto();
        sincronizarVistaPrevia();
        estado.textContent = 'Borrador cargado. Los cambios se guardan automáticamente.';
    }

    function completarDatos() {
        const gastos = [...document.querySelectorAll('#body-gastos tr.fila-gasto')].map(fila => ({
            fila: fila.id,
            concepto: fila.querySelector('.input-concepto').value,
            tipo: fila.querySelector('.input-tipo-hidden').value,
            rubro: fila.querySelector('.select-rubro').value,
            grupo: fila.querySelector('.select-grupo').value,
            monto: fila.querySelector('.input-monto').value,
        }));
        document.getElementById('gastos-json').value = JSON.stringify(gastos);
    }

    function periodoCompleto() {
        const anio = Number(document.getElementById('select-anio').value);
        return document.getElementById('select-consorcio').value &&
            document.getElementById('select-mes').value && anio >= 2000 && anio <= 2100;
    }

    async function guardar() {
        if (finalizando || !periodoCompleto()) return;
        if (guardadoEnCurso) { pendiente = true; return guardadoEnCurso; }
        completarDatos();
        estado.textContent = 'Guardando borrador…';
        guardadoEnCurso = fetch(form.dataset.autosaveUrl, {
            method: 'POST', body: new FormData(form), credentials: 'same-origin',
        }).then(async respuesta => {
            const resultado = await respuesta.json();
            if (respuesta.status === 409 && resultado.url) {
                const enlace = document.createElement('a');
                enlace.href = resultado.url;
                enlace.textContent = 'Abrir borrador existente';
                estado.replaceChildren(document.createTextNode(`${resultado.error} `), enlace);
                return;
            }
            if (!respuesta.ok) throw new Error(resultado.error || 'No se pudo guardar.');
            idBorrador.value = resultado.id;
            history.replaceState(null, '', resultado.url);
            estado.textContent = 'Borrador guardado.';
        }).catch(error => {
            estado.textContent = `No se pudo guardar: ${error.message}`;
        }).finally(() => {
            guardadoEnCurso = null;
            if (pendiente && !finalizando) { pendiente = false; guardar(); }
        });
        return guardadoEnCurso;
    }

    function programarGuardado() {
        clearTimeout(temporizador);
        temporizador = setTimeout(guardar, 900);
    }
    form.addEventListener('input', programarGuardado);
    form.addEventListener('change', programarGuardado);
    form.addEventListener('click', event => {
        if (event.target.closest('button[type="button"]')) setTimeout(programarGuardado, 0);
    });
    form.addEventListener('submit', async event => {
        event.preventDefault();
        clearTimeout(temporizador);
        finalizando = true;
        if (guardadoEnCurso) await guardadoEnCurso;
        completarDatos();
        form.submit();
    });
});