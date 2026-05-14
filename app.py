<<<<<<< HEAD:app.py
from flask import Flask, render_template, request, redirect, flash
from pymongo import MongoClient

client = MongoClient("mongodb+srv://24308060610098_db_user:karla1223@clusterkarla.qbnowlm.mongodb.net/?retryWrites=true&w=majority&appName=ClusterKarla")
db = client["restaurante"]
usuarios = db["usuarios"]
reservas = db["reservaciones"]

app = Flask(__name__)
app.secret_key = "algo_secreto"


def password_valida(password):
    return (
        len(password) >= 8
        and any(letra.isupper() for letra in password)
        and any(letra.islower() for letra in password)
        and any(letra.isdigit() for letra in password)
    )

@app.route('/', methods=['GET', 'POST'])
def inicio():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        usuario = usuarios.find_one({"correo": email})

        if not usuario:
            flash("Correo no registrado")
            return render_template('inicio.html')

        if usuario.get("contraseña") != password:
            flash("Contraseña incorrecta")
            return render_template('inicio.html')

        return redirect('/principal')

    return render_template('inicio.html')


@app.route('/registro', methods=['GET', 'POST'])
def registrar():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        apellidos = request.form.get('apellidos')
        email = request.form.get('email')
        password = request.form.get('password')

        if usuarios.find_one({"correo": email}):
            flash("Ese correo ya está registrado")
            return render_template('registro.html')
        
        if "@" not in email or "." not in email:
            flash("Correo inválido")
            return render_template('registro.html')

        if not password_valida(password):
            flash("La contraseÃ±a debe tener mÃ­nimo 8 caracteres, una mayÃºscula, una minÃºscula y un nÃºmero")
            return render_template('registro.html')

        usuarios.insert_one({
            "nombre": nombre,
            "apellidos": apellidos,
            "correo": email,
            "contraseña": password
        })

        return redirect('/principal')

    return render_template('registro.html')


@app.route("/principal")
def principal():
    return render_template("principal.html")


@app.route("/recuperar")
def recuperar():
    return render_template("recuperar_contraseña.html")


@app.route("/reservas")
def mostrar_reservas():
    return render_template("reservas.html")
    

if __name__ == "__main__":
    app.run(debug=True)
=======
from flask import Flask, render_template, request, redirect, flash
from pymongo import MongoClient


client = MongoClient("mongodb://localhost:27017")
db = client["Restaurante"]
usuarios = db["usuarios"]


app = Flask(__name__)
app.secret_key = "algo_secreto"

@app.route('/', methods=['GET', 'POST'])
def inicio():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        usuario = usuarios.find_one({"email": email})

        if not usuario:
            flash("Correo no registrado")
            return render_template('inicio.html')

        if usuario["password"] != password:
            flash("Contraseña incorrecta")
            return render_template('inicio.html')

        return redirect('/principal')

    return render_template('inicio.html')


@app.route('/registro', methods=['GET', 'POST'])
def registrar():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        apellidos = request.form.get('apellidos')
        email = request.form.get('email')
        password = request.form.get('password')

        if usuarios.find_one({"email": email}):
            flash("Ese correo ya está registrado")
            return render_template('registro.html')
        
        if "@" not in email or "." not in email:
            flash("Correo inválido")
            return render_template('registro.html')

        usuarios.insert_one({
            "nombre": nombre,
            "apellidos": apellidos,
            "email": email,
            "password": password
        })

        return redirect('/principal')

    return render_template('registro.html')


@app.route("/principal")
def principal():
    return render_template("principal.html")
    

if __name__ == "__main__":
    app.run(debug=True)
>>>>>>> cbef4181c1912cedcf6469f9eb817b0321b5d27d:Restaurante/app.py
