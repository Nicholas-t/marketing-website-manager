# Storyblok Stories Manager

A simple Streamlit app that lists all stories from your Storyblok space.

## Features

- 📚 View all stories from your Storyblok space
- 🔍 Search stories by name, slug, or content
- 🏷️ Filter by content type
- 📊 Show published vs draft status
- ⚡ Cached data for better performance
- 📱 Responsive design

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Your Storyblok API key is already configured in `.streamlit/secrets.toml`

3. Run the app:
```bash
streamlit run app.py
```

## Configuration

The app uses your Storyblok API key from `.streamlit/secrets.toml`. Make sure it's set correctly:

```toml
STORYBLOK_API_KEY=your_api_key_here
```

## Usage

### Main App
1. Open the app in your browser (usually http://localhost:8501)
2. Select a tool from the sidebar
3. Use authentication if required (production mode)

### Direct URL Access for Sales Post Meeting Notes
You can access the Sales Post Meeting Notes tool directly via URL with HubSpot ID pre-filled:

**URL Format:**
```
https://your-app-url/sales-post-meeting-notes?hs_id=YOUR_HUBSPOT_ID
```

**Example:**
```
https://your-app-url/sales-post-meeting-notes?hs_id=39594287242
```

This will:
- Automatically load the Sales Post Meeting Notes tool
- Pre-fill the HubSpot Company ID field with the provided value
- Show confirmation that the ID was loaded from the URL

### Marketing Tool Usage
1. The app will automatically load all stories from your Storyblok space
2. Use the sidebar filters to narrow down results
3. Use the search box to find specific stories
4. Each story card shows:
   - Story name and slug
   - Content preview
   - Publication status
   - Creation and update dates
   - Content type

## Notes

- Data is cached for 5 minutes to improve performance
- The app fetches published stories by default
- Maximum of 2500 stories will be loaded (100 pages × 25 stories per page)
