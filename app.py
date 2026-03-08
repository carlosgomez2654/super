from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "clave-super-segura")

# ==========================
# CONFIG DB
# ==========================
db_config = {
    'host': os.environ.get("DB_HOST"),
    'user': os.environ.get("DB_USER"),
    'password': os.environ.get("DB_PASSWORD"),
    'database': os.environ.get("DB_NAME")
}


def get_db_connection():
    return mysql.connector.connect(**db_config)

# ==========================
# REDIRECCIÓN GENERAL
# ==========================
@app.route('/')
def index():
    if 'user_id' in session:
        rol = session.get('rol')  # evita KeyError
        if rol == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif rol == 'cajero':
            return redirect(url_for('cajero_dashboard'))
        elif rol == 'cliente':
            return redirect(url_for('cliente_dashboard'))
        else:
            # Si por algún motivo no existe rol, limpia sesión
            session.clear()
            return redirect(url_for('login'))
    return redirect(url_for('login'))

# ==========================
# REGISTRO
# ==========================
@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        nombre = request.form['nombre']
        correo = request.form['correo']
        password = request.form['password']
        hashed_password = generate_password_hash(password)
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
            INSERT INTO usuarios(nombre, correo, password)
            VALUES (%s, %s, %s)
            """, (nombre, correo, hashed_password))
            conn.commit()
            flash('Registro exitoso. Inicia sesión.', 'success')
            return redirect(url_for('login'))
        except mysql.connector.Error as err:
            flash(f'Error al registrar: {err}', 'danger')
        finally:
            cursor.close()
            conn.close()
    return render_template('form_register.html')

# ==========================
# LOGIN
# ==========================
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        nombre = request.form['username']
        password = request.form['password']
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM usuarios WHERE nombre = %s", (nombre,))
            user = cursor.fetchone()
            if user and check_password_hash(user['password'], password):
                session['user_id'] = user['id']
                session['username'] = user['nombre']
                session['rol'] = user['rol']
                # Redirección según rol
                if user['rol'] == 'admin':
                    return redirect(url_for('admin_dashboard'))
                elif user['rol'] == 'cajero':
                    return redirect(url_for('cajero_dashboard'))
                else:
                    return redirect(url_for('cliente_dashboard'))
            else:
                flash("Usuario o contrasena incorrectos", "danger")
        finally:
            cursor.close()
            connection.close()
    return render_template('login.html')

# ==========================
# DASHBOARD CLIENTE
# ==========================
@app.route('/cliente/dashboard')
def cliente_dashboard():
    if 'user_id' not in session or session.get('rol') != 'cliente':
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM categoria")
    categorias = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'index.html',
        username=session['username'],
        categorias=categorias
    )

# ==========================
# TIENDA GENERAL
# ==========================
@app.route('/tienda')
def tienda():
    if 'user_id' not in session or session.get('rol') != 'cliente':
        return redirect(url_for('login'))

    q = request.args.get('q', '')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if q:
        cursor.execute(
            "SELECT * FROM producto WHERE NOMBRE_PRODUCTO LIKE %s",
            (f"%{q}%",)
        )
    else:
        cursor.execute("SELECT * FROM producto")

    productos = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'tienda.html',
        username=session['username'],
        productos=productos,
        categoria=0
    )

# ==========================
# TIENDA POR CATEGORÍA
# ==========================
@app.route('/tienda/categoria/<int:cat>')
def tienda_categoria(cat):
    print("ENTRÓ A CATEGORIA:", cat)

    if 'user_id' not in session or session.get('rol') != 'cliente':
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM producto WHERE CATEGORIA_ID = %s", (cat,))
    productos = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'tienda.html',
        username=session['username'],
        productos=productos,
        categoria=cat
    )

# ==========================
# CARRITO
# ==========================
@app.route('/carrito')
def carrito():
    if 'user_id' not in session or session.get('rol') != 'cliente':
        return redirect(url_for('login'))
    return render_template('carrito.html', username=session['username'])

# ==========================
# PROCESAR COMPRA
# ==========================
@app.route('/procesar_compra', methods=['POST'])
def procesar_compra():
    if 'user_id' not in session:
        return jsonify({"error": "No has iniciado sesión"}), 401
    carrito = request.get_json().get("carrito", [])
    if not carrito:
        return jsonify({"error": "Carrito vacío"}), 400
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True, buffered=True)
    errores = []
    factura_items = []
    try:
        for item in carrito:
            producto_id = int(item["id"])
            cantidad_comprada = int(item["cantidad"])
            # 1️⃣ Verificar inventario
            cursor.execute("SELECT cantidad FROM inventario WHERE PRODUCTO_COD = %s", (producto_id,))
            inventario = cursor.fetchone()
            # 2️⃣ Si no existe → crear registro
            if not inventario:
                cursor.execute("""
                    INSERT INTO inventario (PRODUCTO_COD, cantidad, fecha_actualizacion)
                    VALUES (%s, 0, NOW())
                """, (producto_id,))
                conn.commit()
                # volver a consultar con registro creado
                cursor.execute("SELECT cantidad FROM inventario WHERE PRODUCTO_COD = %s", (producto_id,))
                inventario = cursor.fetchone()
            stock_actual = int(inventario["cantidad"])
            # 3️⃣ Validar stock
            if cantidad_comprada > stock_actual:
                errores.append(f"Stock insuficiente para producto {producto_id}")
                continue
            nuevo_stock = stock_actual - cantidad_comprada
            # 4️⃣ Actualizar inventario
            cursor.execute("""
                UPDATE inventario 
                SET cantidad=%s, fecha_actualizacion=NOW()
                WHERE PRODUCTO_COD=%s
            """, (nuevo_stock, producto_id))
            factura_items.append({
                "producto_id": producto_id,
                "cantidad": cantidad_comprada,
                "restante": nuevo_stock
            })
        if errores:
            conn.rollback()
            return jsonify({"error": errores}), 400
        conn.commit()
        return jsonify({
            "mensaje": "Compra procesada con éxito",
            "factura": factura_items
        }), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# ==========================
# ADMIN DASHBOARD
# ==========================
@app.route('/admin/dashboard')
def admin_dashboard():
    if 'user_id' not in session or session.get('rol') != 'admin':
        return redirect(url_for('login'))
    return render_template('index_admin.html', username=session['username'])

# ==========================
# ADMIN - LISTA USUARIOS
# ==========================
@app.route('/admin')
def admin():
    if 'user_id' not in session or session.get('rol') != 'admin':
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM usuarios")
    usuarios = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("admin.html", username=session['username'], usuarios=usuarios)

# ==========================
# ADMIN - LISTA EMPLEADOS
# ==========================
@app.route('/empleados')
def empleados():
    if 'user_id' not in session or session.get('rol') != 'admin':
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM empleado")
    empleados = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("empleados.html", username=session['username'], empleados=empleados)

# ==========================
# EDITAR USUARIO (ADMIN)
# ==========================
@app.route('/editar/usuario/<int:id>', methods=['GET','POST'])
def editar(id):
    if session.get('rol') != 'admin':
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    if request.method == 'POST':
        nombre = request.form['nombre']
        correo = request.form['correo']
        password = request.form['password']
        if password:  # solo si el admin cambia la contraseña
            hashed_password = generate_password_hash(password)
            cursor.execute("""
                UPDATE usuarios 
                SET nombre=%s, correo=%s, password=%s 
                WHERE id=%s
            """, (nombre, correo, hashed_password, id))
        else:
            cursor.execute("""
                UPDATE usuarios 
                SET nombre=%s, correo=%s
                WHERE id=%s
            """, (nombre, correo, id))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect('/empleados')
    cursor.execute("SELECT * FROM usuarios WHERE id=%s", (id,))
    usuario = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template("editar.html", usuario=usuario, username=session['username'])

# ==========================
# EDITAR EMPLEADO (ADMIN)
# ==========================
@app.route('/editar/empleado/<int:id>', methods=['GET', 'POST'])
def editar_empleado(id):
    if session.get('rol') != 'admin':
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    if request.method == 'POST':
        nombre = request.form['nombre']
        apellido = request.form['apellido']
        direccion = request.form['direccion']
        telefono = request.form['telefono']
        correo = request.form['correo']
        no_doc = request.form['no_doc']
        estado_civil = request.form['estado_civil']
        sexo = request.form['sexo']
        eps = request.form['eps']
        cesantias = request.form['cesantias']
        cargo_cod = request.form['cargo_cod']
        sucursal = request.form['sucursal']
        cursor.execute("""
            UPDATE empleado SET
                nombre=%s,
                apellido=%s,
                direccion=%s,
                telefono=%s,
                correo=%s,
                no_doc=%s,
                estado_civil=%s,
                sexo=%s,
                eps=%s,
                cesantias=%s,
                cargo_cod=%s,
                sucursal_cod=%s
            WHERE cod_empleado=%s
        """, (nombre, apellido, direccion, telefono, correo, no_doc,
            estado_civil, sexo, eps, cesantias, cargo_cod, sucursal, id))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect('/empleados')
    # Corregido aquí también:
    cursor.execute("SELECT * FROM empleado WHERE cod_empleado=%s", (id,))
    empleado = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template("editar_empleado.html", empleado=empleado, username=session['username'])

# ==========================
# ELIMINAR USUARIO (ADMIN)
# ==========================
@app.route('/eliminar/<int:id>')
def eliminar(id):
    if session.get('rol') != 'admin':
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM usuarios WHERE id=%s", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect('/admin')

# =========================
# ELIMINAR EMPLEADOS (ADMIN)
# =========================

@app.route('/eliminar/empleado/<int:id>')
def eliminar_empleado(id):
    if session.get('rol') != 'admin':
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM empleado WHERE cod_empleado=%s", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('empleados'))

# ==========================
# CAJERO DASHBOARD
# ==========================
@app.route('/cajero/dashboard')
def cajero_dashboard():
    if 'user_id' not in session or session.get('rol') != 'cajero':
        return redirect(url_for('login'))
    return render_template('index_cajero.html', username=session['username'])

# ==========================
# LOGOUT
# ==========================
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ==========================
# RUN
# ==========================
if __name__ == "__main__":
    app.run(debug=True, port=5000)
