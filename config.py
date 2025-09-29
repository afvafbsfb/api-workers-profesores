import os

class Config:
    """
    Clase base para manejar configuraciones de la aplicación.
    """
    DB_ENV = os.getenv('DB_ENV', 'memory')  # Valores posibles: 'memory', 'development', 'production'

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
            'DB_HOST': 'dev-host',
            'DB_PORT': '3306',
            'DB_USER': 'dev_user',
            'DB_PASS': 'dev_pass',
            'DB_NAME': 'dev_db',
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

# Ejemplo de uso
if __name__ == "__main__":
    db_config = Config.get_database_config()
    print(f"Conectando a la base de datos en el entorno '{Config.DB_ENV}':")
    print(db_config)