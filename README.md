# Recorded Voice Insight Extraction Webapp (ReVIEW)

**_A generative AI tool to boost productivity by transcribing and analyzing audio or video recordings containing speech_**

# Contents
- [Recorded Voice Insight Extraction Webapp (ReVIEW)](#recorded-voice-insight-extraction-webapp-review)
- [Contents](#contents)
- [Overview](#overview)
  - [Key Features](#key-features)
- [Architecture](#architecture)
- [Deployment](#deployment)
    - [*Clone the Repository*](#clone-the-repository)
    - [*CDK Prerequisites*](#cdk-prerequisites)
    - [*AWS Permission Prerequisites*](#aws-permission-prerequisites)
    - [*Edit the Deployment Config File*](#edit-the-deployment-config-file)
    - [*Deploy the CDK stacks*](#deploy-the-cdk-stacks)
    - [*Destroy the CDK stacks*](#destroy-the-cdk-stacks)
- [Repo Structure](#repo-structure)
- [Frontend Replacement](#frontend-replacement)
  - [Pending Updates](#pending-updates)
  - [Additional Resources](#additional-resources)
  - [Contributors](#contributors)

# Overview

The Recorded Voice Insight Extraction Webapp (ReVIEW) is a cdk-deployed, robust, and scalable application built on AWS and Bedrock that boosts productivity by allowing users to upload recordings containing speech and leverage generative AI to answer questions based on the recordings. The AI assistant chatbot functionality will answer specific questions about a recording (or recordings) **and queue up the parent media to specific timestamps for users to validate the answers themselves** This is the critical workflow that allows the users to verify accuracy of LLM-generated answers for themselves.

Additionally, this application includes the capability to use an LLM to analyze the transcripts with custom templates including generating summaries, draft custom readout documents, identify topics discussed, and more. 

A 4 minute video demonstrating the features as of May 28, 2024 [can be viewed here](https://amazon.awsapps.com/workdocs-preview/index.html#/document/4e6f1bcfcd420cd4e650e7008a946a6d1214d735336d2b3c40784ba2af1b0ed2). Note this video demonstrates a version of the application before the knowledge base / RAG component was integrated to allow chatting with multiple media sources, and before the API Gateway was added.

## Key Features

- User authentication is provided by Amazon Cognito.
- Upload any audio or video recording file through a user friendly frontend.
- Files automatically get transcribed, with status that can be viewed in the frontend.
- Interactive chat-with-your-media function provides an AI assistant who will answer specific questions about one media file or a collection of multiple media files, and **will identify timestamps in the media files when the answer was provided. The media automatically gets played back starting at that timestamp, with clickable citations if multiple sources are relevant to the answer.**
- Provided analysis templates allow for easy GenAI summarization, document generation, next-steps and blockers identifications, and more.
- Complete frontend/backend separation via API Gateway to enable users to replace Streamlit if desired.
Here is an overview of the architecture for the solution.

Here is a screenshot of the chat functionality. Here, the user asked whether any new products were announced in a collection of uploaded videos of public AWS presentations. Since several videos mentioned the announcement of SageMaker HyperPods, three buttons appear which auto play the cited videos at the relevant timestamp when the announcements occurred. This is the critical user experience that allows the users to verify accuracy of LLM-generated answers for themselves.
<p align="center">
    <img src=diagram/ReVIEW-chat-screenshot-20241022.png alt="chat_screenshot" width="90%">
</p>

# Architecture
Here is an overview of the architecture for the solution.
<p align="center">
    <img src=diagram/ReVIEW-architecture-20241022.png alt="architecture" width="90%">
</p>

* **(1)** Users connect to a CloudFront distribution which forwards traffic to the application load balancer via HTTPS with a custom header. 
* **(2)** The containerized Streamlit application running in ECS connects to Amazon Cognito to authenticate users and to get a bearer token for API Gateway authentication.
* **(3 and 4)** The frontend uploads media files to an S3 bucket by first requesting a presigned URL and then POSTing the file to it. The media files then automatically transcribed. Once transcripts are created in s3, an EventBridge notification triggers an AWS Step Functions workflow to asynchronously sync the transcripts (and track the sync job status) with a Bedrock Knowledge Base. The Knowledge Base handles chunking, embedding, and later retrieval. 
* **(5)** The application functionality leverages Large Language Models in Bedrock to analyze transcripts (or chunks of transcripts retrieved from the knowledge base **(6)**) and identify timestamps at which to replay media to the users. 
* **(7)** DynamoDB is used to track job processing statuses and cache previous LLM responses.

Here are the details of the [AWS Step Functions](https://aws.amazon.com/step-functions/) workflow for knowledge base sync and checking sync status, which gets triggered initially via [Amazon Event Bridge](https://aws.amazon.com/eventbridge/) by a transcript appearing in s3:
<p align="center">
    <img src=diagram/step-functions-kb-sync-workflow.png alt="Knowledge Base Sync Step Functions Workflow" width="80%">
</p>
The workflow is triggered by an Event Bridge notifications 

# Deployment

The code base behind the solution consists of four stacks:
1) A backend which handles transcribing uploaded media and tracking job statuses, 
2) A RAG stack which handles setting up OpenSearch and Bedrock Knowledge bases, 
3) An API stack which stands up a Cognito-authorized REST API and various lambda functions to logically separate the frontend from the backend, and
4) A frontend stack which consists of a containerized streamlit application running as a load balanced service in an ECS cluster in a VPC, with a cloudfront distribution connected to the load balancer.

### *Clone the Repository*
Fork the repository, and clone it to the location of your choice. For example:
```{bash}
$ git@ssh.gitlab.aws.dev:genaiic-reusable-assets/demo-artifacts/ReVIEW.git
```

### *CDK Prerequisites*
It is assumed you have set up a development environment with CDK dependencies installed. 

* [Install CDK](https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html)
* [Install NodeJS](https://docs.aws.amazon.com/sdk-for-javascript/v2/developer-guide/setting-up-node-on-ec2-instance.html)

Additional prerequisites:
* [Docker](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/create-container-image.html#create-container-image-install-docker)

Install required python packages into the virtual environment of your choice with `pip install -r requirements.txt`.


### *AWS Permission Prerequisites*
The minimal IAM permissions needed to bootstrap and deploy the cdk are described in `ReVIEW/infra/minimal-iam-policy.json`. Ensure the customer creates this policy and associates it with your user or role in their environment.

### *Edit the Deployment Config File*
Edit the `infra/config.yaml` file to provide a base name for your stack (`stack_name_base`), bucket names, Bedrock model IDs, etc for your application. 

### *Deploy the CDK stacks*

```{bash}
$ cd infra
$ cdk bootstrap
$ cdk deploy --all --require-approval never
```

The above bootstrap command only needs to be done once per AWS account. The deploy command will deploy all three stacks, and the `--require-approval never` flag will bypass any y/n questions during deployment, so use at your own risk.

To optionally deploy one stack at a time, you can do
```{bash}
$ cdk deploy [stack_name_base]-backend
$ cdk deploy [stack_name_base]-rag
$ cdk deploy [stack_name_base]-api
$ cdk deploy [stack_name_base]-frontend
```

Note there are dependencies between stacks so they must be deployed in this order.

### *Destroy the CDK stacks*

```{bash}
$ cdk destroy --all --force
```

This will destroy all three ReVIEW stacks and remove all components from your AWS account. The `--force` flag will bypass any y/n questions during deployment, so use at your own risk.

# Repo Structure
- infra - Python backend code
  - app.py - Main CDK app definition
  - config.yaml - Main CDK app configuration (edit this!)
  - lambdas/ - Python lambda function code to be deployed
  - assets/ - Python lambda dependencies stored as a .zip file
  - constructs/
    - Custom Python CDK constructs separated out to make stack deployment code more modular
  - stacks/
    - backend_stack - Python CDK containing the backend stack definition
    - rag_stack - Python CDK containing the OpenSearch and Knowledge Base setup
    - frontend_stack - Python CDK containing the frontend stack definition
  - utils - Utility functions related to infra, like configuration managers
- frontend - Python streamlit application code for the frontend
  - 💡_Home.py - Main streamlit application entrypoint
  - components/ - Utilities used by streamlit application
  - pages/ - Different pages displayed in the frontend application
  - assets/ - Static assets used by the frontend, e.g. analysis templates that application users can select
  - schemas/ - Data models and schemas used by the frontend
  - Dockerfile - Docker file to build containerized frontend application within this directory
- notebooks/ - Misc sandbox-style notebooks used during development
- diagram/ - Architecture diagrams of the solution used in READMEs

# Frontend Replacement
This application has been designed to make the frontend easily replaceable, as end users may want to replace Streamlit with something more production-grade whilst preserving the backend. Besides the frontend being deployed as a separate stack, it also connects to the backend exclusively through a REST API hosted by API Gateway. 

At a high level, the steps to replace the frontend are:

1. Determine an OAuth provider or other way to authorize the new frontend to access the API Gateway via bearer token. Currently, Cognito is used.
2. Connect the new frontend to the `/s3-presigned` endpoint. This endpoint will generate presigned urls for the frontend to `POST` and `GET` files to and from s3.
3. Connect the new frontend to the three `POST` REST API endpoints: `/llm`, `/ddb`, `/kb` to access large language models, dynamodb, and knowledge bases respectively.
4. Leverage the `FullQAnswer` pydantic model (defined in `frontend/schemas/qa_response.py`) to parse the LLM responses in the chat application. This model includes citations which reference specific timestamps in media files.

If the new frontend is written in Python, it is recommend to re-use the `frontend/components/` which is where most of the REST API calls are made.

## Pending Updates
See the [issues board](https://gitlab.aws.dev/genaiic-reusable-assets/demo-artifacts/ReVIEW/-/issues) for a list of all pending updates

## Additional Resources
* [AWS APG Pattern for ReVIEW](https://apg-library.amazonaws.com/content-viewer/author/3642bafc-3b2e-4bc4-8725-a492823db860) (pre knowledge base integration)
* [Instructions to access an already-deployed version of the app](https://quip-amazon.com/26b2AbDN6W8Y/ReVIEW-Application-New-User-Onboarding)
* [Tech exchange talk recording](https://amazon.awsapps.com/workdocs-preview/index.html#/document/1af14339831b9fcfe1cb51c79e0acf38008120e8082314df5e6e23d7c2461a3a) and [associated slides](https://amazon.awsapps.com/workdocs-preview/index.html#/document/f540c23cbd61a81a7185a5a97ed08dcb0fda198df6874625eb285a2b6afea910) (pre knowledge base integration)
* [GenAIIC Builder Forum talk recording](https://amazon.awsapps.com/workdocs-preview/index.html#/document/28a354ef105ed669b517eef50abc50da02f93f0d45590ec5cf8426bf539289d9) and [associated slides](https://amazon.awsapps.com/workdocs-preview/index.html#/document/04fafed932a0590769af6b0d78356994ef318593b2bf4f357d819b20d0703415) (pre knowledge base integration)

## Contributors
- [David Kaleko](https://phonetool.amazon.com/users/kaleko), Senior Applied Scientist, AWS Generative AI Innovation Center