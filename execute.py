import os
import glob2
from base import Base
from message_publisher import MessagePublisher
from script_runner import ScriptRunner

class Execute(Base):
    def __init__(self, message):
        Base.__init__(self, __name__)
        self.home_directory = '/home/shippable'
        self.message = self.__validate_message(message)
        self.step_name = self.config['STEP_NAME'].lower()
        self.step = self.get_top_of_stack(self.message)
        self.__validate_step_content(self.step)
        self.total_report_filesize_bytes = 0

        self.user_publisher = MessagePublisher(
            self.module,
            self.config,
            self.config['SHIPPABLE_AMQP_URL'])

        self.overall_status = self.message['overAllStatus']

    def __validate_message(self, message):
        self.log.debug('Validating message format')
        error_message = ''
        error_occurred = False
        try:
            execute_plan = message
            self.headers = execute_plan.get('headers')
            self.headers['buildId'] = self.headers.get('id')
            self.config['DM_QUEUE'] = execute_plan['listeningQueue']
            self.log.debug('Valid message received')
            return execute_plan
        except ValueError as val_err:
            error_message = 'Invalid execute plan received while deploying: ' \
                            'Error:{0} : {1}'.format(str(val_err), message)
            error_occurred = True
        except Exception as exc:
            error_message = 'Invalid execute plan received while deploying : ' \
                            'Error : {0} : {1}'.format(str(exc), message)
            error_occurred = True
        finally:
            if error_occurred:
                self.log.error(error_message, self.log.logtype['USER'])
                raise Exception(error_message)

    def __validate_step_content(self, step):
        self.log.debug('Validating message content')

        if step is None:
            error_message = 'No step data provided'
            raise Exception(error_message)

        if not step.get('name'):
            error_message = 'No step name provided: '\
                    ' : {0}'.format(step)
            raise Exception(error_message)

        if not step.get('payload'):
            error_message = 'Invalid step content, no payload provided : ' \
                            ' : {0}'.format(step)
            raise Exception(error_message)

        if not step.get('boot'):
            error_message = 'No boot section in step {0}'.format(
                step)
            raise Exception(error_message)
        boot_section = step.get('boot')

        self.container_name = boot_section.get('containerName')

        step_payload = step.get('payload')
        self.step_scripts = step_payload.get('scripts')

        self.execute_on_failure = step.get('executeOnFailure', False)

        if self.step_scripts is None:
            error_message = 'Invalid step content, no "scripts"' \
                            'data provided : {0}'.format(step)
            raise Exception(error_message)

        self.log.debug('Valid step data received')

    def run(self):
        self.log.debug('Executing step : {0}'.format(self.step))

        script_status = self.__execute()

        if self.overall_status == self.STATUS['PROCESSING'] or \
                self.overall_status == self.STATUS['SUCCESS']:
            ## update overallStatus ONLY if message was in PROCESSING
            ## or SUCCESS state

            self.overall_status = script_status
            self.message['overAllStatus'] = self.overall_status
            self.log.debug('Updated overall status: {0}'.format(script_status))
        else:
            self.log.debug('Overall status not PROCESSING: {0}'.format(
                self.overall_status))

        self.pop_step(self.message, self.step)
        self.__requeue_message()
        self.__write_terminate_file()

    def __execute(self):
        self.log.debug('Executing step')

        if self.step_scripts:
            self.log.debug('Step scripts: {0}'.format(
                self.step_scripts))
            scripts_execution_success = self.STATUS['SUCCESS']
            for script in self.step_scripts:
                script_runner = ScriptRunner(header_params=self.headers)
                script_status = script_runner.execute_script(script)

                if script_status != self.STATUS['SUCCESS']:
                    scripts_execution_success = script_status

                self.log.debug('Script competed with status: {0}'.format(
                    script_status))

            self.log.debug('All scripts competed with status: {0}'.format(
                scripts_execution_success))

            coverage_reports = self.__get_coverage_reports()
            self.log.debug('Loaded coverage reports from disk: {0}'.format(
                coverage_reports))
            if coverage_reports:
                self.message['coverageResults'] = coverage_reports

            test_reports = self.__get_test_reports()
            self.log.debug('Loaded test reports from disk: {0}'.format(
                test_reports))
            if test_reports:
                self.message['testResults'] = test_reports

            return scripts_execution_success
        else:
            self.log.error('No scripts to execute, returning error')
            return self.STATUS['FAILED']

    def __requeue_message(self):
        self.log.debug('Reueueing back remaining message {0}'.format(
            self.message))
        self.user_publisher.publish_message(
            self.message,
            self.config['DM_QUEUE'],
            amqp_url=self.config['VHOST_AMQP_URL'],
            exchange=self.config['DEFAULT_EXCHANGE'],
            retry_count=0)

    def __get_test_reports(self):
        self.log.info('Getting test reports from {0}'.format(
            self.config['ARTIFACTS_DIR']))
        test_reports = []

        src_dir = self.config['ARTIFACTS_DIR']
        test_results_glob_pattern = os.path.join(
            src_dir,
            '**/**/**/shippable/testresults/**/*.xml')

        self.log.debug('Looking for test results in {0}'.format(
            test_results_glob_pattern))

        test_report_filenames = glob2.glob(test_results_glob_pattern)

        if len(test_report_filenames) > 0:
            self.log.debug('Found {0} test reports'.format(
                len(test_report_filenames)))
            self.log.debug(test_report_filenames)

            for test_report_filename in test_report_filenames:
                current_filesize_bytes = os.path.getsize(test_report_filename)
                if (self.total_report_filesize_bytes + current_filesize_bytes >= self.config['MAX_USER_REPORT_SIZE_BYTES']):
                    continue

                self.total_report_filesize_bytes += current_filesize_bytes
                with open(test_report_filename) as test_file:
                    test_reports.append({
                        'content': test_file.read(),
                        'filename': test_report_filename
                        })

            self.log.info('Test reports parsed : {0}'.format(test_reports))
        else:
            self.log.info('No test reports to upload')
        return test_reports

    def __get_coverage_reports(self):
        self.log.info('getting coverage reports from {0}'.format(
            self.config['ARTIFACTS_DIR']))
        coverage_reports = []

        src_dir = self.config['ARTIFACTS_DIR']
        xml_coverage_glob_pattern = os.path.join(
            src_dir,
            '**/**/**/shippable/codecoverage/**/*.xml')

        self.log.debug('Looking for coverage reports in {0}'.format(
            xml_coverage_glob_pattern))

        xml_coverage_report_filenames = glob2.glob(xml_coverage_glob_pattern)

        csv_coverage_glob_pattern = os.path.join(
            src_dir,
            '**/**/**/shippable/codecoverage/**/*.csv')

        self.log.debug('Looking for coverage reports in {0}'.format(
            csv_coverage_glob_pattern))

        csv_coverage_report_filenames = glob2.glob(csv_coverage_glob_pattern)

        coverage_report_filenames = (
            xml_coverage_report_filenames + csv_coverage_report_filenames)

        if len(coverage_report_filenames) > 0:
            self.log.debug('Found {0} coverage reports'.format(
                len(coverage_report_filenames)))

            self.log.debug(coverage_report_filenames)

            for coverage_report_filename in coverage_report_filenames:
                current_filesize_bytes = os.path.getsize(coverage_report_filename)
                if (self.total_report_filesize_bytes + current_filesize_bytes >= self.config['MAX_USER_REPORT_SIZE_BYTES']):
                    continue

                self.total_report_filesize_bytes += current_filesize_bytes
                with open(coverage_report_filename) as report_file:
                    coverage_reports.append({
                        'content': report_file.read(),
                        'filename': coverage_report_filename
                        })
            self.log.info('got coverage reports: {0}'.format(coverage_reports))
        else:
            self.log.info('No coverage reports to upload')
        return coverage_reports

    def __write_terminate_file(self):
        if not os.path.exists(self.home_directory):
            os.makedirs(self.home_directory)
        with open('{0}/terminate'.format(self.home_directory), 'a') as the_file:
            the_file.write('true')
