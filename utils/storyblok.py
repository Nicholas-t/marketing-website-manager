import streamlit as st
import requests
import uuid
# Get API key from secrets
try:
    api_key = st.secrets["STORYBLOK_API_KEY"]
    cdn_api_key = st.secrets["STORYBLOK_CDN_API_KEY"]
    STORYBLOK_SPACE_ID = st.secrets["STORYBLOK_SPACE_ID"]
except KeyError:
    st.error("❌ Storyblok API key not found in secrets. Please add it to .streamlit/secrets.toml")
    st.stop()


# Storyblok API configuration
STORYBLOK_API_BASE = f"https://mapi.storyblok.com/v1/spaces/{STORYBLOK_SPACE_ID}/stories/"
STORYBLOK_API_BASE_CDN = "https://api.storyblok.com/v2/cdn/stories/"
HEADERS = {
    "Authorization": api_key,
    "Content-Type": "application/json"
}

@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_all_stories(test=False):
    """Fetch all stories from Storyblok"""
    all_stories = []
    page = 1
    per_page = 100
    
    with st.spinner("🔄 Loading stories from Storyblok..."):
        while True:
            try:
                # Fetch stories with pagination
                params = {
                    "per_page": per_page,
                    "page": page,
                    "story_only": True
                }
                
                
                response = requests.get(STORYBLOK_API_BASE, params=params, headers=HEADERS, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                stories = data.get("stories", [])
                
                if not stories:
                    break
                    
                all_stories.extend(stories)
                page += 1
                
                if page > 100 or test: 
                    break
                
            except requests.exceptions.RequestException as e:
                st.error(f"❌ Error fetching stories: {str(e)}")
                return []
            except (ValueError, KeyError) as e:
                st.error(f"❌ Error parsing response: {str(e)}")
                return []
    
    return all_stories

@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_all_stories_cdn(test=False):
    """Fetch all stories from Storyblok CDN"""
    all_stories = []
    page = 1
    per_page = 100
    with st.spinner("🔄 Loading stories from Storyblok CDN..."):
        while True:
            try:
                params = {
                    "per_page": per_page,
                    "page": page,
                    "token": cdn_api_key
                }
                response = requests.get(STORYBLOK_API_BASE_CDN, params=params, headers=HEADERS, timeout=30)
                response.raise_for_status()
                data = response.json()
                stories = data.get("stories", [])
                if not stories:
                    break
                all_stories.extend(stories)
                page += 1
                if page > 100 or test:
                    break
            except requests.exceptions.RequestException as e:
                st.error(f"❌ Error fetching stories: {str(e)}")
                return []
    return all_stories

def change_page_group_id(page_id, group_id):
    """Change the group_id of a page"""
    try:
        # First, get the current story data
        get_url = f"{STORYBLOK_API_BASE}{page_id}"
        response = requests.get(get_url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        
        story_data = response.json().get('story', {})
        
        # Update the group_id in the story data
        story_data['group_id'] = str(group_id)
        
        # Update the story via PUT request
        put_url = f"{STORYBLOK_API_BASE}{page_id}"
        update_response = requests.put(put_url, headers=HEADERS, json={'story': story_data}, timeout=30)
        update_response.raise_for_status()
        
        return True
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Error updating page {page_id}: {str(e)}")
        return False
    except (ValueError, KeyError) as e:
        st.error(f"❌ Error parsing response for page {page_id}: {str(e)}")
        return False

def group_pages(page_ids):
    """Group pages by their group_id"""
    if not page_ids:
        st.error("❌ No page IDs provided for grouping")
        return None
        
    group_id = str(uuid.uuid4())
    st.write(f"🔄 Grouping {len(page_ids)} pages with group_id: {group_id}")
    
    success_count = 0
    failed_pages = []
    
    for page_id in page_ids:
        st.write(f"📝 Updating page_id: {page_id}...")
        if change_page_group_id(page_id, group_id):
            success_count += 1
        else:
            failed_pages.append(page_id)
    
    if success_count == len(page_ids):
        st.success(f"✅ Successfully grouped all {success_count} pages!")
        return group_id
    elif success_count > 0:
        st.warning(f"⚠️ Successfully grouped {success_count} out of {len(page_ids)} pages.")
        if failed_pages:
            st.error(f"❌ Failed to group pages: {', '.join(map(str, failed_pages))}")
        return group_id
    else:
        st.error("❌ Failed to group any pages. Please check the page IDs and try again.")
        return None