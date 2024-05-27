# Recorded Voice Insight Extraction Webapp (ReVIEW)

**_A generative AI tool to boost productivity by transcribing and analyzing audio or video recordings containing speech_**

# Contents
- [Overview](#overview)
- [Architecture](#architecture)
- [Deployment](#deployment)
- [Repo Structure](#repo-structure)
- [Pending Updates](#pending-updates)
- [Contributors](#contributors)

# Overview

The Recorded Voice Insight Extraction Webapp (ReVIEW) is a cdk-deployed application built on AWS and Bedrock that boosts productivity by allowing users to upload recordings containing speech and leverage generative AI to answer questions based on the transcripts, create custom summaries, draft custom readout documents, identify topics discussed, and more. 

This application also includes a chat functionality with an AI assistant who can answer specific questions and queue up the parent recording to specific timestamps for users to validate the answers themselves.

### Key Features

- Upload any audio or video recording file through a user friendly frontend.
- Files automatically get transcribed, with status that can be viewed in the frontend.
- Provided analysis templates allow for easy GenAI summarization, document generation, next-steps and blockers identifications, and more.
- Interactive chat-with-your-media function provides an AI assistant who will answer specific questions about the media and identify the timestamp in the media when the answer was provided. The media automatically gets played back starting at that timestamp.


# Architecture
Here is an overview of the architecture for the solution.
<p align="center">
    <img src=diagram/ReVIEW-architecture-20240524.png alt="architecture" width="60%">
</p>

Note that the frontend stack as shown isn't fully implemented as of 20240521.

# Deployment
### *Clone the Repository*
Fork the repository, and clone it to the location of your choice. For example:
```{bash}
$ git clone git@ssh.gitlab.aws.dev:<your-username>/ReVIEW.git
```

### *CDK Prerequisites*
It is assumed you have set up a development environment with CDK dependencies installed. 

* [Install CDK](https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html)
* [Install NodeJS](https://docs.aws.amazon.com/sdk-for-javascript/v2/developer-guide/setting-up-node-on-ec2-instance.html)

Additional prerequisites:
* [Docker](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/create-container-image.html#create-container-image-install-docker)

Install required python packages into the virtual environment of your choice with `pip install -r requirements.txt`.


### AWS Permission Prerequisites
The minimal IAM permissions needed to bootstrap and deploy the stacks from this repo are described in `ReVIEW/infra/minimal-iam-policy.json`. Ensure the customer creates this policy and associates it with your user or role in their environment.


### *Deploy the backend CDK stack*

```{bash}
$ cd infra
$ cdk bootstrap
$ cdk deploy --all
```

This will deploy the ReVIEW backend stack into your AWS account.

### *Deploy the frontend CDK stack*
Not yet implemented. Currently you must run the following command interactively and port forward as necessary to access the UI in your browser:

```{bash}
$ streamlit run ReVIEW/frontend/🦻_Home.py --server.port=8502 --server.address=0.0.0.0
```

# Repo Structure
- infra - Python backend code
    - lambdas - Python lambda function code to be zipped then uploaded during deployment
    - review_stack - Python CDK containing the backend stack
- frontend - Python streamlit application code for the frontend
    - Home.py - Main streamlit application entrypoint
    - components/ - Utilities used by streamlit application
    - pages/ - Different pages displayed in the frontend application
    - assets/ - Static assets used by the frontend, e.g. analysis templates that application users can select
- notebooks - Misc sandbox-style notebooks used during development
- diagram - Architecture diagrams of the solution used in READMEs

## Pending Updates
See the [issues board](FIX_THIS_TO_POINT_TO_GITLAB_ISSUES) for a list of all pending updates. Major updates include:

* Adding a Cognito user pool and sharding the backend accordingly
* Creating a separate frontend stack with containerized streamlit application running in ECS
* Allowing users to delete old uploaded meetings from the frontend

## Contributors
- [David Kaleko](https://phonetool.amazon.com/users/kaleko), Senior Applied Scientist, AWS Generative AI Innovation Center