#*******************************************************************************
# Licensed Materials - Property of IBM
# (c) Copyright IBM Corp. 2023. All Rights Reserved.
#
# Note to U.S. Government Users Restricted Rights:
# Use, duplication or disclosure restricted by GSA ADP Schedule
# Contract with IBM Corp.
#*******************************************************************************
from __future__ import absolute_import, division, print_function
__metaclass__ = type

from ansible.errors import AnsibleError

def _wd_create_item_ (artifact, wd_deploy_dir_uss, wd_type, is_backup:bool, is_delete:bool, verbose:bool, is_restore: bool = False):
    if verbose:
        print(f"Create item for:\n\tName: {artifact['name']}\n\tType: {wd_type['type']}\n\tUSS Deploy Folder: {wd_deploy_dir_uss}\n\tIs Backup: {is_backup}")
    item = {}
    path_prop = list(filter(lambda prop: ('path' == prop['key']), artifact['properties']))
    path = path_prop[0]['value']
    
    item['is_binary'] = wd_type.get('is_binary', False)
    item['is_load'] = wd_type.get('is_load', False)
    item['is_sequential'] = wd_type.get('is_sequential', False)
    item['is_uss'] = wd_type.get('is_uss', False)
    item['type'] = wd_type
    item['name'] = artifact['name']
    if wd_type.get('encoding'):
        item['encoding'] = wd_type.get('encoding')
    if wd_type.get('uss'):
        item['dest_mode'] = wd_type['uss']['dest_mode'] 
        item['artifact_mode'] = wd_type['uss']['artifact_mode']    
    fingerprint_prop = list(filter(lambda prop: ('old_fingerprint' == prop['key']), artifact['properties']))
    if len(fingerprint_prop) == 0:
        fingerprint_prop = list(filter(lambda prop: ('fingerprint' == prop['key']), artifact['properties']))
    if len(fingerprint_prop) != 0:
        fingerprint = fingerprint_prop[0]['value']
    else:
        fingerprint = ""    
    item['fingerprint'] = fingerprint
    
    if wd_type.get('pds'):
        if verbose:
            print(f"Create PDS item for:\n{str(artifact)})")
        if wd_type.get('is_load', False):
            # Force binary mode
            item['is_binary'] = True
        try:
            if is_delete:
                item['src'] = f"{wd_type['pds']['name']}({artifact['name'].upper()})"
            elif is_backup:
                item['src'] = f"{wd_type['pds']['name']}({artifact['name'].upper()})"
                item['dest'] = f"{wd_type['pds']['backup']}({artifact['name'].upper()})"
            elif is_restore:
                item['src'] = f"{wd_type['pds']['backup']}({artifact['name'].upper()})" 
                item['dest'] = f"{wd_type['pds']['name']}({artifact['name'].upper()})"   
            else:
                item['src'] = wd_deploy_dir_uss + '/' + path
                item['dest'] = f"{wd_type['pds']['name']}({artifact['name'].upper()})"
        except KeyError as exc:
            raise AnsibleError(f"ERROR: Attribute {str(exc)} not found in 'types.{wd_type['type']}.pds' tag!!!")
    elif wd_type.get('ds'):
        if verbose:
            print(f"Create DS item for:\n{str(artifact)})")
        try:
            if is_delete:
                item['src'] = f"{wd_type['ds']['prefix']}.{artifact['name'].upper()}"
            elif is_backup:
                item['src'] = f"{wd_type['ds']['prefix']}.{artifact['name'].upper()}"
                item['dest'] = f"{wd_type['ds']['backup_prefix']}.{artifact['name'].upper()}"
            else:
                item['src'] = wd_deploy_dir_uss + '/' + path
                item['dest'] = f"{wd_type['ds']['prefix']}.{artifact['name'].upper()}"
        except KeyError as exc:
            raise AnsibleError(f"ERROR: Attribute {str(exc)} not found in 'types.{wd_type['type']}.ds' tag!!!")
    elif wd_type.get('uss'):
        if verbose:
            print(f"Create USS item for:\n{str(artifact)})")
        try:
            if is_delete:
                item['src'] = f"{wd_type['uss']['dest']}/{artifact['name']}.{wd_type['type']}"
            elif is_backup:
                item['src'] = f"{wd_type['uss']['dest']}/{artifact['name']}.{wd_type['type']}"
                item['dest'] = f"{wd_type['uss']['backup_dest']}"
            else:
                item['src'] = wd_deploy_dir_uss + '/' + path
                item['dest'] = f"{wd_type['uss']['dest']}/{artifact['name']}.{wd_type['type']}"
        except KeyError as exc:
            raise AnsibleError(f"ERROR: Attribute {str(exc)} not found in 'types.{wd_type['type']}.uss' tag!!!")
    else:
        raise AnsibleError(f"ERROR: No attributes 'pds|ds|uss' for type: {wd_type['type']} declared in the inventory!!!")

    return item

def wd_artifact_list(artifacts, wd_deploy_dir_uss, wd_types,  is_backup:bool, is_delete:bool, verbose:bool, is_restore:bool = False):
    if verbose:
        print(f"Types:\n{str(wd_types)})")
        print(f"Artifacts:\n{str(artifacts)})")

    list_result = []
    list_load = [] 
    for artifact in artifacts:
        if verbose:
            print(f"Artifact:\n{str(artifact)})")
        type_prop = list(filter(lambda prop: ('type' == prop['key']), artifact['properties']))
        artifact_type = type_prop[0]['value']
        wd_type =  list(filter(lambda wd_type: wd_type['type'].lower() == artifact_type.lower(), wd_types))
        if verbose:
            print(f"Type:\n{str(wd_type)})")
        if len ( wd_type ) == 0:
            raise AnsibleError(f"ERROR: No type {type_prop[0]['value']} declared in the inventory!!!")
        if  wd_type[0].get('is_load', False):
            list_load.append(_wd_create_item_(artifact, wd_deploy_dir_uss, wd_type[0], is_backup, is_delete, verbose, is_restore))
        else:
            list_result.append(_wd_create_item_(artifact, wd_deploy_dir_uss, wd_type[0], is_backup, is_delete, verbose, is_restore))
    # We put loads at the end we have a side effect with the current copy mode of zos_copy
    list_result.extend(list_load)
    if verbose:
        print(f"Results:\n{str(list_result)})\n")

    return list_result

def wd_cics_artifact_list(artifacts, wd_types, verbose:bool):
    if verbose:
        print(f"Types:\n{str(wd_types)})")
        print(f"Artifacts:\n{str(artifacts)})")

    list_result = [] 
    for artifact in artifacts:
        if verbose:
            print(f"Artifact:\n{str(artifact)})")
        type_prop = list(filter(lambda prop: ('type' == prop['key']), artifact['properties']))
        artifact_type = type_prop[0]['value']
        wd_type =  list(filter(lambda wd_type: wd_type['type'].lower() == artifact_type.lower(), wd_types))
        if verbose:
            print(f"Type:\n{str(wd_type)})")
        if len ( wd_type ) == 0:
            raise AnsibleError(f"ERROR: No type {type_prop[0]['value']} declared in the inventory!!!")
        cics_systems = wd_type[0].get('cics_systems', None)
        if cics_systems and type(cics_systems) == list:
            for cics_system in cics_systems:
                item = {}
                item['name'] = artifact['name']
                item['cics_system'] = cics_system
                list_result.append(item)
        else:
            raise AnsibleError(f"No 'cics_systems' attribute declared in the type: '{wd_type[0]['type']}'. Or 'cics_systems' attribute is not a list.")

    if verbose:
        print(f"Results:\n{str(list_result)})\n")

    return list_result

def wd_db2_artifact_list(artifacts, wd_types, verbose:bool) -> []:
    if verbose:
        print(f"Types:\n{str(wd_types)})")
        print(f"Artifacts:\n{str(artifacts)})")
    list_result = [] 
    db2_systems_items = {}
    db2_systems = None
    for artifact in artifacts:
        type_prop = list(filter(lambda prop: ('type' == prop['key']), artifact['properties']))
        artifact_type = type_prop[0]['value']
        wd_type =  list(filter(lambda wd_type: wd_type['type'].lower() == artifact_type.lower(), wd_types))
        if len ( wd_type ) == 0:
            raise AnsibleError(f"ERROR: No type {type_prop[0]['value']} declared in the inventory!!!")
        db2_systems = wd_type[0].get('db2_systems', None)
        if db2_systems and type(db2_systems) == list:
            for db2_system in db2_systems:
                key = db2_systems.index(db2_system)
                if  db2_systems_items.get(key, None):
                    db2_systems_items[key].append({ 'name': artifact['name']})
                else:
                    db2_systems_items[key] = []
                    db2_systems_items[key].append({ 'name': artifact['name']})
        else:
            raise AnsibleError(f"No 'db2_systems' attribute declared in the type: '{wd_type[0]['type']}'. Or 'db2_systems' attribute is not a list.")

    if db2_systems:
        index = 0
        for db2_system_item_index in db2_systems_items.keys():
            current_db2_system = db2_systems[db2_system_item_index]
            current_artifacts = db2_systems_items[db2_system_item_index]
            item = {}
            item['artifacts'] = current_artifacts
            item['db2_system'] = current_db2_system
            item['dest_pds'] = wd_type[0]['pds']['name']
            list_result.append(item)
            index += 1

    if verbose:
        print(f"Results:\n{str(list_result)})\n")

    return list_result

def wd_type_list(artifacts, wd_types, verbose:bool = False):
    list_result = [] 
    for artifact in artifacts:
        if verbose:
            print(f"Artifact:\n{str(artifact)})")
        type_prop = list(filter(lambda prop: ('type' == prop['key']), artifact['properties']))
        artifact_type = type_prop[0]['value']
        wd_type =  list(filter(lambda wd_type: wd_type['type'].lower() == artifact_type.lower(), wd_types))
        if len ( wd_type ) == 0:
            raise AnsibleError(f"ERROR: No type {type_prop[0]['value']} declared in the inventory!!!")
        if not wd_type[0] in list_result:
            list_result.append(wd_type[0])
        
    if verbose:
        for result in list_result: 
            print(result)

    return list_result

def wd_folder_list(artifacts, wd_types,  is_backup:bool = False, verbose:bool = False):
    list_result = [] 
    for artifact in artifacts:
        folder = {}
        if verbose:
            print(f"Artifact:\n{str(artifact)})")
        type_prop = list(filter(lambda prop: ('type' == prop['key']), artifact['properties']))
        artifact_type = type_prop[0]['value']
        wd_type =  list(filter(lambda wd_type: wd_type['type'].lower() == artifact_type.lower(), wd_types))
        if len ( wd_type ) == 0:
            raise AnsibleError(f"ERROR: No type {type_prop[0]['value']} declared in the inventory!!!")
        if wd_type[0].get('uss'):
            folder['dest_mode'] = wd_type[0].get('uss')['dest_mode']
            try:
                if is_backup:
                    folder['src'] = wd_type[0].get('uss')['backup_dest']
                else:
                    folder['src'] = wd_type[0].get('uss')['dest']
                folder_dict =  list(filter(lambda folder_dict: folder_dict['src'].lower() == folder['src'], list_result))    
                if len (folder_dict) == 0:
                    list_result.append(folder)
            except KeyError as exc:
                raise AnsibleError(f"ERROR: Attribute {str(exc)} not found in 'types.{wd_type['type']}.uss' tag!!!")
    if verbose:
        for result in list_result: 
            print(result)
    return list_result

def wd_directories_list(artifacts, wd_deploy_dir_uss, wd_types, verbose:bool = False):
    list_result = []
    for artifact in artifacts:
        if verbose:
            print(f"Artifact:\n{str(artifact)})")
        directories_dic = {}
        type_prop = list(filter(lambda prop: ('path' == prop['key']), artifact['properties']))
        artifact_path = type_prop[0]['value']
        index = artifact_path.rfind('/')
        folder_path = artifact_path[:index]
        type_prop = list(filter(lambda prop: ('type' == prop['key']), artifact['properties']))
        artifact_type = type_prop[0]['value']
        wd_type =  list(filter(lambda wd_type: wd_type['type'].lower() == artifact_type.lower(), wd_types))
        if len ( wd_type ) == 0:
            raise AnsibleError(f"ERROR: No type {type_prop[0]['value']} declared in the inventory!!!")
        copy_by_folder = wd_type[0].get('copy_by_folder', False)
        if copy_by_folder :
            directories_dic['src'] = wd_deploy_dir_uss + '/' + folder_path
            path =  list(filter(lambda path: path['src'].upper() == directories_dic['src'].upper(), list_result))
            if len (path) == 0:
                if wd_type[0].get('pds'):
                    pds = wd_type[0].get('pds')
                    directories_dic['dest'] = pds['name']
                    is_binary = wd_type[0].get('is_binary', False)
                    if  wd_type[0].get('is_load', False):
                        is_binary = True
                    directories_dic['is_binary'] = is_binary 
                    if wd_type[0].get('encoding', False):
                        directories_dic['encoding'] = wd_type[0].get('encoding')   
                    list_result.append(directories_dic)
    return list_result

class FilterModule(object):
    ''' Ansible core jinja2 filters '''
    def filters(self):
        filters = {
            'wd_artifact_list': wd_artifact_list,
            'wd_cics_artifact_list': wd_cics_artifact_list,
            'wd_db2_artifact_list': wd_db2_artifact_list,
            'wd_type_list': wd_type_list,
            'wd_folder_list': wd_folder_list,
            'wd_directories_list': wd_directories_list
        }
        return filters