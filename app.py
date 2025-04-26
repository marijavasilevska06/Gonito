from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import pandas as pd

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///products.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'your_secret_key'  # Use a strong secret key for production

db = SQLAlchemy(app)

# Models
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    barcode = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    discount_price = db.Column(db.Float, nullable=True)

class AdminUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

# Load Products from Excel
def load_products():
    try:
        df = pd.read_excel("products.xlsx")
        for _, row in df.iterrows():
            # Check if required fields are available
            if pd.isnull(row["Шифра"]) or pd.isnull(row["Име на артикал"]) or pd.isnull(row["Продажна цена"]):
                continue  # Skip if any required field is missing
            existing_product = Product.query.filter_by(barcode=str(row["Шифра"])).first()
            if not existing_product:
                new_product = Product(
                    barcode=str(row["Шифра"]),
                    name=row["Име на артикал"],
                    price=row["Продажна цена"]
                )
                db.session.add(new_product)
        db.session.commit()
    except Exception as e:
        print(f"Error while loading products: {e}")

# User-facing routes
@app.route("/", methods=["GET"])
def index():
    search = request.args.get("search", "").strip()
    akcija = request.args.get("akcija", "")
    
    query = Product.query
    if search:
        query = query.filter(Product.name.ilike(f"%{search}%"))
    if akcija == "1":
        query = query.filter(Product.discount_price.isnot(None))

    products = query.all()
    return render_template("index.html", products=products, search=search, akcija=akcija, year=datetime.now().year)

# Login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = AdminUser.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session["admin"] = user.id
            flash("Successfully logged in!", "success")
            return redirect("/admin")
        else:
            flash("Invalid login credentials.", "danger")
    return render_template("login.html", year=datetime.now().year)

@app.route("/logout")
def logout():
    session.pop("admin", None)
    flash("Successfully logged out.", "info")
    return redirect("/")

# Admin panel view
class SecureModelView(ModelView):
    def is_accessible(self):
        return "admin" in session  # Ensure only logged-in admins can access

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login'))  # Redirect to login if not authenticated

admin = Admin(app, name='Market Gonito Admin', template_mode='bootstrap3')
admin.add_view(SecureModelView(Product, db.session))  # Register Product model in admin

# Initialize the app
def setup_app():
    db.create_all()
    # Add a default admin user if none exists
    if not AdminUser.query.first():
        admin_user = AdminUser(
            username="admin",
            password=generate_password_hash("admin123", method="pbkdf2:sha256")
        )
        db.session.add(admin_user)
        db.session.commit()
    load_products()  # Load products from the Excel file

if __name__ == "__main__":
    with app.app_context():
        setup_app()  # Set up the database and products
    app.run(debug=True)
