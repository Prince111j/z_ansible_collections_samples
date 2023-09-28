#*******************************************************************************
# Licensed Materials - Property of IBM
# (c) Copyright IBM Corp. 2022. All Rights Reserved.
#
# Note to U.S. Government Users Restricted Rights:
# Use, duplication or disclosure restricted by GSA ADP Schedule
# Contract with IBM Corp.
#*******************************************************************************
from __future__ import (absolute_import, division, print_function)
import os
__metaclass__ = type

from ansible.plugins.action import ActionBase
from ansible.utils.display import Display

global_display = Display()

def find_task_path (task, current_step_name:str,
                        role_path:str, tasks_folder:str,
                        verbose:bool = False):
    task_path = None

    task_file_name = current_step_name.lower()
    full_role_path = f"{role_path}/{tasks_folder}"
    if verbose:
        print(f"Task File Base Name: {task_file_name}")
        print(f"Full Role Path: {full_role_path}")

    for file in os.listdir(full_role_path):
        if file.lower() == f"{task_file_name}.yml":
            task_path=f"{full_role_path}/{file}"
            break
    if not task_path:
        msg = f"The task '{task_file_name}.yml' is not found in {role_path}. Trying to found a custom task '{task_file_name}.yml' on the Ansible Controller search path (Only in tasks folders)."
        global_display.warning(msg)
        current_task = task
        while current_task._parent:
            try:
                for search_path in current_task.get_search_path():
                    if not search_path.startswith(role_path):
                        for root,dir_names,file_names in os.walk(search_path):
                            if verbose:
                                print (root,dir_names,file_names)
                            for file_name in file_names:
                                if file_name.lower() == f"{task_file_name}.yml":
                                    task_path=f"{root}/{file_name}"
                                    msg = f"Found a custom task '{task_path} on the Ansible Controller search path."
                                    if verbose:
                                        print (msg)
                                    global_display.warning(msg)
                                    break
                            if task_path:
                                break
                    if task_path:
                        break
            except:
                pass
            current_task = current_task._parent

    if verbose:
        print(f"Task Path: {task_path}")
    return task_path

class ActionModule(ActionBase):

    def run(self, tmp=None, task_vars=None):
        super(ActionModule, self).run(tmp, task_vars)
        module_args = self._task.args.copy()

        if module_args.get('verbose', False):
            print(module_args)
        result = {}
        try:
            deployment_plan = module_args.get('deployment_plan', None)
            if deployment_plan:
                collected_tasks = []
                for activity in deployment_plan['activities']:
                    for action in activity['actions']:
                        for step in action['steps']:
                            task_name = None
                            try:
                                template_prop = list(filter(lambda prop: ('template' == prop['key']), step['properties']))
                            except KeyError:
                                template_prop=[]
                            if len(template_prop) > 0:
                                task_name = template_prop[0]['value']
                            else:
                                try:
                                    var_template_prop = list(filter(lambda prop: ('var_template' == prop['key']), step['properties']))
                                except KeyError:
                                    var_template_prop=[]
                                if len(var_template_prop) > 0:
                                    var_task_name = var_template_prop[0]['value']
                                    for key in task_vars.keys():
                                        if key == var_task_name:
                                            task_name =task_vars.get(key)
                                            break
                                    if not task_name:
                                        msg = f"The Ansible variable '{var_task_name}' for 'var_template' property is not found at this early check stage. It will be checked again when running this step {activity['name']}>{action['name']}>{step['name']}."
                                        global_display.warning(msg)
                                elif step.get('short_name', None):
                                    task_name = step['short_name']
                                else:
                                    task_name = step['name']
                            if task_name:
                                collected_tasks.append((task_name, f"{activity['name']}>{action['name']}>{step['name']}"))
                for task_file_name, full_step_name in collected_tasks:
                    task_path = find_task_path (
                            self._task,
                            task_file_name,
                            module_args.get('role_path', None),
                            module_args.get('tasks_folder', None),
                            module_args.get('verbose', False)
                            )
                    if not task_path:
                        result['failed'] = True
                        result['msg'] = f"The task '{task_file_name.lower()}.yml' for this step {full_step_name} is not found in {module_args.get('role_path', None)} and in any custom 'tasks' folders on the Ansible Controller search path (Only in tasks folders)."
                        return result
            else:
                task_name = module_args.get('task_name', None)
                var_task_name = module_args.get('var_task_name', None)
                step = module_args.get('step' , None)
                task_file_name = None
                if task_name:
                    task_file_name = f"{task_name}"
                elif var_task_name:
                    for key in task_vars.keys():
                        if key == var_task_name:
                            task_file_name =task_vars.get(key)
                            break
                    if not task_file_name:
                        result['failed'] = True
                        result['msg'] = f"The Ansible variable '{var_task_name}' for 'var_template' property is not defined for this step {step['name']}."
                        return result
                elif step.get('short_name', None):
                    task_file_name = step['short_name']
                else:
                    task_file_name = step['name']
                task_path = find_task_path (
                            self._task,
                            task_file_name,
                            module_args.get('role_path', None),
                            module_args.get('tasks_folder', None),
                            module_args.get('verbose', False)
                            )
                if not task_path:
                    result['failed'] = True
                    result['msg'] = f"The task '{task_file_name}.yml' is not found in {module_args.get('role_path', None)} and in any custom 'tasks' folders on the Ansible Controller search path (Only in tasks folders)."
                else:
                    result['wd_task_filename_path'] = task_path
                    result['wd_task_filename'] = os.path.basename(task_path)
        except Exception as ex:
            raise  ex

        return result 