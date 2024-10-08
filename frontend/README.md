Run command:
>> source /home/ubuntu/gitlab/ReVIEW/tmp_dev_env.sh
>> streamlit run /home/ubuntu/gitlab/ReVIEW/frontend/💡_Home.py \
--server.port=8502 --server.address=0.0.0.0 --server.maxUploadSize=1028

Or to run with docker:
>> cd frontend
>> docker build . --tag "sometag" --no-cache
>> docker run -e COGNITO_POOL_ID=$COGNITO_POOL_ID -e COGNITO_CLIENT_ID=$COGNITO_CLIENT_ID -e s3_bucket_name=$s3_bucket_name -e ddb_table_name=$ddb_table_name -e AWS_DEFAULT_REGION=$AWS_DEFAULT_REGION -e KNOWLEDGE_BASE_ID=$KNOWLEDGE_BASE_ID -e llm_model_id=$llm_model_id -e region_name=$region_name -p 8501:8501 sometag

