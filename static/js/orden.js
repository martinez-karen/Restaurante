const ORDEN_KEY = "ambar_orden";

function dinero(valor) {
  return Number(valor).toFixed(2);
}

function leerOrden() {
  return JSON.parse(localStorage.getItem(ORDEN_KEY) || "[]");
}

function guardarOrden(items) {
  localStorage.setItem(ORDEN_KEY, JSON.stringify(items));
}

function renderizarOrden() {
  const tabla = document.getElementById("tablaOrdenActual");
  const totalElemento = document.getElementById("totalOrdenActual");
  const inputItems = document.getElementById("itemsOrdenActual");
  const ordenVacia = document.getElementById("ordenVacia");
  const items = leerOrden();
  const total = items.reduce((suma, item) => suma + item.precio * item.cantidad, 0);

  tabla.innerHTML = "";
  inputItems.value = JSON.stringify(items);
  totalElemento.textContent = dinero(total);
  ordenVacia.classList.toggle("d-none", items.length > 0);

  items.forEach((item, index) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${item.nombre}</td>
      <td>$${dinero(item.precio)}</td>
      <td>
        <input class="form-control form-control-sm cantidad-orden" type="number" min="1" value="${item.cantidad}" data-index="${index}">
      </td>
      <td>$${dinero(item.precio * item.cantidad)}</td>
      <td>
        <button type="button" class="btn btn-outline-danger btn-sm borrar-item" data-index="${index}">Borrar</button>
      </td>
    `;
    tabla.appendChild(tr);
  });
}

document.addEventListener("DOMContentLoaded", () => {
  if (limpiarOrden) {
    localStorage.removeItem(ORDEN_KEY);
  }

  renderizarOrden();

  document.addEventListener("input", (event) => {
    if (!event.target.classList.contains("cantidad-orden")) {
      return;
    }

    const items = leerOrden();
    const index = Number(event.target.dataset.index);
    items[index].cantidad = Math.max(Number(event.target.value), 1);
    guardarOrden(items);
    renderizarOrden();
  });

  document.addEventListener("click", (event) => {
    if (!event.target.classList.contains("borrar-item")) {
      return;
    }

    const items = leerOrden();
    const index = Number(event.target.dataset.index);
    items.splice(index, 1);
    guardarOrden(items);
    renderizarOrden();
  });

  document.getElementById("formOrdenActual").addEventListener("submit", (event) => {
    if (!leerOrden().length) {
      event.preventDefault();
      alert("Agrega por lo menos un producto a tu orden.");
    }
  });
});
