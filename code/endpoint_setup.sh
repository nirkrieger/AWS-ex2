#!/bin/bash
sudo apt update -y
# setup AWS CLI
sudo apt install awscli zip -y
# Configure AWS setup (keys, region, etc)
aws configure

SEC_GRP="ex2_sec_grp"

# figure out my ip
MY_IP=$(curl ipinfo.io/ip)
echo "My IP: $MY_IP"

# setup firewall rules
echo "setup rule allowing SSH access to $MY_IP only"
aws ec2 authorize-security-group-ingress        \
    --group-name $SEC_GRP --port 22 --protocol tcp \
    --cidr $MY_IP/32

echo "setup rule allowing HTTP (port 8000) access to $MY_IP only"
aws ec2 authorize-security-group-ingress        \
    --group-name $SEC_GRP --port 8000 --protocol tcp \
    --cidr $MY_IP/32


sudo apt install pip -y
pip install pyOpenSSL --upgrade
pip install flask requests boto3 apscheduler paramiko