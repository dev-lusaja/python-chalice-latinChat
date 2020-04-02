from chalice import WebsocketDisconnectedError

class Sender(object):
    """Class to send messages over websockets."""
    def __init__(self, app, storage):
        """Initialize a sender object.

        :param app: A Chalice application object.

        :param storage: A Storage object.
        """
        self._app = app
        self._storage = storage

    def send(self, connection_id, message):
        """Send a message over a websocket.

        :param connection_id: API Gateway Connection ID to send a
            message to.

        :param message: The message to send to the connection.
        """
        try:
            # Call the chalice websocket api send method
            self._app.websocket_api.send(connection_id, message)
        except WebsocketDisconnectedError as e:
            # If the websocket has been closed, we delete the connection
            # from our database.
            self._storage.delete_connection(e.connection_id)

    def broadcast(self, connection_ids, message):
        """"Send a message to multiple connections.

        :param connection_id: A list of API Gateway Connection IDs to
            send the message to.

        :param message: The message to send to the connections.
        """
        for cid in connection_ids:
            self.send(cid, message)