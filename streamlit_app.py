import datetime
import json
import time
import streamlit as st
import requests
from pprint import pprint

"""
# Welcome to Document Translator!

Ensure you have an Azure AI Translator instance and two Azure Blob containers.
"""

azure_trans_endpoint = st.text_input('please input azure translation endpoint')
azure_trans_key = st.text_input('please input key', max_chars=100, help='copy from azure portal')
azure_trans_region = st.text_input('please input region')
source_url = st.text_input('please input source url')
target_url = st.text_input('please input target url')

path = 'translator/text/batch/v1.1/batches'
constructed_url = azure_trans_endpoint + path


col1, col2 = st.columns(2)

with col1:
    uploaded_file = st.file_uploader('choose a file to upload')
    if uploaded_file is not None:
        file_path, sas_token = source_url.split('?')
        source_path_with_sas = file_path + '/' + uploaded_file.name + '?' + sas_token
        bytes_data = uploaded_file.getvalue()
        headers = {
            'x-ms-blob-type': 'BlockBlob',
            'x-ms-version': '2015-02-21'
            #'Authorization': sas_token
            #'x-ms-date': datetime.datetime.utcnow()
        }
        response = requests.put(source_path_with_sas, bytes_data, headers=headers)
        st.success(f'response status code: {response.status_code}\nresponse status: {response.reason}\n')

with col2:
    if st.button('translate'):
        headers = {
            'Ocp-Apim-Subscription-Key': azure_trans_key,
            'Ocp-Apim-Subscription-Region': azure_trans_region,
            'Content-Type': 'application/json',
        }
        body= {
            "inputs": [
                {
                    "source": {
                        "sourceUrl": source_url,
                        "storageSource": "AzureBlob",
                        "language": "en"
                    },
                    "targets": [
                        {
                            "targetUrl": target_url,
                            "storageSource": "AzureBlob",
                            "category": "general",
                            "language": "zh-Hans"
                        }
                    ]
                }
            ]
        }
        response = requests.post(constructed_url, headers=headers, json=body)
        response_headers = response.headers
        if response.status_code != 202:
            st.error(response.reason)
        else:
            st.info(f'response status code: {response.status_code}\nresponse status: {response.reason}\n')
            callback_url = response_headers['Operation-Location']
            st.info(callback_url)

            move_to_download = False

            with st.spinner('loading'):
                for i in range(1000):
                    response = requests.get(callback_url, headers=headers)
                    response_body = response.json()

                    if response_body['status'] == 'Succeeded':
                        st.success('successful')
                        st.success(json.dumps(response_body['summary']))
                        move_to_download = True
                        break
                    elif response_body['status'] == 'Failed':
                        st.error('Failed')
                        st.error(json.dumps(response_body['error']))
                        break
                    elif response_body['status'] == 'ValidationFailed':
                        st.error('ValidationFailed')
                        st.error(json.dumps(response_body['error']))
                        break
                    else:
                        time.sleep(1)

            if move_to_download == True:
                documents_result = callback_url + '/documents'
                response = requests.get(documents_result, headers=headers)
                response_body = response.json()
                target_path = response_body['value'][0]['path']
                source_path = response_body['value'][0]['sourcePath']
                st.session_state.target_path = target_path
                st.session_state.source_path = source_path
                st.success(target_path)

col3, col4 = st.columns(2)

with col3:
    if st.button('remove target'):
        if st.session_state.target_path != '':
            sas_token = target_url.split('?')[1]
            target_path_with_sas = st.session_state.target_path + '?' + sas_token
            response = requests.delete(target_path_with_sas)
            st.success(f'response status code: {response.status_code}\nresponse status: {response.reason}\n')
            st.session_state.target_path = ''
        else:
            st.info('target path is empty')

with col4:
    if st.button('remove source'):
        if st.session_state.source_path != '':
            sas_token = source_url.split('?')[1]
            source_path_with_sas = st.session_state.source_path + '?' + sas_token
            response = requests.delete(source_path_with_sas)
            st.success(f'response status code: {response.status_code}\nresponse status: {response.reason}\n')
            st.session_state.source_path = ''
        else:
            st.info('source path is empty')