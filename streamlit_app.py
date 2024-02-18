import json
import time
import streamlit as st
import requests
from streamlit_cookies_manager import CookieManager

"""
# Welcome to Document Translator!

Ensure you have an Azure AI Translator instance and two Azure Blob containers.
"""

path = 'translator/text/batch/v1.1/batches'

cookie_manager = CookieManager()
if not cookie_manager.ready():
            st.stop()

item_keys = ['azure_trans_endpoint', 
             'azure_trans_key', 
             'azure_trans_region', 
             'source_url', 
             'target_url']

if 'azure_trans_endpoint' in cookie_manager and 'azure_trans_key' in cookie_manager and 'azure_trans_region' in cookie_manager and 'source_url' in cookie_manager and 'target_url' in cookie_manager:
    azure_trans_endpoint = cookie_manager.get('azure_trans_endpoint')
    azure_trans_key = cookie_manager.get('azure_trans_key')
    azure_trans_region = cookie_manager.get('azure_trans_region')
    source_url = cookie_manager.get('source_url')
    target_url = cookie_manager.get('target_url')
    st.text('azure_trans_endpoint: ' + azure_trans_endpoint)
    st.text('azure_trans_key: ' + azure_trans_key)
    st.text('azure_trans_region: ' + azure_trans_region)
    st.text('source_url: ' + source_url)
    st.text('target_url: ' + target_url)
else:
    azure_trans_endpoint = st.text_input('please input azure translation endpoint', key='azure_trans_endpoint')
    azure_trans_key = st.text_input('please input key', max_chars=100, help='copy from azure portal', key = 'azure_trans_key')
    azure_trans_region = st.text_input('please input region', key='azure_trans_region')
    source_url = st.text_input('please input source url', key='source_url')
    target_url = st.text_input('please input target url', key='target_url')

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
                sas_token = target_url.split('?')[1]
                target_path = target_path + '?' + sas_token
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

col5, col6 = st.columns(2)

with col5:
    if st.button('save settings'):
        cookie_manager['azure_trans_endpoint'] = azure_trans_endpoint
        cookie_manager['azure_trans_key'] = azure_trans_key
        cookie_manager['azure_trans_region'] = azure_trans_region
        cookie_manager['source_url'] = source_url
        cookie_manager['target_url'] = target_url
        cookie_manager.save()
        st.rerun()

with col6:
    if st.button('clean settings'):
        value = None
        if 'azure_trans_endpoint' in cookie_manager:
            value = cookie_manager.pop('azure_trans_endpoint')
            value = cookie_manager.pop('azure_trans_key')
            value = cookie_manager.pop('azure_trans_region')
            value = cookie_manager.pop('source_url')
            value = cookie_manager.pop('target_url')
            st.rerun()

class NEW_CM:
    def __init__(self) -> None:
        self.cookie_manager = CookieManager()
        #self.cookie_manager._default_expiry = datetime.now() + timedelta(minutes=1)

        if not self.cookie_manager.ready():
            st.stop()

    def set_cookie(self):
        self.cookie_manager['azure_trans_endpoint'] = azure_trans_endpoint
        self.cookie_manager['azure_trans_key'] = azure_trans_key
        self.cookie_manager['azure_trans_region'] = azure_trans_region
        self.cookie_manager['source_url'] = source_url
        self.cookie_manager['target_url'] = target_url
        self.cookie_manager.save()

    def get_cookie(self):
        azure_trans_endpoint = self.cookie_manager.get('azure_trans_endpoint')
        azure_trans_key = self.cookie_manager.get('azure_trans_key')
        azure_trans_region = self.cookie_manager.get('azure_trans_region')
        source_url = self.cookie_manager.get('source_url')
        target_url = self.cookie_manager.get('target_url')
        constructed_url = azure_trans_endpoint + path
        st.session_state.azure_trans_endpoint = azure_trans_endpoint
        st.session_state.azure_trans_key = azure_trans_key
        st.session_state.azure_trans_region = azure_trans_region
        st.session_state.source_url = source_url
        st.session_state.target_url = target_url

    def delete_cookie(self):
        value = None
        if 'azure_trans_endpoint' in self.cookie_manager:
            value = self.cookie_manager.pop('azure_trans_endpoint')
            value = self.cookie_manager.pop('azure_trans_key')
            value = self.cookie_manager.pop('azure_trans_region')
            value = self.cookie_manager.pop('source_url')
            value = self.cookie_manager.pop('target_url')

#cookie_manager = NEW_CM()

#st.button("Set cookie", on_click=cookie_manager.set_cookie)
#st.button("Get Cookie", on_click=cookie_manager.get_cookie)
#st.button("Delete cookie", on_click=cookie_manager.delete_cookie)