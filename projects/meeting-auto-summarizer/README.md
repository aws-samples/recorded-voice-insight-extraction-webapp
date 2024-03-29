# Meeting Auto Summarizer

[Original blog post](https://aws.amazon.com/blogs/machine-learning/build-a-serverless-meeting-summarization-backend-with-large-language-models-on-amazon-sagemaker-jumpstart/)

[Original code base](https://github.com/aws-samples/serverless-summarization-backend-with-amazon-sagemaker)

What I did: 

1. Download original code base `template.yaml` into `original-cf-template.yaml` locally
2. Convert yaml template into python cdk code (mostly because I want practice with python cdk), via `cdk migrate --from-path "original-cf-template.yaml" --stack-name "MASStack" --language "python"`
`
3. Follow instructions in the `MASStack/` folder it created