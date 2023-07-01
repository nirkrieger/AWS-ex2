# AWS-ex2
## Instructions
1. Connect to an EC2 instance.
2. git clone https://github.com/nirkrieger/AWS-ex2.git
3. chmod u+x ./setup.sh & chmod u+x ./run.sh
2. deploy code with ./setup.sh
3. ./run.sh

## File Content
- **setup.sh** -  used for code deployment.  access keys are need to be set manually (aws configure is part of the script.)
- **endpoint_setup.sh** - bash script that sets up the node instances.
- **endpoint_app.py** - the python code running the flask server and the actual logic.
- **worker_setp.sh** - bash script that sets up the worker instances.
- **worker.py** - worker application.

## Failure Modes
1. This code assumes that endpoint ips do not change. It will break if they do.
2. This code assumes that nodes are accessible, it is not resilient to network faults.
3. It also assumes no memory loss, as jobs are stored in a list.