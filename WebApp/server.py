#!/usr/bin/python3
# Import all libraries used by this project
# System library
import sys
import json
# Flask library
from flask import Flask
from flask import request
from flask import session
from flask import render_template
from flask import redirect
from flask import url_for
# Bootstrap library extension for Flask
from flask_bootstrap import Bootstrap

import pika, struct

import db as db
import datastorage as datastorage

# Configure modbus client logging, so server prints out errors to server console
import logging
import logging.handlers as handlers
import time

# FORMAT = ('%(asctime)-15s %(threadName)-15s '
#           '%(levelname)-8s %(module)-15s:%(lineno)-8s %(message)s')
FORMAT = ('%(asctime)-15s at:%(lineno)-8s %(message)s')
logging.basicConfig(format=FORMAT)

log_path = 'webapp.log'

handler = handlers.RotatingFileHandler(log_path, maxBytes=2048, backupCount=5)
handler.setLevel(logging.INFO)

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
#logger.addHandler(handler)

# Create flask server app
app = Flask(__name__)
app.secret_key = b')xDEADBEEF'

# Initialize bootstrap
Bootstrap(app)

# Queue helper methods
GlobalHost = 'amqp://0.0.0.0:5672/'
CommandQueue = 'modbus_commands'
EventQueue = 'modbus_events'
LogQueue = 'log_queue'

def trySet(data, name, default):
	if data.get(name):
		return data.get(name)
	return default

def loadConfig():
	config_path = 'webapp.config'
	try:
		with open(config_path,'r') as config_file:
			data = json.loads(config_file.read())

			global GlobalHost, CommandQueue, EventQueue, LogQueue

			GlobalHost = trySet(data, 'QueueHost', 'ampq://0.0.0.0:5672')
			CommandQueue = trySet(data, 'CommandQueue', 'modbus_commands')
			EventQueue = trySet(data, 'EventQueue', 'modbus_events')
			LogQueue = trySet(data, 'LogQueue', 'log_queue')
	except Exception as error:
		logger.warning(' [Warn] Unable to open webapp.config, using defaults...\n\tError: ' + str(error))

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
		logger.info(' [DEBUG] Publishing to queue ' + queueName)
		q, ch, cnn = openQueue(queueName)
		ch.basic_publish(exchange='', routing_key=queueName, body=msg)
		closeQueue(ch, cnn)

	except pika.exceptions.ConnectionClosedByBroker:
		# Uncomment this to make the example not attempt recovery
		# from server-initiated connection closure, including
		# when the node is stopped cleanly
		#
		# break
		logger.error(' [Error] Connection closed by broker')

	# Do not recover on channel errors
	except pika.exceptions.AMQPChannelError as err:
		logger.error(" [Error] Caught a channel error: {}, stopping...".format(err))

	# Recover on all other connection errors
	except pika.exceptions.AMQPConnectionError:
		logger.error(" [Error] Connection was closed, retrying...")

	# Write whatever was thrown
	except Exception as error:
		logger.error(" [Error] Catched exception: " + str(error))

########################################################
# Definitions of all methods which can be run on server
########################################################

def process_event_data(widget_id, data):
	try:
		widget = datastorage.get_widgets()[int(widget_id)]
		db_context = db.get_db()
		cur = db_context.cursor()

		if widget['type'] == 2:
			encoded_float = struct.pack('hh', [0,data])
			decoded_float = struct.unpack('f', encoded_float) # as two shorts

			cur.execute ('UPDATE widgets SET data_float_0 = ? WHERE id == ?', [decoded_float, widget_id])
			logger.info (" [Info] Changed data_float_0 of '" + widget['name'] + "' to '" + str(decoded_float) + "'!")

	except Exception as error:
		print(' [error] Widget event processing error: ' + str(error))
	return

def get_event_desc(widget_id, data):
	try:
		widget = datastorage.get_widgets()[int(widget_id)]
		name = widget['name']
		desc = "(nothing)"

		if widget['type'] == 2:
			desc = "Temperature changed to " + str(data)

		if widget['type'] == 4 and int(data) == 1:
			desc = "ALARM RAISED"

		return name, desc

	except Exception as error:
		return "Noname","Unknown"

# Get events sent by modbus
def get_events():
	try:
		logger.info("\n [Info] Checking events...")
		q, ch, cnn = openQueue(EventQueue)
		for method, properties, rawData in ch.consume(queue=EventQueue, inactivity_timeout=0.5):
			if rawData:
				body = rawData.decode("utf-8")
				events = json.loads(body)
				logger.info('\n [EVENT]' + body)

				for datastore in events:
					index = datastore['index']
					data = datastore['data']
					date = datastore['timedate']

					process_event_data(int(index) - 1, int(data))

					name, desc = get_event_desc(int(index) - 1, int(data))

					logger.info("\n [Info] Got event " + str(name) + " with data " + str(data) + " at: " + str(date))

					db_context = db.get_db()
					cur = db_context.cursor()
					cur.execute("INSERT INTO events (name, desc, date) VALUES (?, ?, ?)", [name, desc, date])
					db_context.commit()
			else:
				break
			ch.basic_ack(delivery_tag=method.delivery_tag)
		closeQueue(ch, cnn)
	except Exception as error:
		logger.error("\n [Error] Event processing error " + EventQueue + " due: " + str(error))

	return datastorage.get_events()

# Events - event page
@app.route("/events")
def show_events():
	# Get event list and display them
	events = get_events()
	data = {'events':events, 'event_count':len(events)}
	return render_template('events.html', title='Modbus - Events', data = data)

# Index - default page, 
# displays status and widget list
@app.route("/")
@app.route("/index")
def index():
	events = get_events()

	# put default message into page data dictionary
	data = {'message':'Unknown error, check log'}

	# if custom message, set by our code is present in session dictionary
	# put it into page data dictionary
	if 'message' in session:
		data['message'] = session['message']

	# put all widget data into page data dictionary
	data['widgets'] = datastorage.get_widgets()
	data['types'] = datastorage.get_widget_types()
	data['event_count'] = len(events)

	# Render index page
	return render_template('index.html', title='Modbus', data = data)

# Test connection - tries to connect to modbus,
# redirects to 'Index' in order to display connection result message
@app.route("/test_connection")
def test_connection():
	# put default message into page data dictionary
	data = {'message':'Unknown error, check log'}
	
	data = {'command':'modbus_ping'}

	body = json.dumps(data)

	publishToQueue(CommandQueue, body)

	# Cache last message in session
	session['message'] = "Check log"

	# Redirect to index
	return redirect(url_for('index'))

# Change ip - simple page with form, which allows to set modbus server ip
# redirects to 'Set ip' on form submit
@app.route("/change_ip")
def change_ip():
	# Try get address from database
	address = datastorage.get_address()

	# Render change_ip page
	return render_template('change_ip.html', address=address)

# Set ip - POST utility method, called by 'Change ip'
# Saves ip to database
@app.route("/set_ip", methods=['GET', 'POST'])
def set_ip():
	# Try get address from page form
	address = request.args.get('address')
	logger.info(" [Info] Got address " + address)
	if address:
		# If address was present in form, save it to database!
		datastorage.set_address(address)

	# Redirect to modbus connection test
	return redirect(url_for('test_connection'))

# Set data - POST utility method, called when user wants to change widget data
# saves data to database, redirects to 'Index'
@app.route("/set_data", methods=['GET', 'POST'])
def set_temp():
	# Get widget id from form
	widget_id = request.args.get('widget_id', 0)
	data_float_0 = request.args.get('data_float_0', 0)
	data_float_1 = request.args.get('data_float_1', 0)
	status_id = request.args.get('Toggle', 0)

	if not widget_id:
		# If theres no widget id in form, return error and redirect to index
		logger.error(" [Error] toggle_widget: no widget_id in form!")
		return redirect(url_for("index"))

	# Get widget by id from database
	db_context = db.get_db()
	cur = db_context.cursor()
	cur.execute ('SELECT * FROM widgets WHERE id == ?', [widget_id])
	widgets = cur.fetchone()

	# Update widget data in database
	if data_float_0:
		cur.execute ('UPDATE widgets SET data_float_0 = ? WHERE id == ?', [data_float_0, widget_id])
		logger.info (" [Info] Changed data_float_0 of '" + widgets['name'] + "' to '" + str(data_float_0) + "'!")

	if data_float_1:
		cur.execute ('UPDATE widgets SET data_float_1 = ? WHERE id == ?', [data_float_1, widget_id])
		logger.info (" [Info] Changed data_float_1 of '" + widgets['name'] + "' to '" + str(data_float_1) + "'!")

	if status_id:
		cur.execute ('UPDATE widgets SET status = ? WHERE id == ?', [status_id, widget_id])
		logger.info (" [Info] Changed status of '" + widgets['name'] + "' to '" + str(status_id) + "'!")

	send_widgets_via_modbus()

	# Close database connection
	db_context.commit()
	db_context.close()

	# Redirect to index
	return redirect(url_for("index"))

# Set status - POST utility method, called when user wants to change statsu, egx. widget on/off
# saves status to database, redirects to 'Index'
@app.route("/set_status", methods=['GET', 'POST'])
def toggle_widget():
	# Get widget id from form
	widget_id = request.args.get('widget_id', 0)
	status_id = request.args.get('Toggle', 0)

	if not widget_id:
		# If theres no widget id in form, return error and redirect to index
		logger.error (" [Error] toggle_widget: no widget_id in form!")
		return redirect(url_for("index"))

	# Get widget by id from database
	db_context = db.get_db()
	cur = db_context.cursor()
	cur.execute ('SELECT * FROM widgets WHERE id == ?', [widget_id])
	widgets = cur.fetchone()

	# Update widget status in database
	cur.execute ('UPDATE widgets SET status = ? WHERE id == ?', [status_id, widget_id])
	logger.info (" [Info] Changed status of '" + widgets['name'] + "' to '" + str(status_id) + "'!")

	send_widgets_via_modbus()

	# Close database connection
	db_context.commit()
	db_context.close()

	# Redirect to index
	return redirect(url_for("index"))

# Edit widget - form dedicated to edition of existing widgets
@app.route("/edit_widget", methods=['GET', 'POST'])
def edit_widget():
	# Get widget id from form
	widget_id = request.args.get('widget_id', 0)
	if not widget_id:
		# If theres no widget id in form, return error and redirect to index
		logger.error (" [Error] edit_widget: no widget_id in form!")
		return redirect(url_for("index"))

	# Get widget by id from database
	db_context = db.get_db()
	cur = db_context.cursor()
	cur.execute ('SELECT * FROM widgets WHERE id == ?', [widget_id])

	data = {'title':'Edit'}
	data['widget'] = cur.fetchone()
	data['types'] = datastorage.get_widget_types()

	# Render edit_widget page
	return render_template('edit_widget.html', title="Edit widget", data=data, widget=data['widget'])

# Add widget - form dedicated to creation of new widget
@app.route("/add_widget", methods=['GET', 'POST'])
def add_widget():
	if 'Commit' in request.form:
		return redirect(url_for("index"))
	else:
		data = {'title':'Add'}
		data['widget'] = {'name':'New widget', 'type':'1', 'img':''}
		data['types'] = datastorage.get_widget_types()
		return render_template('add_widget.html', title="Add widget", data=data, widget=data['widget'])

# Post edit - utility method, called by widget edit or creation page
# Can commit new, update existing or delete widget from database
@app.route('/post_edit', methods=['GET', 'POST'])
def post_edit():
	# Dispath by 'Submit' to decide what to do next
	if 'Submit' in request.args:
		logger.warning(" [Warn] Submit: " + request.args['Submit'])
		if request.args['Submit'] == 'Commit':
			add_new_widget()
		elif request.args['Submit'] == 'Update':
			widget_id = request.args.get('widget_id', 0)
			if widget_id:
				update_widget(widget_id)
		elif request.args['Submit'] == 'Delete':
			widget_id = request.args.get('widget_id', 0)
			if widget_id:
				delete_widget(widget_id)
	else:
		logger.error(" [Error] No Submit!")
	return redirect(url_for('index'))

@app.route('/show_log', methods=['GET', 'POST'])
def show_log():
	try:
		q, ch, cnn = openQueue(LogQueue)
		for method, properties, rawData in ch.consume(queue=CommandQueue, inactivity_timeout=0.5):
			body = rawData.decode("utf-8")
			logger.info(' [RASP]' + body)
			ch.basic_ack(delivery_tag=method.delivery_tag)
	except Exception as error:
		logger.error(" [Error] Unable to open queue " + LogQueue)

	render = ''
	with open(log_path,'r') as log_file:
		data = log_file.read().split('\n')
		for line in data:
			render += ('<p>' + line)

	return render

# Update widget - method which simplifies updating widget in database
def update_widget(id):
	logger.info (' [Info] Editing widget id ' + id)

	name = request.args.get("name")
	type_id = request.args.get("type")
	img = request.args.get("img")

	modbus_write_0 = request.args.get("modbus_write_0")
	modbus_write_1 = request.args.get("modbus_write_1")
	modbus_read_0 = request.args.get("modbus_read_0")
	modbus_read_1 = request.args.get("modbus_read_1")

	base_cmd = 'UPDATE widgets SET name = ?, type = ?, img = ?'
	base_data = [name, type_id, img]

	if modbus_write_0:
		base_cmd += ', modbus_write_0 = ?'
		base_data.append(modbus_write_0)

	if modbus_write_1:
		base_cmd += ', modbus_write_1 = ?'
		base_data.append(modbus_write_1)

	if modbus_read_0:
		base_cmd += ', modbus_read_0 = ?'
		base_data.append(modbus_read_0)

	if modbus_read_1:
		base_cmd += ', modbus_read_1 = ?'
		base_data.append(modbus_read_1)

	base_cmd += ' WHERE id == ?'
	base_data.append(id)

	# Update existing widget by id in database
	db_context = db.get_db()
	cur = db_context.cursor()
	cur.execute (base_cmd, base_data)

	db_context.commit()

# Add widget - method which simplifies creation of widget in database
def add_new_widget():
	name = request.args.get("name")
	type_id = request.args.get("type")
	img = request.args.get("img")

	# Insert new widget into database
	db_context = db.get_db()
	cur = db_context.cursor()
	cur.execute("INSERT INTO widgets (name, type, img) VALUES (?, ?, ?)", [name, type_id, img])
	db_context.commit()

# Delete widget - method which simplifies deletion of widget from database
def delete_widget(id):
	# Delete widget by id from database
	db_context = db.get_db()
	cur = db_context.cursor()
	cur.execute ('DELETE FROM widgets WHERE id == ?', [id])
	db_context.commit()

# View widget - main test method, sends statuses of widgets via modbus to server
@app.route("/view_data")
def view_data():
	send_widgets_via_modbus()
	return redirect(url_for('show_log'))

# Send widgets via modbus - utility method for modbus packet creation
def send_widgets_via_modbus():
	# Connect to modbus
	#modbus = sm.get_modbus()

	# Get widgets from database
	data = {'command':'modbus_send'}
	temp_widgets = datastorage.get_widgets()

	temp_array = []
	for widget in temp_widgets:
		type_id = widget['type']
		if type_id == 1: # Simple status for Light
			temp_array.append({
				'type':type_id,
				'status': (1).__lshift__(int(widget['status'])),
				'modbus_write_0':widget['modbus_write_0']
			})
		elif type_id == 3: # Simple Blinders
			temp_array.append({
				'type':type_id,
				'status':widget['status'],
				'modbus_write_0':widget['modbus_write_0']
			})
		elif type_id == 2: # Value for Temperature 
			temp_array.append({
				'type':type_id,
				'status':widget['status'],
				'data_float_1':widget['data_float_1'],
				'modbus_write_0':widget['modbus_write_0'],
				'modbus_write_1':widget['modbus_write_1'],
				'modbus_read_0':widget['modbus_read_0'],
				'modbus_read_1':widget['modbus_read_1'],
			})
		elif type_id == 4: # Value for Alarm
			temp_array.append({
				'type':type_id,
				'status':widget['status'],
				'data_float_0':widget['data_float_0'],
				'modbus_write_0':widget['modbus_write_0'],
				'modbus_write_1':widget['modbus_write_1'],
				'modbus_read_0':widget['modbus_read_0']
			})

	data['widgets'] = temp_array

	body = json.dumps(data)

	publishToQueue(CommandQueue, body)

# Python specific - startup of flask server
def start():
	loadConfig()
	app.run(debug=True, host='0.0.0.0')

if __name__ == '__main__':
    start()
