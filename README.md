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

1. Open the app in your browser (usually http://localhost:8501)
2. The app will automatically load all stories from your Storyblok space
3. Use the sidebar filters to narrow down results
4. Use the search box to find specific stories
5. Each story card shows:
   - Story name and slug
   - Content preview
   - Publication status
   - Creation and update dates
   - Content type

## Notes

- Data is cached for 5 minutes to improve performance
- The app fetches published stories by default
- Maximum of 2500 stories will be loaded (100 pages × 25 stories per page)
