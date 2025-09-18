import streamlit as st
import os
from datetime import datetime, timedelta

from utils.storyblok import fetch_all_stories
from utils.plausible import get_page_visits_custom_date_range
from apps.page_language_grouping_app import page_language_grouping_app
from apps.post_sales_notes_app import post_sales_notes_app

if os.path.exists('style.css'):
    with open('style.css', 'r', encoding='utf-8') as f:
        st.markdown("<style>" + f.read() + "</style>", unsafe_allow_html=True)
st.markdown("<meta name='noindex' content='noindex'>", unsafe_allow_html=True)

# Configure Streamlit page
st.set_page_config(
    page_title="Dashdoc Streamlit Internal Tool",
    page_icon="🛠️",
    layout="wide"
)

APPS_LIST = [
    "Marketing - Page Language Grouping",
    "Sales - Post Sales Notes",
]

# Check URL parameters for direct routing
query_params = st.query_params
app_to_open = None
hs_id = None
# Check for direct URL routing - support both page parameter and direct URL paths
if query_params.get("page") == "sales-post-meeting-notes" or "sales-post-meeting-notes" in str(query_params):
    app_to_open = "Sales - Post Sales Notes"
    hs_id = query_params.get("hs_id")
    print(hs_id)
# Reorder APPS_LIST so that app_to_open appears first
if app_to_open and app_to_open in APPS_LIST:
    reordered_apps_list = [app_to_open] + [app for app in APPS_LIST if app != app_to_open]
else:
    reordered_apps_list = APPS_LIST

# Sidebar navigation
st.sidebar.title("🛠️ Dashdoc Streamlit Internal Tool")
with st.sidebar.expander("Settings"):
    DEV_MODE = st.checkbox("Dev Mode", value=False)

USERNAME = st.secrets["USERNAME"]
PASSWORD = st.secrets["PASSWORD"]
ENV = st.secrets["ENV"]

# Authentication form in sidebar
st.sidebar.markdown("---")
st.sidebar.subheader("Authentication")
username_input = st.sidebar.text_input("Username", value="")
password_input = st.sidebar.text_input("Password", value="", type="password")

# App selection - use direct route if available, otherwise show selector
app_selection = st.sidebar.selectbox(
    "Select Tool",
    reordered_apps_list
)

# Main app router
def main():
    if app_selection == "Marketing - Page Language Grouping":
        start_date, end_date = st.date_input("Select date range for analytics", value=(datetime.now() - timedelta(days=30), datetime.now()))
        start_date = start_date.strftime("%Y-%m-%d")
        end_date = end_date.strftime("%Y-%m-%d")
        analytics = get_page_visits_custom_date_range(start_date=start_date, end_date=end_date)
        stories = fetch_all_stories(test=DEV_MODE)
        page_language_grouping_app(stories, analytics, dev_mode=DEV_MODE)
    elif app_selection == "Sales - Post Sales Notes":
        post_sales_notes_app(dev_mode=DEV_MODE, hs_id=hs_id)
if __name__ == "__main__":
    if ENV == "dev":
        main()
    else:
        if username_input == USERNAME and password_input == PASSWORD:
            main()
        else:
            st.error("Invalid username or password")
