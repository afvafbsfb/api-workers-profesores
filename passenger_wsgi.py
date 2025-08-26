try:
    from main import app as application
except Exception as e:
    import sys
    sys.stderr.write(f"[WSGI Error] {e}\n")
    raise
