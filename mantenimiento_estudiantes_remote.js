let currentPage = 1;
const rowsPerPage = 25;

function normalizeCedula(input) {
    return (input || "").replace(/[^0-9A-Za-z]/g, "");
}

function allRows() {
    return Array.from(document.querySelectorAll("#studentsTable tbody tr"));
}

function filteredRows() {
    return allRows().filter((row) => row.dataset.filteredOut !== "1");
}

function updateCounter() {
    const counter = document.getElementById("rowsCounter");
    if (counter) counter.textContent = `${filteredRows().length} registros`;
}

function renderPagination() {
    const rows = filteredRows();
    const totalPages = Math.max(1, Math.ceil(rows.length / rowsPerPage));
    if (currentPage > totalPages) currentPage = totalPages;
    if (currentPage < 1) currentPage = 1;

    const start = (currentPage - 1) * rowsPerPage;
    const end = start + rowsPerPage;

    allRows().forEach((row) => {
        row.style.display = "none";
    });

    rows.forEach((row, idx) => {
        row.style.display = idx >= start && idx < end ? "" : "none";
    });

    const info = document.getElementById("pageInfo");
    const prev = document.getElementById("prevPageBtn");
    const next = document.getElementById("nextPageBtn");
    if (info) info.textContent = `Pagina ${currentPage} de ${totalPages}`;
    if (prev) prev.disabled = currentPage <= 1;
    if (next) next.disabled = currentPage >= totalPages;
}

function filterTable() {
    const input = document.getElementById("searchInput");
    const filter = (input?.value || "").toUpperCase();

    allRows().forEach((row) => {
        const text = (row.textContent || "").toUpperCase();
        row.dataset.filteredOut = text.includes(filter) ? "0" : "1";
    });

    currentPage = 1;
    updateCounter();
    renderPagination();
}

function abrirModalEdicionDesdeBoton(btn) {
    const title = document.getElementById("studentModalTitle");
    const saveBtn = document.getElementById("studentModalSaveBtn");
    if (title) title.textContent = "Editar estudiante";
    if (saveBtn) saveBtn.textContent = "Guardar cambios";
    document.getElementById("modal_id_estudiante").value = btn.dataset.id || "";
    document.getElementById("modal_nombre").value = btn.dataset.nombre || "";
    document.getElementById("modal_apellido1").value = btn.dataset.apellido1 || "";
    document.getElementById("modal_apellido2").value = btn.dataset.apellido2 || "";
    document.getElementById("modal_nivel").value = btn.dataset.nivel || "";
    document.getElementById("modal_cedula").value = normalizeCedula(btn.dataset.cedula || "");

    showModalSafe("editStudentModal");
}

function abrirModalCreacion() {
    const title = document.getElementById("studentModalTitle");
    const saveBtn = document.getElementById("studentModalSaveBtn");
    if (title) title.textContent = "Agregar estudiante";
    if (saveBtn) saveBtn.textContent = "Guardar estudiante";

    document.getElementById("modal_id_estudiante").value = "";
    document.getElementById("modal_nombre").value = "";
    document.getElementById("modal_apellido1").value = "";
    document.getElementById("modal_apellido2").value = "";
    document.getElementById("modal_nivel").value = "";
    document.getElementById("modal_cedula").value = "";

    showModalSafe("editStudentModal");
}

function showModalSafe(modalId) {
    const modalEl = document.getElementById(modalId);
    if (!modalEl) return;

    if (window.bootstrap && typeof window.bootstrap.Modal === "function") {
        const modal = new window.bootstrap.Modal(modalEl);
        modal.show();
        return;
    }

    // Fallback si bootstrap JS no está disponible
    modalEl.style.display = "block";
    modalEl.classList.add("show");
    modalEl.removeAttribute("aria-hidden");
    document.body.classList.add("modal-open");

    let backdrop = document.querySelector(".modal-backdrop");
    if (!backdrop) {
        backdrop = document.createElement("div");
        backdrop.className = "modal-backdrop fade show";
        document.body.appendChild(backdrop);
    }
}

document.addEventListener("DOMContentLoaded", function () {
    const modalCedula = document.getElementById("modal_cedula");
    if (modalCedula) {
        modalCedula.addEventListener("input", function () {
            this.value = normalizeCedula(this.value);
        });
    }

    const prev = document.getElementById("prevPageBtn");
    const next = document.getElementById("nextPageBtn");
    if (prev) {
        prev.addEventListener("click", function () {
            currentPage -= 1;
            renderPagination();
        });
    }
    if (next) {
        next.addEventListener("click", function () {
            currentPage += 1;
            renderPagination();
        });
    }

    document.querySelectorAll(".btn-edit-student").forEach((btn) => {
        btn.addEventListener("click", function () {
            abrirModalEdicionDesdeBoton(btn);
        });
    });

    const btnCreate = document.getElementById("btnOpenCreateModal");
    if (btnCreate) {
        btnCreate.addEventListener("click", abrirModalCreacion);
    }

    document.querySelectorAll('#editStudentModal [data-bs-dismiss="modal"]').forEach((btn) => {
        btn.addEventListener("click", function () {
            hideModalSafe("editStudentModal");
        });
    });

    allRows().forEach((row) => {
        row.dataset.filteredOut = "0";
    });

    updateCounter();
    renderPagination();
});

function hideModalSafe(modalId) {
    const modalEl = document.getElementById(modalId);
    if (!modalEl) return;
    if (window.bootstrap && typeof window.bootstrap.Modal === "function") {
        const instance = window.bootstrap.Modal.getInstance(modalEl);
        if (instance) instance.hide();
        return;
    }
    modalEl.classList.remove("show");
    modalEl.style.display = "none";
    modalEl.setAttribute("aria-hidden", "true");
    document.body.classList.remove("modal-open");
    document.querySelectorAll(".modal-backdrop").forEach((el) => el.remove());
}
