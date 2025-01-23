// Agrega listeners de eventos a los elementos con las clases especificadas
const cargarEventListeners = (anadirListeners = true) => {
    const anadirElementos = document.querySelectorAll(".anadir");
    const eliminarElementos = document.querySelectorAll(".eliminar");

    // Quita los listeners de eventos existentes
    eliminarElementos.forEach(el => el.removeEventListener("click", eliminar));
    if (anadirListeners) {
        anadirElementos.forEach(el => el.removeEventListener("click", anadir));
    }

    // Agrega nuevos listeners de eventos
    eliminarElementos.forEach(el => el.addEventListener("click", eliminar));
    if (anadirListeners) {
        anadirElementos.forEach(el => el.addEventListener("click", anadir));
    }
};

// Reindexa los elementos del formulario para asegurarse de que tengan valores de índice secuenciales
const reindex = (anadir = false, formClass = "") => {
    const forms = document.querySelectorAll(`.${formClass}`);
    const formRegex = new RegExp(`${formClass}-(\\d)+-`, "g");

    forms.forEach((form, i) => {
        const currentPrefix = `${formClass}-${i}-`;
        let valores = {};

        form.querySelectorAll("input, select").forEach(el => {
            if (!(anadir && i === forms.length - 1 && el.id.includes("-id"))) {
                valores[el.id.replace(formRegex, currentPrefix)] = el.value;
            } else {
                valores[el.id.replace(formRegex, currentPrefix)] = "";
            }
        });

        if (!form.innerHTML.includes(currentPrefix)) {
            form.innerHTML = form.innerHTML.replace(formRegex, currentPrefix);
        }

        form.querySelectorAll("input, select").forEach(el => {
            el.value = valores[el.id];
        });
    });
};

// Elimina un elemento del formulario y actualiza los índices
const eliminar = (e) => {
    const formClass = e.target.closest('tr').classList[0];
    const forms = document.querySelectorAll(`.${formClass}`);
    const formNum = forms.length;
    const totalForms = document.querySelector(`#id_${formClass}-TOTAL_FORMS`);

    totalForms.setAttribute("value", `${formNum - 1}`);
    e.target.parentElement.parentElement.remove();

    reindex(false, formClass);
    cargarEventListeners(false);

    const lastId = document.querySelector(`#id_${formClass}-${formNum}-id`);
    if (lastId) lastId.remove();
};

// Agrega un nuevo elemento del formulario y actualiza los índices
const anadir = (e) => {
    const formClass = e.target.closest('tr').classList[0];
    const forms = document.querySelectorAll(`.${formClass}`);
    const formContainer = document.querySelector(`#${formClass}`);
    const totalForms = document.querySelector(`#id_${formClass}-TOTAL_FORMS`);
    const formNum = forms.length;

    const newForm = forms[0].cloneNode(true);
    const formRegex = new RegExp(`${formClass}-(\\d)+-`, "g");
    const formPrefix = `${formClass}-${formNum}-`;

    newForm.innerHTML = newForm.innerHTML.replace(formRegex, formPrefix);

    const newElement = formContainer.insertBefore(newForm, e.target.parentNode.parentNode.lastSibling);

    const anadirElement = newElement.querySelector(".anadir");
    anadirElement.classList.replace("anadir", "eliminar");
    anadirElement.classList.replace("btn-success", "btn-error");
    anadirElement.textContent = "-";

    reindex(true, formClass);
    cargarEventListeners(false);

    totalForms.setAttribute("value", `${formNum + 1}`);

    const newIdElement = newElement.querySelector(`#id_${formPrefix}-id`);
    if (newIdElement) newIdElement.remove();
};

// Inicializa los listeners de eventos al cargar la página
cargarEventListeners();

// Desactiva el botón de envío en el envío del formulario
document.addEventListener("submit", (e) => {
    const submitButton = e.target.querySelector("#submit");
    if (submitButton) {
        submitButton.setAttribute("disabled", "disabled");
    }
});

document.addEventListener("DOMContentLoaded", () => {
    const idFields = document.querySelectorAll('[id*="-id"]');
    idFields.forEach(idField => idField.remove());

    const initialFormsFields = document.querySelectorAll('[id$="-INITIAL_FORMS"]');
    initialFormsFields.forEach(initialField => initialField.value = "0");
});
