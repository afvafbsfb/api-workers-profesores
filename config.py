import os

class Config:
    """
    Clase base para manejar configuraciones de la aplicación.
    """
    DB_ENV = os.getenv('DB_ENV', 'development')  # Valores posibles: 'memory', 'development', 'production'

    # Configuración de bases de datos
    DATABASES = {
        'memory': {
            'DB_HOST': 'localhost',
            'DB_PORT': '3306',
            'DB_USER': 'root',
            'DB_PASS': '',
            'DB_NAME': 'memory_db',
        },
        'development': {
            'DB_HOST': 'localhost',
            'DB_PORT': '3307',
            'DB_USER': 'angel',
            'DB_PASS': 'Abanca0795',
            'DB_NAME': 'api_workers',
        },
        'production': {
            'DB_HOST': 'prod-host',
            'DB_PORT': '3306',
            'DB_USER': 'prod_user',
            'DB_PASS': 'prod_pass',
            'DB_NAME': 'prod_db',
        },
    }

    @classmethod
    def get_database_config(cls):
        """
        Retorna la configuración de la base de datos según el entorno actual.
        """
        return cls.DATABASES.get(cls.DB_ENV, cls.DATABASES['memory'])

    @classmethod
    def set_environment_variables(cls):
        """
        Establece las variables de entorno dinámicamente según la configuración actual.
        """
        # Leer DB_ENV en tiempo de ejecución para permitir cambiarlo desde el shell
        env_db_env = os.getenv('DB_ENV', cls.DB_ENV)
        # Actualizar la variable de clase para que get_database_config() la use
        cls.DB_ENV = env_db_env

        db_config = cls.get_database_config()

        if cls.DB_ENV == 'memory':
            url = 'sqlite:///:memory:'
        else:
            url = f"mysql+pymysql://{db_config['DB_USER']}:{db_config['DB_PASS']}@{db_config['DB_HOST']}:{db_config['DB_PORT']}/{db_config['DB_NAME']}"

        # Exportar tanto DATABASE_URL (usado por la app/tests) como SQLALCHEMY_DATABASE_URI
        os.environ["DATABASE_URL"] = url
        os.environ["SQLALCHEMY_DATABASE_URI"] = url
        os.environ["DEBUG"] = "1" if cls.DB_ENV == "development" else "0"

# Ejemplo de uso
if __name__ == "__main__":
    db_config = Config.get_database_config()
    print(f"Conectando a la base de datos en el entorno '{Config.DB_ENV}':")
    print(db_config)

# Llamar al método para establecer las variables de entorno
Config.set_environment_variables()