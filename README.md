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
2. For running the unit tests, I analyzed how tests are executed in the github workflow build.yml
I exported the required environment variables and ran the test.
Here is the output of the test:
Start the test using:
```bash
pytest connect_session.py
```

Test logs (Shows test passed at the bottom):
```bash

============================= test session starts ==============================
platform linux -- Python 3.10.13, pytest-8.1.1, pluggy-1.4.0
rootdir: /workspaces/faaskeeper/tests
plugins: anyio-4.2.0
collected 2 items

connect_session.py ..                                                    [100%]

=============================== warnings summary ===============================
connect_session.py::test_connection[aws_connect]
connect_session.py::test_connection[aws_connect]
connect_session.py::test_connection[aws_connect]
connect_session.py::test_connection[aws_connect]
connect_session.py::test_connection[aws_connect]
connect_session.py::test_reconnection[aws_connect]
connect_session.py::test_reconnection[aws_connect]
connect_session.py::test_reconnection[aws_connect]
connect_session.py::test_reconnection[aws_connect]
  /usr/local/python/3.10.13/lib/python3.10/site-packages/botocore/httpsession.py:57: DeprecationWarning: ssl.PROTOCOL_TLS is deprecated
    context = SSLContext(ssl_version or ssl.PROTOCOL_SSLv23)

connect_session.py::test_connection[aws_connect]
connect_session.py::test_connection[aws_connect]
connect_session.py::test_reconnection[aws_connect]
connect_session.py::test_reconnection[aws_connect]
connect_session.py::test_reconnection[aws_connect]
  /usr/local/python/3.10.13/lib/python3.10/site-packages/urllib3/connection.py:407: DeprecationWarning: ssl.match_hostname() is deprecated
    match_hostname(cert, asserted_hostname)

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================= 2 passed, 14 warnings in 10.49s ========================
```
