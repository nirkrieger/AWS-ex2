# debug
# set -o xtrace

#Flow:
#   1) init base machine, install aws cli, setup ssh keys, security group and etc.
#   2) create two endpoint instances. copy endpoint_setup.sh, connect to each via ssh, setup , install packages and run flask apps.
#   
#   3) experiment with creating & terminating instances via boto3
#   4) implement spawn worker 



KEY_NAME="cloud-course-`date +'%N'`"
KEY_PEM="$KEY_NAME.pem"

ACCESS_KEY="AKIATI5FPVXQLN5TEN5C"
SECRET_KEY="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"
REGION="us-east-1"

# setup AWS CLI
sudo apt install awscli zip
# Configure AWS setup (keys, region, etc)
aws configure set aws-access-key $ACCESS_KEY
aws configure set aws-secret-access-key $SECRET_KEY
aws configure set region $REGION

    echo "create key pair $KEY_PEM to connect to instances and save locally"
aws ec2 create-key-pair --key-name $KEY_NAME \
    | jq -r ".KeyMaterial" > $KEY_PEM

# secure the key pair
chmod 400 $KEY_PEM

SEC_GRP="my-sg-`date +'%N'`"

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
    --arg v3 "$ACCESS_KEY" \
    --arg v4 "$SECRET_KEY" \
    '{key_name: $v1, sec_grp: $v2, access_key: $v3, secret_key: $v4}' > config.json

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
    scp -i $KEY_PEM -o "StrictHostKeyChecking=no" -o "ConnectionAttempts=60" endpoint_setp.sh ubuntu@$IP:/home/ubuntu/
    scp -i $KEY_PEM -o "StrictHostKeyChecking=no" -o "ConnectionAttempts=60" worker_setp.sh ubuntu@$IP:/home/ubuntu/

    echo "Copying config file to $IP..."
    scp -i $KEY_PEM -o "StrictHostKeyChecking=no" -o "ConnectionAttempts=60" config.json ubuntu@$IP:/home/ubuntu/

    echo "Copying private key file to $IP..."
    scp -i $KEY_PEM -o "StrictHostKeyChecking=no" -o "ConnectionAttempts=60" $KEY_PEM ubuntu@$IP:/home/ubuntu/

    echo "Copying code to production @ $IP"
    # scp -i $KEY_PEM -o "StrictHostKeyChecking=no" -o "ConnectionAttempts=60" server.py ubuntu@$IP:/home/ubuntu/
    scp -i $KEY_PEM -o "StrictHostKeyChecking=no" -o "ConnectionAttempts=60" endpoint_app.py ubuntu@$IP:/home/ubuntu/
    scp -i $KEY_PEM -o "StrictHostKeyChecking=no" -o "ConnectionAttempts=60" worker.py ubuntu@$IP:/home/ubuntu/

    echo "Config file copied to $IP."

    echo "setup production environment"
    ssh -i $KEY_PEM -o "StrictHostKeyChecking=no" -o "ConnectionAttempts=10" ubuntu@$IP <<EOF
    chmod u+x endpoint_setup.sh
    # run setup
    ./endpoint_setup.sh
    exit
EOF
done

#run app on node 1
 ssh -i $KEY_PEM -o "StrictHostKeyChecking=no" -o "ConnectionAttempts=10" ubuntu@$PUBLIC_IP_1 <<EOF
    # run app
    # nohup python3 server.py &>server.log &
    sudo nohup python3 endpoint_app.py --port 8000 --other $PUBLIC_IP_2:8000  &>server.log &
    exit
EOF

#run app on node 2
 ssh -i $KEY_PEM -o "StrictHostKeyChecking=no" -o "ConnectionAttempts=10" ubuntu@$PUBLIC_IP_2 <<EOF
    # run app
    # nohup python3 server.py &>server.log &
    sudo nohup python3 endpoint_app.py --port 8000 --other $PUBLIC_IP_1:8000  &>server.log &
    exit
EOF
    



echo "test that it all worked"
for ip in "${IP_LIST[@]}"; do
    echo "Test $ip"
    curl  --retry-connrefused --retry 10 --retry-delay 1  http://$ip:8000
done