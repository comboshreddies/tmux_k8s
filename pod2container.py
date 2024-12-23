""" this module converts from pod name to container name """

import re

def pod2container(base_pod_name):
    """pod to container"""
    if re.search(r'^consumer', base_pod_name) :
        return base_pod_name.split("-")[0]
    if re.search(r'^producer', base_pod_name) :
        return '-'.join(base_pod_name.split("-")[:2])
    if re.search(r'^specific-pod-name', base_pod_name) :
        return 'specific-container-name'
    if re.search(r'^nginx-sample', base_pod_name) :
        return 'nginx'
    return base_pod_name
