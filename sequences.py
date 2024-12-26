""" this module defines set of available sequences for tmux_k8s """


from seq_constants import COMMENT_TAG, NO_RETURN, FINAL_EXEC
from seq_constants import DO_ATTACH, DO_TERMINATE


KUBE_CTL = "kubectl --context {k8s_context} -n {k8s_namespace} "
KUBE_CTL_EXEC = KUBE_CTL + " exec {pod} -c {p2c(pod)} -- "
KUBE_CTL_EXEC_IT = KUBE_CTL + " exec -it {pod} -c {p2c(pod)} -- "

# logs is just example, it is simpler to use single kubectl logs with label selector
KUBE_CTL_LOGS = KUBE_CTL + "logs -f --prefix --timestamps {pod} -c {p2c(pod)}"

sequences={
    'env' : [ 
        COMMENT_TAG + " execute env on each pod and put to pod.env file",
        KUBE_CTL_EXEC + 'env > {pod}.env'
        ],
    'env-ac' : [ 
        COMMENT_TAG + " execute env on each pod and put to pod.env file, auto close",
        KUBE_CTL_EXEC + 'env > {pod}.env',
        DO_TERMINATE
        ],
    'procTcp' : [
        COMMENT_TAG + " get /proc/net/tcp on each then convert it to netstat format",
        KUBE_CTL_EXEC + ' /bin/cat /proc/net/tcp  > {pod}.procTcp.raw',
        'cat {pod}.procTcp.raw | ./proc_netstat.sh > {pod}.procTcp.parsed'
        ],
    'tcpdump-all' : [
        COMMENT_TAG + " tcpdump on any interface all traffic for 300 seconds or 100k packets",
        KUBE_CTL_EXEC + '/bin/bash -c ' +
            '"apt -y update && apt -y install tcpdump"',
        KUBE_CTL_EXEC + '/bin/bash -c ' +
            '"timeout 300 tcpdump -i any -w /tmp/{pod}.pcap -s65535 -c 100000"',
        KUBE_CTL_EXEC + '/bin/bash -c ' +
            '"rm -f /tmp/{pod}.pcap.gz && cd /tmp && gzip {pod}.pcap"',
        KUBE_CTL + 'cp {pod}:/tmp/{pod}.pcap.gz -c {p2c(pod)} --retries=4 ./{pod}.pcap.gz'
        ],
    'tcpdump-http-80' : [
        KUBE_CTL_EXEC + '/bin/bash -c "apt -y update && apt -y install tcpdump"',
        KUBE_CTL_EXEC + '/bin/bash -c ' +
            '"timeout 300 tcpdump -i any -w /tmp/{pod}.pcap -s65535 -c 100000 port 6379"',
        KUBE_CTL_EXEC + '/bin/bash -c ' +
            '"rm -f /tmp/{pod}.pcap.gz && cd /tmp && gzip {pod}.pcap"',
        KUBE_CTL + ' cp {pod}:/tmp/{pod}.pcap.gz -c {p2c(pod)} --retries=4 ./{pod}.pcap.gz'
        ],
    'tcpdump-redis-6379' : [
        KUBE_CTL_EXEC + '/bin/bash -c "apt -y update && apt -y install tcpdump"',
        KUBE_CTL_EXEC + '/bin/bash -c ' +
            '"timeout 300 tcpdump -i any -w /tmp/{pod}.pcap -s65535 -c 100000 port 6379"',
        KUBE_CTL_EXEC + '/bin/bash -c ' +
            '"rm -f /tmp/{pod}.pcap.gz && cd /tmp && gzip {pod}.pcap"',
        KUBE_CTL + 'cp {pod}:/tmp/{pod}.pcap.gz -c {p2c(pod)} --retries=4 ./{pod}.pcap.gz'
        ],
    'tcpdump-memcache-11211' : [
        KUBE_CTL_EXEC + '/bin/bash -c "apt -y update &&apt -y install tcpdump"',
        KUBE_CTL_EXEC + '/bin/bash -c ' +
            '"timeout 300 tcpdump -i any -w /tmp/{pod}.pcap -s65535 -c 100000 port 11211"',
        KUBE_CTL_EXEC + '/bin/bash -c "rm -f /tmp/{pod}.pcap.gz && cd /tmp && gzip {pod}.pcap"',
        KUBE_CTL + 'cp {pod}:/tmp/{pod}.pcap.gz -c {p2c(pod)} --retries=4 ./{pod}.pcap.gz'
        ],
    'strace' : [
        KUBE_CTL_EXEC + '/bin/bash -c "apt -y update && apt -y install strace psmisc procps"',
        KUBE_CTL_EXEC + '/bin/bash -c ' +
            '"timeout 300 strace -o /tmp/{pod}.strace -s999999 -yy -tt -T ' +
            '$(pgrep php | awk \'{print " -p " $1 }\'"',
        KUBE_CTL_EXEC + '/bin/bash -c ' +
            '"rm -f /tmp/{pod}.strace.gz && cd /tmp && gzip {pod}.strace"',
        KUBE_CTL + 'cp {pod}:/tmp/{pod}.strace.gz -c {p2c(pod)} --retries=4 ./{pod}.strace.gz'
        ],
    'strace-net-sc' : [
        KUBE_CTL_EXEC + '/bin/bash -c "apt -y update && apt -y install strace psmisc procps"',
        KUBE_CTL_EXEC + '/bin/bash -c "timeout 30' +
            '/usr/bin/strace -o /tmp/{pod}.strace -s999999 -e trace=network -yy -tt -T ' +
            '$(pgrep php | xargs -Ix echo -p x  )"',
        KUBE_CTL_EXEC + '/bin/bash -c "rm -f /tmp/{pod}.strace.gz && cd /tmp && gzip {pod}.strace"',
        KUBE_CTL + ' cp {pod}:/tmp/{pod}.strace.gz -c {p2c(pod)} --retries=4 ./{pod}.strace.gz'
        ],
     'pingKubeSvcHost' : [
        KUBE_CTL_EXEC + '/bin/bash -c "apt -y update && apt -y install iputils-ping"',
        KUBE_CTL_EXEC + '/bin/bash -c "ping -c 10 ' + '\\' + '$KUBERNETES_SERVICE_HOST"'
    ],
    'tcpdumpInstall' : [
        KUBE_CTL_EXEC + '/bin/bash -c "apt -y update && apt -y install tcpdump"'
        ],
    'straceInstall' : [
        KUBE_CTL_EXEC + '/bin/bash -c "apt -y update && apt -y install strace"'
    ],
    'pingInstall' : [
        KUBE_CTL_EXEC + '/bin/bash -c "apt -y update && apt -y install iputils-ping"'
    ],
    'psInstall' : [
        KUBE_CTL_EXEC + '/bin/bash -c "apt -y update && apt -y install psmisc procps"'
    ],

    'ps-tcpdump' : [
        KUBE_CTL_EXEC + '/bin/bash -c "ps ax | grep tcpdump"'
        ],
    'ps-strace' : [
        KUBE_CTL_EXEC + '/bin/bash -c "ps ax | grep tcpdump"'
        ],
    'pgrep-php' : [
        KUBE_CTL_EXEC + '/bin/bash -c "ps ax | grep tcpdump"'
        ],
    'exec-it-bash' : [
        KUBE_CTL_EXEC_IT + '/bin/bash',
        NO_RETURN,
        DO_ATTACH
        ],
    'exec-it-sh' : [
        KUBE_CTL_EXEC_IT + '/bin/sh',
        NO_RETURN,
        DO_ATTACH
        ],
    'logs1' : [
    KUBE_CTL_LOGS + ' > {k8s_namespace}_logs_{pod}_{p2c(pod)}.log',
    NO_RETURN,
    FINAL_EXEC + 'tail -f -q {k8s_namespace}_logs_*'
    ],
    'dry' : [ "echo \"ctx {k8s_context} ns {k8s_namespace} pod {pod} co {p2c(pod)}\" " ]
    }
