#*******************************************************************************
# Licensed Materials - Property of IBM
# (c) Copyright IBM Corp. 2022, 2023. All Rights Reserved.
#
# Note to U.S. Government Users Restricted Rights:
# Use, duplication or disclosure restricted by GSA ADP Schedule
# Contract with IBM Corp.
#*******************************************************************************

import yaml
import os
from pathlib import Path
import sys
from ansible import constants as C
from ansible.utils.path import makedirs_safe
from ansible.plugins.callback.default import CallbackModule as Default
from ansible.parsing.yaml.dumper import AnsibleDumper
import string
import re
from ansible.vars.clean import strip_internal_keys, module_response_deepcopy
from ansible.module_utils.common.text.converters import to_text
from _datetime import datetime
from wazideploy.service.utilities import Utilities

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent.parent.parent.parent)+'/python')
sys.path.insert(0, str(Path(__file__).resolve().parent))

from wazideploy_translator.service import evidences

__metaclass__ = type

DOCUMENTATION = '''
    author: IBM
    name: evidences
    type: stdout
    short_description: write playbook output to evidence log file
    description:
      - This callback writes playbook output to a file per host in the C(./evidences) directory
    extends_documentation_fragment:
      - default_callback
    requirements:
     - Whitelist in configuration
     - A writeable ./evidences directory by the user executing Ansible on the controller
    options:
      evidence_folder:
        default: ./evidences
        description: The folder where log files will be created.
        env:
          - name: EVIDENCES_FOLDER
        ini:
          - section: callback_evidences
            key: evidences_folder
'''

YAML_FILE_DEPLOY = 'task_deploy.yml'
YAML_FILE_ACTIVITY = 'task_activity.yml'
YAML_FILE_ACTION = 'task_action.yml'
YAML_FILE_STEP = 'task_step.yml'
YAML_FILE_SMF_RECORD = 'task_smf_record.yml'
ACTIVITY = 'wd_activity'
ACTION = 'wd_action'
STEP = 'wd_step'

class CallbackModule(Default):
    """
    logs playbook results, per host
    """
    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = 'stdout'
    CALLBACK_NAME = 'evidences'
    CALLBACK_NEEDS_WHITELIST = True

    all_evidences = {}
    current_evidences = None
    current_evidences_step = None
    current_evidences_step_result = None
    include_in_console = False

    def __init__(self):
        super(CallbackModule, self).__init__()

    def set_options(self, task_keys=None, var_options=None, direct=None):
        super(CallbackModule, self).set_options(task_keys=task_keys, var_options=var_options, direct=direct)

        self.evidence_folder = self.get_option("evidence_folder")
        if not os.path.exists(self.evidence_folder):
            makedirs_safe(self.evidence_folder)

    def v2_runner_on_ok(self, result):
        return_bool = self.log(result, evidences.EvidenceStatus.OK)
        if not return_bool:
            Default.v2_runner_on_ok(self, result)

    def v2_runner_on_failed(self, result, ignore_errors=False):
        self.log(result, evidences.EvidenceStatus.FAILED)
        Default.v2_runner_on_failed(self, result, ignore_errors)

    def v2_runner_on_skipped(self, result):
        self.log(result, evidences.EvidenceStatus.SKIPPED)
        Default.v2_runner_on_skipped(self, result)

    def v2_runner_item_on_skipped(self, result):
        if self.display_skipped_hosts:
            if self._last_task_banner != result._task._uuid:
                self._print_task_banner(result._task)

            self._clean_results(result._result, result._task.action)
            msg = "skipping: [%s]" % result._host.get_name()
            if self._run_is_verbose(result):
                msg += " => %s" % self._dump_results(result._result)
            self._display.display(msg, color=C.COLOR_SKIP)

    def v2_playbook_on_include(self, included_file):
        if self.include_in_console:
            Default.v2_playbook_on_include(self, included_file)

    def v2_playbook_on_stats(self, stats):
        all_evidences_file_name = []
        for evidence_host_name in self.all_evidences.keys():
            time = datetime.now()
            filename_for_evidences = f'{evidence_host_name}_evidences_{time.strftime("%Y%m%d%H%M%S")}.yml'
            path_evidences = os.path.abspath(os.path.join(self.evidence_folder, filename_for_evidences))
            all_evidences_file_name.append(path_evidences)
            Utilities.dump_to_yaml_file(self.all_evidences[evidence_host_name], path_evidences)
        Default.v2_playbook_on_stats(self, stats)
        for file_name in all_evidences_file_name:
            print(f'Evidences saved in {file_name}')


    def log (self, result, ok_skipped_failed):
        current_host = str(result._host.get_name())
        self.current_evidences = None
        self.current_evidences_step = None
        self.current_evidences_step_result = None
        if current_host in self.all_evidences:
            self.current_evidences = self.all_evidences[current_host]
            if len(self.current_evidences.activities) > 0:
                current_evidences_activity = self.current_evidences.activities[-1]
                if len(current_evidences_activity.actions) > 0:
                    current_evidences_action = current_evidences_activity.actions[-1]
                    if len(current_evidences_action.steps) > 0:
                        self.current_evidences_step = current_evidences_action.steps[-1]
                        self.current_evidences_step_result = self.current_evidences_step.step_result
        #self.debug_vars(result)
        playbook_name = None
        line_number = None
        if result._task.get_path():
            liste = self.playbook_name(result._task.get_path())
            playbook_name = liste[0]
            line_number = liste[1]
        if playbook_name is not None:
            parent_name = self.parent_name(result)
            if YAML_FILE_DEPLOY == playbook_name:
                if self.current_evidences is None:
                    self.current_evidences = evidences.Evidence()
                    self.current_evidences.status = evidences.EvidenceStatus.OK.value
                    self.all_evidences[current_host] = self.current_evidences
                if 'ansible_facts' in result._result:
                    current_dict = result._result['ansible_facts']
                    if current_dict and 'wd_deployment_plan' in current_dict:
                        current_plan_dict = current_dict['wd_deployment_plan']
                        if current_plan_dict:
                            if 'metadata' in current_plan_dict:
                                metadata_dict = current_plan_dict['metadata']
                                self.current_evidences.metadata = self.dump_json_in_yaml(metadata_dict)
                            else:
                                self.current_evidences.metadata = {}
                            if not 'annotations' in self.current_evidences.metadata:
                                self.current_evidences.metadata['annotations'] = {}
                            self.current_evidences.metadata['annotations']['environment_name'] = current_host
                            self.current_evidences.metadata['annotations']['deploy_timestamp'] = datetime.utcnow().strftime('%Y%m%d.%H%M%S.%f')[:-3]
                            self.current_evidences.metadata['annotations']['inventory_hostname'] = current_host
                            self.current_evidences.metadata['annotations']['ansible_host'] = str(result._host.vars['ansible_host'])
                            if 'manifests' in current_plan_dict:
                                manifests_dict = current_plan_dict['manifests']
                                self.current_evidences.manifests = self.dump_json_in_yaml(manifests_dict)
            elif YAML_FILE_ACTIVITY == playbook_name:
                if result._task.get_vars():
                    current_dict = result._task.get_vars()[ACTIVITY]
                    if current_dict:
                        ev_activity = evidences.EvidenceActivity()
                        ev_activity.name = str(current_dict['name'])
                        ev_activity.properties = self.dump_json_in_yaml(current_dict.get('properties', []))
                        self.current_evidences.activities.append(ev_activity)
            elif YAML_FILE_ACTION == playbook_name:
                if result._task.get_vars():
                    current_dict = result._task.get_vars()[ACTION]
                    if current_dict:
                        ev_action = evidences.EvidenceAction()
                        ev_action.name = str(current_dict['name'])
                        ev_action.properties = self.dump_json_in_yaml(current_dict.get('properties', []))
                        current_evidences_activity.actions.append(ev_action)
            elif YAML_FILE_STEP == playbook_name:
                if result._task.get_vars():
                    current_dict = result._task.get_vars()[STEP]
                    if current_dict:
                        self.current_evidences_step_result = None
                        ev_step = evidences.EvidenceStep()
                        ev_step.name = str(current_dict['name'])
                        ev_step.properties = self.dump_json_in_yaml(current_dict.get('properties', []))
                        ev_step.artifacts = self.dump_json_in_yaml(current_dict.get('artifacts', []))
                        if 'action' in result._task_fields and 'include_tasks' == result._task_fields['action'] \
                                and (self.current_evidences_step is None or self.current_evidences_step.name != ev_step.name):
                            self.current_evidences_step = ev_step
                            current_evidences_action.steps.append(ev_step)
                            if 'skip_reason' in result._result:
                                ev_step_result = evidences.EvidenceStepResult()
                                self.current_evidences_step.step_result = ev_step_result
                                ev_step_result.status = evidences.EvidenceStatus.SKIPPED.value
                                ev_step_result.msg = result._result['skip_reason']
                                ev_step_result.results = []
            elif YAML_FILE_STEP == parent_name:
                self.log_special_step(result, playbook_name, line_number, ok_skipped_failed)
            elif YAML_FILE_SMF_RECORD == playbook_name:
                if 'smf_record_shell_result' == result._task.register:
                    smf_record =  evidences.EvidenceSMFRecord()
                    self.current_evidences.metadata['annotations']['smf_record'] = smf_record
                    if evidences.EvidenceStatus.OK == ok_skipped_failed:
                        smf_record.status = evidences.EvidenceStatus.OK.value
                    else:
                        smf_record.status = evidences.EvidenceStatus.FAILED.value
                        smf_record.msg = f"stdout: {result._result['stdout']}\nstderr: {result._result['stderr']}"
            elif self.step_in_task_hierarchy(result):
                self.log_special_step(result, playbook_name, line_number, ok_skipped_failed)
            if result._task_fields:
                if 'no_log' in result._task_fields:
                    return bool(result._task_fields['no_log'])

    def step_in_task_hierarchy(self, result):
        task_hierarchy = []
        current_truc = result._task
        while current_truc.get_first_parent_include():
            task_hierarchy.append(current_truc.get_first_parent_include().get_path())
            current_truc = current_truc.get_first_parent_include()
        if len(task_hierarchy) > 0:
            for item in task_hierarchy:
                if self.playbook_name(item)[0] == YAML_FILE_STEP:
                    return True

    def log_special_step(self, result, playbook_name, line_number, ok_skipped_failed):
            if self.current_evidences_step_result is None:
                ev_step_result = evidences.EvidenceStepResult()
                self.current_evidences_step.step_result = ev_step_result
                self.current_evidences_step_result = ev_step_result
                self.current_evidences_step_result.status = evidences.EvidenceStatus.OK.value
                result_msg = playbook_name + ' : ' + evidences.EvidenceStatus.OK.value
                self.current_evidences_step_result.msg = result_msg
                ev_step_result.results = []
            current_ev_step_result = evidences.EvidenceStepResult()
            self.current_evidences_step_result.results.append(current_ev_step_result)
            msg = f'{playbook_name} line {line_number} : {result._task.get_name()}'
            current_ev_step_result.msg = msg
            current_ev_step_result.status = ok_skipped_failed
            if evidences.EvidenceStatus.OK == ok_skipped_failed:
                self.store_success_result(result, current_ev_step_result)
            elif evidences.EvidenceStatus.SKIPPED == ok_skipped_failed:
                self.store_success_result(result, current_ev_step_result)
            elif evidences.EvidenceStatus.FAILED == ok_skipped_failed:
                self.current_evidences_step_result.status = evidences.EvidenceStatus.FAILED.value
                self.current_evidences.status = evidences.EvidenceStatus.FAILED.value
                result_msg = playbook_name + ' : ' + evidences.EvidenceStatus.FAILED.value
                self.current_evidences_step_result.msg = result_msg
                self.store_failed_result(result, current_ev_step_result)

    def store_success_result(self, result, ev_step_result):
        dict_result = {}
        dict_result['register'] = str(result._task.register)
        dict_result['args'] = self.dump_json_in_yaml(result._task_fields['args'])
        action = result._task_fields['action']
        if 'fail' == action and action in result._result:
            dict_result['result'] = self.dump_json_in_yaml(result._result[action])
        else:
            dict_result['result'] = self.dump_json_in_yaml(result._result)
        ev_step_result.results = dict_result

    def store_failed_result(self, result, ev_step_result):
        dict_result = {}

        if result._task.register:
            dict_result['register'] = str(result._task.register)

        if result._task_fields and 'args' in result._task_fields:
            dict_result['args'] = self.dump_json_in_yaml(result._task_fields['args'])

        result_ok = False
        if result._task_fields and 'action' in result._task_fields:
            action = result._task_fields['action']
            if 'fail' == action and action in result._result:
                dict_result['result'] = self.dump_json_in_yaml(result._result[action])
                result_ok = True
        if not result_ok:
            dict_result['result'] = self.dump_json_in_yaml(result._result)
        ev_step_result.results = dict_result

    def playbook_name (self, current_path):
        path_and_line = current_path.split(':')
        file_name = os.path.basename(path_and_line[0])
        return [file_name, path_and_line[1]]

    def parent_name(self, result):
        if result._task.get_first_parent_include():
            return self.playbook_name(result._task.get_first_parent_include().get_path())[0]
        return None

    def dump_json_in_yaml(self, result):
        # All result keys stating with _ansible_ are internal, so remove them from the result before we output anything.
        abridged_result = strip_internal_keys(module_response_deepcopy(result))

        if 'changed' in abridged_result:
            del abridged_result['changed']

        if 'skipped' in abridged_result:
            del abridged_result['skipped']

        dumped = ''
        if abridged_result:
            dumped += '\n'
            dumped += to_text(yaml.dump(abridged_result, allow_unicode=True, width=1000, Dumper=MyDumper, default_flow_style=False))

        return yaml.safe_load(dumped)

    def debug_vars(self, result):
        print(f' DEBUG - type(result) : {type(result)}')
        print(f' DEBUG - dir(result) : {dir(result)}')
        print(f' DEBUG - result._task_fields : {result._task_fields}')
        print(f' DEBUG - dir(result._result) : {dir(result._result)}')
        print(f' DEBUG - type(result._result) : {type(result._result)}')
        print(f' DEBUG - result._result : {result._result}')
        print(f' DEBUG - type(result._task) : {type(result._task)}')
        print(f' DEBUG - dir(result._task) : {dir(result._task)}')
        print(f' DEBUG - result._task.register : {str(result._task.register)}')
        print(f' DEBUG - result._task : {result._task}')
        print(f' DEBUG - result._task.get_vars() : {result._task.get_vars()}')
        print(f' DEBUG - result._task.get_path() : {result._task.get_path()}')
        print(f' DEBUG - result._task.get_name() : {result._task.get_name()}')
        print(f' DEBUG - dir(result._task.vars) : {dir(result._task.vars)}')


def should_use_block(value):
    """Returns true if string should be in block format"""
    for c in u"\u000a\u000d\u001c\u001d\u001e\u0085\u2028\u2029":
        if c in value:
            return True
    return False


class MyDumper(AnsibleDumper):
    def represent_scalar(self, tag, value, style=None):
        """Uses block style for multi-line strings"""
        if style is None:
            if should_use_block(value):
                style = '|'
                # we care more about readable than accuracy, so...
                # ...no trailing space
                value = value.rstrip()
                # ...and non-printable characters
                value = ''.join(x for x in value if x in string.printable or ord(x) >= 0xA0)
                # ...tabs prevent blocks from expanding
                value = value.expandtabs()
                # ...and odd bits of whitespace
                value = re.sub(r'[\x0b\x0c\r]', '', value)
                # ...as does trailing space
                value = re.sub(r' +\n', '\n', value)
            else:
                style = self.default_style
        node = yaml.representer.ScalarNode(tag, value, style=style)
        if self.alias_key is not None:
            self.represented_objects[self.alias_key] = node
        return node
