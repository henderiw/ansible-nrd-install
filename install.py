#! /usr/bin/python

# ***************************************************************************
#
#              Copyright (c) 2013-2015 Alcatel-Lucent, 2016 Nokia
#
# **************************************************************************
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

class installUpdates():
    def __init__(self, *args, **kwargs):
        self.host = hostname
        self.username = username
        self.docker_dir = docker_dir
        self.script_dir = script_dir
        self.helm_dir = helm_dir
        self.rbac_dir = rbac_dir
 
    def run_scripts(self):
        self.load_docker_images(self.host,self.username,self.docker_dir)
        self.load_helm_charts(self.host,self.username,self.helm_dir)
        self.load_scripts(self.host,self.username,self.script_dir)
        self.db_tasks(self.host,self.username)

    def run_load_docker_images(self):
        self.load_docker_images(self.host,self.username,self.docker_dir)

    def run_load_helm_charts(self):
        self.load_helm_charts(self.host,self.username,self.helm_dir)

    def run_load_scripts(self):
        self.load_scripts(self.host,self.username,self.script_dir)

    def run_db_tasks(self):
        self.db_tasks(self.host,self.username)

    def create_config_map(self, name='nrf', namespace='nrd', file="scripts/nrf.json", istio='enabled'):
        config_file = "--from-file=" + file
        with open(os.devnull, 'w') as devnull:
            name_space = Popen(["kubectl", "create", "namespace", namespace], stdout=devnull, stderr=devnull)
            name_space.communicate()

            name_space = Popen(["kubectl", "create", "namespace", "nrd-management"], stdout=devnull, stderr=devnull)
            name_space.communicate()

            name_space = Popen(["kubectl", "create", "namespace", "nrd-database"], stdout=devnull, stderr=devnull)
            name_space.communicate()

            if istio == 'enabled':
                name_space = Popen(["kubectl", "label", "namespace", namespace, "istio-injection=enabled"], stdout=devnull, stderr=devnull)
                name_space.communicate()
            
            proc = Popen(["kubectl", "create", "configmap", name, config_file, "-n", namespace], stdout=PIPE, stderr=PIPE)
            out, err = proc.communicate()

    def sendSshCommand(self, cmd, username, host):
        final_cmd = ["ssh", "-o", "UserKnownHostsFile=/dev/null", "-o", "LogLevel=ERROR", "-o", "StrictHostKeyChecking=no", "-i", "~/.ssh/paco_rsa", username+"@"+host] + cmd

        pipe = Popen(final_cmd, stdout=PIPE, stderr=PIPE)
        out, err = pipe.communicate()

        return out, err

    def get_json_file(self, tag, username, host):
        dirpath = "/tmp/" + "nrd_" + str(randint(111111, 999999))
        temp_file = dirpath + "/" + "nrf.json"
        cmd_list = [["mkdir", str(dirpath)],
                    ["sudo", "docker", "create", "-ti", "--name", "dummy", tag, "bash"],
                    ["sudo", "docker", "cp", "dummy:/etc/sysconfig/nrf.json", temp_file],
                    ["sudo", "chmod", "777", temp_file],
                    ["sudo", "docker", "rm", "-fv", "dummy"]]
        for cmd in cmd_list:
            self.sendSshCommand(cmd, username, host)

        self.create_config_map(name='nrf', namespace='nrd', file=temp_file)
        # we will create config map for nrfparameters and qcow2 version json files
        self.create_config_map(name='nrdplatformcfg', namespace='default', file="/etc/sysconfig/nrfKubernetes.json", istio='disabled')
        self.create_config_map(name='imageversion', namespace='default', file="/etc/sysconfig/nrfKubernetes_version.json", istio='disabled')
        with open(os.devnull, 'w') as devnull:
            cm = Popen(["kubectl", "create", "configmap", "kpikci", "--from-literal=ci=15", "--from-literal=ri=15", "--from-literal=retention=7"], stdout=devnull, stderr=devnull)
            cm.communicate()

    def db_tasks(self, host, username):
      self.update_pv_file(host, username)
      self.update_pvc_file(host, username)
      with open(os.devnull, 'w') as devnull:
          proc = Popen(["kubectl", "create", "namespace", "nrd-database"], stdout=PIPE, stderr=PIPE)
          out, err = proc.communicate()

          proc = Popen(["kubectl", "create", "-f", "/tmp/nrddb-pv.yaml"], stdout=PIPE, stderr=PIPE)
          out, err = proc.communicate()

          proc = Popen(["kubectl", "create", "-f", "/tmp/nrddb-pvc.yaml"], stdout=PIPE, stderr=PIPE)
          out, err = proc.communicate()
    
    def load_docker_images(self, host, username, location):
      files = [f for f in listdir(location) if isfile(join(location, f))]
      nrd_tag_name = None
      for docker_file in files:
        docker_file_full = location + "/" + docker_file
        try:
            subprocess.check_output(["scp","-o", "UserKnownHostsFile=/dev/null", "-o", "LogLevel=ERROR", "-o", "StrictHostKeyChecking=no", "-i", "~/.ssh/paco_rsa", docker_file_full, username+"@"+host+":/tmp/"])
        except Exception as error:
            return str(error) 
##        out, err = self.sendSshCommand(["sudo", "-u", "root", "docker", "load", "--input", "/tmp/" + docker_file], username, host)
        if err is not None:
            out = re.search('Loaded image: (.*)', out)
        if out:
            registry_name = host + ":5000/" + out.group(1)
            print(registry_name)
            print(out)
            print(out.group(0))
            print(out.group(1))
            if "nrd:NRD" in out.group(1):
                self.update_user_local_cli(host, username, out.group(1))
##                if "master" in hostname:
                    self.get_json_file(out.group(1), username, host)
            try:
##                subprocess.check_output(["ssh","-o", "UserKnownHostsFile=/dev/null", "-o", "LogLevel=ERROR", "-o", "StrictHostKeyChecking=no", "-i", "~/.ssh/paco_rsa", username+"@"+host,"sudo","-u","root", "docker","image","tag",out.group(1), registry_name])
            except Exception as error:
                return str(error) 
            try:
##                subprocess.check_output(["ssh","-o", "UserKnownHostsFile=/dev/null", "-o", "LogLevel=ERROR", "-o", "StrictHostKeyChecking=no", "-i", "~/.ssh/paco_rsa", username+"@"+host,"sudo","-u","root","docker","image","push", registry_name])
            except Exception as error:
                return str(error)
        subprocess.check_output(["ssh","-o", "UserKnownHostsFile=/dev/null", "-o", "LogLevel=ERROR", "-o", "StrictHostKeyChecking=no", "-i", "~/.ssh/paco_rsa", username+"@"+host, "rm", "-f", "/tmp/"+docker_file])

    def update_user_local_cli(self, host, username, nrd_tag_name):
        if nrd_tag_name is not None:
            cli_file = "/usr/local/bin/cli"
            default_tag = "tag=" + nrd_tag_name
            cli_str = "sudo docker run  -v /mnt/glusterfs/system/user:/var/lib/system/user -v /etc/kubernetes/pki:/var/lib/pki -v /home/\`whoami\`/.kubecfg/.kube:/home/nrd/.kube/ -v /mnt/glusterfs/cli:/var/lib/cli -it " + "\$tag" + " sudo -u nrd cli "
            non_sudo_cli_str = "docker run  -v /mnt/glusterfs/system/user:/var/lib/system/user -v /etc/kubernetes/pki:/var/lib/pki -v /home/\`whoami\`/.kube:/home/nrd/.kube/ -v /mnt/glusterfs/cli:/var/lib/cli -it " + "\$tag" + " sudo -u nrd cli "
            cmd_list = [["sudo", "touch", cli_file ],
                      ["sudo", "echo", "\"#!/bin/sh\"", ">", "/tmp/cli"],
                      ["sudo", "echo", "if [ -z \\\"\$1\\\" ]", ">>", "/tmp/cli"],
                      ["sudo", "echo", "then", ">>", "/tmp/cli"],
                      ["sudo", "echo", default_tag, ">>", "/tmp/cli"],
                      ["sudo", "echo", "else", ">>", "/tmp/cli"],
                      ["sudo", "echo", "tag=\$1", ">>", "/tmp/cli"],
                      ["sudo", "echo", "fi", ">>", "/tmp/cli"],
                      ["sudo", "echo", "DIREC=\'/var/lib/cli\'", ">>", "/tmp/cli"],
                      ["sudo", "echo", "if [ ! -d \$DIREC ]", ">>", "/tmp/cli"],
                      ["sudo", "echo", "then", ">>", "/tmp/cli"],
                      ["sudo", "echo", "sudo mkdir /mnt/glusterfs/cli", ">>",  "/tmp/cli"],
                      ["sudo", "echo", "sudo chmod 755 /mnt/glusterfs/cli", ">>", "/tmp/cli"],
                      ["sudo", "echo", "sudo chown nrd /mnt/glusterfs/cli", ">>", "/tmp/cli"],
                      ["sudo", "echo", "sudo chgrp nrd /mnt/glusterfs/cli", ">>", "/tmp/cli"],
                      ["sudo", "echo", "sudo ln -s /mnt/glusterfs/cli /var/lib/", ">>", "/tmp/cli"],
                      ["sudo", "echo", "sudo chmod 755 /var/lib/cli", ">>", "/tmp/cli"],
                      ["sudo", "echo", "sudo chown nrd /var/lib/cli", ">>", "/tmp/cli"],
                      ["sudo", "echo", "sudo chgrp nrd /var/lib/cli", ">>", "/tmp/cli"],
                      ["sudo", "echo", "fi", ">>", "/tmp/cli"],
                      ["sudo", "echo", "if \(sudo \-vn \&\& sudo \-ln\) 2\>\&1 \| grep -v \\\"may not\\\" \> /dev/null\; then", ">>", "/tmp/cli"],
                      ["sudo", "echo", "DIREC=/home/\`whoami\`/.kubecfg", ">>", "/tmp/cli"],
                      ["sudo", "echo", "sudo rm -rf \$DIREC", ">>", "/tmp/cli"],
                      ["sudo", "echo", "if [ ! -d \$DIREC ]", ">>", "/tmp/cli"],
                      ["sudo", "echo", "then", ">>", "/tmp/cli"],
                      ["sudo", "echo", "sudo mkdir \$DIREC", ">>", "/tmp/cli"],
                      ["sudo", "echo", "sudo chown nrd \$DIREC", ">>", "/tmp/cli"],
                      ["sudo", "echo", "sudo cp -r /home/\`whoami\`/.kube \$DIREC", ">>", "/tmp/cli"],
                      ["sudo", "echo", "sudo chmod 771 /home/\`whoami\`/.kubecfg/.kube", ">>", "/tmp/cli"],
                      ["sudo", "echo", "sudo chown nrd /home/\`whoami\`/.kubecfg/.kube", ">>", "/tmp/cli"],
                      ["sudo", "echo", "sudo chgrp nrd /home/\`whoami\`/.kubecfg/.kube", ">>", "/tmp/cli"],
                      ["sudo", "echo", "sudo chown nrd /home/\`whoami\`/.kubecfg/.kube/config", ">>", "/tmp/cli"],
                      ["sudo", "echo", "sudo chgrp nrd /home/\`whoami\`/.kubecfg/.kube/config", ">>", "/tmp/cli"],
                      ["sudo", "echo", "sudo chmod 771 /home/\`whoami\`/.kubecfg/.kube/config", ">>", "/tmp/cli"],
                      ["sudo", "echo", "fi", ">>", "/tmp/cli"],
                      ["sudo", "echo", cli_str, ">>", "/tmp/cli"],
                      ["sudo", "echo", "else", ">>", "/tmp/cli"],
                      ["sudo", "echo", non_sudo_cli_str, ">>", "/tmp/cli"],
                      ["sudo", "echo", "fi", ">>", "/tmp/cli"],
                      ["sudo", "mv", "/tmp/cli", cli_file],
                      ["sudo", "chmod", "+x", cli_file ]]

            for cmd in cmd_list:
                out, err = self.sendSshCommand(cmd, username, host)

    def update_pv_file(self, host, username):
        pv_file = "/tmp/nrddb-pv.yaml"
        cmd_list = [["sudo", "touch", pv_file],
                    ["sudo", "chmod", "777", pv_file],
                    ["sudo", "echo", "kind:", "PersistentVolume", ">>", pv_file],
                    ["sudo", "echo", "apiVersion:", "v1", ">>", pv_file],
                    ["sudo", "echo", "metadata:", ">>", pv_file],
                    ["sudo", "echo", "'  name:'", "task-pv-volume", ">>", pv_file],
                    ["sudo", "echo", "'  namespace:'", "nrd-database", ">>", pv_file],
                    ["sudo", "echo", "'  labels:'", ">>", pv_file],
                    ["sudo", "echo", "'    type:'", "local", ">>", pv_file],
                    ["sudo", "echo", "spec:", ">>", pv_file],
                    ["sudo", "echo", "'  storageClassName:'", "manual", ">>", pv_file],
                    ["sudo", "echo", "'  capacity:'", ">>", pv_file],
                    ["sudo", "echo", "'    storage:'", "2Gi", ">>", pv_file],
                    ["sudo", "echo", "'  accessModes:'", ">>", pv_file],
                    ["sudo", "echo", "'    -'", "ReadWriteMany", ">>", pv_file],
                    ["sudo", "echo", "'  hostPath:'", ">>", pv_file],
                    ["sudo", "echo", "'    path:'", "\"/mnt/glusterfs/db\"", ">>", pv_file],
                    ["sudo", "chmod", "+x", pv_file ]]
        for cmd in cmd_list:
                out, err = self.sendSshCommand(cmd, username, host)

    def update_pvc_file(self, host, username):
        pvc_file = "/tmp/nrddb-pvc.yaml"
        cmd_list = [["sudo", "touch", pvc_file],
                    ["sudo", "chmod", "777", pvc_file],
                    ["sudo", "echo", "kind:", "PersistentVolumeClaim", ">>", pvc_file],
                    ["sudo", "echo", "apiVersion:", "v1", ">>", pvc_file],
                    ["sudo", "echo", "metadata:", ">>", pvc_file],
                    ["sudo", "echo", "'  name:'", "task-pv-claim", ">>", pvc_file],
                    ["sudo", "echo", "'  namespace:'", "nrd-database", ">>", pvc_file],
                    ["sudo", "echo", "spec:", ">>", pvc_file],
                    ["sudo", "echo", "'  storageClassName:'", "manual", ">>", pvc_file],
                    ["sudo", "echo", "'  accessModes:'", ">>", pvc_file],
                    ["sudo", "echo", "'    -'", "ReadWriteMany", ">>", pvc_file],
                    ["sudo", "echo", "'  resources:'", ">>", pvc_file],
                    ["sudo", "echo", "'    requests:'", ">>", pvc_file],
                    ["sudo", "echo", "'      storage:'", "1Gi",  ">>", pvc_file],
                    ["sudo", "chmod", "+x", pvc_file ]] 
        for cmd in cmd_list:
                out, err = self.sendSshCommand(cmd, username, host)    

    def load_helm_charts(self, host, username, location):
      dirs = [d for d in listdir(location) if isdir(join(location, d))]
      for helm_dir in dirs:
        helm_dir_full = location + "/" + helm_dir
        self.sendSshCommand(["rm", "-rf", "/tmp/" + helm_dir], username, host)
        try:
###            subprocess.check_output(["scp","-o", "UserKnownHostsFile=/dev/null", "-o", "LogLevel=ERROR", "-o", "StrictHostKeyChecking=no", "-i", "~/.ssh/paco_rsa",  "-r", helm_dir_full,  username+"@"+host+":/tmp/"])
            self.sendSshCommand(["rm", "-f", "/tmp/" + helm_dir + "/templates/Namespace_Label.yaml" ], username, host)
        except Exception as error:
            return str(error)    
        try:
            subprocess.check_output(["ssh","-o", "UserKnownHostsFile=/dev/null", "-o", "LogLevel=ERROR", "-o", "StrictHostKeyChecking=no", "-i", "~/.ssh/paco_rsa",  username+"@"+host, "helm","push","-f","/tmp/"+helm_dir,host])
        except Exception as error:
            return str(error)    
        try:
            subprocess.check_output(["ssh","-o", "UserKnownHostsFile=/dev/null", "-o", "LogLevel=ERROR", "-o", "StrictHostKeyChecking=no", "-i", "~/.ssh/paco_rsa",  username+"@"+host, "helm","repo","update"])
        except Exception as error:
            return str(error)

    def load_scripts(self, host, username, location):
        try:
            with open(location + "/nrd.service", "w+") as fid:
              # Create NRD-CLI-Service file
              service_file_content = [
                "[Unit]",
                "Description=NRD CLI - Remote Services",
                "After=multi-user.target",
                "[Service]",
                "Type=simple",
                "User=root",
                "ExecStart=/usr/bin/hostRpc",
                "RemainAfterExit=no",
                "Restart=on-failure",
                "RestartSec=5s",
                "[Install]",
                "WantedBy=multi-user.target"
              ]
              for line in service_file_content:
                fid.write(line + "\n")
        except Exception as error:
            print(error)

        files = [f for f in listdir(location) if isfile(join(location, f))]
        scp_cmd = ["scp","-o", "UserKnownHostsFile=/dev/null", "-o", "LogLevel=ERROR", "-o", "StrictHostKeyChecking=no", "-i", "~/.ssh/paco_rsa",]
        ssh_cmd = ["ssh","-o", "UserKnownHostsFile=/dev/null", "-o", "LogLevel=ERROR", "-o", "StrictHostKeyChecking=no", "-i", "~/.ssh/paco_rsa", username+"@"+host]
        for script_file in files:
            script_file_full = location + "/" + script_file
            print(script_file_full)
            if script_file == "admin_tech_support.py":
                try:
                    subprocess.check_output(scp_cmd + [script_file_full, username+"@"+host+":/tmp/"])
                except Exception as error:
                    return str(error) 
                try:
##                    subprocess.check_output(ssh_cmd + ["sudo","-u","root", "cp","/tmp"+script_file, "/usr/bin/"])
##                    subprocess.check_output(ssh_cmd + ["sudo","-u","root", "chmod","+x","/usr/bin/"+script_file])
                except Exception as error:
                    return str(error)

            if script_file == "rpc.py":
                try:
                    subprocess.check_output(scp_cmd + [script_file_full, username+"@"+host+":/tmp/"])
                except Exception as error:
                    return str(error) 
                try:
#                    subprocess.check_output(ssh_cmd + ["sudo","-u","root", "cp","/tmp/"+script_file, "/usr/bin/hostRpc"])
#                    subprocess.check_output(ssh_cmd + ["sudo","-u","root", "chmod","+x","/usr/bin/hostRpc"])
                except Exception as error:
                    return str(error)

            if script_file == "nrdcli.service":
                try:
                    subprocess.check_output(scp_cmd + [script_file_full, username+"@"+host+":/tmp/"])
                except Exception as error:
                    return str(error) 
                try:

                    with open(os.devnull, 'w') as devnull:
##                        nrd_cli_service = Popen(ssh_cmd + ["sudo", "-u", "root", "cp", "/tmp/"+script_file, "/usr/lib/systemd/system/"], stdout=devnull, stderr=devnull)
                        nrd_cli_service.communicate()

##                        nrd_cli_service = Popen(ssh_cmd + ["sudo", "-u", "root", "systemctl", "enable", "nrdcli.service"], stdout=devnull, stderr=devnull)
                        nrd_cli_service.communicate()

##                        nrd_cli_service = Popen(ssh_cmd + ["sudo", "-u", "root", "systemctl", "daemon-reload"], stdout=devnull, stderr=devnull)
                        nrd_cli_service.communicate()

##                        nrd_cli_service = Popen(ssh_cmd + ["sudo", "-u", "root", "systemctl", "restart", "nrdcli"], stdout=devnull, stderr=devnull)
                        nrd_cli_service.communicate()

                except Exception as error:
                    return str(error)

            if script_file == "find_service_worker":
                try:
                    subprocess.check_output(scp_cmd + [script_file_full,  username+"@"+host+":/tmp/"])
                except Exception as error:
                    return str(error)
                try:
##                    subprocess.check_output(ssh_cmd + ["sudo","-u","root", "cp","/tmp/"+script_file, "/usr/local/bin/"])
##                    subprocess.check_output(ssh_cmd + ["sudo","-u","root", "chmod","+x","/usr/local/bin/"+script_file])
                except Exception as error:
                    return str(error)
        

class pullImages():
    def __init__(self, *args, **kwargs):
        self.host = hostname
        self.username = username
        self.docker_dir = docker_dir
        self.script_dir = script_dir
        self.helm_dir = helm_dir

    def run_scripts(self):
        self.load_docker_images(self.host,self.username,self.docker_dir)
        self.load_helm_charts(self.host,self.username,self.helm_dir)
        self.load_scripts(self.host,self.username,self.script_dir)
        self.db_tasks(self.host,self.username)

    def run_pull_images(self):
        self.pull_images(self.host,self.username)

    def pull_images(self, host, username):
        #pull all the docker images proactively to worker node
        # we can assume the master node from which this install script is called already has all images locaed by now, so we will get list from docker image ls command
        proc = Popen(["sudo", "docker", "image", "ls"], stdout=PIPE, stderr=PIPE)
        out, err = proc.communicate()
        if out:
            for line in out.splitlines():
##                if "master" in line:
                    fields = line.split()
                    image_name= fields[0] + ":" + fields[1]
                    try:
                        subprocess.check_output(["ssh","-o", "UserKnownHostsFile=/dev/null", "-o", "LogLevel=ERROR", "-o", "StrictHostKeyChecking=no",  username+"@"+host,"sudo","docker","image", "pull",image_name])
                    except Exception as error:
                        return str(error)
            
        

def worker(job):
    job.run_scripts()

def docker_task(job):
    job.run_load_docker_images()

def helm_task(job):
    job.run_load_helm_charts()

def script_task(job):
    job.run_load_scripts()

def db_task(job):
    job.run_db_tasks()

def image_task(job):
    job.run_pull_images()

def progressbar(it, prefix="", size=60, file=sys.stdout):
    count = len(it)
    def show(j):
        x = int(size*j/count)
        file.write("%s[%s%s] %i/%i\r" % (prefix, "#"*x, "."*(size-x), j, count))
        file.flush()

    show(0)
    for i, item in enumerate(it):
        yield item
        show(i+1)

    file.write("\n")
    file.flush()

def get_hostnames():
    with open('/etc/hosts', 'r') as f:
        hostlines = f.readlines()
    hostlines = [line.strip() for line in hostlines
                 if not line.startswith('#') and line.strip() != '']
    hosts = []
    for line in hostlines:
        if "localhost" not in line and "tfMaster" in line:
            hostname = line.split('#')[0].split()[1]
            hosts.append(hostname)
    return hosts

def get_workers_hostnames():
    with open('/etc/hosts', 'r') as f:
        hostlines = f.readlines()
    hostlines = [line.strip() for line in hostlines
                 if not line.startswith('#') and line.strip() != '']
    hosts = []
    for line in hostlines:
        if "localhost" not in line and "tfWorker" in line:
            hostname = line.split('#')[0].split()[1]
            hosts.append(hostname)
    return hosts

def get_masters_hostnames():
    with open('/etc/hosts', 'r') as f:
        hostlines = f.readlines()
    hostlines = [line.strip() for line in hostlines
                 if not line.startswith('#') and line.strip() != '']
    hosts = []
    for line in hostlines:
        if "localhost" not in line and "tfMaster" in line:
            hostname = line.split('#')[0].split()[1]
            hosts.append(hostname)
    return hosts

def keyboardInterruptHandler(signal, frame):
    print("KeyboardInterrupt (ID: {}) has been caught, Cleaning up...".format(signal))

if __name__ == "__main__":
    signal.signal(signal.SIGINT, keyboardInterruptHandler)

    hostname_list = get_hostnames()
    username = 'henderiw'
    #username = str(getpass.getuser())
    job_list = list()
    worker_job_list = list()

    cwd = os.getcwd()
    docker_dir  = cwd + "/docker_images"
    helm_dir = cwd + "/charts"
    script_dir = cwd + "/scripts"
    rbac_dir = cwd + "/scripts/rbac/access-group"

    for hostname in hostname_list:
        job = installUpdates(hostname=hostname,
                             username=username,
                             docker_dir=docker_dir,
                             helm_dir=helm_dir,
                             script_dir=script_dir,
                             rbac_dir=rbac_dir)
        job_list.append(job)

    process_list = []

    #this is a temporary solution, we ahve to give write access to glusterfs mount on all workers to all suers(777)
    workers_node_list = get_workers_hostnames()
    for worker_node in workers_node_list:
        cmd_list = [["sudo","mkdir", "/mnt/glusterfs/db"],                    
                    ["sudo", "chmod", "777", "/mnt/glusterfs/db"],
                   ]
        for cmd in cmd_list:
            final_cmd = ["ssh", "-o", "UserKnownHostsFile=/dev/null", "-o", "LogLevel=ERROR", "-o", "StrictHostKeyChecking=no", "-i", "~/.ssh/paco_rsa", username+"@"+worker_node] + cmd

            pipe = Popen(final_cmd, stdout=PIPE, stderr=PIPE)
            out, err = pipe.communicate()

    masters_node_list = get_masters_hostnames()
    for master_node in masters_node_list:
        cmd_list = [
                    ["sudo", "mkdir", "/mnt/glusterfs/snmp"],
                    ["sudo", "mkdir", "/mnt/glusterfs/kpikci"],
                    ["sudo", "mkdir", "/mnt/glusterfs/cli"],
                    ["sudo", "mkdir", "/mnt/glusterfs/cli/system"],
                    ["sudo", "mkdir", "/mnt/glusterfs/cli/user"],
                    ["sudo", "mkdir", "/mnt/glusterfs/system"],
                    ["sudo", "mkdir", "/mnt/glusterfs/system/user"],
                    ["sudo", "chown", "nrd", "/mnt/glusterfs/snmp"],
                    ["sudo", "chown", "nrd", "/mnt/glusterfs/kpikci"],
                    ["sudo", "chown", "nrd", "/mnt/glusterfs/cli"],
                    ["sudo", "chown", "nrd", "/mnt/glusterfs/cli/system"],
                    ["sudo", "chown", "nrd", "/mnt/glusterfs/cli/user"],
                    ["sudo", "chown", "nrd", "/mnt/glusterfs/system"],
                    ["sudo", "chown", "nrd", "/mnt/glusterfs/system/user"],
                    ["sudo", "chgrp", "nrd", "/mnt/glusterfs/snmp"],
                    ["sudo", "chgrp", "nrd", "/mnt/glusterfs/kpikci"],
                    ["sudo", "chgrp", "nrd", "/mnt/glusterfs/cli"],
                    ["sudo", "chgrp", "nrd", "/mnt/glusterfs/cli/system"],
                    ["sudo", "chgrp", "nrd", "/mnt/glusterfs/cli/user"],
                    ["sudo", "chgrp", "nrd", "/mnt/glusterfs/system"],
                    ["sudo", "chgrp", "nrd", "/mnt/glusterfs/system/user"],
                    ["sudo", "chmod", "755", "/mnt/glusterfs/snmp"],
                    ["sudo", "chmod", "755", "/mnt/glusterfs/kpikci"],
                    ["sudo", "chmod", "755", "/mnt/glusterfs/cli"],
                    ["sudo", "chmod", "751", "/mnt/glusterfs/cli/system"],
                    ["sudo", "chmod", "775", "/mnt/glusterfs/cli/user"],
                    ["sudo", "chmod", "755", "/mnt/glusterfs/system"],
                    ["sudo", "chmod", "751", "/mnt/glusterfs/system/user"],
                    ["sudo", "ln", "-s", "/mnt/glusterfs/snmp", "/var/lib/"],
                    ["sudo", "ln", "-s", "/mnt/glusterfs/kpikci", "/var/lib/"],
                    ["sudo", "ln", "-s", "/mnt/glusterfs/cli", "/var/lib/"],
                    ["sudo", "chown", "nrd", "/var/lib/cli"],
                    ["sudo", "chgrp", "nrd", "/var/lib/cli"],
                   ]
        for cmd in cmd_list:
            final_cmd = ["ssh", "-o", "UserKnownHostsFile=/dev/null", "-o", "LogLevel=ERROR", "-o", "StrictHostKeyChecking=no", "-i", "~/.ssh/paco_rsa", username+"@"+master_node] + cmd

            pipe = Popen(final_cmd, stdout=PIPE, stderr=PIPE)
            out, err = pipe.communicate()

    worker_list = [docker_task, helm_task, script_task, db_task]
    for worker in worker_list:
        for job in job_list:
            process = Process(target=worker, args=(job,))
            process_list.append(process)
            process.start()

    active_count_at_start = [process.is_alive() for process in process_list if process.is_alive() == True]
    active_count = [process.is_alive() for process in process_list if process.is_alive() == True]
    for i in progressbar(range(process_list.__len__()), "Installing on Master Nodes", 40):
        while active_count.__len__():
            active_count = [process.is_alive() for process in process_list if process.is_alive() == True]
            if active_count_at_start.__len__() == active_count.__len__():
                time.sleep(1)
                continue
            elif active_count_at_start.__len__() > active_count.__len__():
                active_count_at_start = active_count
                break
            time.sleep(1)

    for process in process_list:
        process.join()

    try:
        files = [f for f in listdir(rbac_dir) if isfile(join(rbac_dir, f))]
        for file in files:
            with open(os.devnull, 'w') as devnull:
                rbac = Popen(["kubectl", "apply", "-f", rbac_dir +  "/" + file], stdout=devnull, stderr=devnull)
                rbac.communicate()
    except Exception:
       pass

    for hostname in workers_node_list:
        job = pullImages(hostname=hostname, username=username, docker_dir=docker_dir, helm_dir=helm_dir, script_dir=script_dir)
        worker_job_list.append(job)

    process_list = []
    task_list = [image_task]
    for task in task_list:
        for job in worker_job_list:
            process = Process(target=task, args=(job,))
            process_list.append(process)
            process.start()

    active_count_at_start = [process.is_alive() for process in process_list if process.is_alive() == True]
    active_count = [process.is_alive() for process in process_list if process.is_alive() == True]
    for i in progressbar(range(process_list.__len__()), "Installing on Worker Nodes", 40):
        while active_count.__len__():
            active_count = [process.is_alive() for process in process_list if process.is_alive() == True]
            if active_count_at_start.__len__() == active_count.__len__():
                time.sleep(1)
                continue
            elif active_count_at_start.__len__() > active_count.__len__():
                active_count_at_start = active_count
                break
            time.sleep(1)

    for process in process_list:
        process.join()

