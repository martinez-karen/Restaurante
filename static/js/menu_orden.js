const ORDEN_KEY = "ambar_orden";
const PRECIO_DEFAULT = 50;

function leerOrden() {
  return JSON.parse(localStorage.getItem(ORDEN_KEY) || "[]");
}

function guardarOrden(items) {
  localStorage.setItem(ORDEN_KEY, JSON.stringify(items));
}

function dinero(valor) {
  return Number(valor).toFixed(2);
}

function actualizarResumenOrden() {
  const items = leerOrden();
  const contador = document.querySelector("[data-orden-contador]");
  const totalElemento = document.querySelector("[data-orden-total]");
  const lista = document.querySelector("[data-orden-lista]");

  const total = items.reduce((suma, item) => suma + item.precio * item.cantidad, 0);

  if (contador) {
    contador.textContent = items.reduce((suma, item) => suma + item.cantidad, 0);
  }

  if (totalElemento) {
    totalElemento.textContent = dinero(total);
  }

  if (!lista) {
    return;
  }

  lista.innerHTML = "";

  if (!items.length) {
    lista.innerHTML = '<li class="list-group-item text-muted">Sin productos todavia</li>';
    return;
  }

  items.forEach((item) => {
    const li = document.createElement("li");
    li.className = "list-group-item d-flex justify-content-between gap-2";
    li.innerHTML = `<span>${item.cantidad} x ${item.nombre}</span><strong>$${dinero(item.precio * item.cantidad)}</strong>`;
    lista.appendChild(li);
  });
}

function agregarAOrden(nombre, precio) {
  const items = leerOrden();
  const existente = items.find((item) => item.nombre === nombre);

  if (existente) {
    existente.cantidad += 1;
  } else {
    items.push({ nombre, precio, cantidad: 1 });
  }

  guardarOrden(items);
  actualizarResumenOrden();
}

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".card").forEach((card) => {
    const boton = card.querySelector(".btn-gris-degradado");
    const nombreElemento = card.querySelector(".card-text");

    if (!boton || !nombreElemento) {
      return;
    }

    const nombre = nombreElemento.textContent.trim();
    const precio = Number(boton.dataset.precio || PRECIO_DEFAULT);

    boton.type = "button";
    boton.dataset.nombre = nombre;
    boton.dataset.precio = precio;

    if (!card.querySelector(".precio-menu")) {
      const precioElemento = document.createElement("p");
      precioElemento.className = "precio-menu fw-bold mb-0";
      precioElemento.textContent = `$${dinero(precio)}`;
      boton.insertAdjacentElement("beforebegin", precioElemento);
    }

    boton.addEventListener("click", () => {
      agregarAOrden(nombre, precio);
      boton.textContent = "Agregado";
      setTimeout(() => {
        boton.textContent = "Agregar";
      }, 900);
    });
  });

  actualizarResumenOrden();
});
