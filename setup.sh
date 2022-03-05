#!bin/bash

python3 -m venv trader &&
source trader/bin/activate &&
pip install -r requirements.txt &&
deactivate 