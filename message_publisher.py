import pika
import time
import json
import uuid
import logging

class MessagePublisher(object):
    EXCHANGE_TYPE = 'topic'
    def __init__(self, module, config, url, default_exchange=None):
        self.config = config
        self.module = module
        self.channel = None
        self.url = str(url)
        logging.basicConfig(level=logging.DEBUG)
        self.log = logging.getLogger(module)
        self.log.setLevel(logging.DEBUG)
        self.exchange = default_exchange

        if default_exchange is None:
            self.exchange = self.config["DEFAULT_EXCHANGE"]

    def __str__(self):
        return 'URL {0} EXC: {1} MOD: {2}'.format(self.url, self.exchange, self.module)

    def __connect_and_publish(self, messages):
        """This connects to RabbitMQ with a blocking connection, sends
        messages from the (message, routing key) tuples in the messages list,
        and closes the connection.
        """
        try:
            self.log.info('Connecting to {0}'.format(self.url))
            parameters = pika.URLParameters(self.url)
            self.log.info('parsed url params {0}'.format(parameters))
            connection = pika.BlockingConnection(parameters)
            self.log.debug('connection done {0}'.format(connection))
            self.channel = connection.channel()
            self.log.debug('channel connected: {0}. ex {1}'.format(
                self.channel, self.exchange))
            #self.channel.exchange_declare(
            #    exchange=self.exchange,
            #    type="topic",
            #    passive=False,
            #    durable=True,
            #    auto_delete=False)

            self.log.debug('Exchange connected {0}'.format(self.exchange))
            while len(messages) > 0:
                message, key = messages.pop(0)
                properties = pika.BasicProperties(message_id=str(uuid.uuid4()))
                self.channel.basic_publish(
                    self.exchange,
                    routing_key=key,
                    body=json.dumps(message),
                    properties=properties)

            self.log.debug('Closing connection')
            connection.close()

        except pika.exceptions.AMQPConnectionError, exc:
            self.log.error('Could not connect to {0}. Error {1}' \
                    .format(self.url, exc))
            raise exc


    def publish_message(
            self, msg, queue, amqp_url=None, exchange=None, retry_count=0):
        self.queue = queue

        self.log.debug('Publishing message {0} \n Queue: {1}'.format(
            msg, queue))
        try:
            if amqp_url is not None:
                self.url = amqp_url
            if exchange is not None:
                self.exchange = exchange

            self.__connect_and_publish([(msg, str(queue))])
        except Exception as exc:
            if retry_count > 5:
                raise Exception(str(exc))
            else:
                self.log.warn('publish status update message step failed ' \
                    'for retry count : {0} with error {1}'.format(
                        retry_count, str(exc)))
                time.sleep(1)
                self.publish_message(
                    msg=msg,
                    queue=queue,
                    amqp_url=amqp_url,
                    exchange=exchange,
                    retry_count=retry_count + 1)
