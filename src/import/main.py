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
# python3 src/import/main.py --bulk-definitions-file <file_name>
#
# Example:
# python3 src/import/main.py --bulk-definitions-file 1_onboard_models_assets.json

import os
from datetime import datetime
import time
import yaml
import argparse
import boto3

import_root_dir_path = os.path.abspath(os.path.dirname(__file__))
src_root_dir_path = os.path.abspath(os.path.dirname(import_root_dir_path))
project_root_dir_path = os.path.abspath(os.path.dirname(src_root_dir_path))
config_dir_path = f'{project_root_dir_path}/config'

twinmaker = boto3.client('iottwinmaker')
s3 = boto3.client('s3')

# Load configuration
with open(f'{config_dir_path}/project_config.yml', 'r') as file:
    project_config = yaml.safe_load(file)
S3_BUCKET_NAME = project_config['s3_bucket_name']

job_id = f'{project_config["job_name_prefix"]}{int(datetime.now().timestamp())}'

# Upload a local file to S3
def upload_file_to_s3(local_file_path: str, bucket: str, s3_key: str) -> None:
    """Upload a local file to S3 bucket
    """
    s3.upload_file(local_file_path, bucket, s3_key)

# Create a bulk import/export job
def create_metadata_job(job_id: str, source_type: str, destination_type: str, s3_bucket: str, s3_key: str) -> None:
    twinmaker.create_metadata_transfer_job(
        metadataTransferJobId = job_id,
        sources = [{
            'type': source_type,
            's3Configuration': {
                'location': f'arn:aws:s3:::{s3_bucket}/{s3_key}'
            }
        }],
        destination = {
            'type': destination_type
        }    
    )

# Print status of a given job id
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
    user_input = input('The operation may create a large set of resources in SiteWise.\nDo you want to perform the import operation? (yes/no): ')
    if user_input.lower() == 'no':
        exit(0)
    elif not user_input.lower() == 'yes':
        print('please type either yes or no')
        exit(0)
    # Create the argument parser
    parser = argparse.ArgumentParser()
    # Add the arguments
    parser.add_argument("--bulk-definitions-file", help="Name of metadata config file")
    # Parse the arguments
    args = parser.parse_args()
    # Access the arguments
    bulk_definitions_file_name = args.bulk_definitions_file
    # Validate if a JSON file is provided
    if os.path.splitext(bulk_definitions_file_name)[1].lower() == '.json':
        print("User input successfully validated")
    else:
        print("User input validation failed! The metadata config file extension should be json")
        exit(0)

    bulk_definitions_file_path = f'{import_root_dir_path}/{bulk_definitions_file_name}'
    bulk_definitions_file_S3_key = f'bulk-operations/import/{bulk_definitions_file_name}'

    upload_file_to_s3(bulk_definitions_file_path, S3_BUCKET_NAME, bulk_definitions_file_S3_key)
    create_metadata_job(job_id, 's3', 'iotsitewise', S3_BUCKET_NAME, bulk_definitions_file_S3_key)
    
    print_job_status(job_id)