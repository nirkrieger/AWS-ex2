#!/bin/bash
sudo apt update -y
# setup AWS CLI
sudo apt install awscli zip -y
# Configure AWS setup (keys, region, etc)
aws configure

sudo apt install pip -y
pip install flask 
pip install requests
pip install atexit
pip install boto3
pip install apscheduler
pip install paramiko