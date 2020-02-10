#! /usr/bin/python

import subprocess
import datetime
import re
import os
import time
import sys
import tarfile
import getpass
import signal
from random import randint
from collections import defaultdict
from multiprocessing import Process
from os import listdir
from os.path import isfile, join, isdir
from subprocess import Popen, PIPE

def test():
    cli_file = "/usr/local/bin/cli"
    default_tag = "tag=" + "nrd:NRD_11_0_R5"
    cli_str = "sudo docker run  -v /mnt/glusterfs/system/user:/var/lib/system/user -v /etc/kubernetes/pki:/var/lib/pki -v /home/\`whoami\`/.kubecfg/.kube:/home/nrd/.kube/ -v /mnt/glusterfs/cli:/var/lib/cli -it " + "\$tag" + " sudo -u nrd cli "
    non_sudo_cli_str = "docker run  -v /mnt/glusterfs/system/user:/var/lib/system/user -v /etc/kubernetes/pki:/var/lib/pki -v /home/\`whoami\`/.kube:/home/nrd/.kube/ -v /mnt/glusterfs/cli:/var/lib/cli -it " + "\$tag" + " sudo -u nrd cli "
    cmd_list = ['#!/bin/sh',
            'if [ -z \"$1" ]',
            'then',
            default_tag,
            'else',
            'tag=$1',
            'fi',
            'DIREC=\'/var/lib/cli\'',
            'if [ ! -d \$DIREC ]',
            'then',
            'sudo mkdir /mnt/glusterfs/cli',
            'sudo chmod 755 /mnt/glusterfs/cli',
            'sudo chown nrd /mnt/glusterfs/cli',
            'sudo chgrp nrd /mnt/glusterfs/cli',
            'sudo ln -s /mnt/glusterfs/cli /var/lib/',
            'sudo chmod 755 /var/lib/cli',
            'sudo chown nrd /var/lib/cli',
            'sudo chgrp nrd /var/lib/cli',
            'fi',
            'if (sudo -vn && sudo -ln) 2>&1 | grep -v "may not" > /dev/null; then',
            'DIREC=/home/`whoami`/.kubecfg',
            'sudo rm -rf $DIREC',
            'if [ ! -d $DIREC ]',
            'then',
            'sudo mkdir $DIREC',
            'sudo chown nrd $DIREC',
            'sudo cp -r /home/`whoami`/.kube $DIREC',
            'sudo chmod 771 /home/\`whoami\`/.kubecfg/.kube',
            'sudo chown nrd /home/\`whoami\`/.kubecfg/.kube',
            'sudo chgrp nrd /home/\`whoami\`/.kubecfg/.kube',
            'sudo chown nrd /home/\`whoami\`/.kubecfg/.kube/config',
            'sudo chgrp nrd /home/\`whoami\`/.kubecfg/.kube/config',
            'sudo chmod 771 /home/\`whoami\`/.kubecfg/.kube/config',
            'fi',
            cli_str,
            'else',
            non_sudo_cli_str,
            'fi']

    for cmd in cmd_list:
        print(cmd)


if __name__ == "__main__":
    test()