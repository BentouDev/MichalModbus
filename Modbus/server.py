#!/usr/bin/python3
import time
import json

# RabbitMq
import pika

# Our own modbus and database modules
import modbus as sm

# Configure modbus client logging, so server prints out errors to server console
import logging
# FORMAT = ('%(asctime)-15s %(threadName)-15s '
#           '%(levelname)-8s %(module)-15s:%(lineno)-8s %(message)s')
# logging.basicConfig(format=FORMAT)
# log = logging.getLogger()
# log.setLevel(logging.DEBUG)

# Predeclare global variables
UNIT = 0x0

# Accepted messages:
#   - Change address - disconnect and connect to a new address
#   - Send data

# Send messages:
#   - Data changed

SendLogToServer = False
ModbusAddress = '0.0.0.0'
GlobalHost = '137.117.194.116'
CommandQueue = 'modbus_commands'
EventQueue = 'modbus_events'
LogQueue = 'log_queue'

def openQueue(name):
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=GlobalHost))

    channel = connection.channel()
    queue = channel.queue_declare(queue=name)

    return queue, channel, connection

def closeQueue(ch, cnn):
    ch.close()
    cnn.close()

def sendLog(msg):
    print(msg)

    if SendLogToServer:
        try:
            q, ch, cnn = openQueue(LogQueue)
            ch.basic_publish(exchange='', routing_key=LogQueue, body=msg)
            closeQueue(ch, cnn)
        except Exception as error:
            print(" [Error] Unable to send log due to: " + error)

def modbus_ping():
    try:
        # Connect to modbus
        modbus = sm.get_modbus(ModbusAddress)
        sendLog(' [Succ] Modbus alive at ip: ' + ModbusAddress)
    except Exception as error:
        sendLog(" [Error] Modbus ip: " + ModbusAddress + " error: " + str(error))

def send_to_modbus(widgets):
    try:
        # Connect to modbus
        modbus = sm.get_modbus(ModbusAddress)
        i = 0
        # Preallocate memory for data
        data = [0x0]*10

        # Foreach widget
        for w in widgets:
            # Increase index
            i += 1

            # Depending on status, put 0000 or 1111 (binary)
            if w['status'] == 1:
                data[i] = 255
            else:
                data[i] = 0x0

        # Write to multiple registers
        rr = modbus.write_registers(0x0, data, unit=UNIT)
        sendLog(" [Info] sending data to modbus at " + ModbusAddress + "...")
        return rr

    except Exception as error:
        sendLog(" [Error] Modbus ip: " + ModbusAddress + " error: " + str(error))

def ProcessCommands():
    try:
        q, ch, cnn = openQueue(CommandQueue)
        for method, properties, body in ch.consume(queue=q):
            sendLog ('[*] Received ' + body)
            datastore = json.loads(body)

            # Refactor better
            if datastore['command'] == 'ping':
                modbus_ping()

            if datastore['command'] == 'change_ip':
                ModbusAddress = datastore['address']
                sendLog('Succ: Changed Modbus ip to ' + ModbusAddress)

            if datastore['command'] == 'modbus_send':
                send_to_modbus(datastore['widgets'])

        closeQueue(ch, cnn)

    except (pika.exceptions.AMQPConnectionError, pika.exceptions.AMQPChannelError) as error:
        sendLog(" [Error] Catched exception: " + str(error))

def ProcessEvents():
    q, ch, cnn = openQueue(EventQueue)

    closeQueue(ch, cnn)

# Python specific - startup of  server
def start():
    sendLog(' Running...')
    sendLog(' [*] Waiting for messages. To exit press CTRL+C')
    while True:
        #ProcessEvents()
        ProcessCommands()
        time.sleep(1)

if __name__ == '__main__':
    start()