import ast
import boto3
import datetime
import time

from botocore.exceptions import ClientError


codecommit_client = boto3.client('codecommit')
codepipeline_client = boto3.client('codepipeline')

repository_name = 'Dev-Dt-Android'
account_number = '323144884758'
role = 'codepipeline-android-service-role'
region = 'ap-south-1'
s3_android_dev_bucket = 'dt-android'

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
                            "BranchName": "development",
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
                            "ProjectName": "ci-test"
                        },
                        "inputArtifacts": [
                            {
                                "name": "SourceArtifact"
                            }
                        ]
                    }
                ],
                "name": "Build"
            }
        ],
        "artifactStore": {
            "type": "S3",
            "location": s3_android_dev_bucket
        },
        "name": "ci-pipeline",
        "roleArn": 'arn:aws:iam::'+account_number+':role/service-role/'+role
    }
}


def get_status(pipeline_name):
    pipeline_status = codepipeline_client.get_pipeline_state(name=pipeline_name)
    return pipeline_status


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


# Beanch Events Ex: referenceCreated, referenceDeleted, referenceUpdated 
def branch_events(message, event_ytpe):
    commit_id = message['detail']['commitId']
    branch_ref = '/'.join(message['detail']['referenceFullName'].split('/')[2:])
    code_pipeline_configuration = pipeline_configuration

    stage, = [ s for s in code_pipeline_configuration['pipeline']['stages'] if s['name'] == 'Source' ]
    stage['actions'][0]['configuration']['BranchName'] = branch_ref

    code_pipeline_configuration['pipeline']['name'] = branch_ref + '-' + commit_id + '-pipeline'
    code_pipeline_configuration['pipeline']['stages'][1]['actions'][0]['configuration']['ProjectName'] = 'android-dev'
    modified_pipeline_json = code_pipeline_configuration['pipeline']

    try:
        new_pipeline_response = codepipeline_client.create_pipeline(pipeline=modified_pipeline_json)
        print(new_pipeline_response)
    except:
        print("Unable to generate new pipeline.")

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

        elif stage['stageName'] == 'Build':
            build_url = stage['actionStates'][0]['latestExecution']['externalExecutionUrl']
            count = 0
            while count < 500:
                pipeline_build_status = get_status(pipeline_name)
                build_execution_status = pipeline_build_status['stageStates'][1]['latestExecution']['status']
                print('Build status :: ', build_execution_status)
                
                if build_execution_status == 'Succeeded':
                    print('Stage Build Passed.')
                    break
                
                elif build_execution_status == 'Failed':
                    print(pipeline_build_status['stageStates'][1]['actionStates'][0]['latestExecution']['errorDetails']['message'])
                    break
                
                else:
                    count += 1
                    time.sleep(10)


# Pull Request Events Ex: pullRequestCreated, pullRequestSourceBranchUpdated
def pr_events(message, event_ytpe):
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
            source_branch = '/'.join(message['detail']['sourceReference'].split('/')[2:])
            print(source_branch)

            code_pipeline_configuration = pipeline_configuration

            stage, = [s for s in code_pipeline_configuration['pipeline']['stages'] if s['name'] == 'Source']
            stage['actions'][0]['configuration']['BranchName'] = source_branch
            code_pipeline_configuration['pipeline']['name'] = pipeline_name

            if destination_branch == 'master':
                code_pipeline_configuration['pipeline']['stages'][1]['actions'][0]['configuration']['ProjectName'] = 'android-master'
            else:
                code_pipeline_configuration['pipeline']['stages'][1]['actions'][0]['configuration']['ProjectName'] = 'android-dev'

            modified_pipeline_json = code_pipeline_configuration['pipeline']

            try:
                new_pipeline_response = codepipeline_client.create_pipeline(pipeline=modified_pipeline_json)
                print('Pipeline '+pipeline_name+' creation succeeded.')
                pipeline_url = 'https://'+region+'.console.aws.amazon.com/codesuite/codepipeline/pipelines/'+pipeline_name+'/view?region='+region
                content = u'\u23F3'+' Pipeline started at {}'.format(datetime.datetime.utcnow().time())+' '+'- See the [Pipeline]({0})'.format(pipeline_url)
                post_comment(pr_id, repository_name, source_commit, destination_commit, content)
            except Exception as e:
                print("Unable to generate new pipeline. %" % e)

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

                elif stage['stageName'] == 'Build':
                    build_url = stage['actionStates'][0]['latestExecution']['externalExecutionUrl']
                    count = 0
                    while count < 500:
                        pipeline_build_status = get_status(pipeline_name)
                        build_execution_status = pipeline_build_status['stageStates'][1]['latestExecution']['status']
                        print('Build status :: ', build_execution_status)
                        if build_execution_status == 'Succeeded':
                            print('Stage Build Passed.')
                            content = u'\u2705'+' Build Passed - See the [Logs]({0})'.format(build_url)
                            post_comment(pr_id, repository_name,
                                         source_commit, destination_commit,
                                         content)

                            if destination_branch == 'master':
                                print('Keeping the Master Branch Pipelines for reference.')
                            else:
                                delete_pipeline(pipeline_name)
                            break

                        elif build_execution_status == 'Failed':
                            content = u'\u274C'+' Build Failed - See the [Logs]({0})'.format(build_url)
                            post_comment(pr_id, repository_name,
                                         source_commit, destination_commit,
                                         content)
                            if destination_branch == 'master':
                                print('Keeping the Master Branch Pipelines for reference.')
                            else:
                                delete_pipeline(pipeline_name)
                            break

                        else:
                            count += 1
                            time.sleep(10)


def lambda_handler(event, context):

    message = ast.literal_eval(event['Records'][0]['Sns']['Message'])
    event_type = message['detail']['event']

    if event_type == 'referenceCreated':
        branch_events(message, event_type)
    elif event_type == 'pullRequestCreated' or event_type == 'pullRequestSourceBranchUpdated':
        pr_events(message, event_type)
