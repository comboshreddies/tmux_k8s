""" this module defines set of available sequences for tmux_k8s """


from seq_constants import COMMENT_TAG, NO_RETURN, FINAL_EXEC
from seq_constants import DO_ATTACH, DO_TERMINATE


KUBE_CTL = "kubectl --context {k8s_context} -n {k8s_namespace} "
KUBE_CTL_EXEC = KUBE_CTL + " exec {pod} -c {p2c(pod)} -- "
KUBE_CTL_EXEC_IT = KUBE_CTL + " exec -it {pod} -c {p2c(pod)} -- "

# logs is just example, it is simpler to use single kubectl logs with label selector
KUBE_CTL_LOGS_SWITCHES = " --prefix --timestamps --max-log-requests 100 "
KUBE_CTL_LOGS1 = KUBE_CTL + "logs -f" + KUBE_CTL_LOGS_SWITCHES + "{pod} -c {p2c(pod)}"
KUBE_CTL_LOGS2 = KUBE_CTL + "logs -f" + KUBE_CTL_LOGS_SWITCHES + "{pod} -c {p2cLog(pod)}"

sequences = {
    'env': [
        COMMENT_TAG + 'execute env on each pod and put to pod.env file',
        KUBE_CTL_EXEC + 'env > {pod}.env'
    ],
    'env-ac': [
        COMMENT_TAG + 'execute env on each pod and put to pod.env file, auto close',
        KUBE_CTL_EXEC + 'env > {pod}.env',
        DO_TERMINATE
    ],
    'env-at': [
        COMMENT_TAG + 'execute env on each pod and put to pod.env file, auto attach',
        KUBE_CTL_EXEC + 'env > {pod}.env',
        DO_ATTACH
    ],
    'procTcp': [
        COMMENT_TAG + 'get /proc/net/tcp on each then convert it to netstat format',
        KUBE_CTL_EXEC + ' /bin/cat /proc/net/tcp  > {pod}.procTcp.raw',
        'cat {pod}.procTcp.raw | ./proc_netstat.sh > {pod}.procTcp.parsed',
        DO_TERMINATE
    ],
    'tcpdump-all': [
        COMMENT_TAG + 'tcpdump on any interface all traffic for 300 seconds or 100k packets',
        KUBE_CTL_EXEC + '/bin/bash -c ' +
        '"apt -y update && apt -y install tcpdump"',
        KUBE_CTL_EXEC + '/bin/bash -c ' +
        '"timeout 300 tcpdump -i any -w /tmp/{pod}.pcap -s65535 -c 100000"',
        KUBE_CTL_EXEC + '/bin/bash -c ' +
        '"rm -f /tmp/{pod}.pcap.gz && cd /tmp && gzip {pod}.pcap"',
        KUBE_CTL + 'cp {pod}:/tmp/{pod}.pcap.gz -c {p2c(pod)} --retries=4 ./{pod}.pcap.gz',
        DO_TERMINATE
    ],
    'tcpdump-http-80': [
        COMMENT_TAG + 'install tcpdump and start tcpdump on all interfaces on port 80',
        KUBE_CTL_EXEC + '/bin/bash -c "apt -y update && apt -y install tcpdump"',
        KUBE_CTL_EXEC + '/bin/bash -c ' +
        '"timeout 300 tcpdump -i any -w /tmp/{pod}.pcap -s65535 -c 100000 port 80"',
        KUBE_CTL_EXEC + '/bin/bash -c ' +
        '"rm -f /tmp/{pod}.pcap.gz && cd /tmp && gzip {pod}.pcap"',
        KUBE_CTL + 'cp {pod}:/tmp/{pod}.pcap.gz -c {p2c(pod)} --retries=4 ./{pod}.pcap.gz',
        DO_TERMINATE
    ],
    'tcpdump-redis-6379': [
        COMMENT_TAG + 'install tcpdump and start tcpdump on all interfaces on port 6379',
        KUBE_CTL_EXEC + '/bin/bash -c "apt -y update && apt -y install tcpdump"',
        KUBE_CTL_EXEC + '/bin/bash -c ' +
        '"timeout 300 tcpdump -i any -w /tmp/{pod}.pcap -s65535 -c 100000 port 6379"',
        KUBE_CTL_EXEC + '/bin/bash -c ' +
        '"rm -f /tmp/{pod}.pcap.gz && cd /tmp && gzip {pod}.pcap"',
        KUBE_CTL + 'cp {pod}:/tmp/{pod}.pcap.gz -c {p2c(pod)} --retries=4 ./{pod}.pcap.gz',
        DO_TERMINATE
    ],
    'tcpdump-memcache-11211': [
        COMMENT_TAG + 'install tcpdump and start tcpdump on all interfaces on port 11211',
        KUBE_CTL_EXEC + '/bin/bash -c "apt -y update &&apt -y install tcpdump"',
        KUBE_CTL_EXEC + '/bin/bash -c ' +
        '"timeout 300 tcpdump -i any -w /tmp/{pod}.pcap -s65535 -c 100000 port 11211"',
        KUBE_CTL_EXEC + '/bin/bash -c "rm -f /tmp/{pod}.pcap.gz && cd /tmp && gzip {pod}.pcap"',
        KUBE_CTL + 'cp {pod}:/tmp/{pod}.pcap.gz -c {p2c(pod)} --retries=4 ./{pod}.pcap.gz',
        DO_TERMINATE
    ],
    'strace-php': [
        COMMENT_TAG + 'install strace and start strace on all php processes',
        KUBE_CTL_EXEC + '/bin/bash -c "apt -y update && apt -y install strace psmisc procps"',
        KUBE_CTL_EXEC + '/bin/bash -c ' +
        '"timeout 300 strace -o /tmp/{pod}.strace -s999999 -yy -tt -T ' +
        '$(pgrep php | awk \'{print " -p " $1 }\'"',
        KUBE_CTL_EXEC + '/bin/bash -c ' +
        '"rm -f /tmp/{pod}.strace.gz && cd /tmp && gzip {pod}.strace"',
        KUBE_CTL + 'cp {pod}:/tmp/{pod}.strace.gz -c {p2c(pod)} --retries=4 ./{pod}.strace.gz',
        DO_TERMINATE
    ],
    'strace-net-php': [
        COMMENT_TAG + 'install strace and start strace on all php processes,' +
        'record net system calls',
        KUBE_CTL_EXEC + '/bin/bash -c "apt -y update && apt -y install strace psmisc procps"',
        KUBE_CTL_EXEC + '/bin/bash -c "timeout 30' +
        '/usr/bin/strace -o /tmp/{pod}.strace -s999999 -e trace=network -yy -tt -T ' +
        '$(pgrep php | xargs -Ix echo -p x  )"',
        KUBE_CTL_EXEC + '/bin/bash -c "rm -f /tmp/{pod}.strace.gz && cd /tmp && gzip {pod}.strace"',
        KUBE_CTL + ' cp {pod}:/tmp/{pod}.strace.gz -c {p2c(pod)} --retries=4 ./{pod}.strace.gz',
        DO_TERMINATE
    ],
    'pingKubeSvcHost': [
        COMMENT_TAG + 'install ping util and ping KUBERNETES_SERVICE_HOST env variable ip',
        KUBE_CTL_EXEC + '/bin/bash -c "apt -y update && apt -y install iputils-ping"',
        KUBE_CTL_EXEC + '/bin/bash -c "ping -c 10 ' + '\\' + '$KUBERNETES_SERVICE_HOST"',
        DO_TERMINATE
    ],
    'tcpdumpInstall': [
        COMMENT_TAG + 'install tcpdump',
        KUBE_CTL_EXEC + '/bin/bash -c "apt -y update && apt -y install tcpdump"',
        DO_TERMINATE
    ],
    'straceInstall': [
        COMMENT_TAG + 'install strace',
        KUBE_CTL_EXEC + '/bin/bash -c "apt -y update && apt -y install strace"',
        DO_TERMINATE
    ],
    'pingInstall': [
        COMMENT_TAG + 'install ping',
        KUBE_CTL_EXEC + '/bin/bash -c "apt -y update && apt -y install iputils-ping"',
        DO_TERMINATE
    ],
    'psInstall': [
        COMMENT_TAG + 'install ps and pgrep',
        KUBE_CTL_EXEC + '/bin/bash -c "apt -y update && apt -y install psmisc procps"',
        DO_TERMINATE
    ],
    'ps-tcpdump': [
        COMMENT_TAG + 'check each pod if there is tcpdump process left running, attaches tmux',
        KUBE_CTL_EXEC + '/bin/bash -c "ps ax | grep tcpdump"',
        DO_ATTACH
    ],
    'exec-it-bash': [
        COMMENT_TAG + 'execute bash on each pod in interactive mode and attach to tmux',
        KUBE_CTL_EXEC_IT + '/bin/bash',
        NO_RETURN,
        DO_ATTACH
    ],
    'xs': [
        COMMENT_TAG + 'execute sh on each pod in interactive mode and attach to tmux',
        KUBE_CTL_EXEC_IT + '/bin/sh',
        NO_RETURN,
        DO_ATTACH
    ],
    'exec-it-sh': [
        COMMENT_TAG + 'execute sh on each pod in interactive mode and attach to tmux',
        KUBE_CTL_EXEC_IT + '/bin/sh',
        NO_RETURN,
        DO_ATTACH
    ],
    'logs1': [
        COMMENT_TAG + 'execute kubectl logs on each pod/container, pass it to local file' +
        ', then tail all files to console',
        KUBE_CTL_LOGS1 + ' > {k8s_namespace}_logs_{pod}_{p2c(pod)}.log',
        NO_RETURN,
        FINAL_EXEC + 'tail -f -q {k8s_namespace}_logs_*'
    ],
    'logs2': [
        COMMENT_TAG + 'execute kubectl logs on each pod/container, pass it to local file' +
        ', then tail all files to console',
        KUBE_CTL_LOGS2 + ' > {k8s_namespace}_logs_{pod}_{p2cLog(pod)}.log',
        NO_RETURN,
        FINAL_EXEC + 'tail -f -q {k8s_namespace}_logs_*'
    ],

    'dry': [
        COMMENT_TAG + ' just echo {k8s_context} {k8s_namespace} {pod} nad p2c(pod) values',
        "echo \"ctx {k8s_context} ns {k8s_namespace} pod {pod} co {p2c(pod)}\" ",
        DO_ATTACH
    ]
}
