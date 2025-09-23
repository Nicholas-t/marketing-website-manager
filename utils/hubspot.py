import requests
import streamlit as st

def get_hubspot_company_data(hubspot_id):
    url = f"https://api.hubapi.com/crm/v3/objects/companies/{hubspot_id}"
    headers = {
        "Authorization": f"Bearer {st.secrets['HUBSPOT_API_KEY']}"
    }
    response = requests.get(url, headers=headers, timeout=30)
    return response.json()

def _sanitize_data(data):
    """Sanitize data by converting empty values to None"""
    sanitized = {}
    for key, value in data.items():
        if not value:
            sanitized[key] = None
        else:
            sanitized[key] = value
    return sanitized

def send_company_data_to_hubspot(hubspot_id, data):
    print(f"📝 Sending company data to HubSpot: {data}")
    url = f"https://api.hubapi.com/crm/v3/objects/companies/{hubspot_id}"
    headers = {
        "Authorization": f"Bearer {st.secrets['HUBSPOT_API_KEY']}",
        "Content-Type": "application/json"
    }
    try:
        # HubSpot v3 API expects properties to be wrapped in a "properties" object
        payload = {"properties": _sanitize_data(data)}
        response = requests.patch(url, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"HubSpot API error: {response.status_code} - {response.text}")
    except Exception as e:
        raise Exception(f"Error in send_company_data_to_hubspot: {str(e)}")

def create_contact_in_hubspot(data):
    print(f"📝 Creating contact in HubSpot: {data}")
    url = f"https://api.hubapi.com/crm/v3/objects/contacts"
    headers = {
        "Authorization": f"Bearer {st.secrets['HUBSPOT_API_KEY']}",
        "Content-Type": "application/json"
    }
    try:
        # HubSpot v3 API expects properties to be wrapped in a "properties" object
        payload = {"properties": _sanitize_data(data)}
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 201:  # Created
            return response.json()
        else:
            raise Exception(f"HubSpot API error: {response.status_code} - {response.text}")
    except Exception as e:
        raise Exception(f"Error in create_contact_in_hubspot: {str(e)}")

def associate_contact_to_company(contact_id, company_id):
    print(f"📝 Associating contact to company in HubSpot: {contact_id} to {company_id}")
    url = f"https://api.hubapi.com/crm/v4/objects/contacts/{contact_id}/associations/companies/{company_id}"
    headers = {
        "Authorization": f"Bearer {st.secrets['HUBSPOT_API_KEY']}",
        "Content-Type": "application/json"
    }
    try:
        # HubSpot v4 API requires a request body with association type
        request_body = [
            {
                "associationCategory": "HUBSPOT_DEFINED",
                "associationTypeId": 1
            }
        ]
        response = requests.put(url, headers=headers, json=request_body, timeout=30)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"HubSpot API error: {response.status_code} - {response.text}")
    except Exception as e:
        raise Exception(f"Error in associate_contact_to_company: {str(e)}")

def get_tms_list_for_field():
    url = f"https://api.hubapi.com/crm/v3/properties/companies/tms"
    headers = {
        "Authorization": f"Bearer {st.secrets['HUBSPOT_API_KEY']}"
    }
    try:
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            if "options" in data and data["options"]:
                return [option["value"] for option in data["options"]]
            else:
                print(f"⚠️ No options found in TMS field response: {data}")
                return []
        else:
            raise Exception(f"HubSpot API error: {response.status_code} - {response.text}")
    except Exception as e:
        raise Exception(f"Error in get_tms_list_for_field: {str(e)}")
