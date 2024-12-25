#!/usr/bin/env python3
""" tmux_k8s - tool for executing command sequences on each pod within  separate tmux window """

import time
import sys
import os
import signal
import libtmux
from kubernetes import client, config
from libtmux._internal.query_list import ObjectDoesNotExist
from libtmux._internal.query_list import MultipleObjectsReturned


from pod2container import pod2container as p2c
from sequences import sequences

COMMENT_TAG = "# "
NO_RETURN = "# no return"
DO_ATTACH = "# attach"
FINAL_EXEC = "# exec : "

SLEEP_TIME = 300 
WAIT_FOR_PROMPT_SECONDS = 2
STEP_COMPLETE = -1


def terminate_all(sess_name):
    """ terminate session """
    tmux_server = libtmux.Server()
    try:
        sess_handle = tmux_server.sessions.get(session_name=sess_name)
    except ObjectDoesNotExist:
        print(f"no such object, probably clean {sess_name}")
        return
    for window in sess_handle.windows:
        temp_pane = window.panes.get()
        lines = temp_pane.cmd('capture-pane','-p').stdout
        print("->" + lines[len(lines)-3] + " - " +  lines[len(lines)-2])
        print("terminating ",end="")
        print(window)
        window.kill()
    sess_handle.kill()
    tmux_server.kill()



def get_pods_list(k8s_context,k8s_namespace,label_selector,selector):
    """ fetch pod list from given context,namespace, label_selector """
    config.load_kube_config(context=k8s_context)

    v1 = client.CoreV1Api()
    k8s_ret = v1.list_namespaced_pod(namespace=k8s_namespace, label_selector=label_selector,
        field_selector=selector, watch=False)

    pods_list = []
    for item in k8s_ret.items:
        pods_list.append(item.metadata.name)
    return pods_list


def get_fsm_prompt(pods_list,sess_handle,session_name):
    """ tmux on start will get base prompt for given shell, catch that one """
    print("---- waiting for prompt to stabilize")
    time.sleep(WAIT_FOR_PROMPT_SECONDS)
    print("---- getting prompt from live windows")
    fsm_prompt = {}
    for pod in pods_list:
        try:
            temp_window = sess_handle.windows.get(window_name = pod)
        except MultipleObjectsReturned:
            print(f"multiple objects returned for window {pod}, most probably old tmux session, try tmux kill-session -t {session_name}")
            sys.exit(1)
        temp_pane = temp_window.panes.get()
        lines = temp_pane.cmd('capture-pane','-p').stdout
        print(f"x {pod} ->" + lines[len(lines)-1])
        fsm_prompt[pod] = lines[len(lines)-1]
    return fsm_prompt


def simple_help(args):
    """ print simple help """
    print(args[0] + " <sequence> <k8s-context> <k8s-namespace> [<k8s-label-selector>]")
    print("or")
    print(args[0] + " list")


def check_args(seq,args):
    """ check cli args """
    if len(args) == 2 :
        if args[1] == 'list':
            print(' '.join(seq.keys()))
            sys.exit(0)
        else:
            simple_help(args)
            sys.exit(1)
    if len(args) < 4 :
        simple_help(args)
        sys.exit(2)

    tmux_cmd = args[1]
    k8s_context = args[2]
    k8s_namespace = args[3]

    if len(sys.argv) == 5:
        label_selector = sys.argv[4]
    else:
        label_selector = ''

    return tmux_cmd,k8s_context,k8s_namespace,label_selector


def execute_fsm(pods_list,sess_handle,sequence,info,session_name):
    """ execute finit state machine, sequence , step by step """
    fsm_step = {}
    fsm_step_executed = {}
    for pod in pods_list:
        fsm_step[pod] = 0
        fsm_step_executed[pod] = False


    k8s_context = info['context'] # used within eval
    k8s_namespace = info['namespace'] # used within eval
    print(f"--- working with context {k8s_context} namespace {k8s_namespace}")
    for pod in pods_list:
        print(f"spawining window for {pod}")
        sess_handle.new_window(attach=False, window_name=pod)

    fsm_prompt = get_fsm_prompt(pods_list,sess_handle,session_name)

    while True :
        for pod in pods_list:
            if fsm_step[pod] == STEP_COMPLETE:
                continue
            if fsm_step[pod] >= len(sequence):
                print(f"{pod} -> complete")
                fsm_step[pod] = STEP_COMPLETE
                continue
            if not fsm_step_executed[pod]:
                print(f"---- {info['cmd']} {pod} step {fsm_step[pod]} {p2c(pod)} ----")
                temp_window = sess_handle.windows.get(window_name = pod)
                temp_pane = temp_window.panes.get()
                execute = eval(f"f'{sequence[fsm_step[pod]]}'")
                print("executing -> " + execute)
                temp_pane.send_keys(execute)
                fsm_step_executed[pod] = True
                if len(sequence) > fsm_step[pod] and sequence[fsm_step[pod]+1].startswith(COMMENT_TAG):
                    fsm_step[pod] = STEP_COMPLETE
            else:
                # fsm step is executed,  waiting for prompt
                temp_window = sess_handle.windows.get(window_name = pod)
                temp_pane = temp_window.panes.get()
                lines = temp_pane.cmd('capture-pane','-p').stdout
                if fsm_prompt[pod] in lines[len(lines)-1] :
                    fsm_step_executed[pod] = False
                    fsm_step[pod] += 1
        all_complete = True
        for pod in pods_list:
            if fsm_step[pod] != STEP_COMPLETE:
                all_complete = False
        if all_complete:
            print("all complete")
            break


def new_tmux_session(tmux_server,session_name):
    """ get new tmux session """
    tmux_server.cmd('new-session', '-d', '-P', '-F#{session_id}','-s',session_name)
    sess_handle = tmux_server.sessions.get(session_name=session_name)
    tmux_server.cmd('rename-window','-t',f'{session_name}:{0}','base')
    print(f"==== new session {session_name} created")
    return sess_handle


def main():
    """ main function, check args, get params for finite state machine """

    (tmux_cmd,k8s_context,k8s_namespace,label_selector) = check_args(sequences,sys.argv)

    session_name = f'{tmux_cmd}-{k8s_context}-{k8s_namespace}'

    if tmux_cmd == 'terminate-all' :
        terminate_all(session_name)
        sys.exit(0)

    if tmux_cmd not in sequences:
        print(f"{tmux_cmd} not in allowed commands, check sequences dictionary in sequences.py")
        sys.exit(1)

    selector = "status.phase=Running"
    pod_list = get_pods_list(k8s_context,k8s_namespace,label_selector,selector)

    tmux_server = libtmux.Server()
    tmux_session_exist = True 
    try:
        tmux_server.sessions.get(session_name=session_name)
    except ObjectDoesNotExist:
        tmux_session_exist = False
    
    if tmux_session_exist:
        print(f"tmux session {session_name} already exist try:")
        print(f"terminating with : tmux kill-session -t {session_name}")
        print(f"attach with: tmux attach-session -t {session_name}")
        print("exiting")
        sys.exit(5)

    tmux_handle = new_tmux_session(tmux_server,session_name)

    def signal_handler_terminate(sig, _):
        """ set signal handler for ctr+c """
        print(f'You pressed Ctrl+C! {sig}, terminating tmux windows')
        terminate_all()
        sys.exit(0)

    def signal_handler_detach(sig, _):
        """ set signal handler for ctr+c """
        print(f'You pressed Ctrl+C! {sig}, exiting, leaving tmux windows')
        sys.exit(9)

    def terminate_all():
        """ terminate session """
        for window in tmux_handle.windows:
            temp_pane = window.panes.get()
            lines = temp_pane.cmd('capture-pane','-p').stdout
            if len(lines) > 3 :
                print("->" + lines[len(lines)-3] + " - " +  lines[len(lines)-2])
            else:
                print("->" + lines[0])
            print("terminating ",end="")
            print(window)
            window.kill()
        tmux_server.kill()

    signal.signal(signal.SIGINT, signal_handler_detach)
    signal.signal(signal.SIGQUIT, signal.SIG_IGN)
    print("--- ctr+c will exit and leave all tmux sessions, sequence execution will be partially done ---")
    print("--- ctr+\\ will be ignored  ---")
 
    info = {}
    info['cmd'] = tmux_cmd
    info['context'] = k8s_context
    info['namespace'] = k8s_namespace
    execute_fsm(pod_list,tmux_handle,sequences[tmux_cmd],info,session_name)

    print(f"--- all executable sequence steps are executed ---")
    signal.signal(signal.SIGQUIT, signal_handler_terminate)
    if sequences[tmux_cmd][-1] == DO_ATTACH:
        print(f"--- attaching tmux ---")
        os.execve('/bin/sh',['/bin/sh','-c',f'tmux attach-session -t {session_name}'],os.environ)
    elif sequences[tmux_cmd][-1].startswith(FINAL_EXEC):
        to_exec = sequences[tmux_cmd][-1][len(FINAL_EXEC):]
        parsed_exec = eval(f"f'{to_exec}'")
        print(f"--- final_exec : " + parsed_exec)
        os.execve('/bin/sh',['/bin/sh','-c',parsed_exec],os.environ)
    else:
        print(f"--- waiting {SLEEP_TIME} seconds before closing ---")
        print(f"--- after {SLEEP_TIME} program will exit and leave all tmux_sessions ---")
        print("--- ctr+c will exit and leave all tmux sessions ---")
        print(f"---    attach with: tmux attach-session -t {session_name} ---")
        print(f"---  or: ---")
        print(f"---    remove with: tmux kill-session -t {session_name} ---")
        print("--- ctr+\\ will exit and terminate all tmux sessions ---")
        time.sleep(SLEEP_TIME)


if __name__ == '__main__':
    main()
