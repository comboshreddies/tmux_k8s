# tmux_k8s

Tool tmux_k8s runs multiple executions scripts (sequences) in multiple tmux windows.
Each window runs script on one pod. You can decide if you want to attach and inspect
executions per each pod, or you want to just execute and exit

It can be executed as [kubectl plugin](https://github.com/comboshreddies/tmux_k8s?tab=readme-ov-file#kubectl-plugin-kubectl-tmux)

![tmux_k8s_1](https://github.com/comboshreddies/tmux_k8s/blob/main/docs/tmux_k8s_1.svg?raw=true)

# purpose
One can easily make a a shell script to execute some sequence on each pod/container.
Executing on more than few pods might not be successful on all pods. Having output of 
many executions on one screen is not practical, and you might need to take a look on 
your own, one pod at the time. 

With this tool you can attach tmux and take a look, or you can gather results of executions. 
If you have some actions that you frequently do, like gathering some info from pods, you 
can add sequence that fits your needs, and next time you can run it fast. Tmux solves 
problem of having multiple outputs of executions on same terminal, as each tmux screen/window
is dedicated to one pod execution, so you have terminal for each pod, do ctrl+b+n and
go to next pod window.

This tool is more a generic tmux-kubectl framework that you should check and adjust to your needs.

Files that you should check and adjusted to your needs are:
* sequences.py - defines set of sequences that one could run with this tool
* pod2container.py - defines a set functions that should provide name of container for given pod-name



# syntax
syntax for running is:
```console
./tmux_k8s <sequence_name> <k8s_context> <k8s_namespace> [<k8s-label-selector>]
or
./tmux_k8s list
or
./tmux_k8s info <sequence_name>
```

list argument shows all available sequence names you can run
info shows details of execution, ie selected sequence template

When sequence_name is selected, from those available in list, pods are selected from 
context (k8s_context argument) and namespace (k8s_namespace argument) and optionally sub 
selected by label selector. Label selector is optional parameter.


# example 1:

If you have applied k8s_sample_deploys/sample_deploy1.yaml to test-run namespace on your
kubernetes service named as dev in your kubectl confguration, then:

```console
$ ./tmux_k8s exec-it-bash dev test-run app=nginx
```
will kubectl exec -it to all selected pods within dev context and test-run namespace.
Pod are seleted by matching app=nginx. After sucessfull execution you will be attached to 
tmux session containing those kubectl executions.

You can check what will be executed by looking at sequence details with command:
```console
$ ./tmux_k8s info exec-it-bash
#! execute bash on each pod in interactive mode and attach to tmux
kubectl --context {k8s_context} -n {k8s_namespace}  exec -it {pod} -c {p2c(pod)} -- /bin/bash
# no return
# attach
```
Info comand shows content of a selected sequence, and in this case (exec-it-bash sequence)  
for each pod kubectl template will be executed. 
Execution will not wait for termination of a command (as it was executed with exec -it switch, i
so kubectl exec sessions stays, and # no return instruction was given to sequence).
After script steps are executed on all pods - in this case script is just a single command - this tool 
will attach tmux to sessions that contains active windows/screens of kubectl per each pod (instruction given
with # attach step in sequence).

This sequence exec-it-bash template is evaluated (python eval), and following tmux_k8s python variables
are injected per pod:
k8s_context - 2nd argument, in this case dev kubectl config, 
k8s_namespace - 3rd argument, test-run namespace,
pod - pod this sequence is running - pod from set of selected pods
p2c(pod) - is call to a function p2c, ie pod2container with argument of a pod name

pod2container function should be customized, and contains a rule that will return container name
for given pod name. In this case, for sample_deploy1.yaml, for example pod name nginx-sample1-b88fdd4c5-9r65d, 
p2c will return container name nginx, as this is container we want to exec to. As pod might contain multiple
containers, this tool needs to know exact container name script should exec to.

# example 2:
If you have applied k8s_sample_deploys/sample_deploy2.yaml to test-run namespace on your
kubernetes service named as dev in your kubectl confguration, then:

```console
./tmux_k8s env dev test-run ver=v2
```

would record each env on each pod/container selected and record output to <pod_name>.env
```console
$ ./tmux_k8s info env
#! execute env on each pod and put to pod.env file
kubectl --context {k8s_context} -n {k8s_namespace}  exec {pod} -c {p2c(pod)} -- env > {pod}.env
```

tmux_k8s runs in a loop for each pod (selected by context/namespace/label), 
While executing each step of sequence, all variableis available to python while executing this loop
is also available for parsing each sequence step.

variable k8s_context used as {k8s_context} is runtime parsed
same goes for variables name_space, pod , and p2c(pod) function.
p2c function is loaded from pod2container.py and available while executing sequence step.

You can extend usage, write your own function, import function into tmux_k8s.py, and use it
within a template/sequence you like, following pythons f-string rules, ie put function call within braces.
Your function call will be evaluated and then executed within tmux window per pod.

If you want to have this tool working on your kubernetes setup, you need to modify 
pod2container.py pod2container function so for given input your_pod_name 
(for example producer-645bb947d5-zhqj7) pod2container function returns (for example)
worker as a container name this tmux should try to exec to on a given pod.


# example 3:

If you have applied one or both of k8s_sample_deploys/sample_deploy1.yaml and k8s_sample_deploys/sample_deploy2.yaml
```console
/tmux_k8s tcpdump-all dev test-run app=nginx 
```

this tcpdump-all sequence looks like this:
```console
$ ./tmux_k8s.py info tcpdump-all
#! tcpdump on any interface all traffic for 300 seconds or 100k packets
kubectl --context {k8s_context} -n {k8s_namespace}  exec {pod} -c {p2c(pod)} -- /bin/bash -c "apt -y update && apt -y install tcpdump"
kubectl --context {k8s_context} -n {k8s_namespace}  exec {pod} -c {p2c(pod)} -- /bin/bash -c "timeout 300 tcpdump -i any -w /tmp/{pod}.pcap -s65535 -c 100000"
kubectl --context {k8s_context} -n {k8s_namespace}  exec {pod} -c {p2c(pod)} -- /bin/bash -c "rm -f /tmp/{pod}.pcap.gz && cd /tmp && gzip {pod}.pcap"
kubectl --context {k8s_context} -n {k8s_namespace} cp {pod}:/tmp/{pod}.pcap.gz -c {p2c(pod)} --retries=4 ./{pod}.pcap.gz
# terminate
```

this command would jump on each pod/container, and:
first step: do apt update, then apt -y instal tcpdump
second step: run tcpdump for observing memcache, limited to 300 seconds or 100000 packets
third step: remove previously present /tmp/{pod}.pcap.gz file , then cd /tmp and gzip {pod}.pcap
fourth step: copy {pod}.pcap.gz from each pod/container to local disk copy

After execution of this tmux_k8s you will have properly named gzipped pcap samples from all pods.
note that kube_ctl_exec and kubect_ctl are prepared macros you can check in sequences.py
After execution on all pods of all steps, # terminate step will instruct tmux_k8s to terminate 
screen session.
Alternatively you can modify last sequence step to do # attach, as shown in example 1, so your
tmux_k8s execution will attach you to tmux and will not terminate tmux session.

anyone can create it's own custom set of instructions (generally any shell script or command)
kubernetes kubectl commands were just nice example of running in parallel set of sequenced scripts
like installing tcpdump, running tcpdump, compressing pcap file, copying pcap file to local


# Parsing: 

Parsing is done by evaluating string, for example sequence
```console
"kubectl --context {k8s_context} -n {name_space} exec {pod} -c {p2c(pod)} -- /bin/bash -c "timeout 300 tcpdump -i any -w /tmp/{pod}.pcap -s65535 -c 100000 port 11211"
```

will render local tmux_k8s.py python script variables :
k8s_context -  given via command line
names_space - given via command line
pod - extracted via python kubernetes call similar to kubectl get pods , for all pods that are matched (all in namespace or subselected by label selector)
container - example logic that is implemented in this code is that container name (that we want to exec to) is same as deployment ie base name of pod
            function p2c is mapper from pod name to container name, if it does not fit your needs , adjust it

if k8s_context was some-context , and names_space was some-ns , this tmux_k8s tool will get all pods from that context and namespace and apply filter (if specified) for labels,
then for every pod selected sequence of commands will be executed

so evaluated sequence that should run via tmux shell  could look like 
```console
kubectl --context some-context -n some-ns exec application-5695f9ff4f-kdzx8 -c main-container -- /bin/bash -c "timeout 300 tcpdump -i any -w /tmp/{application-5695f9ff4f-kdzx8}.pcap -s65535 -c 100000 port 11211
```

# Best practice:

- do always run time limited (timeout) and execution limited commands (like -c in tcpdump), otherwise
your execution might be left running on a pod for a very long time, and affect normal pod state

- if you are running something withoult limitations, create sequence that could terminate such executions
for example if you are running tcpdump, do create sequence to kill any tcpdump that might be left running

- if you need longer set of sequences, then frequent kubectl exec sequence is not optimal. 
Create local script, then on each tmux-windows/k8s-pod customize script
copy script to pod/container, run script, copy back results

- escaping quote or double quote characeters for python f formatting might not be a easy task.
I had an awk script that was pain to quote or escape properly - I've created local shell script
./proc_netstat.sh that is added to this repo and you can see how it is used within procTcp sequence


# Kubectl plugin kubectl-tmux

![tmux_k8s_2](https://github.com/comboshreddies/tmux_k8s/blob/main/docs/tmux_k8s_2.svg?raw=true)

If you put scripts kubectl-tmux and tmux_k8s in your binary path (you should adjust venv path or 
global install requirements) kubectl-tmux (shell script) is a kubectl-plugin that should be used as
```console
kubectl tmux exec-it-sh --context minikube -n test-run get pod -l app=busybox1
```
in this example exec-it-sh is sequnce available from tmux_k8s tool
you can obtain list of available sequences with 
```console
tmux_k8s list
````

# Customizing and Extending

## pod2container.py

There are two pod2container functions that tmux_k8s imports in shortened form.
```python
from pod2container import pod2container as p2c
from pod2container import pod2container_log as p2cLog
```

Both functions are imported in shortened form to make scripts/tempaltes from sequences.py compact.
Both functions are used to convert pod name (input argument) to container name.

First function pod2container ie p2c function is used for selecting main container for most operations (like exec, cp or such).

Second function pod2container_log is used in deployments like sample_deploy3.yaml, where main container you should exec to
is not the same container as the one you should take logs from.

If you need some additional container selecting logic you should add new function to pod2containe.py, import it in tmux_k8s.py
and then use it in sequences ie templates within sequences.py .

## sequences.py

Dictionary called sequences from sequences.py is imported in tmux_k8s, and it is used as source of all available scripts, sequences
within tmux_k8s. There are few simple rules:
* if first item in a list of sequences begins with a COMMENT_TAG, it is used as a help displayed in tmux_k8s list command
* you can use as many comments as you like, comments will be displayed while executing selected sequence
* within sequence you can use braces to fetch any variable or function that is available to execute_fsm function - a function in tmux_k8s that executes each step of selected sequence on each selected pod.
* as a final step you can use few predefined contants defined in seq_constants:
  * NO_RETURN instructs main sequence execution that last function should not return value, so sequence should be considered complete, otherwise execution will wait for prompt, ie return from shell executed command
  * DO_ATTACH as a last function step instructs tmux_k8s that after all sequences are complete, tmux_k8s should attach you to tmux session
  * DO_TERMINATE - after execution of all sequences tmux_k8s will terminate session an close all terminal windows.
  * FINAL_EXEC will execute final execution on local tmux_k8s running machine once all sequences are done (weather complete or not)

# NOTE:

If you do not specify attach or terminate as a last sequence step, you will be prompted with option to either:
ctrl+c to detach tmux_k8s from console while not terminating created tmux_session
ctrl+\ to terminate session and exit

This option will stay in console/terminal for configurable 330 seconds, after 330 sec expire tmux_k8s will leave tmux session.

