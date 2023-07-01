#!/bin/bash

PUBLIC_IP_1=$(jq '.. | select(.ip1?) | .ip1' "instances.json" | tr -d '"')
PUBLIC_IP_2=$(jq '.. | select(.ip2?) | .ip2' "instances.json" | tr -d '"') 

KEY_NAME=$(jq '.. | select(.key_name?) | .key_name' "config.json")
KEY_PEM="$(echo $KEY_NAME | tr -d '"').pem"     

#run app on node1
echo "Run endpoint application on Node 1 @ $PUBLIC_IP_1"
ssh -i $KEY_PEM -o "StrictHostKeyChecking=no" -o "ConnectionAttempts=10" ubuntu@$PUBLIC_IP_1 <<EOF
    # run app
    # nohup python3 server.py &>server.log &
    sudo nohup python3 endpoint_app.py --port 8000 --other $PUBLIC_IP_2:8000  &>server.log &
    exit
EOF

#run app on node 2
echo "Run endpoint application on Node 2 @ $PUBLIC_IP_2"
ssh -i $KEY_PEM -o "StrictHostKeyChecking=no" -o "ConnectionAttempts=10" ubuntu@$PUBLIC_IP_2 <<EOF
    # run app
    # nohup python3 server.py &>server.log &
    sudo nohup python3 endpoint_app.py --port 8000 --other $PUBLIC_IP_1:8000  &>server.log &
    exit
EOF
