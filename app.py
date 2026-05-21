import os
import smtplib
import bcrypt 
from email.message import EmailMessage

from flask import Flask, render_template, request, redirect, flash, url_for, session
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


@app.route("/reservas")
def mostrar_reservas():
    return render_template("reservas.html")

@app.route("/domicilio")
def mostrar_reservas():
    return render_template("domi.html")


if __name__ == "__main__":
    app.run(debug=True)
