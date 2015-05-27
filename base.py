import os
import threading
import traceback
import datetime
import subprocess
from config import Config
from app_logger import AppLogger

class Base(object):
    STATUS = {
        'WAITING': 0,
        'QUEUED': 10,
        'PROCESSING': 20,
        'SUCCESS': 30,
        'SKIPPED': 40,
        'UNSTABLE': 50,
        'TIMEOUT': 60,
        'CANCELLED': 70,
        'FAILED': 80
    }

    def __init__(self, module_name):
        self.module = module_name
        self.config = Config()
        self.log = AppLogger(self.config, self.module)

    def command(self, cmd, working_dir, script=False):
        self.log.info('Executing command: {0}\nDir: {1}'.format(
            cmd, working_dir))
        if script:
            self.log.debug('Executing user command')
            return self.__exec_user_command(cmd, working_dir)
        else:
            self.log.debug('Executing system command')
            self.__exec_system_command(cmd, working_dir)

    def __exec_system_command(self, cmd, working_dir):
        self.log.debug('System command runner \nCmd: {0}\nDir: {1}'.format(
            cmd, working_dir))
        cmd = '{0} 2>&1'.format(cmd)
        self.log.info('Running {0}'.format(cmd))

        proc = None
        try:
            proc = subprocess.Popen(
                cmd, shell=True,
                stdout=subprocess.PIPE,
                cwd=working_dir,
                env=os.environ.copy(),
                universal_newlines=True)
            stdout = proc.communicate()
            returncode = proc.returncode
            if returncode != 0:
                raise Exception(stdout)
            else:
                self.log.debug('System command completed {0}\nOut:{1}'.format(
                    cmd, stdout))
        except Exception as exc:
            error_message = 'Error running system command. Err: {0}'.format(exc)
            self.log.error(error_message)
            trace = traceback.format_exc()
            self.log.error(exc)
            self.log.error(trace)
            raise Exception(error_message)
        return stdout

    def __exec_user_command(self, cmd, working_dir):
        self.log.debug('Executing streaming command {0}'.format(cmd))
        current_step_state = self.STATUS['FAILED']

        command_thread_result = {
            'success': False,
            'returncode': None
        }

        command_thread = threading.Thread(
            target=self.__command_runner,
            args=(cmd, working_dir, command_thread_result,))

        command_thread.start()

        self.log.debug('Waiting for command thread to complete')
        command_thread.join(self.config['MAX_COMMAND_SECONDS'])
        self.log.debug('Command thread join has returned. Result: {0}'\
                .format(command_thread_result))

        if command_thread.is_alive():
            self.log.log_command_err('Command timed out')
            self.log.error('Command thread is still running')
            is_command_success = False
            current_step_state = self.STATUS['TIMEOUT']
            self.log.log_command_err('Command thread timed out')
        else:
            is_command_success = command_thread_result['success']
            if is_command_success:
                self.log.debug('command executed successfully: {0}'.format(cmd))
                current_step_state = self.STATUS['SUCCESS']
            else:
                error_message = 'Command failed : {0}'.format(cmd)
                exception = command_thread_result.get('exception', None)
                if exception:
                    error_message += '\nException {0}'.format(exception)
                self.log.error(error_message)
                current_step_state = self.STATUS['FAILED']
                self.log.error(error_message)

        return current_step_state

    def __command_runner(self, cmd, working_dir, result):
        self.log.debug('command runner \nCmd: {0}\nDir: {1}'.format(
            cmd, working_dir))
        cmd = '{0} 2>&1'.format(cmd)
        self.log.info('Running {0}'.format(cmd))

        proc = None
        success = False
        try:
            proc = subprocess.Popen(
                cmd, shell=True,
                stdout=subprocess.PIPE,
                cwd=working_dir,
                env=os.environ.copy(),
                universal_newlines=True)

            exception = 'Invalid or no script tags received'
            for line in iter(proc.stdout.readline, ''):
                if line.startswith('__SH__BUILD_END_SUCCESS__'):
                    ## Build script specific processing
                    success = True
                    break
                elif line.startswith('__SH__BUILD_END_FAILURE__'):
                    ## Build script specific processing
                    success = False
                    exception = 'Build failure tag received'
                    break
                elif line.startswith('__SH__ARCHIVE_END__'):
                    success = True
                    break
                elif line.startswith('__SH__SCRIPT_END_SUCCESS__'):
                    success = True
                    break
                elif line.startswith('__SH__SCRIPT_END_FAILURE__'):
                    success = False
                    exception = 'Script failure tag received'
                    break
                else:
                    self.log.debug(line)
                    #self.log.append_console_buffer(line)

            proc.kill()
            if success == False:
                self.log.debug('Command failure')
                result['returncode'] = 99
                result['success'] = False
                result['exception'] = exception
            else:
                self.log.debug('Command successful')
                result['returncode'] = 0
                result['success'] = True
        except Exception as exc:
            self.log.error('Exception while running command: {0}'.format(exc))
            trace = traceback.format_exc()
            self.log.error(trace)
            result['returncode'] = 98
            result['success'] = False
            result['exception'] = trace

        self.log.info('Command returned {0}'.format(result['returncode']))

    def __utc_now(self):
        return datetime.datetime.utcnow().isoformat()


    def pop_step(self, execute_plan, step):
        self.log.debug('popping the top of stack: {0}'\
                .format(execute_plan['steps']))
        try:
            for k in execute_plan['steps'].keys():
                if k == step['step_key']:
                    del execute_plan['steps'][k]
                    self.log.debug('popped out top of stack. \n stack {0}'\
                        .format(execute_plan['steps']))
            return execute_plan
        except Exception as exc:
            self.log.error('error occurred while poping ' \
                'step: {0}'.format(str(exc)))
            raise exc

    def get_top_of_stack(self, execute_plan):
        error_occurred = False
        error_message = ''
        try:
            self.log.info('inside get_top_of_stack')
            steps = execute_plan.get('steps', None)
            if steps is None:
                error_message = 'No steps found in the execute plan: {0}'\
                        .format(execute_plan)
                error_occurred = True
                return
            if len(steps) == 0:
                self.log.info('No steps present in execute plan, returning' \
                    'empty TopOfStack')
                return None
            keys = []
            for k in steps.keys():
                keys.append(int(str(k)))

            self.log.debug('steps keys {0}'.format(keys))
            keys.sort()
            self.log.debug('sorted keys {0}'.format(keys))
            current_step_key = str(keys[0])
            current_step = steps[current_step_key]
            current_step['step_key'] = current_step_key
            return current_step
        except Exception as exc:
            error_message = 'Error occurred while trying to get the step' \
                    ' from execute plan \nError: {0} execute plan: {1}' \
                    .format(str(exc), execute_plan)
            error_occurred = True
        finally:
            if error_occurred:
                raise Exception(error_message)
