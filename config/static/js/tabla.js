// Funcion para agregar flechas
function agregarFlechasDeOrdenamiento() {
    // Obtener todos los elementos <th> en el encabezado de la tabla (Solo obtener los que tienen la clase orderable)
    const headers = document.querySelectorAll(".tabla thead th.orderable");
    // Iterar headers
    headers.forEach(header => {
        // Obtener el link dentro del header
        const link = header.querySelector("a");
        // Chequear la clase y agregar la flecha correspondiente
        if (header.classList.contains("asc")) {
            link.innerHTML += ' ↑'
        } else if (header.classList.contains("desc")) {
            link.innerHTML += ' ↓'
        }
    });
}

// Ejecutar funcion al cargar la pagina
agregarFlechasDeOrdenamiento();

// Select2 emite el cambio mediante jQuery, por eso escuchamos con jQuery.
$(document).on("change", ".tabla__filtro form select", function () {
    if (this.form) this.form.requestSubmit();
});
