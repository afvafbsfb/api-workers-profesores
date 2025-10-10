import pytest
import os
from flask.testing import FlaskClient
from typing import Generator
from app import create_app
from config import Config


def pytest_configure(config):
    """Pytest hook to configure test environment before running tests.

    We force DEBUG = False here so that debug prints controlled by
    `Config.DEBUG` do not appear during CI/test runs. However, we still
    want to print the name of each test case (see `print_test_name`).
    """
    # Ensure environment variables used by Config are set before anything
    # else; tests may call Config.set_environment_variables() again in
    # fixtures, but set an explicit DEBUG off here.
    # Allow tests to enable debug prints by setting TEST_DEBUG=true in the environment.
    try:
        env_val = os.environ.get('TEST_DEBUG')
        if env_val is not None:
            Config.DEBUG = str(env_val).lower() in ('1', 'true', 'yes')
        else:
            Config.DEBUG = False
    except Exception:
        # If Config cannot be mutated for some reason, ignore and continue
        pass


@pytest.fixture
def client() -> Generator[FlaskClient, None, None]:
    # Asegurar la configuración de BD antes de crear la app
    Config.set_environment_variables()
    app = create_app()
    app.config['TESTING'] = True

    # Ensure tests run inside application context so model queries succeed
    with app.app_context():
        yield app.test_client()


@pytest.fixture(autouse=True)
def print_test_name(request):
    """Autouse fixture that prints the test name before each test.

    This print must appear regardless of Config.DEBUG; it's used to
    produce a single-line trace of which test is running.
    """
    # Build a short, one-line title for the test comprising:
    #  - the test function name
    #  - a short description: first line of the function's docstring, if present,
    #    otherwise a readable title derived from the function name.
    def _first_line_of_doc(obj):
        try:
            doc = getattr(obj, '__doc__', None)
            if not doc:
                return None
            return doc.strip().splitlines()[0].strip()
        except Exception:
            return None

    node = request.node
    short_name = getattr(node, 'name', None) or getattr(node, 'nodeid', 'unknown_test')

    # If the test has a pytest.mark.meta(title=..., desc=...), prefer those values
    marker = None
    try:
        marker = request.node.get_closest_marker('meta')
    except Exception:
        marker = None

    title_part = None
    desc = None
    if marker:
        # marker can hold kwargs
        title_part = marker.kwargs.get('title') if hasattr(marker, 'kwargs') else None
        desc = marker.kwargs.get('desc') if hasattr(marker, 'kwargs') else None

    # Fall back to docstring or derived description
    if not desc:
        func = getattr(node, 'function', None)
        desc = _first_line_of_doc(func) or _first_line_of_doc(node) or ''

    if not title_part:
        # derive a short title from the function name
        title_part = short_name

    # Compose a compact single-line title and trim excessive length
    title = f"{title_part}: {desc}"

    # Normalize whitespace and limit to 120 chars
    title = ' '.join(title.split())
    if len(title) > 120:
        title = title[:117].rstrip() + '...'

    # Print this line always (not gated by Config.DEBUG)
    import builtins
    orig_print = builtins.print
    # Use the original print to output the title regardless of Config.DEBUG
    orig_print(f">>> PRUEBA: {title}")

    # If debug is disabled, replace print with a filtered version that only
    # allows lines starting with the test-title marker. This silences noisy
    # prints inside tests while keeping the one-line trace.
    if not getattr(Config, 'DEBUG', False):
        def _filtered_print(*args, **kwargs):
            try:
                s = ' '.join(str(a) for a in args)
            except Exception:
                # If something goes wrong serializing args, drop the print
                return None
            # Allow the title marker and keep any explicit test markers
            if s.startswith('>>> PRUEBA:'):
                return orig_print(*args, **kwargs)
            # Optionally allow very short lines (like single-char progress),
            # but by default suppress everything else.
            return None

        builtins.print = _filtered_print

    try:
        yield
    finally:
        # Restore original print to avoid side-effects between tests
        try:
            builtins.print = orig_print
        except Exception:
            pass
