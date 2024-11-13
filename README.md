# Recorded Voice Insight Extraction Webapp (ReVIEW)

**_A generative AI tool to boost productivity by transcribing and analyzing audio or video recordings containing speech_**

# Contents
- [Recorded Voice Insight Extraction Webapp (ReVIEW)](#recorded-voice-insight-extraction-webapp-review)
- [Contents](#contents)
- [🔥 Overview](#-overview)
- [🔑 Key Features](#-key-features)
- [🏗️ Architecture](#️-architecture)
- [🔧 Deployment](#-deployment)
- [🏛️ Repo Structure](#️-repo-structure)
- [🚪 Frontend Replacement](#-frontend-replacement)
- [🔒️ Security](#️-security)
- [👥 Authors](#-authors)
- [📝 License](#-license)

# 🔥 Overview

The Recorded Voice Insight Extraction Webapp (ReVIEW) is a cdk-deployed, robust, and scalable application built on AWS and Bedrock that boosts productivity by allowing users to upload recordings containing speech and leverage generative AI to answer questions based on the recordings. The AI assistant chatbot functionality will answer specific questions about a recording (or recordings) **and queue up the parent media to specific timestamps for users to validate the answers themselves**. This is the critical workflow that allows the users to verify accuracy of LLM-generated answers for themselves.

Additionally, this application includes the capability to use an LLM to analyze the transcripts with custom templates including generating summaries, draft custom readout documents, identify topics discussed, and more. 

# 🔑 Key Features

- User authentication is provided by Amazon Cognito.
- Upload any audio or video recording file through a user friendly frontend.
- Files automatically get transcribed, with status that can be viewed in the frontend.
- Interactive chat-with-your-media function provides an AI assistant who will answer specific questions about one media file or a collection of multiple media files, and **will identify timestamps in the media files when the answer was provided. The media automatically gets played back starting at that timestamp, with clickable citations if multiple sources are relevant to the answer.**
- Provided analysis templates allow for easy GenAI summarization, document generation, next-steps and blockers identifications, and more.
- Complete frontend/backend separation via API Gateway to enable users to replace Streamlit if desired.
Here is an overview of the architecture for the solution.

Below is a screenshot of the chat functionality. Here, the user asked whether any new products were announced in a collection of uploaded videos of public AWS presentations. Since several videos mentioned the announcement of SageMaker HyperPods, three buttons appear which auto play the cited videos at the relevant timestamp when the announcements occurred. This is the critical user experience that allows the users to verify accuracy of LLM-generated answers for themselves.
<p align="center">
    <img src=diagram/ReVIEW-chat-screenshot-20241113.png alt="chat_screenshot" width="90%">
</p>

# 🏗️ Architecture
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
The workflow is triggered by an Event Bridge notifications in the transcripts s3 bucket.

# 🔧 Deployment

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

The following tools should be installed, as well as access to the target AWS account:

- [AWS CLI](https://cdkworkshop.com/15-prerequisites/100-awscli.html)
- [AWS Account](https://cdkworkshop.com/15-prerequisites/200-account.html)
- [Node.js](https://cdkworkshop.com/15-prerequisites/300-nodejs.html)
- [AWS CDK Toolkit](https://cdkworkshop.com/15-prerequisites/500-toolkit.html)
- [Python](https://cdkworkshop.com/15-prerequisites/600-python.html)
- [Docker](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/create-container-image.html#create-container-image-install-docker)

Install required python packages into the virtual environment of your choice with `pip install -r infra/requirements.txt`.


### *AWS Permission Prerequisites*
The minimal IAM permissions needed to bootstrap and deploy the cdk are described in `ReVIEW/infra/minimal-iam-policy.json`. Ensure the customer creates this policy and associates it with your user or role in their environment.

### *Configure the Stack*
Edit the `infra/config.yaml` file to provide a base name for your stack (`stack_name_base`), bucket names, Bedrock model IDs, etc for your application. 

### *Configure Bedrock Model Access*

- Open the target AWS account
- Open AWS Bedrock console and navigate to the region specified in `config.yaml`
- Select "Model Access" in the left sidebar and browse through the list of available LLMs
- Make sure to request and enable access for the model IDs that are specified in  `config.yaml`


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

# 🏛️ Repo Structure
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
- diagram/ - Architecture diagrams of the solution used in READMEs

# 🚪 Frontend Replacement
This application has been designed to make the frontend easily replaceable, as end users may want to replace Streamlit with something more production-grade whilst preserving the backend. Besides the frontend being deployed as a separate stack, it also connects to the backend exclusively through a REST API hosted by API Gateway. 

At a high level, the steps to replace the frontend are:

1. Determine an OAuth provider or other way to authorize the new frontend to access the API Gateway via bearer token. Currently, Cognito is used.
2. Connect the new frontend to the `/s3-presigned` endpoint. This endpoint will generate presigned urls for the frontend to `POST` and `GET` files to and from s3.
3. Connect the new frontend to the three `POST` REST API endpoints: `/llm`, `/ddb`, `/kb` to access large language models, dynamodb, and knowledge bases respectively.
4. Leverage the `FullQAnswer` pydantic model (defined in `frontend/schemas/qa_response.py`) to parse the LLM responses in the chat application. This model includes citations which reference specific timestamps in media files.

If the new frontend is written in Python, it is recommend to re-use the `frontend/components/` which is where most of the REST API calls are made.

# 🔒️ Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

Note: this asset represents a proof-of-value for the services included and is not intended as a production-ready solution. You must determine how the AWS Shared Responsibility applies to their specific use case and implement the needed controls to achieve their desired security outcomes. AWS offers a broad set of security tools and configurations to enable our customers.

The following are some security best practices one should keep in mind when using and further developing this tool:

- **Amazon Cognito**
  - Enable MFA and strict password requirements for users.
  - Consider implementing AdvanceSecurityMode to ENFORCE in Cognito User Pools.
- **Amazon CloudFront:**
  - Use geography-aware rules to block or allow access to CloudFront distributions where required.
  - Use AWS WAF on public CloudFront distributions.
  - Ensure that solution CloudFront distributions use a security policy with minimum TLSv1.1 or TLSv1.2 and appropriate security ciphers for HTTPS viewer connections. Currently, the CloudFront distribution allows for SSLv3 or TLSv1 for HTTPS viewer connections and uses SSLv3 or TLSv1 for communication to the origin.
- **Amazon API Gateway**
  - Activate request validation on API Gateway endpoints to do first-pass input validation.
  - Use AWS WAF on public-facing API Gateway Endpoints.
- **Amazon Bedrock**
  - Enable model invocation logging and set alerts to ensure adherence to any responsible AI policies. Model invocation logging is disabled by default. See https://docs.aws.amazon.com/bedrock/latest/userguide/model-invocation-logging.html
  - Consider enabling Bedrock Guardrails to add baseline protections against analyzing documents or extracting attributes covering certain protected topics.
- **AWS Lambda**:
  - Periodically scan all AWS Lambda container images for vulnerabilities according to lifecycle policies. AWS Inspector can be used for that.
- **Amazon DynamoDB**
  - Use IAM policies for access control, following principle of least privilege.
  - Enable encryption at rest, both server-side and client-side, and encryption in transit (https).
  - Use DynamoDB VPC Endpoints to connect your VPC to DynamoDB without traversing the public internet.
  - Monitor and audit access via CloudTrail logging and/or CloudWatch alarms.
  - Regularly review access keys and IAM roles, and rotate credentials.

# 👥 Authors
<div style="display: flex; align-items: center;">
  <img src="diagram/kaleko_headshot_cropped_resized.png" alt="David Kaleko" width="25%" style="margin-right: 20px;margin-left: 10px">
  <div>
    <a href="https://www.linkedin.com/in/david-kaleko/">David Kaleko</a><br>
    Senior Applied Scientist<br>
    <a href="https://aws.amazon.com/ai/generative-ai/innovation-center/">AWS Generative AI Innovation Center</a>
  </div>
</div>

# 📝 License

This library is licensed under the MIT-0 License. See the LICENSE file.