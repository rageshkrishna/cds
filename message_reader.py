import json
import traceback
import pika
import uuid
import sys

class MessageReader(object):

    EXCHANGE_TYPE = 'topic'

    def __init__(self, reader, url, read_queue_name, default_exchange=None):
        self.config = reader.config
        self.log = reader.log
        self.url = url
        self.exchange = default_exchange
        self.queue = read_queue_name
        self.channel = None
        self.connection = None
        #self.initialize_read_queue()

    def initialize_read_queue(self):
        self.log.info('Connecting to {0}'.format(self.url))
        try:
            parameters = pika.URLParameters(self.url)
            self.log.info('parsed url params {0}'.format(parameters))
            self.connection = pika.BlockingConnection(parameters)
            self.log.debug('connection done {0}'.format(self.connection))
            self.channel = self.connection.channel()
            self.log.debug('channel connected: {0}. ex {1}'.format(
                self.channel, self.exchange))
            self.log.info('Exchange successfully initialied: {0}'.format(
                self.exchange))
            self.connection.close()
            self.log.info('Read queue successfully initialized: {0}'.format(
                self.queue))
        except Exception as exc:
            self.log.error('Error while creating read queue: {0}'.format(exc))
            raise exc

    def connect_and_read(self, callback, retry_count=0):
        method_frame = None
        try:
            self.log.info('Connecting to {0}'.format(self.url))
            parameters = pika.URLParameters(self.url)
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()

            # pylint: disable=W0612,C0301
            method_frame, header_frame, body = self.channel.basic_get(self.queue)
            # pylint: enable=W0612,C0301

            self.log.debug('Tried reading next queued message')

            ## received a message ##
            if method_frame and callback:
                body = str(body)
                body = body.replace("\n\t", "|")
                message = json.loads(body)

                message_id = message.get('messageId', None)
                if message_id != self.config['MESSAGE_ID']:
                    self.log.error('Invalid DS message received' \
                        ' Message ID Mismatch. Message ID: {0}, ' \
                        '\nMF: {1}'.format(message_id, method_frame))
                    # recurse and read other messages from same connection
                    # Note: connection is not closed while recursing because all
                    # messages are being read over a single connection.
                    # DO NOT close the connection here to avoid infinte loops
                    return self.connect_and_read(callback)
                else:
                    # message ID correct, process message
                    response = {}
                    response = callback(message)
                    if not response['success']:
                        self.log.debug('Invalid DS message received,' \
                            '\nErr: {0}'.format(response['error']))
                        ## recurse and read other messages from same connection
                        return self.connect_and_read(callback)
                    else:
                        self.log.debug('Valid message received, acknowledging')
                        self.channel.basic_ack(method_frame.delivery_tag)
            else:
                self.log.debug('No message received, exiting')
        except Exception as exc:
            trace = traceback.format_exc()
            self.log.error('Error occurred while reading message. ' \
                '\nErr {0}\n{1}'.format(exc, trace))
            if self.connection and self.channel and method_frame:
                self.channel.basic_reject(method_frame.delivery_tag)
            if retry_count < 5:
                retry_count += 1
                self.log.error('Error occurred while reading message, trying again ' + retry_count)
                self.connect_and_read(callback, retry_count)
            else:
                raise exc

        finally:
            if self.connection is not None:
                self.log.debug('Closing connection {0}'.format(self.connection))
                self.connection.close()
            self.connection = None
            self.channel = None
            quit()

    def ping(self):
        if self.connection is not None:
            self.channel.basic_publish(
                exchange=self.exchange,
                routing_key='pint', body="ping",
                properties=pika.BasicProperties(message_id=str(uuid.uuid4())))
