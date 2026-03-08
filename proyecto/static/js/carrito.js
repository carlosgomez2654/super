let productosEnCarrito = JSON.parse(localStorage.getItem("productos-en-carrito") || "[]");


const contenedorCarritoVacio = document.querySelector("#carrito-vacio");
const contenedorCarritoProductos = document.querySelector("#carrito-productos");
const contenedorCarritoAcciones = document.querySelector("#carrito-acciones");
const contenedorCarritoComprado = document.querySelector("#carrito-comprado");

const botonVaciar = document.querySelector("#carrito-acciones-vaciar");
const contenedorTotal = document.querySelector("#total");
const botonComprar = document.querySelector("#carrito-acciones-comprar");

/* ================================
   CARGAR PRODUCTOS DEL CARRITO
================================= */
function cargarProductosCarrito() {
    if (productosEnCarrito.length > 0) {

        contenedorCarritoVacio.classList.add("disabled");
        contenedorCarritoProductos.classList.remove("disabled");
        contenedorCarritoAcciones.classList.remove("disabled"); // permite clicks
        contenedorCarritoComprado.classList.add("disabled");

        contenedorCarritoProductos.innerHTML = "";

        productosEnCarrito.forEach(producto => {
            if (!producto.imagen.startsWith("/static/")) {
        producto.imagen = `/static/${producto.imagen}`;
        }
            const div = document.createElement("div");
            div.classList.add("carrito-producto");

            div.innerHTML = `
                <img class="carrito-producto-imagen" src="${producto.imagen}" alt="${producto.titulo}">

                <div class="carrito-producto-titulo">
                    <small>Producto</small>
                    <h3>${producto.titulo}</h3>
                </div>

                <div class="carrito-producto-cantidad">
                    <small>Cantidad</small>
                    <div class="cantidad-controles">
                        <button class="cantidad-btn restar" data-id="${producto.id}">-</button>
                        <p>${producto.cantidad}</p>
                        <button class="cantidad-btn sumar" data-id="${producto.id}">+</button>
                    </div>
                </div>

                <div class="carrito-producto-precio">
                    <small>Precio</small>
                    <p>$${producto.precio}</p>
                </div>

                <div class="carrito-producto-subtotal">
                    <small>Subtotal</small>
                    <p>$${producto.precio * producto.cantidad}</p>
                </div>

                <button class="carrito-producto-eliminar" data-id="${producto.id}">
                    <i class="bi bi-trash-fill"></i>
                </button>
            `;

            contenedorCarritoProductos.append(div);
        });

    } else {
        contenedorCarritoVacio.classList.remove("disabled");
        contenedorCarritoProductos.classList.add("disabled");
        contenedorCarritoAcciones.classList.add("disabled"); // no hay productos
        contenedorCarritoComprado.classList.add("disabled");
    }

    actualizarBotonesEliminar();
    activarBotonesCantidad();
    actualizarTotal();
}

cargarProductosCarrito();

/* ========================
   ELIMINAR PRODUCTO
======================== */
function actualizarBotonesEliminar() {
    const botonesEliminar = document.querySelectorAll(".carrito-producto-eliminar");

    botonesEliminar.forEach(boton => {
        boton.addEventListener("click", e => {
            const id = e.currentTarget.dataset.id;

            productosEnCarrito = productosEnCarrito.filter(p => p.id !== id);
            localStorage.setItem("productos-en-carrito", JSON.stringify(productosEnCarrito));
            cargarProductosCarrito();
        });
    });
}

/* ================================
   SUMAR / RESTAR CANTIDAD
================================= */
function activarBotonesCantidad() {
    const botonesSumar = document.querySelectorAll(".sumar");
    const botonesRestar = document.querySelectorAll(".restar");

    botonesSumar.forEach(b => {
        b.addEventListener("click", e => {
            const id = e.currentTarget.dataset.id;
            const item = productosEnCarrito.find(p => p.id === id);

            item.cantidad++;
            localStorage.setItem("productos-en-carrito", JSON.stringify(productosEnCarrito));
            cargarProductosCarrito();
        });
    });

    botonesRestar.forEach(b => {
        b.addEventListener("click", e => {
            const id = e.currentTarget.dataset.id;
            const item = productosEnCarrito.find(p => p.id === id);

            if (item.cantidad > 1) {
                item.cantidad--;
            }

            localStorage.setItem("productos-en-carrito", JSON.stringify(productosEnCarrito));
            cargarProductosCarrito();
        });
    });
}

/* ========================
   VACIAR CARRITO
======================== */
botonVaciar.addEventListener("click", () => {
    productosEnCarrito = [];
    localStorage.setItem("productos-en-carrito", "[]");
    cargarProductosCarrito();
});

/* ========================
   TOTAL
======================== */
function actualizarTotal() {
    const totalCalculado = productosEnCarrito.reduce(
        (acc, p) => acc + (p.precio * p.cantidad),
        0
    );

    contenedorTotal.innerText = `$${totalCalculado}`;
}

/* ========================
   COMPRAR - ENVÍO A BACKEND
======================== */
botonComprar.addEventListener("click", async () => {
    if (productosEnCarrito.length === 0) {
        swal("Carrito vacío", "Agrega productos antes de comprar", "warning");
        return;
    }

    try {
        const respuesta = await fetch("/procesar_compra", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ carrito: productosEnCarrito })
        });


        const data = await respuesta.json();

        if (data.error) {
            swal("Error", data.error.toString(), "error");
            return;
        }

        swal("Compra realizada", "Gracias por su compra", "success");

        productosEnCarrito = [];
        localStorage.setItem("productos-en-carrito", "[]");

        contenedorCarritoProductos.classList.add("disabled");
        contenedorCarritoAcciones.classList.add("disabled");
        contenedorCarritoComprado.classList.remove("disabled");

        console.log("Factura recibida:", data.factura);

    } catch (err) {
        console.error(err);
        swal("Error", "No se pudo procesar la compra", "error");
    }
});
