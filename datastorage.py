import db as db

def get_server_data():
    db_context = db.get_db()
    cur = db_context.cursor()
    cur.execute("SELECT * FROM data")
    return cur.fetchall()[0]

def get_address():
    db_app_data = get_server_data()
    if db_app_data:
        return db_app_data['address']
    print("No data in db..?")
    return None

def set_address(address):
    db_context = db.get_db()
    cur = db_context.cursor()
    cur.execute ('UPDATE data SET address = ?', [address])
    db_context.commit()
    print ("Set address to " + address)