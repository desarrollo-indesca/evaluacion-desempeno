function checkNivel() {
    var nivel = parseInt(document.querySelector('#id_nivel_comp').value);
    var selectedOption = document.querySelector('#nivel').selectedOptions[0];
    var selectedNivel = parseInt(selectedOption.value);

    if (nivel < selectedNivel) {
        alert('El nivel seleccionado para promoción (' + selectedOption.textContent + ') es mayor que el recomendado por competencias técnicas. Tomar en consideración que en este caso se recomienda justificar la promoción para su revisión.');
    }
}

function cambiarEtiquetas() {
    document.querySelectorAll('option[value="unknown"]').forEach(opcion => {
        opcion.textContent = "Justificar";
    });
}

cambiarEtiquetas();
checkNivel();    

document.querySelector('#nivel').addEventListener('change', checkNivel);
document.addEventListener('htmx:afterSwap', cambiarEtiquetas);