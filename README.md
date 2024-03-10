# Entry task for FaasKeeper: Deploy and run unit tests

1. Deploying to AWS: To do this, I had to run the following commands after cloning the repo (used Linux):
```bash
# Install python deps
pip3 install requirements.txt
pip3 install git+https://github.com/spcl/faaskeeper-python

# Install node version manager to download an older version of node. Because the README mentions node <= 15.4.0 will work
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.1/install.sh | bash
source ~/.bashrc # or whatever is your shell. Eg: zshrc for macOS

# Used node v14.15.0 because it is LTS
nvm install 14.15.0
nvm use 14.15.0

# Install serverless framework
npm install -g serverless

# Install required plugins
serverless plugin install -n serverless-export-env --config /workspaces/faaskeeper/aws.yml
serverless plugin install -n serverless-python-requirements  --config /workspaces/faaskeeper/aws.yml
serverless plugin install -n serverless-iam-roles-per-function --config /workspaces/faaskeeper/aws.yml

# Deploy
./fk.py deploy service config/user_config_final.json --provider aws --config config/user_config.json
```
