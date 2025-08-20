try:
    # Expose the WSGI callable as "application" for Gunicorn/EB
    from main import app as application
except Exception as e:
    import sys, traceback
    sys.stderr.write(f"[WSGI Error] {e}\n{traceback.format_exc()}")
    raise
