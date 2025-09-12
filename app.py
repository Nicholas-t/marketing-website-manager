import streamlit as st
from apps.page_language_grouping_app import page_language_grouping_app
import os

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
username_input = st.sidebar.text_input("Username", value=USERNAME)
password_input = st.sidebar.text_input("Password", value=PASSWORD, type="password")

app_selection = st.sidebar.selectbox(
    "Select Tool",
    ["Page Language Grouping", "Content Management", "Analytics Dashboard", "SEO Tools"]
)

# Main app router
def main():
    if app_selection == "Page Language Grouping":
        page_language_grouping_app(dev_mode=DEV_MODE)

if __name__ == "__main__":
    if ENV == "dev":
        main()
    else:
        if username_input == USERNAME and password_input == PASSWORD:
            main()
        else:
            st.error("Invalid username or password")
