// Keep the existing English checkbox consistent with an exclusive profile.
document.querySelectorAll('select[name="judge_evaluation_scope"], select[name="evaluation_scope"]').forEach(function (select) {
    var form = select.closest('form');
    var checkbox = form && form.querySelector('input[type="checkbox"][name="judge_can_evaluate_english"], input[type="checkbox"][name="can_evaluate_english"]');
    if (!checkbox) return;
    function sync() {
        var englishOnly = select.value === 'ingles';
        if (englishOnly) checkbox.checked = true;
        checkbox.disabled = englishOnly;
    }
    select.addEventListener('change', sync);
    sync();
});
