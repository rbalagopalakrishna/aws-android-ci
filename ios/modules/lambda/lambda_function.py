import ast
import boto3
import botocore
import datetime
import time

from botocore.exceptions import ClientError


codecommit_client = boto3.client('codecommit')
codepipeline_client = boto3.client('codepipeline')

# Repository name from codecommit
repository_name = 'iOS'

# AWS account details
account_number = ''
role = 'codepipeline-ios-service-role'
region = 'ap-south-1'

# S3 bucket to store Source and Build Artifacts
s3_ios_bucket_development = 'ios-source'
s3_ios_bucket_release = 'ios-release'

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
                            "App": "InstaTam.ipa",
                            "AppType": "iOS",
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
        ],
        "artifactStore": {
            "type": "S3",
            "location": s3_ios_bucket_development
        },
        "name": "ci-pipeline",
        "version": 1,
        "roleArn": 'arn:aws:iam::'+account_number+':role/service-role/'+role
    }
}

def update_pipeline(code_pipeline_configuration, branch_ref, destination_branch=None):
    for stage in code_pipeline_configuration['pipeline']['stages']:
        if stage['name'] == 'Source':
            stage['actions'][0]['configuration']['BranchName'] = branch_ref
        elif stage['name'] == 'Build':
            if destination_branch == 'master':
                stage['actions'][0]['configuration']['ProjectName'] = 'ios-master-ipa-build'
            else:
                stage['actions'][0]['configuration']['ProjectName'] = 'ios-develop-ipa-build'

    return code_pipeline_configuration['pipeline']


def get_status(pipeline_name):
    pipeline_status = codepipeline_client.get_pipeline_state(name=pipeline_name)
    return pipeline_status


def create_pipeline(modified_pipeline_json):
    new_pipeline_response = codepipeline_client.create_pipeline(pipeline=modified_pipeline_json)
    return new_pipeline_response


def get_jenkins_build_number(pipeline_name):
    count = 0
    while count < 100:
        try:
            build_status = get_status(pipeline_name)
            build_url = build_status['stageStates'][1]['actionStates'][0]['latestExecution']['externalExecutionUrl']
            print(build_url)
            break
        except KeyError:
            print('Waiting for build status.')
        count += 1
        time.sleep(2)
    return build_url


# Beanch Events Ex: referenceCreated, referenceDeleted, referenceUpdated 
def branch_events(message, event_ytpe):
    print(message)
    #reference_type = message['detail']['referenceType'] == 'branch' or 'tag'
    commit_id = message['detail']['commitId']
    print("Commit ID :: %s" % commit_id)
    #branch_ref = '/'.join(message['detail']['referenceFullName'].split('/')[2:])
    branch_ref = message['detail']['referenceName']

    branch_name = '-'.join(message['detail']['referenceName'].split('/'))
    print("Branch Name :: %s" % branch_ref)

    code_pipeline_configuration = pipeline_configuration
    pipeline_name = branch_name + '-' + commit_id + '-pipeline'
    
    code_pipeline_configuration['pipeline']['name'] = pipeline_name

    modified_pipeline_json = update_pipeline(code_pipeline_configuration, branch_ref)
    print(modified_pipeline_json)
    new_pipeline_response = create_pipeline(modified_pipeline_json)

    time.sleep(10)

    pipeline_name = new_pipeline_response['pipeline']['name']
    pipeline_stages = get_status(pipeline_name)

    for stage in pipeline_stages['stageStates']:

        if stage['stageName'] == 'Source':
            source_execution_status = stage['actionStates'][0]['latestExecution']['status']

            if source_execution_status == 'Succeeded':
                print('Stage Source Succeeded.')
            else:
                print('Stage Source Failed.')
                break

        elif stage['stageName'] == 'Build':
            count = 0
            while count < 2000:
                pipeline_build_status = get_status(pipeline_name)
                build_execution_status = pipeline_build_status['stageStates'][1]['latestExecution']['status']
                #print('Build status :: ', build_execution_status)

                if build_execution_status == 'Succeeded':
                    print('Stage Jenkins Build Succeeded.')
                    jenkins_build_id = get_jenkins_build_number(pipeline_name)
                    print(jenkins_build_id)
                    #delete_pipeline(pipeline_name)
                    break

                elif build_execution_status == 'Failed':
                    print('Stage jenkins Build failed')
                    jenkins_build_id = get_jenkins_build_number(pipeline_name)
                    print(jenkins_build_id)
                    #delete_pipeline(pipeline_name)
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
                    print('Stage '+pipeline_test_status['stageStates'][2]['actionStates'][0]['latestExecution']['summary'])
                    devicefarm_url = pipeline_test_status['stageStates'][2]['actionStates'][0]['latestExecution']['externalExecutionUrl']
                    print(devicefarm_url)
                    break
                elif test_execution_status == 'Failed':
                    print('Stage Deploy failed')
                    break
                else:
                    count += 1
                    time.sleep(2)


# Pull Request Events Ex: pullRequestCreated, pullRequestSourceBranchUpdated
def pr_events(message, event_ytpe):
    print(message)
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

    try:
        pipeline_response = codepipeline_client.get_pipeline(name=pipeline_name)
    except ClientError as e:
        if e.response['Error']['Code'] == 'PipelineNotFoundException':
            print("Pipeline %s does not exist, creating a new one." % pipeline_name)
            branch_ref = '/'.join(message['detail']['sourceReference'].split('/')[2:])
            print("Branch Name :: %s" % branch_ref)

            code_pipeline_configuration = pipeline_configuration
            code_pipeline_configuration['pipeline']['name'] = pipeline_name
            #code_pipeline_configuration['pipeline']['stages'][2]['actions'][0]['configuration']['ObjectKey'] = source_commit
            #code_pipeline_configuration['pipeline']['stages'][3]['actions'][0]['configuration']['App'] = source_commit+'/app-debug.apk'

            modified_pipeline_json = update_pipeline(code_pipeline_configuration, branch_ref, destination_branch)
            new_pipeline_response = create_pipeline(modified_pipeline_json)

            pipeline_url = 'https://'+region+'.console.aws.amazon.com/codesuite/codepipeline/pipelines/'+pipeline_name+'/view?region='+region
            content = u'\u23F3'+' Pipeline started at {}'.format(datetime.datetime.utcnow().time())+' '+'- See the [Pipeline]({0})'.format(pipeline_url)
            post_comment(pr_id, repository_name, source_commit, destination_commit, content)

            # TO-DO get the comment ID and use it to post all other status updates
            time.sleep(10)

            pipeline_name = new_pipeline_response['pipeline']['name']
            pipeline_stages = get_status(pipeline_name)

            for stage in pipeline_stages['stageStates']:

                if stage['stageName'] == 'Source':
                    source_execution_status = stage['actionStates'][0]['latestExecution']['status']
                    if source_execution_status == 'Succeeded':
                        print('Stage Source Passed.')
                    else:
                        print('Stage Source Failed.')
                        break

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

                            #if destination_branch == 'master':
                            #    print('Keeping the Master Branch Pipelines for reference.')
                            #else:
                            #    delete_pipeline(pipeline_name)
                            break

                        elif build_execution_status == 'Failed':
                            jenkins_build_id = get_jenkins_build_number(pipeline_name)
                            content = u'\u274C'+' Build Failed - See the [Logs]({0})'.format(jenkins_build_id)
                            post_comment(pr_id, repository_name,
                                         source_commit, destination_commit,
                                         content)
                            #if destination_branch == 'master':
                            #    print('Keeping the Master Branch Pipelines for reference.')
                            #else:
                            #    delete_pipeline(pipeline_name)
                            break

                        else:
                            count += 1
                            time.sleep(10)


def lambda_handler(event, context):

    message = ast.literal_eval(event['Records'][0]['Sns']['Message'])
    event_type = message['detail']['event']

    if event_type == 'referenceCreated' or event_type == 'referenceUpdated':
        branch_events(message, event_type)
    elif event_type == 'pullRequestCreated' or event_type == 'pullRequestSourceBranchUpdated':
        pr_events(message, event_type)
