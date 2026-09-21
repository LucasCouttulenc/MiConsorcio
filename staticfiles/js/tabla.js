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