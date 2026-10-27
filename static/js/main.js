/* ==========================================================================
   SGA · Sistema de Gestión Agrícola
   Interacciones del frontend (vanilla JS, sin dependencias)
   ========================================================================== */
(function () {
    "use strict";

    /* ----------------------------------------------------------------------
       Barra lateral en móviles
       ---------------------------------------------------------------------- */
    const sidebar = document.querySelector(".sidebar");
    const respaldo = document.querySelector(".respaldo-lateral");
    const botonMenu = document.getElementById("botonMenu");

    function alternarMenu(abrir) {
        if (!sidebar) return;
        const visible = typeof abrir === "boolean" ? abrir : !sidebar.classList.contains("abierto");
        sidebar.classList.toggle("abierto", visible);
        if (respaldo) respaldo.classList.toggle("visible", visible);
    }

    if (botonMenu) botonMenu.addEventListener("click", () => alternarMenu());
    if (respaldo) respaldo.addEventListener("click", () => alternarMenu(false));
    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") {
            alternarMenu(false);
            cerrarModales();
        }
    });

    /* ----------------------------------------------------------------------
       Alertas flash: cierre manual y ocultado automático
       ---------------------------------------------------------------------- */
    document.querySelectorAll(".alerta").forEach((alerta, indice) => {
        const cerrar = alerta.querySelector(".alerta__cerrar");
        if (cerrar) {
            cerrar.addEventListener("click", () => {
                alerta.style.transition = "opacity .25s ease, transform .25s ease";
                alerta.style.opacity = "0";
                alerta.style.transform = "translateY(-8px)";
                setTimeout(() => alerta.remove(), 260);
            });
        }
        // Los mensajes de éxito/información desaparecen solos
        if (alerta.classList.contains("alerta--success") || alerta.classList.contains("alerta--info")) {
            setTimeout(() => cerrar && cerrar.click(), 6000 + indice * 400);
        }
    });

    /* ----------------------------------------------------------------------
       Modales genéricos (atributos data-modal-abrir / data-modal-cerrar)
       ---------------------------------------------------------------------- */
    function abrirModal(id) {
        const modal = document.getElementById(id);
        if (!modal) return;
        modal.classList.add("abierto");
        document.body.classList.add("modal-abierto");
        const primerCampo = modal.querySelector("input:not([type=hidden]), select, textarea");
        if (primerCampo) setTimeout(() => primerCampo.focus(), 120);
    }

    function cerrarModales() {
        document.querySelectorAll(".modal.abierto").forEach((modal) => modal.classList.remove("abierto"));
        document.body.classList.remove("modal-abierto");
    }

    document.querySelectorAll("[data-modal-abrir]").forEach((disparador) => {
        disparador.addEventListener("click", (e) => {
            e.preventDefault();
            abrirModal(disparador.getAttribute("data-modal-abrir"));
        });
    });

    document.querySelectorAll("[data-modal-cerrar]").forEach((boton) => {
        boton.addEventListener("click", (e) => {
            e.preventDefault();
            cerrarModales();
        });
    });

    document.querySelectorAll(".modal").forEach((modal) => {
        modal.addEventListener("click", (e) => {
            if (e.target === modal) cerrarModales();
        });
    });

    /* ----------------------------------------------------------------------
       Modal de tareas: modo crear / editar
       ---------------------------------------------------------------------- */
    const modalTarea = document.getElementById("modalTarea");
    const formTarea = document.getElementById("formTarea");

    function rellenar(elemento, valor) {
        if (elemento) elemento.value = valor == null ? "" : valor;
    }

    if (modalTarea && formTarea) {
        const tituloModal = document.getElementById("tituloModalTarea");
        const accionCrear = formTarea.getAttribute("data-accion-crear");

        document.querySelectorAll("[data-tarea-nueva]").forEach((boton) => {
            boton.addEventListener("click", (e) => {
                e.preventDefault();
                formTarea.reset();
                formTarea.setAttribute("action", accionCrear);
                rellenar(formTarea.querySelector('[name="fecha_inicio"]'), new Date().toISOString().slice(0, 10));
                rellenar(formTarea.querySelector('[name="estado"]'), "Pendiente");
                rellenar(formTarea.querySelector('[name="prioridad"]'), "Media");
                if (tituloModal) tituloModal.innerHTML = '<i class="fa-solid fa-plus"></i> Nueva tarea';
                abrirModal("modalTarea");
            });
        });

        document.querySelectorAll("[data-tarea-editar]").forEach((boton) => {
            boton.addEventListener("click", (e) => {
                e.preventDefault();
                let tarea;
                try {
                    tarea = JSON.parse(boton.getAttribute("data-tarea-editar"));
                } catch (err) {
                    return;
                }
                formTarea.reset();
                formTarea.setAttribute("action", tarea.accion);
                rellenar(formTarea.querySelector('[name="titulo"]'), tarea.titulo);
                rellenar(formTarea.querySelector('[name="descripcion"]'), tarea.descripcion);
                rellenar(formTarea.querySelector('[name="operario_id"]'), tarea.operario_id);
                rellenar(formTarea.querySelector('[name="lote"]'), tarea.lote);
                rellenar(formTarea.querySelector('[name="cultivo"]'), tarea.cultivo);
                rellenar(formTarea.querySelector('[name="prioridad"]'), tarea.prioridad);
                rellenar(formTarea.querySelector('[name="estado"]'), tarea.estado);
                rellenar(formTarea.querySelector('[name="fecha_inicio"]'), tarea.fecha_inicio);
                rellenar(formTarea.querySelector('[name="fecha_limite"]'), tarea.fecha_limite);
                if (tituloModal) {
                    tituloModal.innerHTML = '<i class="fa-solid fa-pen-to-square"></i> Editar tarea #' + tarea.id;
                }
                abrirModal("modalTarea");
            });
        });
    }

    /* ----------------------------------------------------------------------
       Modal de operarios: modo crear / editar
       ---------------------------------------------------------------------- */
    const modalOperario = document.getElementById("modalOperario");
    const formOperario = document.getElementById("formOperario");

    if (modalOperario && formOperario) {
        const tituloOperario = document.getElementById("tituloModalOperario");
        const accionCrearOp = formOperario.getAttribute("data-accion-crear");

        document.querySelectorAll("[data-operario-nuevo]").forEach((boton) => {
            boton.addEventListener("click", (e) => {
                e.preventDefault();
                formOperario.reset();
                formOperario.setAttribute("action", accionCrearOp);
                rellenar(formOperario.querySelector('[name="estado"]'), "Activo");
                if (tituloOperario) tituloOperario.innerHTML = '<i class="fa-solid fa-user-plus"></i> Nuevo operario';
                abrirModal("modalOperario");
            });
        });

        document.querySelectorAll("[data-operario-editar]").forEach((boton) => {
            boton.addEventListener("click", (e) => {
                e.preventDefault();
                let operario;
                try {
                    operario = JSON.parse(boton.getAttribute("data-operario-editar"));
                } catch (err) {
                    return;
                }
                formOperario.reset();
                formOperario.setAttribute("action", operario.accion);
                ["nombre", "documento", "telefono", "email", "cargo",
                 "estado", "fecha_ingreso", "observaciones"].forEach((campo) => {
                    rellenar(formOperario.querySelector('[name="' + campo + '"]'), operario[campo]);
                });
                if (tituloOperario) {
                    tituloOperario.innerHTML = '<i class="fa-solid fa-user-pen"></i> Editar operario';
                }
                abrirModal("modalOperario");
            });
        });
    }

    /* ----------------------------------------------------------------------
       Confirmación previa a acciones destructivas
       ---------------------------------------------------------------------- */
    document.querySelectorAll("form[data-confirmar]").forEach((formulario) => {
        formulario.addEventListener("submit", (e) => {
            const mensaje = formulario.getAttribute("data-confirmar") || "¿Confirmas esta acción?";
            if (!window.confirm(mensaje)) e.preventDefault();
        });
    });

    /* ----------------------------------------------------------------------
       Envío automático al cambiar un filtro del listado
       ---------------------------------------------------------------------- */
    document.querySelectorAll("form[data-autofiltro]").forEach((formulario) => {
        formulario.querySelectorAll("select").forEach((select) => {
            select.addEventListener("change", () => formulario.submit());
        });
    });

    /* ----------------------------------------------------------------------
       Medidores circulares: animación del valor inicial
       ---------------------------------------------------------------------- */
    document.querySelectorAll(".medidor").forEach((medidor) => {
        const valor = parseFloat(medidor.getAttribute("data-valor") || "0");
        medidor.style.setProperty("--valor", "0");
        requestAnimationFrame(() => {
            setTimeout(() => medidor.style.setProperty("--valor", String(valor)), 180);
        });
    });

    /* ----------------------------------------------------------------------
       Animación de barras de progreso al cargar
       ---------------------------------------------------------------------- */
    document.querySelectorAll(".progreso__barra, .barra-fila__fill").forEach((barra) => {
        const ancho = barra.style.width;
        barra.style.width = "0";
        setTimeout(() => { barra.style.width = ancho; }, 180);
    });
})();
