document.addEventListener("DOMContentLoaded", function() {
    const selects = document.querySelectorAll('select');
    selects.forEach(function(select) {
        select.addEventListener('change', function() {
            if (this.value == -1) {
                this.parentElement.parentElement.querySelector('input[name*="comentario_empleado"]').setAttribute('required', true);
                this.parentElement.parentElement.querySelector('input[name*="comentario_empleado"]').classList.add('input-error');
            } else {
                this.parentElement.parentElement.querySelector('input[name*="comentario_empleado"]').removeAttribute('required');
                this.parentElement.parentElement.querySelector('input[name*="comentario_empleado"]').classList.remove('input-error');
            }
        });
    });
    
    selects.forEach(function(select) {
        select.dispatchEvent(new Event('change'));
    });
});