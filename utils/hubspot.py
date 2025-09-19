import requests
import streamlit as st

def get_hubspot_company_data(hubspot_id):
    url = f"https://api.hubapi.com/companies/v2/companies/{hubspot_id}"
    headers = {
        "Authorization": f"Bearer {st.secrets['HUBSPOT_API_KEY']}"
    }
    response = requests.get(url, headers=headers, timeout=30)
    return response.json()

def send_company_data_to_hubspot(hubspot_id, data):
    url = f"https://api.hubapi.com/companies/v2/companies/{hubspot_id}"
    headers = {
        "Authorization": f"Bearer {st.secrets['HUBSPOT_API_KEY']}"
    }
    response = requests.post(url, headers=headers, json=data, timeout=30)
    return response.json()