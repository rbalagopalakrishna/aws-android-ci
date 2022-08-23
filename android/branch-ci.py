import ast
import boto3
import botocore
import datetime
import json
import time

from botocore.exceptions import ClientError


codecommit_client = boto3.client('codecommit')
codepipeline_client = boto3.client('codepipeline')
codebuild_client = boto3.client('codebuild')
iam_client = boto3.client('iam')
events_client = boto3.client('events')

# Repository name
repository_name = 'Android'

# AWS account details
region = 'ap-south-1'
role = 'codepipeline-android-service-role'

# S3 bucket to store Source and Build Artifacts
s3_android_bucket_development = 'android-source'
s3_android_bucket_builds = 'android-builds'
s3_android_bucket_release = 'android-release'

# DeviceFarm Project and DevicePool arn to test the application
device_farm_project_id = ''
device_farm_device_pool_arn = ''

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
                            "provider": "CodeBuild",
                            "version": "1",
                            "owner": "AWS"
                        },
                        "name": "CodeBuild",
                        "outputArtifacts": [
                            {
                                "name": "BuildArtifact"
                            }
                        ],
                        "configuration": {
                            "BatchEnabled": "false",
                            "ProjectName": ""
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
                "name": "Test",
                "actions": [
                    {
                        "name": "TestDeviceFarm",
                        "actionTypeId": {
                            "category": "Test",
                            "owner": "AWS",
                            "provider": "DeviceFarm",
                            "version": "1"
                        },
                        "runOrder": 1,
                        "configuration": {
                            "App": "app-debug.apk",
                            "AppType": "Android",
                            "DevicePoolArn": device_farm_device_pool_arn,
                            "FuzzEventCount": "6000",
                            "FuzzEventThrottle": "50",
                            "ProjectId": device_farm_project_id,
                            "TestType": "BUILTIN_FUZZ"
                        },
                        "outputArtifacts": [],
                        "inputArtifacts": [
                            {
                                "name": "BuildArtifact"
                            }
                        ],
                        "region": region
                    }
                ]
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
                            "BucketName": s3_android_bucket_builds,
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
            "location": s3_android_bucket_development
        },
        "name": "",
        "version": 1,
        "roleArn": ""
    }
}

release_pipeline_configuration = {
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
                            "provider": "CodeBuild",
                            "version": "1",
                            "owner": "AWS"
                        },
                        "name": "CodeBuild",
                        "outputArtifacts": [
                            {
                                "name": "BuildArtifact"
                            }
                        ],
                        "configuration": {
                            "BatchEnabled": "false",
                            "ProjectName": ""
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
                            "BucketName": s3_android_bucket_release,
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
            {
                "name": "Publish",
                "actions": [
                    {
                        "name": "ApprovalStage",
                        "actionTypeId": {
                            "category": "Approval",
                            "owner": "AWS",
                            "provider": "Manual",
                            "version": "1"
                        },
                        "runOrder": 1,
                        "configuration": {
                        },
                        "outputArtifacts": [],
                        "inputArtifacts": [],
                        "region": region
                    },
                    {
                        "name": "Publish-AAB-To-Playstore",
                        "actionTypeId": {
                            "category": "Invoke",
                            "owner": "AWS",
                            "provider": "Lambda",
                            "version": "1"
                        },
                        "runOrder": 2,
                        "configuration": {
                            "FunctionName": "Publish-AAB-To-Playstore"
                        },
                        "outputArtifacts": [],
                        "inputArtifacts": [
                            {
                                "name": "BuildArtifact"
                            }
                        ],
                        "region": region
                    }
                ],
            },
        ],
        "artifactStore": {
            "type": "S3",
            "location": s3_android_bucket_development
        },
        "name": "",
        "version": 1,
        "roleArn": ""
    }
}


def create_iam_policy(branch_name):
    policy = json.dumps({
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "codepipeline:StartPipelineExecution"
                ],
                "Resource": [
                    "arn:aws:codepipeline:ap-south-1:<ACCCOUNT>:"+branch_name
                ]
            }
        ]
    })

    response = iam_client.create_policy(
        PolicyName='start-pipeline-execution-ap-south-1-'+branch_name,
        PolicyDocument=policy,
    )
    return response

def create_iam_role(branch_name):
    assume_role_policy_document = json.dumps({
        "Version": "2012-10-17",
        "Statement": [
            {
            "Effect": "Allow",
            "Principal": {
                "Service": "events.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
            }
        ]
    })

    response = iam_client.create_role(
        RoleName='cwe-role-ap-south-1-'+branch_name,
        AssumeRolePolicyDocument=assume_role_policy_document,
        Description='Allows Amazon CloudWatch Events to start Pipeline execution'
    )
    return response

def attach_iam_policy(role_name, policy_arn):
    response = iam_client.attach_role_policy(
        RoleName=role_name,
        PolicyArn=policy_arn
    )
    return response


def create_rule(branch_name):
    event_pattern = json.dumps({
        "source": [
            "aws.codecommit"
        ],
        "detail-type": [
            "CodeCommit Repository State Change"
        ],
        "resources": [
            "arn:aws:codecommit:ap-south-1:<AACCOUNT>:<REPOSITORY>"
        ],
        "detail": {
            "event": [
                "referenceCreated",
                "referenceUpdated"
            ],
        "referenceType": [
            "branch"
        ],
        "referenceName": [branch_name]
        }
    })

    response = events_client.put_rule(
        Name='codepipeline-'+branch_name+'-rule',
        EventPattern=event_pattern,
        State='ENABLED',
        Description='Amazon CloudWatch Events rule to automatically start your pipeline when a change occurs in CodeCommit Repository'
    )
    return response


def create_target(branch_name, role_arn):
    pipeline_name = branch_name
    response = events_client.put_targets(
        Rule='codepipeline-'+branch_name+'-rule',
        Targets=[
            {
                'Id': branch_name,
                'Arn': 'arn:aws:codepipeline:ap-south-1:<AACOUNT>:'+pipeline_name,
                'RoleArn': role_arn
            }
        ]
    )
    return response

def get_status(pipeline_name):
    try:
        pipeline_status = codepipeline_client.get_pipeline_state(name=pipeline_name)
        return pipeline_status
    except ClientError as e:
        if e.response['Error']['Code'] == 'PipelineNotFoundException':
            print("Pipeline %s does not exist." % pipeline_name)


def post_comment(pr_id, repository_name, source_commit,
                 destination_commit, content):
    codecommit_client.post_comment_for_pull_request(
            pullRequestId=pr_id,
            repositoryName=repository_name,
            beforeCommitId=source_commit,
            afterCommitId=destination_commit,
            content=content
        )


def delete_pipeline(pipeline_name):
    try:
        print("Cleaning up, deleting pipeline %s" % pipeline_name)
        codepipeline_client.delete_pipeline(name=pipeline_name)
    except ClientError as e:
        if e.response['Error']['Code'] == 'PipelineNotFoundException':
            print("Pipeline %s does not exist, nothing to do." % pipeline_name)
        else:
            print("Unexpected error: %s" % e)


def update_pipeline(message, code_pipeline_configuration, branch_ref, destination_branch=None):
    for stage in code_pipeline_configuration['pipeline']['stages']:
        if stage['name'] == 'Source':
            stage['actions'][0]['configuration']['BranchName'] = branch_ref
        elif stage['name'] == 'Build':
            try:
                if message['detail']['referenceType'] == 'tag':
                    stage['actions'][0]['configuration']['ProjectName'] = 'android-release-aab-build'
                    break
            except KeyError:
                pass
            try:
                merge_options = ('FAST_FORWARD_MERGE', 'SQUASH_MERGE')
                if message['detail']['mergeOption'] in merge_options and message['detail']['referenceName'] == 'master':
                    stage['actions'][0]['configuration']['ProjectName'] = 'android-master-apk-build'
                    break
            except KeyError:
                pass
            stage['actions'][0]['configuration']['ProjectName'] = 'android-develop-apk-build'
    return code_pipeline_configuration['pipeline']


def create_pipeline(modified_pipeline_json):
    try:
        new_pipeline_response = codepipeline_client.create_pipeline(pipeline=modified_pipeline_json)
        return new_pipeline_response
    except ClientError as e:
        if e.response['Error']['Code'] == 'PipelineNameInUseException':
            print("A Pipeline with name already exist. Skipping pipeline creation")


def get_pipeline_artifact(build_id):
    response = codebuild_client.batch_get_builds(ids=[build_id])
    pipeline_artifact = '/'.join(response['builds'][0]['artifacts']['location'].split('/')[1:])
    return pipeline_artifact


# Beanch Events Ex: referenceCreated, referenceDeleted, referenceUpdated 
def branch_events(message, event_ytpe):
    print(message)
    account_number = message['account']
    print("AWS Account number :: %s" % account_number)
    region = message['region']
    print("Region :: %s" % region)
    commit_id = message['detail']['commitId']
    print("Commit ID :: %s" % commit_id)
    branch_ref = message['detail']['referenceName']
    branch_name = '-'.join(message['detail']['referenceName'].split('/'))
    print("Branch Name :: %s" % branch_ref)
    
    # CodePipeline configurations for futurebranch/master
    code_pipeline_configuration = pipeline_configuration
    #pipeline_name = branch_name+'-'+commit_id+'-pipeline'
    #code_pipeline_configuration['pipeline']['name'] = pipeline_name
    code_pipeline_configuration['pipeline']['name'] = branch_name
    code_pipeline_configuration['pipeline']['roleArn'] = 'arn:aws:iam::'+account_number+':role/service-role/'+role
    code_pipeline_configuration['pipeline']['stages'][3]['actions'][0]['configuration']['ObjectKey'] = branch_name
    

    # CodePipeline configurations for tag creations
    if message['detail']['referenceType'] == 'tag':
        code_pipeline_configuration = release_pipeline_configuration
        code_pipeline_configuration['pipeline']['name'] = branch_name
        code_pipeline_configuration['pipeline']['roleArn'] = 'arn:aws:iam::'+account_number+':role/service-role/'+role
        code_pipeline_configuration['pipeline']['stages'][2]['actions'][0]['configuration']['ObjectKey'] = commit_id

        # Use master branch for tags
        branch_ref = 'master'

    modified_pipeline_json = update_pipeline(message, code_pipeline_configuration, branch_ref)

    #delete_pipeline(pipeline_name)
    time.sleep(5)
    
    try:
        create_role = create_iam_role(branch_name)
        role_name = create_role["Role"]["RoleName"]
        print(role_name)
        role_arn = create_role["Role"]["Arn"]
        print(role_arn)
    except ClientError as e:
        if e.response['Error']['Code'] == 'EntityAlreadyExists':
            print('Role already exists')
        else:
            print(e)
    
    try:
        create_policy = create_iam_policy(branch_name)
        policy_arn = create_policy['Policy']['Arn']
        print(policy_arn)
        attach_iam_policy(role_name, policy_arn)
    except ClientError as e:
        if e.response['Error']['Code'] == 'EntityAlreadyExists':
            print('Policy already exists')
        else:
            print(e)
    
    new_pipeline_response = create_pipeline(modified_pipeline_json)
    create_rule(branch_name)
    create_target(branch_name, role_arn)


# Pull Request Events Ex: pullRequestCreated, pullRequestSourceBranchUpdated
def pr_events(message, event_ytpe):
    print(message)
    account_number = message['account']
    print("AWS Account number :: %s" % account_number)
    region = message['region']
    print("Region :: %s" % region)

    pr_id = message['detail']['pullRequestId']
    print("Pull Request ID :: %s" % pr_id)
    source_commit = message['detail']['sourceCommit']
    print("Source Commit ID :: %s" % source_commit)
    destination_commit = message['detail']['destinationCommit']
    print("Destination Commit ID :: %s" % destination_commit)
    pipeline_name = str(repository_name+'-'+'PullRequest'+'-'+pr_id)
    print("Pipeline Name :: %s" % pipeline_name)
    destination_branch = message['detail']['destinationReference'].split('/')[-1]
    print("Destination Branch Reference :: %s" % destination_branch)

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
            code_pipeline_configuration['pipeline']['stages'][3]['actions'][0]['configuration']['ObjectKey'] = source_commit
            
            modified_pipeline_json = update_pipeline(message, code_pipeline_configuration, branch_ref, destination_branch)
            
            # Delete existing pipeline before creating new one
            delete_pipeline(pipeline_name)
            time.sleep(5)
            new_pipeline_response = create_pipeline(modified_pipeline_json)

            pipeline_url = 'https://'+region+'.console.aws.amazon.com/codesuite/codepipeline/pipelines/'+pipeline_name+'/view?region='+region
            content = u'\u23F3'+' Pipeline started at {}'.format(datetime.datetime.utcnow().time())+' '+'- See the [Pipeline]({0})'.format(pipeline_url)
            post_comment(pr_id, repository_name, source_commit, destination_commit, content)

            time.sleep(10)

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
                    build_url = stage['actionStates'][0]['latestExecution']['externalExecutionUrl']
                    count = 0
                    while count < 2000:
                        pipeline_build_status = get_status(pipeline_name)
                        build_execution_status = pipeline_build_status['stageStates'][1]['latestExecution']['status']
                        print('Build status :: ', build_execution_status)
                        if build_execution_status == 'Succeeded':
                            print('Stage Build Passed.')
                            content = u'\u2705'+' Stage Build Passed - See the [Logs]({0})'.format(build_url)
                            post_comment(pr_id, repository_name,
                                         source_commit, destination_commit,
                                         content)
                            break

                        elif build_execution_status == 'Failed':
                            content = u'\u274C'+' Build Failed - See the [Logs]({0})'.format(build_url)
                            post_comment(pr_id, repository_name,
                                         source_commit, destination_commit,
                                         content)
                            break

                        else:
                            count += 1
                            time.sleep(2)

                elif stage['stageName'] == 'Test':
                    count = 0
                    while count < 500:
                        pipeline_test_status = get_status(pipeline_name)
                        test_execution_status = pipeline_test_status['stageStates'][2]['latestExecution']['status']
                        if test_execution_status == 'Succeeded':
                            summary = pipeline_test_status['stageStates'][2]['actionStates'][0]['latestExecution']['summary']
                            print('Stage '+summary)
                            devicefarm_url = pipeline_test_status['stageStates'][2]['actionStates'][0]['latestExecution']['externalExecutionUrl']
                            print(devicefarm_url)
                            content = u'\u2705'+' '+summary+' - See the logs [DeviceFarm]({0})'.format(devicefarm_url)
                            post_comment(pr_id, repository_name,
                                         source_commit, destination_commit,
                                         content)
                            break
                        elif test_execution_status == 'Failed':
                            print('Stage Deploy failed')
                            break
                        else:
                            count += 1
                            time.sleep(2)
                            
                elif stage['stageName'] == 'Deploy':
                    count = 0
                    while count < 500:
                        pipeline_deploy_status = get_status(pipeline_name)
                        deploy_execution_status = pipeline_deploy_status['stageStates'][3]['latestExecution']['status']
                        if deploy_execution_status == 'Succeeded':
                            print('Stage '+pipeline_deploy_status['stageStates'][3]['actionStates'][0]['latestExecution']['summary'])
                            build_path = pipeline_deploy_status['stageStates'][3]['actionStates'][0]['latestExecution']['externalExecutionId']
                            print(build_path)
                            apk_s3_location = 'https://'+region+'.console.aws.amazon.com/s3/buckets/dt-android-builds?region='+region+'&prefix='+source_commit+'/&showversions=false'
                            print('Download APK file from :: {}'.format(apk_s3_location))
                            content = u'\u2705'+' Stage Deploy Passed - See the [Artifactory]({0})'.format(apk_s3_location)
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

    if event_type == 'referenceCreated':
        branch_events(message, event_type)
    elif event_type == 'pullRequestCreated':
        pr_events(message, event_type)
