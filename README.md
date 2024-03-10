# Entry task for FaasKeeper: Deploy and run unit tests

1. Deploying to AWS: To do this, I had to run the following commands after cloning the repo (used Linux):
```bash
pip3 install requirements.txt
pip3 install git+https://github.com/spcl/faaskeeper-python
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.1/install.sh | bash
source ~/.bashrc # or whatever is your shell. Eg: zshrc for macOS
nvm install 14.15.0
nvm use 14.15.0
npm install -g serverless
serverless plugin install -n serverless-export-env --config /workspaces/faaskeeper/aws.yml
serverless plugin install -n serverless-python-requirements  --config /workspaces/faaskeeper/aws.yml
serverless plugin install -n serverless-iam-roles-per-function --config /workspaces/faaskeeper/aws.yml
./fk.py deploy service config/user_config_final.json --provider aws --config config/user_config.json
./fk.py deploy functions --provider aws --config config/user_config.json
```
