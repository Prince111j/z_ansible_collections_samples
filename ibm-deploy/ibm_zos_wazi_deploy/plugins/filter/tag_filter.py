#*******************************************************************************
# Licensed Materials - Property of IBM
# (c) Copyright IBM Corp. 2022. All Rights Reserved.
#
# Note to U.S. Government Users Restricted Rights:
# Use, duplication or disclosure restricted by GSA ADP Schedule
# Contract with IBM Corp.
#*******************************************************************************
from __future__ import absolute_import, division, print_function
__metaclass__ = type

def tag_filter(args, activity_tags, action_tags, step_tags, plan_tags, plan_skip_tags, current_level, verbose:bool = False):
    
    if verbose:
        print(f"Current level: {current_level}")
        print(f"Activity tags: {activity_tags}")
        print(f"Action tags: {action_tags}")
        print(f"Steps tags: {step_tags}")

    tags_result = False
            
    var_tags = plan_tags
    var_skip_tags = plan_skip_tags
    
    if var_tags:
        planTags = var_tags.split(',')
    else:
        planTags = []
    if var_skip_tags:
        planSkipTags = var_skip_tags.split(',')
    else:
        planSkipTags = []
        
    # build tag list 
    task_tags = []
    if activity_tags and len(activity_tags) > 0:
        task_tags = activity_tags
    if action_tags and len(action_tags) > 0:
        task_tags = action_tags
    if step_tags and len(step_tags) > 0:
        task_tags = step_tags
    
    if verbose:
        print(f"Current plan tags: {planTags}")
        print(f"Current skip plan tags: {planSkipTags}")
        print(f"Current task tags: {task_tags}")
    # handle tags
    if len(planTags) > 0:
        for tag in task_tags:
            if tag in planTags or tag == 'always':
                tags_result = True
                break
    else:
        tags_result = 'never' not in task_tags
    
    # handle skipTags
    if len(planSkipTags) > 0:
        for tag in task_tags:
            if tag in planSkipTags:
                return False
            
    if not tags_result:
        if not activity_tags and 1 == current_level:
            # Visit actions
            tags_result = True
        elif not activity_tags and not action_tags and 2 == current_level:
            # Visit steps
            tags_result = True
         
    if verbose:
        print(f"Tags filter result: {tags_result}")
    return tags_result
    
class FilterModule(object):
    ''' Ansible core jinja2 filters '''

    def filters(self):
        filters = {
            'tag_filter': tag_filter,
        }
        return filters