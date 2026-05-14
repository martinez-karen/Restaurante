import os
import smtplib
from email.message import EmailMessage

from flask import Flask, render_template, request, redirect, flash, url_for
from pymongo import MongoClient
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer


client = MongoClient("mongodb+srv://24308060610098_db_user:karla1223@clusterkarla.qbnowlm.mongodb.net/?retryWrites=true&w=majority&appName=ClusterKarla")
db = client["restaurante"]
usuarios = db["usuarios"]
reservas = db["reservaciones"]

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "algo_secreto")
serializer = URLSafeTimedSerializer(app.secret_key)


def password_valida(password):
    return (
        len(password) >= 8
        and any(letra.isupper() for letra in password)
        and any(letra.islower() for letra in password)
        and any(letra.isdigit() for letra in password)
    )


def enviar_correo_recuperacion(destinatario, enlace):
    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER")
    smtp_password = os.environ.get("SMTP_PASSWORD")
    email_from = os.environ.get("EMAIL_FROM", smtp_user)

    if not smtp_user or not smtp_password or not email_from:
        raise RuntimeError("Faltan SMTP_USER, SMTP_PASSWORD o EMAIL_FROM")

    mensaje = EmailMessage()
    mensaje["Subject"] = "Recuperacion de contraseña - Ambar"
    mensaje["From"] = email_from
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

    with smtplib.SMTP(smtp_host, smtp_port) as servidor:
        servidor.starttls()
        servidor.login(smtp_user, smtp_password)
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

        if usuario.get("contraseña") != password:
            flash("Contraseña incorrecta")
            return render_template("inicio.html")

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

        usuarios.insert_one({
            "nombre": nombre,
            "apellidos": apellidos,
            "correo": email,
            "contraseña": password,
        })

        return redirect("/principal")

    return render_template("registro.html")


@app.route("/principal")
def principal():
    return render_template("principal.html")


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

        usuarios.update_one(
            {"correo": email},
            {"$set": {"contraseña": password}},
        )

        flash("Contraseña actualizada. Ya puedes iniciar sesión")
        return redirect("/")

    return render_template("restablecer_contraseña.html")


@app.route("/reservas")
def mostrar_reservas():
    return render_template("reservas.html")


if __name__ == "__main__":
    app.run(debug=True)
