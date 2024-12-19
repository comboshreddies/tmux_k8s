# tmux_k8s

Tool tmux_k8s runs multiple executions scripts (sequences) in multiple tmux windows.
Each window runs script on one pod.

syntax for running is:
```console
./tmux_k8s <sequence_name> <k8s_context> <k8s_namespace> [<k8s-label-selector>]
or
./tmux_k8s list
```

list argument shows all available sequence names you can run


example 1:
```console
./tmux_k8s exec-it-bash usw2-staging producers app.kubernetes.io/name=main
```

This will kubectl exec -it to all pods within usw2-staging context and producers namespace,
on pods that match label app.kubernetes.io/name=main, and it will leave tmux session for 330 seconds.

You have configurable 330 seconds time to attach to tmux, switch between windows, each window
is running one kubectl --context usw2-staging -n producers exec -it selected-pod -- /bin/bash .

Once you're complete you can press ctrl+c on tmux_k8s window and tmux_k8s will terminate all windows and
created session.


Pods are selected from context and namespace and optionally sub selected by label selector. 
Label selector is optional parameter.


This tool is more a generic tmux framework that you should check and adjust before running.
Files that you should check and adjusted to your needs are:
sequences.py - defines set of sequences that one could run with this tool
pod2container.py - defines a function that should provide name of container for given pod-name

example 2:
```console
./tmux_k8s env usw2-staging producers app.kubernetes.io/name=main
```

would record each env on each pod/container selected and record output to <pod_name>.env
sequence.py section for `env` is 
```console
'env' : [ 'kubectl --context {k8s_context} -n {name_space}  exec {pod} -c {p2c(pod)} --  env > {pod}.env' ],
```

tmux_k8s runs in a loop for each pod (selected by context/namespace/label), 
executing each step of sequence, and any variable available to python, while executing this loop
is also available for parsing each sequence step.
variable k8s_context used as {k8s_context} is runtime parsed
same goes for variables name_space , pod , and p2c(pod) function.
p2c function is loaded from pod2container.py and available while executing sequence step.

You can extend usage, import any function, and if you want to use it, specify sequence as a python f
format, and it will be evaluated and then executed within tmux window, each window for each pod
For example pod named producer might have container named main-producer, and you
shuold modify pod2container.py pod2container function so for given input producer-645bb947d5-zhqj7
it returns worker as a container name this tmux should try to exec to on a given pod.


example 3:
```console
/tmux_k8s tcpdump usw2-staging web-api 
```

this tcpdump sequence looks like:
```console
'tcpdump-memcache-11211' : [
   kube_ctl_exec + '/bin/bash -c "apt -y update &&apt -y install tcpdump"',
   kube_ctl_exec + '/bin/bash -c "timeout 300 tcpdump -i any -w /tmp/{pod}.pcap -s65535 -c 100000 port 11211"',
   kube_ctl_exec + '/bin/bash -c "rm -f /tmp/{pod}.pcap.gz && cd /tmp && gzip {pod}.pcap"',
   kube_ctl + ' cp {item.metadata.name}:/tmp/{pod}.pcap.gz -c {p2c(pod)} --retries=4 ./{pod}.pcap.gz'
```

this command would jump on each pod/container, and:
first step: do apt update, then apt -y instal tcpdump
second step: run tcpdump for observing memcache, limited to 300 seconds or 100000 packets
third step: remove previously present /tmp/{pod}.pcap.gz file , then cd /tmp and gzip {pod}.pcap
fourth step: copy {pod}.pcap.gz from each pod/container to local disk copy

After execution of this tmux_k8s you will have properly named gzipped pcap samples from all pods.
note that kube_ctl_exec and kubect_ctl are prepared macros you can check in sequences.py


anyone can create it's own custom set of instructions (generally any shell script or command)
kubernetes kubectl commands were just nice example of running in parallel set of sequenced scripts
like installing tcpdump, running tcpdump, compressing pcap file, copying pcap file to local


Parsing: 

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

if k8s_context was uswest2 , and names_space was some-ns , this tmux_k8s tool will get all pods from that context and namespace and apply filter (if specified) for labels,
then for every pod selected sequence of commands will be executed

so evaluated sequence that should run via tmux shell  could look like 
```console
kubectl --context uswest2 -n some-ns exec application-5695f9ff4f-kdzx8 -c main-container -- /bin/bash -c "timeout 300 tcpdump -i any -w /tmp/{application-5695f9ff4f-kdzx8}.pcap -s65535 -c 100000 port 11211
```

Best practice:

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


