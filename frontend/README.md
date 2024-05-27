Run command:

>> streamlit run /home/ubuntu/gitlab/ReVIEW/frontend/💡_Home.py \
--server.port=8502 --server.address=0.0.0.0 --server.maxUploadSize=1028

Or to run with docker:
>> cd frontend
>> docker build . --tag "sometag"
>> docker run -e COGNITO_POOL_ID=$COGNITO_POOL_ID -e COGNITO_CLIENT_ID=$COGNITO_CLIENT_ID -p 8501:8501 sometag
