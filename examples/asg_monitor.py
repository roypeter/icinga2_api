#!/usr/bin/env python

""" 
Quick and dirty program to add and delete AWS autoscaled nodes in Icinga2.

Setup:
1.Create a AWS lambda function with 'AWSLambdaBasicExecutionRole' and 'AmazonEC2Re
adOnlyAccess' role
2.Add api.yml file in same level as this file. With following content
default:
  host: 52.x.x.x
  port: 5665
  user: root
  password: icinga
  timeout: 5
  verbose: false
  verify: false
3.For packaging AWS lambda function follow this doc 
http://docs.aws.amazon.com/lambda/latest/dg/lambda-python-how-to-create-deployment-package.html
4.Create a SNS trigger for lambda from autoscaling group
"""

from __future__ import print_function
from icinga2_api import api
import json
import boto3

print('Loading function')

def get_ec2_ip(id, region):
  client = boto3.client('ec2',region_name=region)
  waiter = client.get_waiter('instance_running')
  print("waiting for ec2 instance state to become 'running'...")
  waiter.wait(
    DryRun=False,
    InstanceIds=[id]
  )
  print('ec2 instance state is running')
  ec2 = boto3.resource('ec2',region_name=region)
  instance = ec2.Instance(id)
  return instance.private_ip_address

def lambda_handler(event, context):
  message = json.loads(event['Records'][0]['Sns']['Message'])
  obj = api.Api()

  if message['Event'] == 'autoscaling:EC2_INSTANCE_LAUNCH':
    uri = '/v1/objects/hosts/{}'.format(message['EC2InstanceId'])
    data = { 
    "templates": [ "generic-host" ],
      "attrs": {
        "address": get_ec2_ip(
          message['EC2InstanceId'],
          message['Details']['Availability Zone'][:-1]
        ),
        "vars.os" : "Linux" 
      } 
    }
    output = obj.create(uri, data)
    print (json.dumps(output['response']['data'], indent=2))
  elif message['Event'] == 'autoscaling:EC2_INSTANCE_TERMINATE':
    uri = '/v1/objects/hosts/{}'.format(message['EC2InstanceId'])
    data = {'cascade': 1}
    output = obj.delete(uri, data)
    print (json.dumps(output['response']['data'], indent=2))
