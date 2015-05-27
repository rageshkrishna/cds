import sys
import traceback
from base import Base
from execute import Execute
from message_reader import MessageReader

class Listen(Base):
    def __init__(self):
        Base.__init__(self, __name__)
        self.log.info('Inside DS listener')
        self.message_reader = MessageReader(
            self, self.config["VHOST_AMQP_URL"],
            self.config['LISTEN_QUEUE'],
            self.config['DEFAULT_EXCHANGE'])

        self.itinerary = None
        self.execute = None
        self.log.info('Boot successful')

    def main(self):
        self.log.info('inside Listen main')
        try:
            self.message_reader.connect_and_read(self.handle_message_callback)
        except Exception as exc:
            self.log.error('Error starting listener - {0}'.format(exc))
        finally:
            self.log.debug('Cleaning up the listener')
            handlers = self.log.handlers[:]
            for handler in handlers:
                handler.close()
                self.log.remove_handler(handler)
            print 'STOP_TAILING'
            sys.stdout.flush()
            
    def handle_message_callback(self, message, is_redelivered=True):
        self.log.info('Message callback invoked: {0}'.format(is_redelivered))
        response = {'success': True}
        try:
            self.execute = Execute(message)

            if self.execute.container_name != self.config['CONTAINER_NAME']:
                error_message = 'Invalid DS message received. ' \
                    'Unmatched container names. \n CONFIG: {0}' \
                    '\nCONTAINER_NAME {1}'.format(
                        self.config, self.execute.container_name)
                self.log.error(error_message)
                response['success'] = False
                response['error'] = error_message
                raise Exception(error_message)
            else:
                self.log.info('Valid DS message : {0}'.format(
                    self.config['BOOT_SUCCESS_MESSAGE']))
                self.log.info(self.execute.message)

                # this is read by HDQ to decide whether DS container
                # boot was successful or not
                print self.config['BOOT_SUCCESS_MESSAGE']
                sys.stdout.flush()

            self.execute.run()
        except Exception as exc:
            self.log.error(str(exc))
            trace = traceback.format_exc()
            self.log.debug(trace)
        return response
