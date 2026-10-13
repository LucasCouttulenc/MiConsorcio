document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-notificaciones]').forEach((contenedor) => {
        const boton = contenedor.querySelector('[data-notificaciones-toggle]');
        const panel = contenedor.querySelector('[data-notificaciones-panel]');
        if (!boton || !panel) return;

        const cerrar = () => {
            panel.hidden = true;
            panel.classList.remove('portal-notificaciones-panel-flotante');
            panel.style.removeProperty('left');
            panel.style.removeProperty('top');
            panel.style.removeProperty('width');
            contenedor.appendChild(panel);
            boton.setAttribute('aria-expanded', 'false');
        };

        const abrir = () => {
            document.body.appendChild(panel);
            panel.hidden = false;
            panel.classList.add('portal-notificaciones-panel-flotante');

            const botonRect = boton.getBoundingClientRect();
            const sidebar = contenedor.closest('.contenedor-sidebar');
            const bordeSidebar = sidebar ? sidebar.getBoundingClientRect().right : botonRect.right;
            const espacioDerecha = window.innerWidth - bordeSidebar - 24;
            const abrirALaDerecha = espacioDerecha >= 220;
            const ancho = Math.max(180, Math.min(350, abrirALaDerecha ? espacioDerecha : bordeSidebar - 24));
            const izquierda = abrirALaDerecha ? bordeSidebar + 8 : Math.max(16, bordeSidebar - ancho - 8);
            const arriba = Math.max(16, Math.min(botonRect.top, window.innerHeight - panel.offsetHeight - 16));
            panel.style.width = `${ancho}px`;
            panel.style.left = `${izquierda}px`;
            panel.style.top = `${arriba}px`;
            boton.setAttribute('aria-expanded', 'true');
        };

        boton.addEventListener('click', (evento) => {
            evento.stopPropagation();
            if (panel.hidden) abrir();
            else cerrar();
        });

        document.addEventListener('click', (evento) => {
            if (!contenedor.contains(evento.target) && !panel.contains(evento.target)) cerrar();
        });

        document.addEventListener('keydown', (evento) => {
            if (evento.key === 'Escape') {
                cerrar();
                boton.focus();
            }
        });
    });
});
