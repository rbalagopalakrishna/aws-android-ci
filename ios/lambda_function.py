import ast
import boto3
import botocore
import datetime
import time

from botocore.exceptions import ClientError


codecommit_client = boto3.client('codecommit')
codepipeline_client = boto3.client('codepipeline')

# Repository name from codecommit
repository_name = 'Dev-Dt-iOS'

# AWS account details
role = 'codepipeline-ios-service-role'
region = 'ap-south-1'

# S3 bucket to store Source and Build Artifacts
s3_ios_bucket_development = 'dt-ios-source'
s3_ios_bucket_release = 'dt-ios-release'
s3_ios_bucket_builds = 'dt-ios-builds'

# DeviceFarm Project and DevicePool arn to test the application
device_farm_project_id = '24810d78-548f-4e16-83c7-5c184af92bec'
device_farm_device_pool_arn = 'arn:aws:devicefarm:us-west-2::devicepool:082d10e5-d7d7-48a5-ba5c-b33d66efa1f5'

pipeline_configuration = {
    "pipeline": {
        "stages": [
            {
                "actions": [
                    {
                        "runOrder": 1,
                        "actionTypeId": {
                            "category": "Source",
                            "provider": "CodeCommit",
                            "version": "1",
                            "owner": "AWS"
                        },
                        "name": "Source",
                        "outputArtifacts": [
                            {
                                "name": "SourceArtifact"
                            }
                        ],
                        "configuration": {
                            "BranchName": "",
                            "OutputArtifactFormat": "CODE_ZIP",
                            "PollForSourceChanges": "false",
                            "RepositoryName": repository_name
                        },
                        "inputArtifacts": []
                    }
                ],
                "name": "Source"
            },
            {
                "actions": [
                    {
                        "runOrder": 1,
                        "actionTypeId": {
                            "category": "Build",
                            "provider": "Jenkins",
                            "version": "1",
                            "owner": "Custom"
                        },
                        "name": "Build",
                        "outputArtifacts": [
                            {
                                "name": "BuildArtifact"
                            }
                        ],
                        "configuration": {
                            "ProjectName": "",
                        },
                        "inputArtifacts": [
                            {
                                "name": "SourceArtifact"
                            }
                        ]
                    }
                ],
                "name": "Build"
            },
            {
                "actions": [
                    {
                        "runOrder": 1,
                        "actionTypeId": {
                            "category": "Deploy",
                            "provider": "S3",
                            "version": "1",
                            "owner": "AWS"
                        },
                        "name": "Deploy",
                        "configuration": {
                            "BucketName": s3_ios_bucket_builds,
                            "ObjectKey": "",
                            "Extract": "true"
                            },
                        "outputArtifacts": [],
                        "region": region,
                        "inputArtifacts": [
                            {
                                "name": "BuildArtifact"
                            }
                        ]
                    }
                ],
                "name": "Deploy"
            },
        ],
        "artifactStore": {
            "type": "S3",
            "location": s3_ios_bucket_development
        },
        "name": "",
        "version": 1,
        "roleArn": ""
    }
}

#            {
#                "name": "Test",
#                "actions": [
#                    {
#                        "name": "TestDeviceFarm",
#                        "actionTypeId": {
#                            "category": "Test",
#                            "owner": "AWS",
#                            "provider": "DeviceFarm",
#                            "version": "1"
#                        },
#                        "runOrder": 1,
#                        "configuration": {
#                            "App": "InstaTam.ipa",
#                            "AppType": "iOS",
#                            "DevicePoolArn": device_farm_device_pool_arn,
#                            "FuzzEventCount": "6000",
#                            "FuzzEventThrottle": "50",
#                            "ProjectId": device_farm_project_id,
#                            "TestType": "BUILTIN_FUZZ"
#                        },
#                        "outputArtifacts": [],
#                        "inputArtifacts": [
#                            {
#                                "name": "BuildArtifact"
#                            }
#                        ],
#                        "region": region
#                    }
#                ]
#            },

def update_pipeline(message, code_pipeline_configuration, branch_ref, destination_branch=None):
    for stage in code_pipeline_configuration['pipeline']['stages']:
        if stage['name'] == 'Source':
            stage['actions'][0]['configuration']['BranchName'] = branch_ref
        elif stage['name'] == 'Build':
            try:
                if message['detail']['referenceType'] == 'tag':
                    stage['actions'][0]['configuration']['ProjectName'] = 'ios-release-ipa-build'
                    break
            except KeyError:
                pass
            try:
                #if message['detail']['isMerged'] == 'True' and message['detail']['pullRequestStatus'] == 'Merged':
                if message['detail']['mergeOption'] == 'FAST_FORWARD_MERGE' and message['detail']['referenceName'] == 'master':
                    stage['actions'][0]['configuration']['ProjectName'] = 'ios-master-ipa-build'
                    break
            except KeyError:
                pass
            stage['actions'][0]['configuration']['ProjectName'] = 'ios-develop-ipa-build'
    return code_pipeline_configuration['pipeline']


def get_status(pipeline_name):
    try:
        pipeline_status = codepipeline_client.get_pipeline_state(name=pipeline_name)
        return pipeline_status
    except ClientError as e:
        if e.response['Error']['Code'] == 'PipelineNotFoundException':
            print("Pipeline %s does not exist." % pipeline_name)


def delete_pipeline(pipeline_name):
    try:
        print("Cleaning up, deleting pipeline %s" % pipeline_name)
        codepipeline_client.delete_pipeline(name=pipeline_name)
    except ClientError as e:
        if e.response['Error']['Code'] == 'PipelineNotFoundException':
            print("Pipeline %s does not exist, nothing to do." % pipeline_name)


def create_pipeline(modified_pipeline_json):
    try:
        new_pipeline_response = codepipeline_client.create_pipeline(pipeline=modified_pipeline_json)
        return new_pipeline_response
    except ClientError as e:
        if e.response['Error']['Code'] == 'PipelineNameInUseException':
            print("A Pipeline with name  %s already exist, please delete the pipeline to create one." % pipeline_name)


def get_jenkins_build_number(pipeline_name):
    count = 0
    while count < 100:
        try:
            build_status = get_status(pipeline_name)
            build_url = build_status['stageStates'][1]['actionStates'][0]['latestExecution']['externalExecutionUrl']
            break
        except KeyError:
            print("Waiting for build status..!")
        count += 1
        time.sleep(2)
    return build_url


def post_comment(pr_id, repository_name, source_commit,
                 destination_commit, content):
    codecommit_client.post_comment_for_pull_request(
            pullRequestId=pr_id,
            repositoryName=repository_name,
            beforeCommitId=source_commit,
            afterCommitId=destination_commit,
            content=content
        )


# Beanch Events Ex: referenceCreated, referenceDeleted, referenceUpdated 
def branch_events(message, event_ytpe):
    print(message)
    account_number = message['account']
    print("AWS Account number :: %s" % account_number)
    commit_id = message['detail']['commitId']
    print("Commit ID :: %s" % commit_id)
    branch_ref = message['detail']['referenceName']
    print("Branch Name :: %s" % branch_ref)
    
    branch_name = '-'.join(message['detail']['referenceName'].split('/'))
    code_pipeline_configuration = pipeline_configuration
    pipeline_name = branch_name + '-' + commit_id + '-pipeline'
    code_pipeline_configuration['pipeline']['roleArn'] = 'arn:aws:iam::'+account_number+':role/service-role/'+role
    code_pipeline_configuration['pipeline']['stages'][2]['actions'][0]['configuration']['ObjectKey'] = commit_id
    
    code_pipeline_configuration['pipeline']['name'] = pipeline_name
    
    if message['detail']['referenceType'] == 'tag':
        code_pipeline_configuration['pipeline']['stages'][2]['actions'][0]['configuration']['BucketName'] = s3_ios_bucket_release
        # Use master branch for tags
        branch_ref = 'master'
        global s3_ios_bucket_builds
        s3_ios_bucket_builds = s3_ios_bucket_release

    modified_pipeline_json = update_pipeline(message, code_pipeline_configuration, branch_ref)
    
    # Delete existing pipeline before creating new one
    delete_pipeline(pipeline_name)
    time.sleep(5)
    new_pipeline_response = create_pipeline(modified_pipeline_json)


# Pull Request Events Ex: pullRequestCreated, pullRequestSourceBranchUpdated
def pr_events(message, event_ytpe):
    print(message)
    account_number = message['account']
    print("AWS Account number :: %s" % account_number)
    pr_id = message['detail']['pullRequestId']
    print("Pull Request ID :: %s" % pr_id)
    source_commit = message['detail']['sourceCommit']
    print("Source Commit ID :: %s" % source_commit)
    destination_commit = message['detail']['destinationCommit']
    print("Destination Commit ID :: %s" % destination_commit)
    pipeline_name = str(repository_name+'-'+'PullRequest'+'-'+pr_id+'-'+source_commit)
    print("Pipeline Name :: %s" % pipeline_name)
    destination_branch = message['detail']['destinationReference'].split('/')[-1]
    print("Destination Branch Reference :: %s" % destination_branch)

    # Delete existing pipeline before creating new one
    delete_pipeline(pipeline_name)

    try:
        pipeline_response = codepipeline_client.get_pipeline(name=pipeline_name)
    except ClientError as e:
        if e.response['Error']['Code'] == 'PipelineNotFoundException':
            print("Pipeline %s does not exist, creating a new one." % pipeline_name)
            branch_ref = '/'.join(message['detail']['sourceReference'].split('/')[2:])
            print("Branch Name :: %s" % branch_ref)

            code_pipeline_configuration = pipeline_configuration
            code_pipeline_configuration['pipeline']['name'] = pipeline_name
            code_pipeline_configuration['pipeline']['roleArn'] = 'arn:aws:iam::'+account_number+':role/service-role/'+role
            code_pipeline_configuration['pipeline']['stages'][2]['actions'][0]['configuration']['ObjectKey'] = source_commit

            modified_pipeline_json = update_pipeline(message, code_pipeline_configuration, branch_ref, destination_branch)

            new_pipeline_response = create_pipeline(modified_pipeline_json)

            pipeline_url = 'https://'+region+'.console.aws.amazon.com/codesuite/codepipeline/pipelines/'+pipeline_name+'/view?region='+region
            content = u'\u23F3'+' Pipeline started at {}'.format(datetime.datetime.utcnow().time())+' '+'- See the [Pipeline]({0})'.format(pipeline_url)
            post_comment(pr_id, repository_name, source_commit, destination_commit, content)

            time.sleep(5)

            pipeline_name = new_pipeline_response['pipeline']['name']
            pipeline_stages = get_status(pipeline_name)

            for stage in pipeline_stages['stageStates']:

                if stage['stageName'] == 'Source':
                    count = 0
                    while count < 500:
                        pipeline_source_status = get_status(pipeline_name)
                        source_execution_status = pipeline_source_status['stageStates'][0]['latestExecution']['status']
                        print('Source status :: ', source_execution_status)
                        if source_execution_status == 'Succeeded':
                            print('Stage Source Passed.')
                            break
                        elif source_execution_status == 'Failed':
                            print('Stage Source Failed.')
                            break
                        else:
                            count += 1
                            time.sleep(2)

                elif stage['stageName'] == 'Build':
                    count = 0
                    while count < 500:
                        pipeline_build_status = get_status(pipeline_name)
                        build_execution_status = pipeline_build_status['stageStates'][1]['latestExecution']['status']
                        print('Build status :: ', build_execution_status)
                        if build_execution_status == 'Succeeded':
                            print('Stage Build Passed.')
                            jenkins_build_id = get_jenkins_build_number(pipeline_name)
                            content = u'\u2705'+' Stage Build Passed - See the [Logs]({0})'.format(jenkins_build_id)
                            post_comment(pr_id, repository_name,
                                         source_commit, destination_commit,
                                         content)
                            break

                        elif build_execution_status == 'Failed':
                            jenkins_build_id = get_jenkins_build_number(pipeline_name)
                            content = u'\u274C'+' Build Failed - See the [Logs]({0})'.format(jenkins_build_id)
                            post_comment(pr_id, repository_name,
                                         source_commit, destination_commit,
                                         content)
                            break

                        else:
                            count += 1
                            time.sleep(10)

                elif stage['stageName'] == 'Deploy':
                    count = 0
                    while count < 500:
                        pipeline_deploy_status = get_status(pipeline_name)
                        try:
                            deploy_execution_status = pipeline_deploy_status['stageStates'][2]['latestExecution']['status']
                            print('Deploy status :: ', deploy_execution_status)
                        except KeyError:
                            pass
                        if deploy_execution_status == 'Succeeded':
                            print('Stage '+pipeline_deploy_status['stageStates'][2]['actionStates'][0]['latestExecution']['summary'])
                            build_path = pipeline_deploy_status['stageStates'][2]['actionStates'][0]['latestExecution']['externalExecutionId']
                            print(build_path)
                            ipa_s3_location = 'https://'+region+'.console.aws.amazon.com/s3/buckets/dt-ios-builds?region='+region+'&prefix='+source_commit+'/&showversions=false'
                            print('Download IPA file from :: {}'.format(ipa_s3_location))
                            content = u'\u2705'+' Stage Deploy Passed - See the [Artifactory]({0})'.format(ipa_s3_location)
                            post_comment(pr_id, repository_name,
                                         source_commit, destination_commit,
                                         content)
                            break
                        elif deploy_execution_status == 'Failed':
                            print('Stage Deploy failed')
                            break
                        else:
                            count += 1
                            time.sleep(2)


def lambda_handler(event, context):

    message = ast.literal_eval(event['Records'][0]['Sns']['Message'])
    event_type = message['detail']['event']

    # Regardless of branch type, the CI Stage will always be created.
    if event_type == 'referenceCreated' or event_type == 'referenceUpdated':
        branch_events(message, event_type)
    elif event_type == 'pullRequestCreated' or event_type == 'pullRequestSourceBranchUpdated':
        pr_events(message, event_type)
