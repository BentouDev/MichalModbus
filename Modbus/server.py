#!/usr/bin/python3
import time, json, numpy

# RabbitMq
import pika

# Our own modbus and database modules
import modbus as sm

# Configure modbus client logging, so server prints out errors to server console
import logging, traceback
# FORMAT = ('%(asctime)-15s %(threadName)-15s '
#           '%(levelname)-8s %(module)-15s:%(lineno)-8s %(message)s')
FORMAT = (' [VERBOSE] %(message)s')
logging.basicConfig(format=FORMAT)
log = logging.getLogger()
log.setLevel(logging.DEBUG)

# Predeclare global variables
UNIT = 0x0

# Accepted messages:
#   - Change address - disconnect and connect to a new address
#   - Send data

# Send messages:
#   - Data changed

SendLogToServer = False
ModbusAddress = '0.0.0.0'
GlobalHost = 'ampq://137.117.194.116:5672'
CommandQueue = 'modbus_commands'
EventQueue = 'modbus_events'
LogQueue = 'log_queue'

DINGUS = sm.TwojStary()

def trySet(data, name, default):
	if data.get(name):
		return data.get(name)
	return default

def loadConfig():
	config_path = 'modbus.config'
	with open(config_path,'r') as config_file:
		data = json.loads(config_file.read())

		global GlobalHost, CommandQueue, EventQueue, LogQueue, ModbusAddress

		ModbusAddress = trySet(data, 'ModbusAddress', '0.0.0.0')
		GlobalHost = trySet(data, 'QueueHost', 'ampq://0.0.0.0:5672')
		CommandQueue = trySet(data, 'CommandQueue', 'modbus_commands')
		EventQueue = trySet(data, 'EventQueue', 'modbus_events')
		LogQueue = trySet(data, 'LogQueue', 'log_queue')

def openQueue(name):
    connection = pika.BlockingConnection(
        pika.connection.URLParameters(GlobalHost))

    channel = connection.channel()
    queue = channel.queue_declare(queue=name,durable=True)

    return queue, channel, connection

def closeQueue(ch, cnn):
    ch.close()
    cnn.close()

def publishToQueue(queueName, msg):
	try:
		print(' [DEBUG] Publishing to queue ' + queueName)
		q, ch, cnn = openQueue(queueName)
		ch.basic_publish(exchange='', routing_key=queueName, body=msg)
		closeQueue(ch, cnn)

	except pika.exceptions.ConnectionClosedByBroker:
		# Uncomment this to make the example not attempt recovery
		# from server-initiated connection closure, including
		# when the node is stopped cleanly
		#
		# break
		print(' [Error] Connection closed by broker')

	# Do not recover on channel errors
	except pika.exceptions.AMQPChannelError as err:
		print(" [Error] Caught a channel error: {}, stopping...".format(err))

	# Recover on all other connection errors
	except pika.exceptions.AMQPConnectionError:
		print(" [Error] Connection was closed, retrying...")

	# Write whatever was thrown
	except Exception as error:
		print(" [Error] Catched exception: " + str(error))

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

def ok(value):
    return value != None and value != "" and value != 'None'

def send_to_modbus(widgets):
    try:
        # Connect to modbus
        DINGUS.aquire_modbus(ModbusAddress)
        DINGUS.cache_request(widgets)

        for widget in widgets:
            type = widget['type']
            if type == 1 or type == 3: #
                state = widget['status']
                regid = widget['modbus_write_0'] 

                if ok(regid) and ok(state):
                    DINGUS.set_byte(int(regid), int(state)+1)
                else:
                    sendLog(' [error] null data [state] for type [1,3]')

            if type == 2: # Temp
                state = widget['status']
                data_float_1 = widget['data_float_1']
                id_state = widget['modbus_write_0']
                id_float = widget['modbus_write_1']

                if ok(id_state) and ok(state):
                    DINGUS.set_byte(int(id_state), int(state))
                else:
                    sendLog(' [error] null data [state] for type [2]')

                if ok(id_float) and ok(data_float_1):
                    DINGUS.set_float(int(id_float), float(data_float_1))
                else:
                    sendLog(' [error] null data [data_float_0] for type [2]')

            if type == 4: # Alarm
                state = widget['status']
                pin = widget['data_float_0']
                id_state = widget['modbus_write_0']
                id_pin = widget['modbus_write_1']

                if ok(id_state) and ok(state):
                    DINGUS.set_byte(int(id_state), int(state))
                else:
                    sendLog(' [error] null data [state] for type [4]')

                if ok(id_pin) and ok(pin):
                    DINGUS.set_byte(int(id_pin), int(pin))
                else:
                    sendLog(' [error] null data [data_float_0] for type [4]')

        sendLog(" [Info] sending data to modbus at " + ModbusAddress + "...")
        rr = DINGUS.send(UNIT)
        return rr

    except Exception as error:
        DINGUS.force_close()
        tb = traceback.format_exc()
        sendLog(" [Error] Modbus WRITE to ip: " + ModbusAddress + " error: " + str(error) + "\n" + tb)

def legacy_send_to_modbus(widgets):
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
        sendLog(" [Error] Modbus WRITE to ip: " + ModbusAddress + " error: " + str(error))

def ProcessCommands():
    try:
        q, ch, cnn = openQueue(CommandQueue)
        for method, properties, rawData in ch.consume(queue=CommandQueue):
            body = rawData.decode("utf-8") 
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
    
    except pika.exceptions.ConnectionClosedByBroker:
        # Uncomment this to make the example not attempt recovery
        # from server-initiated connection closure, including
        # when the node is stopped cleanly
        #
        # break
        sendLog(' [Error] Connection closed by broker')

    # Do not recover on channel errors
    except pika.exceptions.AMQPChannelError as err:
        sendLog(" [Error] Caught a channel error: {}, stopping...".format(err))
        exit()

    # Recover on all other connection errors
    except pika.exceptions.AMQPConnectionError:
        sendLog(" [Error] Connection was closed, retrying...")

    # Write whatever was thrown
    except Exception as error:
        sendLog(" [Error] Catched exception: " + str(error))

def ProcessEvents():
    # nothing to do!
    if not DINGUS or not DINGUS.request:
        return

    registers_to_read = []
    index = 0

    # Search cached widgets for register id's to read
    for widget in DINGUS.request:
        for widget in DINGUS.REGISTER_CACHE:
            index = index + 1
            if 'modbus_read_0' in widget:
                read_register = widget['modbus_read_0']
                registers_to_read.append({ 'widget' : widget, 'register' : read_register, 'index' : index })

    data_to_send = []
    try:
        for data in registers_to_read:
            # Connect to modbus
            modbus = sm.get_modbus(ModbusAddress)
            rh = modbus.read_holding_registers(0x1 + data['register'], 1, unit=UNIT)

            # If no error code in function code, save readed value
            if rh.function_code < 0x80:
                received_data = rh.registers[0]
                data_to_send.append({'data' : received_data, 'index' : data['index']})
                sendLog(' [Debug] Modbus succ ' + str(received_data) + ' from ' + data['register'] + ' reg.')
            else:
                sendLog(" [Error] Modbus READ returned function code : " + str(rh.function_code))

    except Exception as error:
        sendLog(" [Error] Modbus READ from ip: " + ModbusAddress + " error: " + str(error))

    try:
        # Pack data to json and send it
        if len(data_to_send) > 0:
            body = json.dumps(data_to_send)
            publishToQueue(EventQueue, body)
            print(' [Debug] Sent event data: ' + body)

    except Exception as error:
        sendLog(" [Error] Error while sending to EVENT queue : " + str(error))

# Python specific - startup of  server
def start():
    loadConfig()
    sendLog(' Queue host : ' + GlobalHost)
    sendLog(' Running...')
    sendLog(' [*] Waiting for messages. To exit press CTRL+C')

    while True:
        try:
            ProcessEvents()
            ProcessCommands()
            time.sleep(1)
        except KeyboardInterrupt :
            print(" Closed")
            break

if __name__ == '__main__':
    start()