'''
This module swaps workers on demand.
'''

import boto3
import json
import paramiko

with open(r'config.json', 'r') as f:
    config = json.load(f)

def spawn_worker(parent, other):
    ec2 = boto3.resource('ec2')
    instance_params = {
            'ImageId': 'ami-0c94855ba95c71c99',  # Ubuntu 20.04 LTS 64-bit image
            'InstanceType': 't2.micro',
            'KeyName': config['key_name'],  # Replace with your key pair name
            'MinCount': 1,
            'MaxCount': 1,
            'SecurityGroupIds': [config['sec_grp']],
            'UserData': '''
                #!/bin/bash
                echo "Hello, EC2!" > /home/ubuntu/greeting.txt
            '''   }

    instance = ec2.create_instances(**instance_params)[0]
    instance.wait_until_running()
    instance.load()

    ssh = paramiko.SSHClient()
    with open(f"{config['key_name']}.pem") as f:
        key = paramiko.RSAKey.from_private_key(f)
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(instance.public_ip_address, username='ubuntu', pkey=key)

    # Copy the setup.sh script to the instance
    local_script, remote_script = 'worker_setup.sh', '/home/ubuntu/worker_setup.sh'
    local_worker_code, remote_worker_code = 'worker.py', '/home/ubuntu/worker.py'
    sftp_client = ssh.open_sftp()
    sftp_client.put(local_script, remote_script)
    sftp_client.put(local_worker_code, remote_worker_code)
    sftp_client.close()
    # Run the setup.sh script on the instance
    stdin, stdout, stderr = ssh.exec_command(f'chmod +x {remote_script} && f{remote_script}')

    # Run the setup.sh script on the instance
    stdin, stdout, stderr = ssh.exec_command(f'sudo nohup python3 worker.py --parent {parent} --other {other} --instance-id {instance.instance_id}  &>server.log &')

    return instance

    

