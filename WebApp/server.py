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

import pika

import db as db
import datastorage as datastorage

# Configure modbus client logging, so server prints out errors to server console
import logging
FORMAT = ('%(asctime)-15s %(threadName)-15s '
          '%(levelname)-8s %(module)-15s:%(lineno)-8s %(message)s')
logging.basicConfig(format=FORMAT)
log = logging.getLogger()
log.setLevel(logging.DEBUG)

# Create flask server app
app = Flask(__name__)
app.secret_key = b')xDEADBEEF'

# Initialize bootstrap
Bootstrap(app)

# Queue helper methods
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

def publishToQueue(queueName, msg):
	try:
		q, ch, cnn = openQueue(queueName)
		ch.basic_publish(exchange='', routing_key=LogQueue, body=msg)
		closeQueue(ch, cnn)

	except pika.exceptions.ConnectionClosedByBroker:
		# Uncomment this to make the example not attempt recovery
		# from server-initiated connection closure, including
		# when the node is stopped cleanly
		#
		# break
		app.logger.error(' [Error] Connection closed by broker')

	# Do not recover on channel errors
	except pika.exceptions.AMQPChannelError as err:
		app.logger.error(" [Error] Caught a channel error: {}, stopping...".format(err))

	# Recover on all other connection errors
	except pika.exceptions.AMQPConnectionError:
		app.logger.error(" [Error] Connection was closed, retrying...")

	# Write whatever was thrown
	except Exception as error:
		app.logger.error(" [Error] Catched exception: " + str(error))

########################################################
# Definitions of all methods which can be run on server
########################################################

# Index - default page, 
# displays status and widget list
@app.route("/")
@app.route("/index")
def index():
	# put default message into page data dictionary
	data = {'message':'Unknown error, check log'}

	# if custom message, set by our code is present in session dictionary
	# put it into page data dictionary
	if 'message' in session:
		data['message'] = session['message']

	# put all widget data into page data dictionary
	data['widgets'] = datastorage.get_widgets()

	# Render index page
	return render_template('index.html', title='Modbus', data = data)

# Test connection - tries to connect to modbus,
# redirects to 'Index' in order to display connection result message
@app.route("/test_connection")
def test_connection():
	# put default message into page data dictionary
	data = {'message':'Unknown error, check log'}

	q, ch, cnn = openQueue(CommandQueue)
	
	data = {'command':'modbus_ping'}

	body = json.dumps(data)

	ch.basic_publish(exchange='', routing_key=q, body=body)

	# Cache last message in session
	session['message'] = "Check log"

	closeQueue(ch, cnn)

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
	print("Got address " + address)
	if address:
		# If address was present in form, save it to database!
		datastorage.set_address(address)

	# Redirect to modbus connection test
	return redirect(url_for('test_connection'))

# Toggle widget - POST utility method, called when user wants to toggle widget on/off
# saves status to database, redirects to 'Index'
@app.route("/toggle_widget", methods=['GET', 'POST'])
def toggle_widget():
	# Get widget id from form
	widget_id = request.args.get('widget_id', 0)
	if not widget_id:
		# If theres no widget id in form, return error and redirect to index
		print("Error: toggle_widget: no widget_id in form!")
		return redirect(url_for("index"))

	# Get widget by id from database
	db_context = db.get_db()
	cur = db_context.cursor()
	cur.execute ('SELECT * FROM widgets WHERE id == ?', [widget_id])
	widgets = cur.fetchone()

	# Get widget status
	status = widgets['status']
	print ("Status of '" + widgets['name'] + "'" + str(status) + "'!")

	# Toggle status itself
	if status == 0:
		status = 1
	else:
		status = 0

	# Update widget status in database
	cur.execute ('UPDATE widgets SET status = ? WHERE id == ?', [status, widget_id])
	print ("Changed status of '" + widgets['name'] + "' to '" + str(status) + "'!")

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
		print("Error: edit_widget: no widget_id in form!")
		return redirect(url_for("index"))

	# Get widget by id from database
	db_context = db.get_db()
	cur = db_context.cursor()
	cur.execute ('SELECT * FROM widgets WHERE id == ?', [widget_id])

	data = {'title':'Edit'}
	data['widget'] = cur.fetchone()

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
		return render_template('add_widget.html', title="Add widget", data=data, widget=data['widget'])

# Post edit - utility method, called by widget edit or creation page
# Can commit new, update existing or delete widget from database
@app.route('/post_edit', methods=['GET', 'POST'])
def post_edit():
	# Dispath by 'Submit' to decide what to do next
	if 'Submit' in request.args:
		app.logger.warning("Submit: " + request.args['Submit'])
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
		app.logger.error("No Submit!")
	return redirect(url_for('index'))

# Update widget - method which simplifies updating widget in database
def update_widget(id):
	name = request.args.get("name")
	type_id = request.args.get("type")
	img = request.args.get("img")

	# Update existing widget by id in database
	db_context = db.get_db()
	cur = db_context.cursor()
	cur.execute ('UPDATE widgets SET name = ?, type = ?, img = ? WHERE id == ?', [name, type_id, img, id])
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
	return "Check log"

# Send widgets via modbus - utility method for modbus packet creation
def send_widgets_via_modbus():
	# Connect to modbus
	#modbus = sm.get_modbus()

	# Get widgets from database
	data = {'command':'modbus_send'}
	temp_widgets = datastorage.get_widgets()

	temp_array = []
	for widget in temp_widgets:
		temp_array.insert({'status':widget['status']})
	
	data['widgets'] = temp_array

	body = json.dumps(data)

	publishToQueue(CommandQueue, body)

# Python specific - startup of flask server
def start():
	app.run(debug=True, host='0.0.0.0')

if __name__ == '__main__':
    start()
