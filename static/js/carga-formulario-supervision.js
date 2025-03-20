document.addEventListener("DOMContentLoaded", function() {
    const selects = document.querySelectorAll('select[name*="respuesta_supervisor"]');
    console.log(selects);
    
    selects.forEach(function(select) {
        select.addEventListener('change', function() {
            if (this.value == -1) {
                this.parentElement.parentElement.querySelector('input[name*="comentario_supervisor"]').setAttribute('required', true);
                this.parentElement.parentElement.querySelector('input[name*="comentario_supervisor"]').classList.add('input-error');
            } else {
                this.parentElement.parentElement.querySelector('input[name*="comentario_supervisor"]').removeAttribute('required');
                this.parentElement.parentElement.querySelector('input[name*="comentario_supervisor"]').classList.remove('input-error');
            }
        });
    });
    
    selects.forEach(function(select) {
        select.dispatchEvent(new Event('change'));
    });
});