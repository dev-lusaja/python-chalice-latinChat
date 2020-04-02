import os

from boto3.session import Session
from chalice import Chalice

from chalicelib.storage import Storage
from chalicelib.sender import Sender
from chalicelib.handler import Handler

app = Chalice(app_name='latinChat')
try:
    app.debug = eval(os.getenv("DEBUG"))
    app.websocket_api.session = Session()
    app.experimental_feature_flags.update([
        'WEBSOCKETS'
    ])

    STORAGE = Storage.from_env()
    SENDER = Sender(app, STORAGE)
    HANDLER = Handler(STORAGE, SENDER)
except Exception as e:
    print(e)


@app.on_ws_connect()
def connect(event):
    print('connect')
    print('ID: ' + event.connection_id)
    STORAGE.create_connection(event.connection_id)


@app.on_ws_disconnect()
def disconnect(event):
    print('disconnect')
    STORAGE.delete_connection(event.connection_id)

@app.on_ws_message()
def message(event):
    print('message')
    HANDLER.handle(event.connection_id, event.body)
