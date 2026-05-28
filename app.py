import os
import smtplib
import bcrypt 
import json
from email.message import EmailMessage
from datetime import datetime

from flask import Flask, render_template, request, redirect, flash, url_for, session
from bson import ObjectId
from pymongo import MongoClient
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer


def cargar_env(ruta=".env"):
    if not os.path.exists(ruta):
        return

    with open(ruta, encoding="utf-8") as archivo:
        for linea in archivo:
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue

            clave, valor = linea.split("=", 1)
            clave = clave.strip()
            valor = valor.strip().strip('"').strip("'")
            os.environ.setdefault(clave, valor)


cargar_env()


client = MongoClient("mongodb+srv://24308060610098_db_user:karla1223@clusterkarla.qbnowlm.mongodb.net/?retryWrites=true&w=majority&appName=ClusterKarla")
db = client["restaurante"]
usuarios = db["usuarios"]
reservas = db["reservaciones"]
opiniones_collection = db["opiniones"]
envios = db["envios"]
ordenes = db["ordenes"]

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "algo_secreto")
serializer = URLSafeTimedSerializer(app.secret_key)
SMTP_HOSTNAME = os.environ.get("SMTP_HOSTNAME") or os.environ.get("SMPT_HOSTNAME") or "smtp.gmail.com"
SMTP_TLS_PORT = int(os.environ.get("SMTP_TLS_PORT") or os.environ.get("SMPT_TLS_PORT") or 587)
SMTP_USER = os.environ.get("SMTP_USER") or os.environ.get("SMPT_USER") or os.environ.get("GMAIL_USER")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD") or os.environ.get("SMPT_PASSWORD") or os.environ.get("GMAIL_APP_PASSWORD")

if SMTP_HOSTNAME == "smpt.gmail.com":
    SMTP_HOSTNAME = "smtp.gmail.com"

if SMTP_HOSTNAME == "smtp.gmail.com" and SMTP_PASSWORD:
    SMTP_PASSWORD = SMTP_PASSWORD.replace(" ", "")


def password_valida(password):
    return (
        len(password) >= 8
        and any(letra.isupper() for letra in password)
        and any(letra.islower() for letra in password)
        and any(letra.isdigit() for letra in password)
    )


def enviar_correo_recuperacion(destinatario, enlace):
    if not SMTP_USER or not SMTP_PASSWORD:
        raise RuntimeError("Faltan SMTP_USER o SMTP_PASSWORD")

    mensaje = EmailMessage()
    mensaje["Subject"] = "Recuperacion de contraseña - Ambar"
    mensaje["From"] = SMTP_USER
    mensaje["To"] = destinatario
    mensaje.set_content(
        f"""Hola.

Recibimos una solicitud para recuperar tu contraseña.
Abre este enlace para crear una nueva:

{enlace}

El enlace vence en 30 minutos.
Si no solicitaste este cambio, ignora este correo.
"""
    )

    with smtplib.SMTP(SMTP_HOSTNAME, SMTP_TLS_PORT, timeout=15) as servidor:
        servidor.starttls()
        servidor.login(SMTP_USER, SMTP_PASSWORD)
        servidor.send_message(mensaje)


def preparar_items_orden(items_json):
    try:
        items_recibidos = json.loads(items_json)
    except (TypeError, json.JSONDecodeError):
        items_recibidos = []

    items = []
    total = 0

    for item in items_recibidos:
        nombre = str(item.get("nombre", "")).strip()
        if not nombre:
            continue

        try:
            precio = float(item.get("precio", 50))
        except (TypeError, ValueError):
            precio = 50

        try:
            cantidad = int(item.get("cantidad", 1))
        except (TypeError, ValueError):
            cantidad = 1

        precio = max(precio, 0)
        cantidad = max(cantidad, 1)
        subtotal = precio * cantidad

        items.append({
            "nombre": nombre,
            "precio": precio,
            "cantidad": cantidad,
            "subtotal": subtotal,
        })
        total += subtotal

    return items, total


@app.route("/", methods=["GET", "POST"])
def inicio():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        usuario = usuarios.find_one({"correo": email})

        if not usuario:
            flash("Correo no registrado")
            return render_template("inicio.html")

        password_guardada = usuario.get("contraseña")

        if isinstance(password_guardada, str):
            password_guardada = password_guardada.encode("utf-8")

        if not bcrypt.checkpw(
            password.encode("utf-8"),
            password_guardada
        ):
            flash("Contraseña incorrecta")
            return render_template("inicio.html")

        session["usuario_id"] = str(usuario["_id"])
        session["nombre_usuario"] = usuario.get("nombre", "usuario")
        session["correo_usuario"] = usuario.get("correo", email)

        return redirect("/principal")

    return render_template("inicio.html")


@app.route("/registro", methods=["GET", "POST"])
def registrar():
    if request.method == "POST":
        nombre = request.form.get("nombre")
        apellidos = request.form.get("apellidos")
        email = request.form.get("email")
        password = request.form.get("password")

        if usuarios.find_one({"correo": email}):
            flash("Ese correo ya está registrado")
            return render_template("registro.html")

        if "@" not in email or "." not in email:
            flash("Correo inválido")
            return render_template("registro.html")

        if not password_valida(password):
            flash("La contraseña debe tener mínimo 8 caracteres, una mayúscula, una minúscula y un número")
            return render_template("registro.html")
        
        password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

        resultado = usuarios.insert_one({
            "nombre": nombre,
            "apellidos": apellidos,
            "correo": email,
            "contraseña": password_hash,
        })

        session["usuario_id"] = str(resultado.inserted_id)
        session["nombre_usuario"] = nombre
        session["correo_usuario"] = email

        return redirect("/principal")

    return render_template("registro.html")



@app.route("/principal")
def principal():
    return render_template("principal.html")


@app.route("/menu")
def menu():
    return render_template("menu.html")


@app.route("/bebidas")
def bebidas():
    return render_template("bebidas.html")


@app.route("/postres")
def postres():
    return render_template("postres.html")


@app.route("/disponibilidad")
def disponibilidad():
    return render_template("disponibilidad.html")


@app.route("/opiniones", methods=["GET", "POST"], endpoint="opiniones")
def mostrar_opiniones():
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        descripcion = request.form.get("descripcion", "").strip()
        calificacion = request.form.get("calificacion", "5")

        if not nombre or not descripcion:
            flash("Escribe tu nombre y opinion para publicarla")
            return redirect(url_for("opiniones"))

        try:
            calificacion = int(calificacion)
        except ValueError:
            calificacion = 5

        calificacion = min(max(calificacion, 1), 5)

        opiniones_collection.insert_one({
            "nombre": nombre,
            "descripcion": descripcion,
            "calificacion": calificacion,
            "likes": 0,
            "dislikes": 0,
            "creado_en": datetime.utcnow(),
            "usuario_id": session.get("usuario_id"),
        })

        flash("Opinion agregada correctamente")
        return redirect(url_for("opiniones"))

    opiniones_lista = list(opiniones_collection.find().sort("creado_en", -1))
    return render_template("opiniones.html", opiniones=opiniones_lista)


@app.route("/opiniones/<opinion_id>/<accion>", methods=["POST"])
def votar_opinion(opinion_id, accion):
    if accion not in ["like", "dislike"]:
        flash("Voto no valido")
        return redirect(url_for("opiniones"))

    campo = "likes" if accion == "like" else "dislikes"

    try:
        opiniones_collection.update_one(
            {"_id": ObjectId(opinion_id)},
            {"$inc": {campo: 1}},
        )
        flash("Gracias por votar")
    except Exception:
        flash("No se pudo registrar tu voto")

    return redirect(url_for("opiniones"))


@app.route("/acerca-de")
def acerca_de():
    return render_template("acerca_de.html")


@app.route("/cerrar-sesion")
def cerrar_sesion():
    session.clear()
    flash("Sesion cerrada correctamente")
    return redirect("/")


@app.route("/recuperar", methods=["GET", "POST"])
def recuperar():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()

        usuario = usuarios.find_one({"correo": email})
        if not usuario:
            flash("Ese correo no está registrado")
            return render_template("recuperar_contraseña.html")

        token = serializer.dumps(email, salt="recuperar-password")
        enlace = url_for("restablecer_password", token=token, _external=True)

        try:
            enviar_correo_recuperacion(email, enlace)
        except Exception as error:
            app.logger.exception("Error enviando correo de recuperación")
            flash("No se pudo enviar el correo. Revisa la configuración SMTP.")
            return render_template("recuperar_contraseña.html")

        flash("Te enviamos un enlace de recuperación a tu correo")
        return redirect("/")

    return render_template("recuperar_contraseña.html")


@app.route("/restablecer/<token>", methods=["GET", "POST"])
def restablecer_password(token):
    try:
        email = serializer.loads(
            token,
            salt="recuperar-password",
            max_age=1800,
        )
    except SignatureExpired:
        flash("El enlace de recuperación expiró")
        return redirect("/recuperar")
    except BadSignature:
        flash("El enlace de recuperación no es válido")
        return redirect("/recuperar")

    usuario = usuarios.find_one({"correo": email})
    if not usuario:
        flash("El correo ya no está registrado")
        return redirect("/recuperar")

    if request.method == "POST":
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirmPassword", "")

        if password != confirm_password:
            flash("Las contraseñas no coinciden")
            return render_template("restablecer_contraseña.html")

        if not password_valida(password):
            flash("La contraseña debe tener mínimo 8 caracteres, una mayúscula, una minúscula y un número")
            return render_template("restablecer_contraseña.html")

        nuevo_hash = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt()
            ).decode("utf-8")

        usuarios.update_one(
            {"correo": email},
            {"$set": {"contraseña": nuevo_hash}},
        )

        flash("Contraseña actualizada. Ya puedes iniciar sesión")
        return redirect("/")

    return render_template("restablecer_contraseña.html")


@app.route("/reservas", methods=["GET", "POST"])
def mostrar_reservas():
    if request.method == "POST":
        reserva = {
            "fecha": request.form.get("fecha", "").strip(),
            "hora": request.form.get("hora", "").strip(),
            "personas": request.form.get("personas", "").strip(),
            "nombre": request.form.get("nombre", "").strip(),
            "apellido": request.form.get("apellido", "").strip(),
            "ocasion": request.form.get("ocasion", "").strip(),
            "peticion": request.form.get("peticion", "").strip(),
            "usuario_id": session.get("usuario_id"),
            "correo": session.get("correo_usuario"),
            "creado_en": datetime.utcnow(),
        }

        if not reserva["fecha"] or not reserva["hora"] or not reserva["personas"] or not reserva["nombre"] or not reserva["apellido"]:
            flash("Completa fecha, hora, personas, nombre y apellido")
            return redirect(url_for("mostrar_reservas"))

        reservas.insert_one(reserva)
        flash("Reserva confirmada correctamente")
        return redirect(url_for("mostrar_reservas"))

    filtro = {}
    if session.get("usuario_id"):
        filtro = {"usuario_id": session.get("usuario_id")}

    reservas_lista = list(reservas.find(filtro).sort("creado_en", -1))
    return render_template("reservas.html", reservas=reservas_lista)

@app.route("/reservas/<reserva_id>/eliminar", methods=["POST"])
def eliminar_reserva(reserva_id):
    try:
        reserva_object_id = ObjectId(reserva_id)
    except Exception:
        flash("Reserva no valida")
        return redirect(url_for("mostrar_reservas"))

    filtro = {"_id": reserva_object_id}
    if session.get("usuario_id"):
        filtro["usuario_id"] = session.get("usuario_id")

    resultado = reservas.delete_one(filtro)
    if resultado.deleted_count:
        flash("Reserva eliminada correctamente")
    else:
        flash("No se encontro la reserva")

    return redirect(url_for("mostrar_reservas"))

@app.route("/domicilio")
def pedidos():
    return render_template("domicilio.html")

@app.route("/orden", methods=["GET"])
def orden():
    filtro = {}
    if session.get("usuario_id"):
        filtro = {"usuario_id": session.get("usuario_id")}

    ordenes_lista = list(ordenes.find(filtro).sort("creado_en", -1))

    reservas_lista = []
    if session.get("usuario_id"):
        reservas_lista = list(
            reservas.find({"usuario_id": session.get("usuario_id")}).sort("creado_en", -1)
        )

    return render_template(
        "orden.html",
        ordenes=ordenes_lista,
        reservas=reservas_lista,
        limpiar_orden=request.args.get("limpiar") == "1",
    )


@app.route("/orden/guardar", methods=["POST"])
def guardar_orden():
    items, total = preparar_items_orden(request.form.get("items", "[]"))
    accion = request.form.get("accion", "guardar")

    if not items:
        flash("Agrega por lo menos un producto a tu orden")
        return redirect(url_for("orden"))

    estado = "finalizado" if accion == "finalizar" else "guardado"
    orden = {
        "usuario": session.get("nombre_usuario", request.form.get("nombre", "Invitado")),
        "usuario_id": session.get("usuario_id"),
        "correo": session.get("correo_usuario"),
        "pedido": items,
        "total": total,
        "estado": estado,
        "reserva_id": request.form.get("reserva_id", "").strip(),
        "direccion": request.form.get("direccion", "").strip(),
        "telefono": request.form.get("telefono", "").strip(),
        "metodo_pago": request.form.get("metodo_pago", "").strip(),
        "creado_en": datetime.utcnow(),
    }

    if estado == "finalizado":
        orden["finalizado_en"] = datetime.utcnow()

    ordenes.insert_one(orden)
    flash("Orden finalizada correctamente" if estado == "finalizado" else "Orden guardada correctamente")
    return redirect(url_for("orden", limpiar=1))


@app.route("/orden/<orden_id>/editar", methods=["POST"])
def editar_orden(orden_id):
    try:
        orden_object_id = ObjectId(orden_id)
    except Exception:
        flash("Orden no valida")
        return redirect(url_for("orden"))

    orden_actual = ordenes.find_one({"_id": orden_object_id})
    if not orden_actual or orden_actual.get("estado") == "finalizado":
        flash("Esta orden ya no se puede editar")
        return redirect(url_for("orden"))

    filtro = {"_id": orden_object_id}
    if session.get("usuario_id"):
        filtro["usuario_id"] = session.get("usuario_id")

    nombres = request.form.getlist("nombre")
    precios = request.form.getlist("precio")
    cantidades = request.form.getlist("cantidad")
    items_recibidos = []

    for nombre, precio, cantidad in zip(nombres, precios, cantidades):
        items_recibidos.append({
            "nombre": nombre,
            "precio": precio,
            "cantidad": cantidad,
        })

    items, total = preparar_items_orden(json.dumps(items_recibidos))
    if not items:
        flash("La orden necesita por lo menos un producto")
        return redirect(url_for("orden"))

    resultado = ordenes.update_one(
        filtro,
        {"$set": {
            "pedido": items,
            "total": total,
            "reserva_id": request.form.get("reserva_id", "").strip(),
            "direccion": request.form.get("direccion", "").strip(),
            "telefono": request.form.get("telefono", "").strip(),
            "metodo_pago": request.form.get("metodo_pago", "").strip(),
            "actualizado_en": datetime.utcnow(),
        }},
    )

    flash("Orden editada correctamente" if resultado.modified_count else "No se hicieron cambios")
    return redirect(url_for("orden"))


@app.route("/orden/<orden_id>/eliminar", methods=["POST"])
def eliminar_orden(orden_id):
    try:
        orden_object_id = ObjectId(orden_id)
    except Exception:
        flash("Orden no valida")
        return redirect(url_for("orden"))

    filtro = {"_id": orden_object_id, "estado": {"$ne": "finalizado"}}
    if session.get("usuario_id"):
        filtro["usuario_id"] = session.get("usuario_id")

    resultado = ordenes.delete_one(filtro)
    flash("Orden eliminada correctamente" if resultado.deleted_count else "La orden finalizada no se puede borrar")
    return redirect(url_for("orden"))


@app.route("/orden/<orden_id>/finalizar", methods=["POST"])
def finalizar_orden(orden_id):
    try:
        orden_object_id = ObjectId(orden_id)
    except Exception:
        flash("Orden no valida")
        return redirect(url_for("orden"))

    filtro = {"_id": orden_object_id, "estado": {"$ne": "finalizado"}}
    if session.get("usuario_id"):
        filtro["usuario_id"] = session.get("usuario_id")

    resultado = ordenes.update_one(
        filtro,
        {"$set": {"estado": "finalizado", "finalizado_en": datetime.utcnow()}},
    )

    flash("Orden finalizada correctamente" if resultado.modified_count else "Esta orden ya estaba finalizada")
    return redirect(url_for("orden"))



if __name__ == "__main__":
    app.run(debug=True)
