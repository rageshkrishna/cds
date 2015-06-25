import sys
import logging
import os
from urlparse import urlparse

class Config(dict):
    """
    Global config. DS does not boot up unless all variables defined here are
    initialized
    """
    def __init__(self):
        print('Setting up configuration')
        self['CONTAINER_NAME'] = os.getenv('CONTAINER_NAME', '')
        self['ITINERARY'] = os.getenv('ITINERARY', None)
        self['MESSAGE_ID'] = os.getenv('MESSAGE_ID', '')

        self['LISTEN_QUEUE'] = os.getenv('LISTEN_QUEUE', '')

        self['VHOST_AMQP_URL'] = os.getenv('VHOST_AMQP_URL')
        self['SHIPPABLE_AMQP_URL'] = os.getenv('SHIPPABLE_AMQP_URL')
        self['CONTAINER_NAME'] = os.getenv('CONTAINER_NAME', '')
        self['STEP_NAME'] = os.getenv('STEP_NAME', '')
        self['SHIPPABLE_VORTEX_URL'] = os.getenv('SHIPPABLE_VORTEX_URL')
        self['SHIPPABLE_API_TOKEN'] = os.getenv('SHIPPABLE_API_TOKEN', '')

        self['DEFAULT_EXCHANGE'] = 'shippableEx'
        self['RUN_MODE'] = os.getenv('RUN_MODE', 'PROD')
        self['LOG_LEVEL'] = os.getenv('LOG_LEVEL', logging.DEBUG)

        default_cmd_timeout = 60 * 30
        self['MAX_COMMAND_SECONDS'] = int(os.getenv('MAX_BUILD_SECONDS', default_cmd_timeout))

        self['MAX_USER_LOG_SIZE'] = 12 * 1024 * 1024
        self['CONSOLE_BUFFER_LENGTH'] = 10

        self['HOME'] = os.getenv('HOME')
        self['USER'] = os.getenv('USER')
        self['ARTIFACTS_DIR'] = os.getenv('ARTIFACTS_DIR', '/tmp/shippable')

        ## the boot message is used by hdq to check whether ds dequeued correct
        ## message or not
        self['BOOT_SUCCESS_MESSAGE'] = os.getenv(
            'BOOT_SUCCESS_MESSAGE', '__SH_DS_BOOT_SUCCESSFUL__')

        system_logging_enabled = os.getenv('SYSTEM_LOGGING_ENABLED', False)
        if system_logging_enabled in ['true', 'yes', 'True', 'y']:
            self['SYSTEM_LOGGING_ENABLED'] = True
        else:
            self['SYSTEM_LOGGING_ENABLED'] = False

        user_system_logging_enabled = os.getenv(
            'USER_SYSTEM_LOGGING_ENABLED', False)
        if user_system_logging_enabled in ['true', 'yes', 'True', 'y']:
            self['USER_SYSTEM_LOGGING_ENABLED'] = True
        else:
            self['USER_SYSTEM_LOGGING_ENABLED'] = False

        self.validate_amqp_url('VHOST_AMQP_URL')
        self.validate_amqp_url('SHIPPABLE_AMQP_URL')

        for k, v in self.iteritems():
            if v == '':
                print('{0} has no value. Make sure the container environment has a '
                               'variable {0} with a valid value'.format(k))
                raise Exception('{0} has no value. Make sure the container environment has a '
                               'variable {0} with a valid value'.format(k))
            else:
                print('{0} - {1}'.format(k, v))

        sys.stdout.flush()

    def validate_amqp_url(self, key):
        if self[key]:
            parsed_url = urlparse(self[key])
            if not parsed_url.scheme:
                raise Exception('No protocol provided from {0}. '
                                'URL format: amqp(s)://user:pass@host:port/vhost'.format(self[key]))
            if not parsed_url.netloc:
                raise Exception('No host provided from {0}. '
                                'URL format: amqp(s)://user:pass@host:port/vhost'.format(self[key]))
        else:
            raise Exception('Missing env "{0}" provided'.format(key))

        if 'heartbeat_interval' not in self[key]:
            if '?' not in self[key]:
                self[key] += '?heartbeat_interval=0'
            else:
                self[key] += '&heartbeat_interval=0'
