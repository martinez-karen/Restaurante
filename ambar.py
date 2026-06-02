import json
import os
import smtplib
from email.message import EmailMessage


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


def normalizar_item_orden(nombre, precio=50, cantidad=1):
    nombre = str(nombre or "").strip()
    if not nombre:
        return None

    try:
        precio = float(precio)
    except (TypeError, ValueError):
        precio = 50

    try:
        cantidad = int(cantidad)
    except (TypeError, ValueError):
        cantidad = 1

    precio = max(precio, 0)
    cantidad = max(cantidad, 1)
    return {
        "nombre": nombre,
        "precio": precio,
        "cantidad": cantidad,
        "subtotal": precio * cantidad,
    }


def agregar_item_orden(items, nombre, precio=50):
    items = list(items or [])
    nuevo_item = normalizar_item_orden(nombre, precio)
    if not nuevo_item:
        return items

    for item in items:
        if item.get("nombre") == nuevo_item["nombre"]:
            item["cantidad"] = int(item.get("cantidad", 1)) + 1
            item["subtotal"] = float(item.get("precio", 0)) * item["cantidad"]
            return items

    items.append(nuevo_item)
    return items


def calcular_total_orden(items):
    return sum(float(item.get("precio", 0)) * int(item.get("cantidad", 1)) for item in items or [])
