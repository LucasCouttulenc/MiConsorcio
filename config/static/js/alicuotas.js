/**
 * calcula en vivo la suma de alícuotas.
 */
(function () {
    const form = document.querySelector('.form-alicuotas');
    if (!form) return;

    const inputs = form.querySelectorAll('.input-alicuota');
    const pie = document.getElementById('pie-suma');
    if (!inputs.length || !pie) return;

    function recalcular() {
        let total = 0;
        inputs.forEach((inp) => {
            const v = parseFloat((inp.value || '').replace(',', '.'));
            if (!isNaN(v)) total += v;
        });
        const redondeado = Math.round(total * 10000) / 10000;
        pie.textContent = redondeado.toFixed(4) + '%';
        pie.classList.toggle('suma-ok', redondeado === 100);
        pie.classList.toggle('suma-mal', redondeado !== 100);
    }

    inputs.forEach((inp) => inp.addEventListener('input', recalcular));
}
)();