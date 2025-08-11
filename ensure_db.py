import os
import sys
import pymysql

def get_env(name, default=None, required=False):
    val = os.getenv(name, default)
    if required and not val:
        print(f"Missing environment variable: {name}")
        sys.exit(1)
    return val

def main():
    host = get_env('DB_HOST', 'localhost')
    port = int(get_env('DB_PORT', '3306'))
    user = get_env('DB_USER', required=True)
    password = get_env('DB_PASS', '')
    dbname = get_env('DB_NAME', required=True)

    try:
        # Connect without selecting a database first
        conn = pymysql.connect(host=host, port=port, user=user, password=password, autocommit=True)
        with conn.cursor() as cur:
            cur.execute(f"CREATE DATABASE IF NOT EXISTS `{dbname}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        print(f"Database ensured: {dbname}")
    except Exception as e:
        print(f"Error ensuring database: {e}")
        sys.exit(2)
    finally:
        try:
            conn.close()
        except Exception:
            pass

if __name__ == '__main__':
    main()
