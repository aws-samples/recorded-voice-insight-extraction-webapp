Run command:
>> source /home/ubuntu/gitlab/ReVIEW/tmp_dev_env.sh
>> streamlit run /home/ubuntu/gitlab/ReVIEW/frontend/💡_Home.py \
--server.port=8502 --server.address=0.0.0.0 --server.maxUploadSize=1028

Or to run with docker:
>> cd frontend
>> docker build . --tag "sometag" --no-cache
>> docker run -e AWS_DEFAULT_REGION=$AWS_DEFAULT_REGION -e s3BucketName=$s3BucketName -e DDBTableName=$DDBTableName -e COGNITO_POOL_ID=$COGNITO_POOL_ID -e COGNITO_CLIENT_ID=$COGNITO_CLIENT_ID -p 8501:8501 sometag