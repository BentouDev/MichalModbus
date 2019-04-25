## Dependencies
### Flask webapp
```bash
$ python3 -m pip install flask flask-jsonpify flask-sqlalchemy flask-restful
$ python3 -m pip install flask-bootstrap
$ python3 -m pip install pika
$ python3 -m pip install numpy
```

### Modbus server
```bash
$ python3 -m pip install pymodbus
$ python3 -m pip install pika
```

## Run
### Web application
```bash
python3 WebApp/server.py
```
### Modbus server
```bash
python3 Modbus/server.py
```
