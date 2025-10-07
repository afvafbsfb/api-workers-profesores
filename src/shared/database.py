from flask_sqlalchemy import SQLAlchemy

# Crear la instancia de SQLAlchemy
# Esta instancia será utilizada para inicializar la base de datos en la aplicación Flask
db = SQLAlchemy()

# Base para los modelos
Base = db.Model