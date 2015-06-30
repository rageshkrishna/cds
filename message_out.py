import json
import time
import logging
import requests

class MessageOut(object):
    def __init__(self, module, config):
        self.log = None
        self.module = module
        self.config = config
        self.vortex_url = self.config['SHIPPABLE_VORTEX_URL']
        self.__setup_logging()

    def __setup_logging(self):
        logging.basicConfig(level=logging.DEBUG)
        self.log = logging.getLogger(self.module)
        self.log.setLevel(self.config['LOG_LEVEL'])

    def console(self, message):
        self.log.debug('Posting message : {0}'.format(message))
        post_data = {
            "where": "micro.cu",
            "payload": {
                "headers": message.get('headers'),
                "console": message.get('console')
            }
        }
        headers = {
            'Authorization': 'apiToken {0}'.format(
                self.config['SHIPPABLE_API_TOKEN']),
            'content-type': 'application/json'
        }
        while True:
            try:
                request = requests.post(
                    self.vortex_url,
                    data=json.dumps(post_data),
                    headers=headers)
                self.log.debug('post console response : {0}'.format(request))
                break
            except Exception as exc:
                self.log.error('Console push to vortex failed, \n ' \
                    'Erro {0} \n retrying...'.format(str(exc)))
                time.sleep(self.config['VORTEX_RETRY_INTERVAL'])


    def status(self, headers, status):
        self.log.debug('Posting status: {0}'.format(status))
        post_data = {
            "where": "micro.su",
            "payload": {
                "headers": headers,
                "status": status
            }
        }
        headers = {
            'Authorization': 'apiToken {0}'.format(
                self.config['SHIPPABLE_API_TOKEN']),
            'content-type': 'application/json'
        }
        while True:
            try:
                request = requests.post(
                    self.vortex_url,
                    data=json.dumps(post_data),
                    headers=headers)
                self.log.debug('post status response : {0}'.format(request))
                break
            except Exception as exc:
                self.log.error('Console push to vortex failed, \n ' \
                    'Erro {0} \n retrying...'.format(str(exc)))
                time.sleep(self.config['VORTEX_RETRY_INTERVAL'])
