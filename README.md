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
    - [AWS Permission Prerequisites](#aws-permission-prerequisites)
    - [*Deploy the CDK stacks*](#deploy-the-cdk-stacks)
- [Repo Structure](#repo-structure)
  - [Pending Updates](#pending-updates)
  - [Contributors](#contributors)

# Overview

The Recorded Voice Insight Extraction Webapp (ReVIEW) is a cdk-deployed application built on AWS and Bedrock that boosts productivity by allowing users to upload recordings containing speech and leverage generative AI to answer questions based on the transcripts, create custom summaries, draft custom readout documents, identify topics discussed, and more. 

This application also includes a chat functionality with an AI assistant who can answer specific questions and queue up the parent recording to specific timestamps for users to validate the answers themselves.

A 5 minute video demonstrating the features as of May 28, 2024 [can be viewed here](https://amazon.awsapps.com/workdocs-preview/index.html#/document/4e6f1bcfcd420cd4e650e7008a946a6d1214d735336d2b3c40784ba2af1b0ed2).

### Key Features

- Upload any audio or video recording file through a user friendly frontend.
- Files automatically get transcribed, with status that can be viewed in the frontend.
- Provided analysis templates allow for easy GenAI summarization, document generation, next-steps and blockers identifications, and more.
- Interactive chat-with-your-media function provides an AI assistant who will answer specific questions about the media and identify the timestamp in the media when the answer was provided. The media automatically gets played back starting at that timestamp.


# Architecture
Here is an overview of the architecture for the solution.
<p align="center">
    <img src=diagram/ReVIEW-architecture-20240528.png alt="architecture" width="60%">
</p>

The solution consists of two stacks, a backend which handles transcribing uploaded media and tracking job statuses, and a frontend which consists of a containerized streamlit application running as a load balanced service in an ECS cluster in a VPC, a cloudfront distribution connected to the load balancer, and a cognito user pool for user authentication.

# Deployment
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


### AWS Permission Prerequisites
The minimal IAM permissions needed to bootstrap and deploy the cdk are described in `ReVIEW/infra/minimal-iam-policy.json`. Ensure the customer creates this policy and associates it with your user or role in their environment.


### *Deploy the CDK stacks*

```{bash}
$ cd infra
$ cdk bootstrap
$ cdk deploy --all
```

This will deploy the ReVIEW backend stack into your AWS account, as well as the nested frontend stack.


# Repo Structure
- infra - Python backend code
  - app.py - Main cdk app definition
  - lambdas - Python lambda function code to be zipped then uploaded during deployment
  - stacks
    - review_stack - Python CDK containing the backend stack definition
    - frontend_stack - Python CDK containing the nested frontend stack definition
- frontend - Python streamlit application code for the frontend
  - 💡_Home.py - Main streamlit application entrypoint
  - components/ - Utilities used by streamlit application
  - pages/ - Different pages displayed in the frontend application
  - assets/ - Static assets used by the frontend, e.g. analysis templates that application users can select
  - Dockerfile - Docker file to build containerized application within this directory.
- notebooks - Misc sandbox-style notebooks used during development
- diagram - Architecture diagrams of the solution used in READMEs

## Pending Updates
See the [issues board](https://gitlab.aws.dev/genaiic-reusable-assets/demo-artifacts/ReVIEW/-/issues) for a list of all pending updates. Major updates include:

* Allowing users to delete old uploaded meetings from the frontend
* Security updates / HTTPS support
* Allowing answers in "chat with your media" to come from multiple timestamps
* Implementing more analysis templates (prompts)
* Improving latency of media viewer loading in "chat with your media"
  
## Contributors
- [David Kaleko](https://phonetool.amazon.com/users/kaleko), Senior Applied Scientist, AWS Generative AI Innovation Center