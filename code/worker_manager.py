'''
This module swaps workers on demand.
'''

import boto3
import json
import paramiko

class WorkerManager:
    def __init__(self, parent, other, config=None):
        if config is None:
            with open(r'config.json', 'r') as f:
                config = json.load(f)
        self.config = config
        self.parent = parent
        self.other = other
        self.workers = {}

    def num_workers(self):
        return len(self.workers)

    def spawn(self):
        try:
            print('Spawning a new instance')
            ec2 = boto3.resource('ec2')
            instance_params = {
                    'ImageId': 'ami-042e8287309f5df03',  # Ubuntu 20.04 LTS 64-bit image
                    'InstanceType': 't2.micro',
                    'KeyName': self.config['key_name'],  # Replace with your key pair name
                    'MinCount': 1,
                    'MaxCount': 1,
                    'SecurityGroupIds': [self.config['sec_grp']]
                    }

            instance = ec2.create_instances(**instance_params)[0]
            instance.wait_until_running()
            instance.load()
            print(f"Instance created - {instance.instance_id} @ {instance.public_ip_address}")
        except:
            print("ERROR: Creating an instance failed!")
            return False

        self.workers[instance.instance_id] = instance
        ssh = paramiko.SSHClient()
        try:
            print(f'Connecting via SSH to {instance.public_ip_address}...')
            with open(f"{self.config['key_name']}.pem") as f:
                key = paramiko.RSAKey.from_private_key(f)
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(instance.public_ip_address, username='ubuntu', pkey=key)
            print('Connected!')
        except:
            print(f'Connecting via SSH failed!')
            return False
        
        try:
            # Copy the setup.sh script to the instance
            local_script, remote_script = 'worker_setup.sh', '/home/ubuntu/worker_setup.sh'
            local_worker_code, remote_worker_code = 'worker.py', '/home/ubuntu/worker.py'
            sftp_client = ssh.open_sftp()
            print(f'Copying {local_script}')
            sftp_client.put(local_script, remote_script)
            print(f'Copying {local_worker_code}')
            sftp_client.put(local_worker_code, remote_worker_code)
            sftp_client.close()
        except:
            print('Establishing SFTP session failed')
            return False
        
        print(f'Running {remote_script}')
        # Run the setup.sh script on the instance
        stdin, stdout, stderr = ssh.exec_command(f'chmod +x {remote_script} && {remote_script}')
        exit_status = stdout.channel.recv_exit_status()
        if exit_status != 0:
            print(f'worker setup has failed! {stderr.read()}')
        print('===== SETUP IS DONE! =====\n')
        print(f'Running: sudo nohup python3 worker.py --parent {self.parent} --other {self.other} --instance-id {instance.instance_id}  &> server.log ')
        # Run the setup.sh script on the instance
        stdin, stdout, stderr = ssh.exec_command(f'sudo nohup python3 worker.py --parent {self.parent} --other {self.other} --instance-id {instance.instance_id}  &>server.log &')
        
        return True
        
    def terminate(self, instance_id):
        if instance_id in self.workers:
            self.workers[instance_id].terminate()
            self.workers.pop(instance_id)
            return True
        
        print(f'Big Balagan! worker {instance_id} is not in workers!')
        return False
    


