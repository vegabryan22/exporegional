function openCandidateModalForCreate() {
    $('#candidateModalTitle').text('Agregar candidato');
    $('#btn-guardar').text('Guardar candidato');
    $('#candidato_id').val('');
    $('#nombre').val('');
    $('#imagen').val('');
    const modal = new bootstrap.Modal(document.getElementById('candidateModal'));
    modal.show();
}

function openCandidateModalForEdit(id, nombre) {
    $('#candidateModalTitle').text('Editar candidato');
    $('#btn-guardar').text('Actualizar candidato');
    $('#candidato_id').val(id);
    $('#nombre').val(nombre);
    $('#imagen').val('');
    const modal = new bootstrap.Modal(document.getElementById('candidateModal'));
    modal.show();
}

$(document).ready(function() {
    $('#btnOpenCreateCandidateModal').on('click', function() {
        openCandidateModalForCreate();
    });

    $('.actualizar-btn').on('click', function() {
        const id = $(this).data('id');
        const nombre = $(this).data('nombre');
        openCandidateModalForEdit(id, nombre);
    });
});
