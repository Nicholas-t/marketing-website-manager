import streamlit as st
from apps.page_language_grouping_app import page_language_grouping_app
import os
from utils.storyblok import fetch_all_stories
from utils.plausible import get_page_visits_custom_date_range
from datetime import datetime, timedelta

if os.path.exists('style.css'):
    with open('style.css', 'r') as f:
        st.markdown("<style>" + f.read() + "</style>", unsafe_allow_html=True)


# Configure Streamlit page
st.set_page_config(
    page_title="Dashdoc Marketing Website Manager",
    page_icon="🚀",
    layout="wide"
)


# Sidebar navigation
st.sidebar.title("🚀 Dashdoc Marketing Website Manager")
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

app_selection = st.sidebar.selectbox(
    "Select Tool",
    ["Page Language Grouping"]
)

# Main app router
def main():
    start_date, end_date = st.date_input("Select date range for analytics", value=(datetime.now() - timedelta(days=30), datetime.now()))
    start_date = start_date.strftime("%Y-%m-%d")
    end_date = end_date.strftime("%Y-%m-%d")
    analytics = get_page_visits_custom_date_range(start_date=start_date, end_date=end_date)
    
    if app_selection == "Page Language Grouping":
        stories = fetch_all_stories(test=DEV_MODE)
        page_language_grouping_app(stories, analytics, dev_mode=DEV_MODE)
if __name__ == "__main__":
    if ENV == "dev":
        main()
    else:
        if username_input == USERNAME and password_input == PASSWORD:
            main()
        else:
            st.error("Invalid username or password")
