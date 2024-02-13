# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Usage:
# python3 src/export/main.py --job-config-file <file_name>
#
# Example:
# python3 src/export/main.py --job-config-file 6_backup_models_assets.json

import os
from datetime import datetime
import time
import argparse
import json
import yaml
import boto3

dir_path = os.path.abspath(os.path.dirname(__file__))
dir_name = os.path.basename(dir_path)
src_root_dir_path = os.path.abspath(os.path.dirname(dir_path))
project_root_dir_path = os.path.abspath(os.path.dirname(src_root_dir_path))
config_dir_path = f'{project_root_dir_path}/config'

twinmaker = boto3.client('iottwinmaker')

# Load configuration
with open(f'{config_dir_path}/project_config.yml', 'r') as file:
    project_config = yaml.safe_load(file)

S3_BUCKET_NAME = project_config['s3_bucket_name']
job_id = f'{project_config["job_name_prefix"]}{int(datetime.now().timestamp())}'

def list_metadata_jobs(source_type: str, destination_type: str):
    print(twinmaker.list_metadata_transfer_jobs(sourceType = source_type, destinationType = destination_type))

def create_metadata_job(job_id, job_config, s3_bucket) -> None:
    job_config["destination"]["s3Configuration"]["location"] = f'arn:aws:s3:::{s3_bucket}'
    twinmaker.create_metadata_transfer_job(
        metadataTransferJobId = job_id,
        sources = job_config["sources"] ,
        destination = job_config["destination"] 
    )

def print_job_status(job_id):
    print(f'\nChecking status of {job_id} job every 15 seconds..')
    while True:
        res = twinmaker.get_metadata_transfer_job(metadataTransferJobId=job_id)
        state = res["status"]["state"]
        if state in ('RUNNING', 'COMPLETED'):
            try:
                progress = res["progress"]
                print(f'Status: {state} | Total: {progress["totalCount"]}, Suceeded: {progress["succeededCount"]}, Skipped: {progress["skippedCount"]}, Failed: {progress["failedCount"]}')                
            except:
                print(f'Status: {state}')
        elif state == 'ERROR':
            print(f'Status: {state} | Report URL: {res["reportUrl"]}')
            break
        else:
            print(f'Status: {state}')
        time.sleep(15) # Check status every 15 seconds
        if state == 'COMPLETED': break
  
if __name__ == "__main__":
    # Get confirmation from user before proceeding with the operation
    user_input = input('The operation may export a large set of SiteWise resources to S3, depending on the filter criteria.\nDo you want to perform the export operation? (yes/no): ')
    if user_input.lower() == 'no':
        exit(0)
    elif not user_input.lower() == 'yes':
        print('please type either yes or no')
        exit(0)
    # Create the argument parser
    parser = argparse.ArgumentParser()
    # Add the arguments
    parser.add_argument("--job-config-file", help="Name of job config file")
    # Parse the arguments
    args = parser.parse_args()
    # Access the arguments
    job_config_file_name = args.job_config_file
    # Validate if a JSON file is provided
    if os.path.splitext(job_config_file_name)[1].lower() == '.json':
        print("User input successfully validated")
    else:
        print("User input validation failed! The metadata config file extension should be json")
        exit(0)
    job_config_file_path = f'{dir_path}/{job_config_file_name}'

    with open(job_config_file_path, 'r') as f:
        job_config = json.load(f)

    create_metadata_job(job_id, job_config, S3_BUCKET_NAME)
    print_job_status(job_id)