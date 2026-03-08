document.addEventListener("DOMContentLoaded", () => {

    const numerito = document.querySelector("#numerito");
    const botonesAgregar = document.querySelectorAll(".producto-agregar");

    // Obtener carrito
    function getCart() {
        return JSON.parse(localStorage.getItem("cart_v1") || "[]");
    }

    // Guardar carrito
    function setCart(cart) {
        localStorage.setItem("cart_v1", JSON.stringify(cart));
        updateCount();
    }

    // Actualizar número del carrito
    function updateCount() {
        let cart = getCart();
        let total = cart.reduce((s, item) => s + item.qty, 0);
        if (numerito) numerito.textContent = total;
    }

    // Agregar al carrito
    botonesAgregar.forEach(btn => {
        btn.addEventListener("click", () => {
            const id = btn.dataset.id;
            let cart = getCart();

            let obj = cart.find(item => item.id == id);

            if (obj) {
                obj.qty++;
            } else {
                cart.push({ id: id, qty: 1 });
            }

            setCart(cart);
            alert("Producto agregado al carrito ✔️");
        });
    });

    updateCount();
});

