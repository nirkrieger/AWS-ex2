#!/bin/bash

ACCESS_KEY="AKIATI5FPVXQLN5TEN5C"
SECRET_KEY="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"
REGION="us-east-1"


sudo apt update
# setup AWS CLI
sudo apt install awscli zip
# Configure AWS setup (keys, region, etc)
sudo aws configure set aws-access-key $ACCESS_KEY
sudo aws configure set aws-secret-access-key $SECRET_KEY
sudo aws configure set region $REGION

sudo apt install pip -y
pip install flask 
pip install requests
pip install atexit
pip install boto3
pip install apscheduler