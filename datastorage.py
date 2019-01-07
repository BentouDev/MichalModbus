import db as db

def get_server_data():
    db_context = db.get_db()
    cur = db_context.cursor()
    cur.execute("SELECT * FROM data")
    return cur.fetchone()

def get_address():
    db_app_data = get_server_data()
    if db_app_data:
        return db_app_data['address']
    return None
