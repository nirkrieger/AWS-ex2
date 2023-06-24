# debug
# set -o xtrace

#Flow:
#   1) init base machine, install aws cli, setup ssh keys, security group and etc.
#   2) create two endpoint instances. copy endpoint_setup.sh, connect to each via ssh, setup , install packages and run flask apps.
#   
#   3) experiment with creating & terminating instances via boto3
#   4) implement spawn worker 




# setup AWS CLI
sudo apt update
sudo apt install awscli zip
sudo apt install jq

# Configure AWS setup (keys, region, etc)
aws configure

KEY_NAME="ex2-key-`date +'%N'`"
KEY_PEM="$KEY_NAME.pem"

echo "create key pair $KEY_PEM to connect to instances and save locally"
aws ec2 create-key-pair --key-name $KEY_NAME \
    | jq -r ".KeyMaterial" > $KEY_PEM


# secure the key pair
chmod 400 $KEY_PEM

SEC_GRP="ex2_sec_grp"

echo "setup firewall $SEC_GRP"
aws ec2 create-security-group   \
    --group-name $SEC_GRP       \
    --description "Access my instances" 

# figure out my ip
MY_IP=$(curl ipinfo.io/ip)
echo "My IP: $MY_IP"


echo "setup rule allowing SSH access to $MY_IP only"
aws ec2 authorize-security-group-ingress        \
    --group-name $SEC_GRP --port 22 --protocol tcp \
    --cidr $MY_IP/32

echo "setup rule allowing HTTP (port 8000) access to $MY_IP only"
aws ec2 authorize-security-group-ingress        \
    --group-name $SEC_GRP --port 8000 --protocol tcp \
    --cidr $MY_IP/32

# Save KEYNAME and SECGRP to config file
jq -n \
    --arg v1 "$KEY_NAME" \
    --arg v2 "$SEC_GRP" \
    '{key_name: $v1, sec_grp: $v2}' > config.json

UBUNTU_20_04_AMI="ami-042e8287309f5df03"

# Create two instances, for each endpoint.
echo "Creating 2 Ubuntu 20.04 instance..."
RUN_INSTANCES=$(aws ec2 run-instances   \
    --image-id $UBUNTU_20_04_AMI        \
    --instance-type t3.micro            \
    --key-name $KEY_NAME                \
    --count 2                           \
    --security-groups $SEC_GRP)

# Get Instance Ids
INSTANCE_ID_1=$(echo $RUN_INSTANCES | jq -r '.Instances[0].InstanceId')
INSTANCE_ID_2=$(echo $RUN_INSTANCES | jq -r '.Instances[1].InstanceId')

echo "Waiting for instance 1 creation..."
aws ec2 wait instance-running --instance-ids $INSTANCE_ID_1
echo "Waiting for instance 2 creation..."
aws ec2 wait instance-running --instance-ids $INSTANCE_ID_2


PUBLIC_IP_1=$(aws ec2 describe-instances  --instance-ids $INSTANCE_ID_1 | 
    jq -r '.Reservations[0].Instances[0].PublicIpAddress'
)

PUBLIC_IP_2=$(aws ec2 describe-instances  --instance-ids $INSTANCE_ID_2 | 
    jq -r '.Reservations[0].Instances[0].PublicIpAddress'
)

echo "Instance 1: $INSTANCE_ID_1 @ $PUBLIC_IP_1"
echo "Instance 2: $INSTANCE_ID_2 @ $PUBLIC_IP_2"



IP_LIST=("$PUBLIC_IP_1" "$PUBLIC_IP_2")

#TODO change to 

for IP in "${IP_LIST[@]}"; do
    # Copy setup file
    echo "Copying setup files to $IP..."
    scp -i $KEY_PEM -o "StrictHostKeyChecking=no" -o "ConnectionAttempts=60" /code/endpoint_setup.sh ubuntu@$IP:/home/ubuntu/
    scp -i $KEY_PEM -o "StrictHostKeyChecking=no" -o "ConnectionAttempts=60" /code/worker_setup.sh ubuntu@$IP:/home/ubuntu/
    echo "Copying config file to $IP..."
    scp -i $KEY_PEM -o "StrictHostKeyChecking=no" -o "ConnectionAttempts=60" config.json ubuntu@$IP:/home/ubuntu/

    echo "Copying private key file to $IP..."
    scp -i $KEY_PEM -o "StrictHostKeyChecking=no" -o "ConnectionAttempts=60" $KEY_PEM ubuntu@$IP:/home/ubuntu/

    echo "Copying code to production @ $IP"
    scp -i $KEY_PEM -o "StrictHostKeyChecking=no" -o "ConnectionAttempts=60" /code/endpoint_app.py ubuntu@$IP:/home/ubuntu/
    scp -i $KEY_PEM -o "StrictHostKeyChecking=no" -o "ConnectionAttempts=60" /code/worker.py ubuntu@$IP:/home/ubuntu/

    echo "Config file copied to $IP."

    echo "setup production environment"
    ssh -i $KEY_PEM -o "StrictHostKeyChecking=no" -o "ConnectionAttempts=10" ubuntu@$IP <<EOF
    chmod u+x endpoint_setup.sh
    # run setup
    ./endpoint_setup.sh
    exit
EOF
done

# Save IPS to config file
jq -n \
    --arg v1 "$PUBLIC_IP_1" \
    --arg v2 "$PUBLIC_IP_2" \
    '{ip1: $v1, ip2: $v2}' > instances.json

chmod u+x run.sh
echo "Setup is done!"