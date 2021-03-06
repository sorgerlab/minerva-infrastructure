#!/usr/bin/env python

import argparse
from enum import Enum
import os
import sys
from ruamel.yaml import YAML
import boto3
import time


def load_config(config):

    yaml = YAML()

    try:
        parsed_config = yaml.load(config)

        if len(parsed_config['SubnetsPublic']) != 2:
            print('Exactly 2 public subnets required')
            sys.exit(1)
        return parsed_config

    except Exception as e:
        print('Error reading configuration YAML: {}'.format(e))
        sys.exit(1)


def make_parameter(key, value):

    return {
        'ParameterKey': key,
        'ParameterValue': value
    }

def print_stack_error(cf, stack_id):
    res = cf.describe_stack_events(StackName=stack_id)
    for event in res["StackEvents"]:
        if "FAILED" in event["ResourceStatus"]:
            print(event["ResourceStatus"])
            print(event["ResourceStatusReason"])

def string_configs_to_parameters(config, keys):

    return [make_parameter(key, str(config[key])) for key in keys]


def get_stack_template_path(stack):

    return os.path.join(os.path.dirname(__file__), '{}.yml'.format(stack))


def prepare_common_parameters(config):

    parameters = string_configs_to_parameters(config, [
        'VpcId',
        'DatabasePassword',
        'EnableRenderedCache',
        'EnableRawCache'
    ])

    parameters.append(make_parameter('SubnetsPublic',
                                     ','.join(config['SubnetsPublic'])))

    return parameters


def prepare_batch_parameters(config):

    parameters = string_configs_to_parameters(config, [
        'BatchAMI',
        'BatchClusterEC2MinCpus',
        'BatchClusterEC2MaxCpus',
        'BatchClusterEC2DesiredCpus',
        'BatchClusterSpotMinCpus',
        'BatchClusterSpotMaxCpus',
        'BatchClusterSpotDesiredCpus',
        'BatchClusterSpotBidPercentage'
    ])

    parameters.append(make_parameter('SubnetsPublic',
                                     ','.join(config['SubnetsPublic'])))

    return parameters


def prepare_cache_parameters(config):
    return string_configs_to_parameters(config, [
        'DefaultSecurityGroup',
        'CacheNodeType',
        'RawCacheNodeType'
    ])

def main(operation, stack, config):
    exit_code = 0
    # Load the configuration file
    config = load_config(config)

    # Get config parameters needed to configure the operation itself
    region = config['Region']
    prefix = config['StackPrefix']
    project_tag = config['ProjectTag']
    aws_profile = config['Profile']
    if aws_profile == 'default':
        aws_profile = None

    # Select the appropriate cloudformation operation
    session = boto3.Session(profile_name=aws_profile)
    cf = session.client('cloudformation', region_name=region)
    cf_methods = {
        'create': cf.create_stack,
        'update': cf.update_stack,
        'delete': cf.delete_stack
    }
    if operation not in cf_methods.keys():
        print(f'Operation "{operation}" is not implemented')
        sys.exit(1)

    cf_method = cf_methods[operation]

    # Build a prefixed name for this stack
    name = f'{prefix}-cf-{stack}'

    # Read the template
    template_path = get_stack_template_path(stack)
    with open(template_path, 'r') as f:
        template_body = f.read()

    # Prepare the parameters common to all stacks
    shared_parameters = string_configs_to_parameters(config, [
        'StackPrefix',
        'Stage',
        'ProjectTag'
    ])

    # Prepare the parameters specific to the requested stack
    if stack == 'common':
        parameters = prepare_common_parameters(config)
    elif stack == 'cognito':
        parameters = []
    elif stack == 'batch':
        parameters = prepare_batch_parameters(config)
    elif stack == 'cache':
        parameters = prepare_cache_parameters(config)
    elif stack == 'author':
        parameters = []

    if operation in ['create', 'update']:
        # Trigger the operation
        response = cf_method(
            StackName=name,
            TemplateBody=template_body,
            Parameters=shared_parameters + parameters,
            Capabilities=[
                'CAPABILITY_NAMED_IAM',
            ],
            Tags=[{
                'Key': 'project',
                'Value': project_tag
            }]
        )
    elif operation == 'delete':
        response = cf_method(
            StackName=name
        )

    print(response)

    if 'StackId' in response:
        stack_id = response['StackId']
        print(f'Stack {stack} {operation} completed: {stack_id}')
        poll_progress = True
    else:
        poll_progress = False

    status = ""
    print('Waiting for stack update to complete')
    rollback = False
    while poll_progress:
        sys.stdout.write('-')
        time.sleep(2)
        response = cf.describe_stacks(StackName=stack_id)

        for stack in response['Stacks']:
            if stack['StackId'] == stack_id:
                if stack['StackStatus'] != status:
                    status = stack['StackStatus']
                    sys.stdout.write('>' + status)
                    poll_progress = 'IN_PROGRESS' in status

                if 'ROLLBACK' in stack['StackStatus']:
                    rollback = True

        sys.stdout.flush()

    print("")
    print("Stack status: ", status)

    if rollback:
        print_stack_error(cf, stack_id)
        exit_code = 1

    return exit_code


if __name__ == '__main__':

    class Stack(Enum):
        common = 'common'
        cognito = 'cognito'
        batch = 'batch'
        cache = 'cache'
        author = 'author'

        def __str__(self):
            return self.value

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='operation')
    parser_create = subparsers.add_parser('create', help='Create stack')
    parser_update = subparsers.add_parser('update', help='Update stack')
    parser_delete = subparsers.add_parser('delete', help='Delete stack')
    parser.add_argument('stack', type=Stack, choices=list(Stack))
    parser.add_argument('config', type=argparse.FileType('r'),
                        help='YAML configuration file path')

    opts = parser.parse_args()

    exit_code = main(opts.operation, str(opts.stack), opts.config)
    sys.exit(exit_code)
