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
from seq_constants import COMMENT_TAG, NO_RETURN, FINAL_EXEC
from seq_constants import DO_ATTACH, DO_TERMINATE


SLEEP_TIME = 300
WAIT_FOR_PROMPT_SECONDS = 1
STEP_COMPLETE = -1


def signal_handler_detach(sig, _):
    """ set signal handler for ctr+c """
    print(f'You pressed Ctrl+C! {sig}, exiting, leaving tmux windows')
    sys.exit(9)

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
            print(f"multiple objects returned for window {pod}, " +
                  f"most probably old tmux session, try tmux kill-session -t {session_name}")
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
            print("Available commands:")
            for item in seq.items():
                if seq[item][0].startswith(COMMENT_TAG):
                    print(f"  {item} - {seq[item][0][len(COMMENT_TAG):]}")
                else:
                    print(f"  {item} - no description")
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

def check_all_complete(state,pods_list):
    """ check if state for all pods is complete """
    all_complete = True
    for pod in pods_list:
        if state[pod] != STEP_COMPLETE:
            all_complete = False
    return all_complete

def execute_fsm(pods_list,sess_handle,sequence,info,session_name):
    """ execute finit state machine, sequence , step by step """
    state = {}
    state['fsm_step'] = {}
    state['fsm_step_executed'] = {}
    for pod in pods_list:
        state['fsm_step'][pod] = 0
        state['fsm_step_executed'][pod] = False

    k8s_context = info['context'] # used within eval
    k8s_namespace = info['namespace'] # used within eval
    print(f"--- working with context {k8s_context} namespace {k8s_namespace}")
    for pod in pods_list:
        print(f"spawining window for {pod}")
        sess_handle.new_window(attach=False, window_name=pod)

    fsm_prompt = get_fsm_prompt(pods_list,sess_handle,session_name)

    while True :
        for pod in pods_list:
            if state['fsm_step'][pod] == STEP_COMPLETE:
                continue
            if state['fsm_step'][pod] >= len(sequence):
                print(f"{pod} -> step complete")
                state['fsm_step'][pod] = STEP_COMPLETE
                continue
            if sequence[state['fsm_step'][pod]].startswith(COMMENT_TAG):
                print(f"---# COMMENT: {sequence[state['fsm_step'][pod]]}")
                state['fsm_step_executed'][pod] = False
                state['fsm_step'][pod] += 1
            if not state['fsm_step_executed'][pod]:
                print(f"---- {info['cmd']} {pod} step " +
                    "{state['fsm_step'][pod]} {p2c(pod)} ----")
                temp_window = sess_handle.windows.get(window_name = pod)
                temp_pane = temp_window.panes.get()
                execute = eval(f"f'{sequence[state['fsm_step'][pod]]}'")
                print("executing -> " + execute)
                temp_pane.send_keys(execute)
                state['fsm_step_executed'][pod] = True
                if len(sequence) - 1 > state['fsm_step'][pod] and \
                    sequence[state['fsm_step'][pod]+1].startswith(NO_RETURN):
                    state['fsm_step'][pod] = STEP_COMPLETE
                    continue
            else:
                # fsm step is executed,  waiting for prompt
                temp_window = sess_handle.windows.get(window_name = pod)
                temp_pane = temp_window.panes.get()
                lines = temp_pane.cmd('capture-pane','-p').stdout
                if lines[-1].startswith(fsm_prompt[pod]) :
                    state['fsm_step_executed'][pod] = False
                    state['fsm_step'][pod] += 1

        if check_all_complete(state['fsm_step'],pods_list):
            print("all complete")
            break


def new_tmux_session(tmux_server,session_name):
    """ get new tmux session """
    tmux_server.cmd('new-session', '-d', '-P', '-F#{session_id}','-s',session_name)
    sess_handle = tmux_server.sessions.get(session_name=session_name)
    tmux_server.cmd('rename-window','-t',f'{session_name}:{0}','base')
    print(f"==== new session {session_name} created")
    return sess_handle


def check_session(session_name,tmux_server):
    """ check if session already exist, and if it does exit """
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


def check_sequence(tmux_command):
    """ check is input command available """
    if tmux_command not in sequences:
        print(f"{tmux_command} not in allowed commands, check sequences dictionary in sequences.py")
        sys.exit(1)


def waiting_message(session_name):
    """ final message before waiting """
    print(f"--- waiting {SLEEP_TIME} seconds before closing ---")
    print(f"--- after {SLEEP_TIME} program will exit and leave all tmux_sessions ---")
    print("--- ctr+c will exit and leave all tmux sessions ---")
    print(f"---    attach with: tmux attach-session -t {session_name} ---")
    print("---  or: ---")
    print(f"---    remove with: tmux kill-session -t {session_name} ---")
    print("--- ctr+\\ will exit and terminate all tmux sessions ---")


def display_pods_and_containers(pod_list):
    """ display selected pods and containers """
    for pod in pod_list:
        print(f"pod : {pod}, container : {p2c(pod)}")
    print("-----------")


def terminate_tmux(tmux_server,tmux_handle):
    """ terminate tmux handle windows and server """
    try:
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
    except libtmux.exc.LibTmuxException as q:
        print(q)


def main():
    """ main function, check args, get params for finite state machine """

    (tmux_cmd,k8s_context,k8s_namespace,label_selector) = check_args(sequences,sys.argv)

    check_sequence(tmux_cmd)
    session_name = f'{tmux_cmd}-{k8s_context}-{k8s_namespace}'

    pod_list = get_pods_list(k8s_context,k8s_namespace,label_selector,"status.phase=Running")
    if pod_list:
        display_pods_and_containers(pod_list)
    else:
        print("no pods selected, exiting")
        sys.exit(6)

    tmux_server = libtmux.Server()
    check_session(session_name, tmux_server)
    tmux_handle = new_tmux_session(tmux_server,session_name)

    def terminate_all():
        """ terminate session """
        terminate_tmux(tmux_server,tmux_handle)

    def signal_handler_terminate(sig, _):
        """ set signal handler for ctr+c """
        print(f'You pressed Ctrl+C! {sig}, terminating tmux windows')
        terminate_all()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler_detach)
    signal.signal(signal.SIGQUIT, signal.SIG_IGN)
    print("--- ctr+c will exit and leave all tmux sessions," +
          "sequence execution will be partially done ---")
    print("--- ctr+\\ will be ignored  ---")

    info = {}
    info['cmd'] = tmux_cmd
    info['context'] = k8s_context
    info['namespace'] = k8s_namespace
    execute_fsm(pod_list,tmux_handle,sequences[tmux_cmd],info,session_name)

    print("--- all executable sequence steps are executed ---")
    signal.signal(signal.SIGQUIT, signal_handler_terminate)
    if sequences[tmux_cmd][-1] == DO_ATTACH:
        print("--- attaching tmux ---")
        os.execve('/bin/sh',['/bin/sh','-c',f'tmux attach-session -t {session_name}'],os.environ)
    elif sequences[tmux_cmd][-1].startswith(DO_TERMINATE):
        terminate_all()
    elif sequences[tmux_cmd][-1].startswith(FINAL_EXEC):
        to_exec = sequences[tmux_cmd][-1][len(FINAL_EXEC):]
        parsed_exec = eval(f"f'{to_exec}'")
        print(f"--- final_exec : {parsed_exec}")
        #os.execve('/bin/sh',['/bin/sh','-c',parsed_exec],os.environ)
        #os.system(parsed_exec)
        pid = os.fork()
        if pid == 0:
            os.system(parsed_exec)
        else:
            os.waitpid(pid,0)
        print("final exec complete, terminating sessions")
        terminate_all()
    else:
        waiting_message(session_name)
        time.sleep(SLEEP_TIME)


if __name__ == '__main__':
    main()
