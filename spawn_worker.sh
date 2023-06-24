#!/bin/bash

log_file="worker.log"

# Redirect stdout and stderr to log file
exec &> >(tee -a "$log_file")

# Read SECGRP & KEYFILE
KEY_NAME=$(jq -r '.key_name' "config.json")
SEC_GRP=$(jq -r '.sec_grp' "config.json")

# Create the EC2 instance and retrieve the instance ID
UBUNTU_20_04_AMI="ami-042e8287309f5df03"

echo "Creating Ubuntu 20.04 instance..."
RUN_INSTANCES=$(aws ec2 run-instances   \
    --image-id $UBUNTU_20_04_AMI        \
    --instance-type t3.micro            \
    --key-name $KEY_NAME                \
    --security-groups $SEC_GRP)

INSTANCE_ID=$(echo $RUN_INSTANCES | jq -r '.Instances[0].InstanceId')

echo "Waiting for instance creation..."
aws ec2 wait instance-running --instance-ids $INSTANCE_ID

PUBLIC_IP=$(aws ec2 describe-instances  --instance-ids $INSTANCE_ID | 
    jq -r '.Reservations[0].Instances[0].PublicIpAddress'
)

# Copy the bash script to the EC2 instance
scp -i $KEY_PEM -o "StrictHostKeyChecking=no" -o "ConnectionAttempts=60" spawn_worker.sh ubuntu@$PUBLIC_IP:/home/ubuntu/
scp -i $KEY_PEM -o "StrictHostKeyChecking=no" -o "ConnectionAttempts=60" worker.py ubuntu@$PUBLIC_IP:/home/ubuntu/

# Run the copied bash script on the EC2 instance
ssh -i $KEY_PEM -o "StrictHostKeyChecking=no" -o "ConnectionAttempts=10" ubuntu@$PUBLIC_IP <<EOF
    cd /home/ubuntu
    sudo bash worker_setup.sh
    sudo python3 worker.py 
    exit
EOF

# Output the instance ID for Python code to retrieve
echo $instance_id