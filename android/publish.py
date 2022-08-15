import boto3
import json
import os
import subprocess
import zipfile

from google.oauth2 import service_account
import googleapiclient.discovery
from urllib import request, parse


s3_client = boto3.client('s3')

#   Defining the scope of the authorization request
SCOPES = ['https://www.googleapis.com/auth/androidpublisher']

#   Package name for app
package_name = 'com.app.name'

#   This is the main handler function
def lambda_handler(event, context):
    #   Create a new client S3 client and download the correct file from the bucket
    s3_client.download_file('service-account-key', 'service-account-key.json', '/tmp/service-account-key.json')
    SERVICE_ACCOUNT_FILE = '/tmp/service-account-key.json'

    #   Download the app-release.aab file that triggered the Lambda
    bucket_name = event['CodePipeline.job']['data']['inputArtifacts'][0]['location']['s3Location']['bucketName']
    file_key = event['CodePipeline.job']['data']['inputArtifacts'][0]['location']['s3Location']['objectKey']
    output_path = file_key.split('/')[-1]

    path = os.path.join('/tmp/', output_path)
    os.mkdir(path)

    s3_client.download_file(bucket_name, file_key, '/tmp/'+output_path+'/'+output_path)

    # Extrract build artifact
    with zipfile.ZipFile('/tmp/'+output_path+'/'+output_path, 'r') as zip_ref:
        zip_ref.extractall('/tmp/'+output_path)

    subprocess.run(["ls", "-l", "/tmp/"])

    APP_BUNDLE = '/tmp/'+output_path+'/app-release.aab'
    print(APP_BUNDLE)

    print(f"A bundle uploaded to {bucket_name} has triggered the Lambda")

    #   Create a credentials object and create a service object using the credentials object
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    service = googleapiclient.discovery.build('androidpublisher', 'v3', credentials=credentials, cache_discovery=False)

    #   Create an edit request using the service object and get the editId
    edit_request = service.edits().insert(body={}, packageName=package_name)
    result = edit_request.execute()
    edit_id = result['id']

    #   Create a request to upload the app bundle
    try:
        bundle_response = service.edits().bundles().upload(
            editId=edit_id,
            packageName=package_name,
            media_body=APP_BUNDLE,
            media_mime_type="application/octet-stream"
        ).execute()
    except Exception as err:
        message = f"There was an error while uploading a new version of {package_name}"
        raise err

    print(f"Version code {bundle_response['versionCode']} has been uploaded")

    #   Create a track request to upload the bundle to the alpha track
    TRACK = 'alpha'  # Can be 'alpha', beta', 'production' or 'rollout'
    track_response = service.edits().tracks().update(
        editId=edit_id,
        track=TRACK,
        packageName=package_name,
        body={u'releases': [{
            u'versionCodes': [str(bundle_response['versionCode'])],
            u'status': u'completed',
        }]}
    ).execute()

    print("The bundle has been committed to the "+TRACK+" track")

    #   Create a commit request to commit the edit to track
    commit_request = service.edits().commit(
        editId=edit_id,
        packageName=package_name
    ).execute()

    print(f"Edit {commit_request['id']} has been committed")

    message = f"Version code {bundle_response['versionCode']} has been uploaded from the bucket {bucket_name}.\nEdit {commit_request['id']} has been committed"

    return {
        'statusCode': 200,
        'body': json.dumps('Successfully executed the app bundle release to '+TRACK)
    }
