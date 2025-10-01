import pytest
from flask.testing import FlaskClient
from typing import Generator
from app import create_app
from config import Config


@pytest.fixture
def client() -> Generator[FlaskClient, None, None]:
    # Asegurar la configuración de BD antes de crear la app
    Config.set_environment_variables()
    app = create_app()
    app.config['TESTING'] = True

    yield app.test_client()
