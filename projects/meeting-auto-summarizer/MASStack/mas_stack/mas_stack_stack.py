import aws_cdk.aws_iam as iam
import aws_cdk.aws_lambda as aws_lambda
import aws_cdk.aws_logs as logs
import aws_cdk.aws_s3 as s3
from aws_cdk import Stack

# import aws_cdk.aws_sagemaker as sagemaker
from constructs import Construct

"""
  Template for Meeting Notes Generator Demo v1.0.1
"""


class MasStackStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Applying default props
        props = {
            "s3BucketName": kwargs.get("s3BucketName", "meeting-note-generator-demo"),
            "s3RecordingsPrefix": kwargs.get("s3RecordingsPrefix", "recordings"),
            "s3TranscriptsPrefix": kwargs.get("s3TranscriptsPrefix", "transcripts"),
            "s3NotesPrefix": kwargs.get("s3NotesPrefix", "notes"),
            "imageUri": kwargs.get(
                "imageUri",
                "763104351884.dkr.ecr.us-east-1.amazonaws.com/huggingface-pytorch-inference:1.10.2-transformers4.17.0-gpu-py38-cu113-ubuntu20.04",
            ),
            "modelData": kwargs.get(
                "modelData",
                "s3://jumpstart-cache-prod-us-east-1/huggingface-infer/prepack/v1.0.3/infer-prepack-huggingface-text2text-flan-t5-xl.tar.gz",
            ),
            "instanceType": kwargs.get("instanceType", "ml.p3.2xlarge"),
            "instanceCount": kwargs.get("instanceCount", "1"),
            "lambdaLayerName": kwargs.get("lambdaLayerName", "demo-layer"),
        }

        # Resources
        # generateMeetingNotesLogGroup = logs.CfnLogGroup(
        #     self,
        #     "GenerateMeetingNotesLogGroup",
        #     log_group_name=f"""/aws/lambda/{self.stack_name}-GenerateMeetingNotes""",
        # )

        generateMeetingTranscriptLogGroup = logs.CfnLogGroup(
            self,
            "GenerateMeetingTranscriptLogGroup",
            log_group_name=f"""/aws/lambda/{self.stack_name}-GenerateMeetingTranscript""",
        )

        loggingBucket = s3.CfnBucket(
            self,
            "LoggingBucket",
            access_control="LogDeliveryWrite",
            ownership_controls={
                "rules": [
                    {
                        "objectOwnership": "ObjectWriter",
                    },
                ],
            },
            bucket_encryption={
                "serverSideEncryptionConfiguration": [
                    {
                        "serverSideEncryptionByDefault": {
                            "sseAlgorithm": "aws:kms",
                            "kmsMasterKeyId": "alias/aws/s3",
                        },
                    },
                ],
            },
            public_access_block_configuration={
                "ignorePublicAcls": True,
                "restrictPublicBuckets": True,
                "blockPublicAcls": True,
                "blockPublicPolicy": True,
            },
        )

        # sageMakerExecutionRole = iam.CfnRole(self, 'SageMakerExecutionRole',
        #       role_name = f"""sagemaker-soln-mng-{self.stack_name}-SageMakerExecutionRole""",
        #       assume_role_policy_document = {
        #         'Version': '2012-10-17',
        #         'Statement': [
        #           {
        #             'Effect': 'Allow',
        #             'Principal': {
        #               'Service': [
        #                 'sagemaker.amazonaws.com',
        #               ],
        #             },
        #             'Action': [
        #               'sts:AssumeRole',
        #             ],
        #           },
        #         ],
        #       },
        #       managed_policy_arns = [
        #         'arn:aws:iam::aws:policy/AmazonSageMakerFullAccess',
        #       ],
        #     )

        # generateMeetingNotesLambdaRole = iam.CfnRole(
        #     self,
        #     "GenerateMeetingNotesLambdaRole",
        #     role_name=f"""{self.stack_name}-GenerateMeetingNotesLambdaRole""",
        #     assume_role_policy_document={
        #         "Version": "2012-10-17",
        #         "Statement": [
        #             {
        #                 "Effect": "Allow",
        #                 "Principal": {
        #                     "Service": [
        #                         "lambda.amazonaws.com",
        #                     ],
        #                 },
        #                 "Action": [
        #                     "sts:AssumeRole",
        #                 ],
        #             },
        #         ],
        #     },
        #     policies=[
        #         {
        #             "policyName": "CreateLogGroupPolicy",
        #             "policyDocument": {
        #                 "Statement": [
        #                     {
        #                         "Effect": "Allow",
        #                         "Action": [
        #                             "logs:CreateLogGroup",
        #                         ],
        #                         "Resource": f"""arn:aws:logs:{self.region}:{self.account}:*""",
        #                     },
        #                 ],
        #             },
        #         },
        #         {
        #             "policyName": "LogsPolicy",
        #             "policyDocument": {
        #                 "Statement": [
        #                     {
        #                         "Effect": "Allow",
        #                         "Action": [
        #                             "logs:CreateLogStream",
        #                             "logs:PutLogEvents",
        #                         ],
        #                         "Resource": generateMeetingNotesLogGroup.attr_arn,
        #                     },
        #                 ],
        #             },
        #         },
        #         {
        #           'policyName': 'SageMakerInvokeEndpointPolicy',
        #           'policyDocument': {
        #             'Statement': [
        #               {
        #                 'Effect': 'Allow',
        #                 'Action': [
        #                   'sagemaker:DescribeEndpointConfig',
        #                   'sagemaker:InvokeEndpointAsync',
        #                   'sagemaker:DescribeEndpoint',
        #                   'sagemaker:InvokeEndpoint',
        #                 ],
        #                 'Resource': [
        #                   f"""arn:aws:sagemaker:{self.region}:{self.account}:endpoint/*""",
        #                   f"""arn:aws:sagemaker:{self.region}:{self.account}:endpoint-config/*""",
        #                 ],
        #               },
        #             ],
        #           },
        #         },
        #         {
        #             "policyName": "S3BucketTranscriptsReadAccess",
        #             "policyDocument": {
        #                 "Statement": [
        #                     {
        #                         "Effect": "Allow",
        #                         "Action": [
        #                             "s3:GetObject",
        #                         ],
        #                         "Resource": f"""arn:aws:s3:::{props['s3BucketName']}-bucket-{self.account}/{props['s3TranscriptsPrefix']}/*""",
        #                     },
        #                 ],
        #             },
        #         },
        #         {
        #             "policyName": "S3BucketNotesWriteAccess",
        #             "policyDocument": {
        #                 "Statement": [
        #                     {
        #                         "Effect": "Allow",
        #                         "Action": [
        #                             "s3:PutObject",
        #                         ],
        #                         "Resource": f"""arn:aws:s3:::{props['s3BucketName']}-bucket-{self.account}/{props['s3NotesPrefix']}/*""",
        #                     },
        #                 ],
        #             },
        #         },
        #     ],
        # )

        generateMeetingTranscriptLambdaRole = iam.CfnRole(
            self,
            "GenerateMeetingTranscriptLambdaRole",
            role_name=f"""{self.stack_name}-GenerateMeetingTranscriptLambdaRole""",
            assume_role_policy_document={
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {
                            "Service": [
                                "lambda.amazonaws.com",
                            ],
                        },
                        "Action": [
                            "sts:AssumeRole",
                        ],
                    },
                ],
            },
            policies=[
                {
                    "policyName": "CreateLogGroupPolicy",
                    "policyDocument": {
                        "Statement": [
                            {
                                "Effect": "Allow",
                                "Action": [
                                    "logs:CreateLogGroup",
                                ],
                                "Resource": f"""arn:aws:logs:{self.region}:{self.account}:*""",
                            },
                        ],
                    },
                },
                {
                    "policyName": "LogsPolicy",
                    "policyDocument": {
                        "Statement": [
                            {
                                "Effect": "Allow",
                                "Action": [
                                    "logs:CreateLogStream",
                                    "logs:PutLogEvents",
                                ],
                                "Resource": generateMeetingTranscriptLogGroup.attr_arn,
                            },
                        ],
                    },
                },
                {
                    "policyName": "S3BucketRecordingsReadAccess",
                    "policyDocument": {
                        "Statement": [
                            {
                                "Effect": "Allow",
                                "Action": [
                                    "s3:GetObject",
                                ],
                                "Resource": f"""arn:aws:s3:::{props['s3BucketName']}-bucket-{self.account}/{props['s3RecordingsPrefix']}/*""",
                            },
                        ],
                    },
                },
                {
                    "policyName": "S3BucketTranscriptsWriteAccess",
                    "policyDocument": {
                        "Statement": [
                            {
                                "Effect": "Allow",
                                "Action": [
                                    "s3:PutObject",
                                ],
                                "Resource": f"""arn:aws:s3:::{props['s3BucketName']}-bucket-{self.account}/{props['s3TranscriptsPrefix']}/*""",
                            },
                        ],
                    },
                },
            ],
            managed_policy_arns=[
                "arn:aws:iam::aws:policy/AmazonTranscribeFullAccess",
            ],
        )

        # sageMakerModel = sagemaker.CfnModel(
        #     self,
        #     "SageMakerModel",
        #     model_name=f"""sagemaker-soln-mng-{self.stack_name}-SageMakerModel""",
        #     containers=[
        #         {
        #             "image": props["imageUri"],
        #             "modelDataUrl": props["modelData"],
        #             "mode": "SingleModel",
        #             "environment": {
        #                 "MODEL_CACHE_ROOT": "/opt/ml/model",
        #                 "SAGEMAKER_ENV": "1",
        #                 "SAGEMAKER_MODEL_SERVER_TIMEOUT": "3600",
        #                 "SAGEMAKER_MODEL_SERVER_WORKERS": "1",
        #                 "SAGEMAKER_PROGRAM": "inference.py",
        #                 "SAGEMAKER_SUBMIT_DIRECTORY": "/opt/ml/model/code/",
        #                 "TS_DEFAULT_WORKERS_PER_MODEL": 1,
        #             },
        #         },
        #     ],
        #     enable_network_isolation=True,
        #     execution_role_arn=sageMakerExecutionRole.attr_arn,
        # )

        generateMeetingTranscript = aws_lambda.CfnFunction(
            self,
            "GenerateMeetingTranscript",
            description=f"""Stack {self.stack_name} Function GenerateMeetingTranscript""",
            function_name=f"""{self.stack_name}-GenerateMeetingTranscript""",
            handler="index.lambda_handler",
            runtime="python3.9",
            memory_size=128,
            timeout=15,
            code={
                "zipFile": "import json\nimport boto3\nimport os\nimport time\n\nS3_BUCKET = os.environ.get('S3_BUCKET')\nSOURCE_PREFIX = os.environ.get('SOURCE_PREFIX')\nDESTINATION_PREFIX = os.environ.get('DESTINATION_PREFIX')\n\ntranscribe_client = boto3.client('transcribe')\n\ndef lambda_handler(event, context):\n    # Transcribe meeting recording to text\n    recording_name = event['Records'][0]['s3']['object']['key']\n    job_tokens = recording_name.split('/')[1].split('.')\n\n    job_name = '{}_{}'.format(job_tokens[0], int(time.time()))\n    media_format = job_tokens[1]\n    media_uri = 's3://{}/{}'.format(S3_BUCKET, recording_name)\n    output_key = '{}/{}.txt'.format(DESTINATION_PREFIX, job_name)\n\n    try:\n        job_args = {\n            'TranscriptionJobName': job_name,\n            'Media': {'MediaFileUri': media_uri},\n            'MediaFormat': media_format,\n            'IdentifyLanguage': True,\n            'OutputBucketName':S3_BUCKET,\n            'OutputKey':output_key\n        }\n        response = transcribe_client.start_transcription_job(**job_args)\n        job = response['TranscriptionJob']\n        print(\"Started transcription job {}.\".format(job_name))\n    except Exception:\n        print(\"Couldn't start transcription job %s.\".format(job_name))\n        raise\n\n    return {\n        'statusCode': 200,\n        'body': json.dumps('Started transcription job {}'.format(job_name))\n    }\n",
            },
            environment={
                "variables": {
                    "DESTINATION_PREFIX": props["s3TranscriptsPrefix"],
                    "S3_BUCKET": f"""{props['s3BucketName']}-bucket-{self.account}""",
                    "SOURCE_PREFIX": props["s3RecordingsPrefix"],
                },
            },
            role=generateMeetingTranscriptLambdaRole.attr_arn,
        )

        # sageMakerEndpointConfig = sagemaker.CfnEndpointConfig(
        #     self,
        #     "SageMakerEndpointConfig",
        #     endpoint_config_name=f"""sagemaker-soln-mng-{self.stack_name}-SageMakerEndpointConfig""",
        #     production_variants=[
        #         {
        #             "modelName": sageMakerModel.attr_model_name,
        #             "variantName": f"""{sageMakerModel.attr_model_name}-1""",
        #             "initialInstanceCount": props["instanceCount"],
        #             "instanceType": props["instanceType"],
        #             "initialVariantWeight": 1,
        #             "volumeSizeInGb": 40,
        #         },
        #     ],
        # )

        generateMeetingTranscriptInvokePermission = aws_lambda.CfnPermission(
            self,
            "GenerateMeetingTranscriptInvokePermission",
            function_name=generateMeetingTranscript.attr_arn,
            action="lambda:InvokeFunction",
            principal="s3.amazonaws.com",
            source_arn=f"""arn:aws:s3:::{props['s3BucketName']}-bucket-{self.account}""",
            source_account=self.account,
        )

        # sageMakerEndpoint = sagemaker.CfnEndpoint(
        #     self,
        #     "SageMakerEndpoint",
        #     endpoint_name=f"""sagemaker-soln-mng-{self.stack_name}-SageMakerEndpoint""",
        #     endpoint_config_name=sageMakerEndpointConfig.attr_endpoint_config_name,
        # )

        # generateMeetingNotes = aws_lambda.CfnFunction(
        #     self,
        #     "GenerateMeetingNotes",
        #     description=f"""Stack {self.stack_name} Function GenerateMeetingNotes""",
        #     function_name=f"""{self.stack_name}-GenerateMeetingNotes""",
        #     handler="index.lambda_handler",
        #     runtime="python3.9",
        #     memory_size=128,
        #     timeout=180,
        #     code={
        #         "zipFile": "import json\nimport boto3\nimport os\nimport math\n\nimport nltk\nfrom nltk.tokenize import word_tokenize\nfrom nltk.tokenize.treebank import TreebankWordDetokenizer\n\nnltk.data.path.append(\"/tmp\")\nnltk.download(\"punkt\", download_dir=\"/tmp\")\n\nS3_BUCKET = os.environ.get('S3_BUCKET')\nSOURCE_PREFIX = os.environ.get('SOURCE_PREFIX')\nDESTINATION_PREFIX = os.environ.get('DESTINATION_PREFIX')\nENDPOINT_NAME = os.environ.get('SAGEMAKER_ENDPOINT_NAME')\n\nCHUNK_LENGTH = 400\n\ns3_client = boto3.client('s3')\n\n\ndef lambda_handler(event, context):\n    print(event)\n\n    # Load transcript\n    transcript_key = event['Records'][0]['s3']['object']['key']\n    tokens = transcript_key.split('/')[1].split('.')\n\n    transcript_name = tokens[0]\n    file_format = tokens[1]\n    source_uri = 's3://{}/{}'.format(S3_BUCKET, transcript_key)\n    output_key = '{}/{}.txt'.format(DESTINATION_PREFIX, transcript_name)\n\n    s3_client.download_file(Bucket=S3_BUCKET, Key=transcript_key, Filename='/tmp/transcript.txt')\n    with open('/tmp/transcript.txt') as f:\n        contents = json.load(f)\n\n    # Chunk transcript into chunks\n    transcript = contents['results']['transcripts'][0]['transcript']\n    transcript_tokens = word_tokenize(transcript)\n\n    num_chunks = int(math.ceil(len(transcript_tokens) / CHUNK_LENGTH))\n    transcript_chunks = []\n    for i in range(num_chunks):\n        if i == num_chunks - 1:\n            chunk = TreebankWordDetokenizer().detokenize(transcript_tokens[CHUNK_LENGTH * i:])\n        else:\n            chunk = TreebankWordDetokenizer().detokenize(transcript_tokens[CHUNK_LENGTH * i:CHUNK_LENGTH * (i + 1)])\n        transcript_chunks.append(chunk)\n\n    print('Transcript broken into {} chunks of {} tokens.'.format(len(transcript_chunks), CHUNK_LENGTH))\n\n\n    # Invoke endpoint with transcript and instructions\n    instruction = 'Summarize the context above.'\n\n    try:\n        # Summarize each chunk\n        chunk_summaries = []\n        for i in range(len(transcript_chunks)):\n            text_input = '{}\\n{}'.format(transcript_chunks[i], instruction)\n\n            payload = {\n                \"text_inputs\": text_input,\n                \"max_length\": 100,\n                \"num_return_sequences\": 1,\n                \"top_k\": 50,\n                \"top_p\": 0.95,\n                \"do_sample\": True\n            }\n            query_response = query_endpoint_with_json_payload(json.dumps(payload).encode('utf-8'))\n            generated_texts = parse_response_multiple_texts(query_response)\n            chunk_summaries.append(generated_texts[0])\n\n        # Create a combined summary\n        text_input = '{}\\n{}'.format(' '.join(chunk_summaries), instruction)\n        payload = {\n            \"text_inputs\": text_input,\n            \"max_length\": 100,\n            \"num_return_sequences\": 1,\n            \"top_k\": 50,\n            \"top_p\": 0.95,\n            \"do_sample\": True\n        }\n        query_response = query_endpoint_with_json_payload(json.dumps(payload).encode('utf-8'))\n        generated_texts = parse_response_multiple_texts(query_response)\n\n        results = {\n            \"summary\": generated_texts,\n            \"chunk_summaries\": chunk_summaries\n        }\n\n    except Exception as e:\n        print('Error generating text')\n        print(e)\n        raise\n\n    # Save response to S3\n    with open('/tmp/output.txt', 'w') as f:\n        json.dump(results, f)\n\n    s3_client.put_object(Bucket=S3_BUCKET, Key='{}/{}.txt'.format(DESTINATION_PREFIX, transcript_name), Body=open('/tmp/output.txt', 'rb'))\n\n    # Return response\n    return {\n        'statusCode': 200,\n        'body': {\n            'message': json.dumps('Completed summary job {}'.format(transcript_name)),\n            'results': results\n        }\n    }\n\ndef query_endpoint(encoded_text):\n    client = boto3.client('runtime.sagemaker')\n    response = client.invoke_endpoint(EndpointName=ENDPOINT_NAME, ContentType='application/x-text', Body=encoded_text)\n    return response\n\ndef parse_response(query_response):\n    model_predictions = json.loads(query_response['Body'].read())\n    generated_text = model_predictions['generated_text']\n    return generated_text\n\ndef query_endpoint_with_json_payload(encoded_json):\n    client = boto3.client('runtime.sagemaker')\n    response = client.invoke_endpoint(EndpointName=ENDPOINT_NAME, ContentType='application/json', Body=encoded_json)\n    return response\n\ndef parse_response_multiple_texts(query_response):\n    model_predictions = json.loads(query_response['Body'].read())\n    generated_text = model_predictions['generated_texts']\n    return generated_text\n",
        #     },
        #     environment={
        #         "variables": {
        #             "DESTINATION_PREFIX": props["s3NotesPrefix"],
        #             "S3_BUCKET": f"""{props['s3BucketName']}-bucket-{self.account}""",
        #             "SAGEMAKER_ENDPOINT_NAME": sageMakerEndpoint.attr_endpoint_name,
        #             "SOURCE_PREFIX": props["s3TranscriptsPrefix"],
        #         },
        #     },
        #     layers=[
        #         f"""arn:aws:lambda:{self.region}:{self.account}:layer:{props['lambdaLayerName']}:1""",
        #     ],
        #     role=generateMeetingNotesLambdaRole.attr_arn,
        # )

        bucket = s3.CfnBucket(
            self,
            "Bucket",
            bucket_name=f"""{props['s3BucketName']}-bucket-{self.account}""",
            bucket_encryption={
                "serverSideEncryptionConfiguration": [
                    {
                        "serverSideEncryptionByDefault": {
                            "sseAlgorithm": "aws:kms",
                            "kmsMasterKeyId": "alias/aws/s3",
                        },
                    },
                ],
            },
            public_access_block_configuration={
                "ignorePublicAcls": True,
                "restrictPublicBuckets": True,
                "blockPublicAcls": True,
                "blockPublicPolicy": True,
            },
            notification_configuration={
                "lambdaConfigurations": [
                    {
                        "event": "s3:ObjectCreated:*",
                        "filter": {
                            "s3Key": {
                                "rules": [
                                    {
                                        "name": "prefix",
                                        "value": f"""{props['s3RecordingsPrefix']}/""",
                                    },
                                ],
                            },
                        },
                        "function": generateMeetingTranscript.attr_arn,
                    },
                    # {
                    #     "event": "s3:ObjectCreated:*",
                    #     "filter": {
                    #         "s3Key": {
                    #             "rules": [
                    #                 {
                    #                     "name": "prefix",
                    #                     "value": f"""{props['s3TranscriptsPrefix']}/""",
                    #                 },
                    #             ],
                    #         },
                    #     },
                    #     "function": generateMeetingNotes.attr_arn,
                    # },
                ],
            },
            logging_configuration={
                "destinationBucketName": loggingBucket.ref,
                "logFilePrefix": "logs",
            },
        )

        # generateMeetingNotesInvokePermission = aws_lambda.CfnPermission(
        #     self,
        #     "GenerateMeetingNotesInvokePermission",
        #     function_name=generateMeetingNotes.attr_arn,
        #     action="lambda:InvokeFunction",
        #     principal="s3.amazonaws.com",
        #     source_arn=f"""arn:aws:s3:::{props['s3BucketName']}-bucket-{self.account}""",
        #     source_account=self.account,
        # )

        bucketPolicy = s3.CfnBucketPolicy(
            self,
            "BucketPolicy",
            bucket=bucket.ref,
            policy_document={
                "Id": "RequireEncryptionInTransit",
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Principal": "*",
                        "Action": "*",
                        "Effect": "Deny",
                        "Resource": [
                            bucket.attr_arn,
                            f"""{bucket.attr_arn}/*""",
                        ],
                        "Condition": {
                            "Bool": {
                                "aws:SecureTransport": "false",
                            },
                        },
                    },
                ],
            },
        )
