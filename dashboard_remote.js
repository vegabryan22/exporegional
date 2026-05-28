$(document).ready(function () {
    let candidateChart = null;
    let participationChart = null;

    function destroyCharts() {
        if (candidateChart) candidateChart.destroy();
        if (participationChart) participationChart.destroy();
    }

    function renderCharts(data) {
        destroyCharts();

        const candidateCtx = document.getElementById('candidateChart').getContext('2d');
        candidateChart = new Chart(candidateCtx, {
            type: 'bar',
            data: {
                labels: data.voting_closed ? data.candidates.map(c => c.nombre) : ['Oculto'],
                datasets: [{
                    label: data.voting_closed ? 'Votos por candidato' : 'Resultados ocultos',
                    data: data.voting_closed ? data.candidates.map(c => c.votos) : [0],
                    backgroundColor: 'rgba(54, 162, 235, 0.2)',
                    borderColor: 'rgba(54, 162, 235, 1)',
                    borderWidth: 1
                }]
            },
            options: { scales: { y: { beginAtZero: true } } }
        });

        const pCtx = document.getElementById('participationChart').getContext('2d');
        participationChart = new Chart(pCtx, {
            type: 'doughnut',
            data: {
                labels: ['Participacion', 'Abstencion'],
                datasets: [{
                    data: [data.participation.participantes, data.participation.abstencionistas],
                    backgroundColor: ['rgba(0,255,0,0.2)', 'rgba(255,0,0,0.2)'],
                    borderColor: ['rgba(255,255,255,1)', 'rgba(255,255,255,1)'],
                    borderWidth: 1
                }]
            }
        });
    }

    function fetchData() {
        $.get('/votaciones/api/voting-stats', function (data) {
            $('#candidate_stats').html('');

            if (data.voting_closed && !data.is_viewer) {
                $('#candidate_hidden_notice').hide();
                data.candidates.forEach(function (candidate) {
                    $('#candidate_stats').append(
                        '<div><p class="text-large">' + candidate.nombre + ': ' + candidate.porcentaje + '%</p>' +
                        '<img src="/votaciones_backend/static/uploads/' + candidate.imagen + '" class="party-image" alt="Imagen de ' + candidate.nombre + '"></div>'
                    );
                });
            } else {
                $('#candidate_hidden_notice').show();
            }

            $('#participation').text(data.participation.tasa_participacion + '% Participacion');
            $('#abstention').text(data.participation.tasa_abstencionismo + '% Abstencion');

            renderCharts(data);
        });
    }

    fetchData();
    setInterval(fetchData, 5000);
});
