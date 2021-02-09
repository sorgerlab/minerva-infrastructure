<img width="500px" src="./Minerva-Cloud_HorizLogo_RGB.svg" />

# Minerva Cloud - AWS backend infrastructure

This repository contains the templates necessary to deploy the Minerva Cloud platform in AWS.
It is comprised of some CloudFormation and Serverless Framework configurations.

## API Documentation

[Minerva API](https://labsyspharm.github.io/minerva-cloud/)

## Prerequisites
These need to be created manually in AWS console
- A VPC in the desired AWS region.
- A pair of public subnets in the VPC.
- A pair of private subnets with NAT gateways configured in the VPC.
- A default security group which allows communication in/out from itself.
- A security group which allows SSH communication to EC2 instances as required.
- A configuration file with these and some other properties.
- A deployment bucket for serverless.

## AWS Profile

If you need to use a different aws profile from the default one, to be able to access aws resources,
this can be setup with:
- export AWS_PROFILE=profile_name

## Configuration File

There is an example configuration file included in the repository: minerva-config.example.yml
You need to update the vpc, subnets and other values in the configuration file.

## Instructions

You can later update the stacks by replacing word "create" with "update"
Instructions below presume you have the configuration file in a folder named minerva-configs,
which is a sibling to the minerva-cloud project root directory.

Before deploying the various serverless applications, you should install the needed node packages by running within each serverless/* directory:
```bash
npm install
```

1. Deploy the common cloudformation infrastructure

```bash
cd cloudformation
python cloudformation.py create common ../../minerva-configs/test/config.yml
```

2. Deploy the cognito cloudformation infrastructure

```bash
cd cloudformation
python cloudformation.py create cognito ../../minerva-configs/test/config.yml
```

3. Build the Batch AMI

```bash
cd ami-builder
python build.py ../../minerva-configs/test/config.yml
```

4. Deploy the Batch cloudformation infrastructure

```bash
cd cloudformation
python cloudformation.py create batch ../../minerva-configs/test/config.yml
```

5. Deploy the auth serverless infrastructure

```bash
cd serverless/auth
serverless deploy --configfile ../../../minerva-configs/test/config.yml
```

6. Deploy the db serverless infrastructure

```bash
cd serverless/db
serverless deploy --configfile ../../../minerva-configs/test/config.yml
```

7. Deploy the batch serverless infrastructure

```bash
cd serverless/batch
serverless deploy --configfile ../../../minerva-configs/test/config.yml
```

8. Deploy the api serverless infrastructure

```bash
cd serverless/api
serverless deploy --configfile ../../../minerva-configs/test/config.yml
```

9. Deploy the author serverless infrastructure (OPTIONAL)
* This is only for integrating Minerva Author with Minerva Cloud
```bash
cd serverless/author
serverless deploy --configfile ../../../minerva-configs/test/config.yml
```

10. Run AWS lambda `initdb` function to initialise the database
* Find the function name (e.g. minerva-test-dev-initDb) from AWS Lambda console
* Open the function and click "Test"

11. Create some users using the AWS Cognito console
* The new users are automatically created in Minerva database by a Cognito trigger.
