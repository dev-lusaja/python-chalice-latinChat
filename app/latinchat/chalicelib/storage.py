import os

import boto3
from boto3.dynamodb.conditions import Key

class Storage(object):
    """An abstraction to interact with the DynamoDB Table."""
    def __init__(self, table):
        """Initialize Storage object

        :param table: A boto3 dynamodb Table resource object.
        """
        self._table = table

    @classmethod
    def from_env(cls):
        """Create table from the environment.

        The environment variable TABLE is present for a deployed application
        since it is set in all of the Lambda functions by a CloudFormation
        reference. We default to '', which will happen when we run
        ``chalice package`` since it loads the application, and no
        environment variable has been set. For local testing, a value should
        be manually set in the environment if '' will not suffice.
        """
        table_name = os.environ.get('TABLE', '')
        table = boto3.resource('dynamodb').Table(table_name)
        return cls(table)

    def create_connection(self, connection_id):
        """Create a new connection object in the dtabase.

        When a new connection is created, we create a stub for
        it in the table. The stub uses a primary key of the
        connection_id and a sort key of username_. This translates
        to a connection with an unset username. The first message
        sent over the wire from the connection is to be used as the
        username, and this entry will be re-written.

        :param connection_id: The connection id to write to
            the table.
        """
        self._table.put_item(
            Item={
                'PK': connection_id,
                'SK': 'username_',
            },
        )

    def set_username(self, connection_id, old_name, username):
        """Set the username.

        The SK entry that goes with this connection id that starts
        with username_ is taken to be the username. The previous
        entry needs to be deleted, and a new entry needs to be
        written.

        :param connection_id: Connection id of the user trying to
            change their name.

        :param old_name: The original username. Since this is part of
            the key, it needs to be deleted and re-created rather than
            updated.

        :param username: The new username the user wants.
        """
        self._table.delete_item(
            Key={
                'PK': connection_id,
                'SK': 'username_%s' % old_name,
            },
        )
        self._table.put_item(
            Item={
                'PK': connection_id,
                'SK': 'username_%s' % username,
            },
        )

    def list_rooms(self):
        """Get a list of all rooms that exist.

        Scan through the table looking for SKs that start with room_
        which indicates a room that a user is in. Collect a unique set
        of those and return them.
        """
        r = self._table.scan()
        rooms = set([item['SK'].split('_', 1)[1] for item in r['Items']
                     if item['SK'].startswith('room_')])
        return rooms

    def set_room(self, connection_id, room):
        """Set the room a user is currently in.

        The room a user is in is in the form of an SK that starts with
        room_ prefix.

        :param connection_id: The connection id to move to a room.

        :param room: The room name to join.
        """
        self._table.put_item(
            Item={
                'PK': connection_id,
                'SK': 'room_%s' % room,
            },
        )

    def remove_room(self, connection_id, room):
        """Remove a user from a room.

        The room a user is in is in the form of an SK that starts with
        room_ prefix. To leave a room we need to delete this entry.

        :param connection_id: The connection id to move to a room.

        :param room: The room name to join.
        """
        self._table.delete_item(
            Key={
                'PK': connection_id,
                'SK': 'room_%s' % room,
            },
        )

    def get_connection_ids_by_room(self, room):
        """Find all connection ids that go to a room.

        This is needed whenever we broadcast to a room. We collect all
        their connection ids so we can send messages to them. We use a
        ReverseLookup table here which inverts the PK, SK relationship
        creating a partition called room_{room}. Everything in that
        partition is a connection in the room.

        :param room: Room name to get all connection ids from.
        """
        r = self._table.query(
            IndexName='ReverseLookup',
            KeyConditionExpression=(
                Key('SK').eq('room_%s' % room)
            ),
            Select='ALL_ATTRIBUTES',
        )
        return [item['PK'] for item in r['Items']]

    def delete_connection(self, connection_id):
        """Delete a connection.

        Called when a connection is disconnected and all its entries need
        to be deleted.

        :param connection_id: The connection partition to delete from
            the table.
        """
        try:
            r = self._table.query(
                KeyConditionExpression=(
                    Key('PK').eq(connection_id)
                ),
                Select='ALL_ATTRIBUTES',
            )
            for item in r['Items']:
                self._table.delete_item(
                    Key={
                        'PK': connection_id,
                        'SK': item['SK'],
                    },
                )
        except Exception as e:
            print(e)

    def get_record_by_connection(self, connection_id):
        """Get all the properties associated with a connection.

        Each connection_id creates a partition in the table with multiple
        SK entries. Each SK entry is in the format {property}_{value}.
        This method reads all those records from the database and puts them
        all into dictionary and returns it.

        :param connection_id: The connection to get properties for.
        """
        r = self._table.query(
            KeyConditionExpression=(
                Key('PK').eq(connection_id)
            ),
            Select='ALL_ATTRIBUTES',
        )
        r = {
            entry['SK'].split('_', 1)[0]: entry['SK'].split('_', 1)[1]
            for entry in r['Items']
        }
        return r
