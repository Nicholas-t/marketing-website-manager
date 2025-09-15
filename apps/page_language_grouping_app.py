from datetime import timedelta, datetime
import pandas as pd
import streamlit as st
from utils.storyblok import group_pages
from utils.plausible import get_page_visits_custom_date_range
LOCALE_TO_ICON={
    "en": "🇬🇧",
    "en-US": "🇺🇸",
    "fr": "🇫🇷",
    "nl": "🇳🇱",
    "es": "🇪🇸"
}

def format_numeric_columns(df):
    """
    Format numeric columns to display as integers without decimal places
    
    Args:
        df: pandas DataFrame
    
    Returns:
        DataFrame with formatted numeric columns
    """
    df_formatted = df.copy()
    
    # Get all columns that contain visitor or pageview data
    numeric_columns = []
    for col in df.columns:
        if '👤' in col or '🔍' in col or col in ['Total Visitors', 'Total Pageviews']:
            numeric_columns.append(col)
    
    # Convert to int and format to remove decimal places
    for col in numeric_columns:
        if col in df_formatted.columns:
            # Fill NaN values with 0 before converting to int
            df_formatted[col] = df_formatted[col].fillna(0).astype(int)
    
    return df_formatted

def apply_filters(grouped_data, show_published_only, show_draft_only, show_missing_locales, page_name_filter, content_type_filter, locales):
    """
    Apply filters to grouped data with AND logic
    
    Args:
        grouped_data: Dictionary of grouped story data
        show_published_only: Boolean to filter only published pages
        show_draft_only: Boolean to filter only groups with draft pages
        show_missing_locales: Boolean to filter only groups with missing locales
        page_name_filter: String filter for page name
        content_type_filter: String filter for content type
        locales: List of available locales
    
    Returns:
        Filtered dictionary of grouped data
    """
    filtered_data = grouped_data.copy()
    
    # Apply published filter
    if show_published_only:
        filtered_data = {
            group_id: data for group_id, data in filtered_data.items()
            if any(loc_data['published'] for loc_data in data['locales'].values())
        }
    
    # Apply draft filter
    if show_draft_only:
        filtered_data = {
            group_id: data for group_id, data in filtered_data.items()
            if any(not loc_data['published'] for loc_data in data['locales'].values())
        }
    
    # Apply missing locales filter
    if show_missing_locales:
        filtered_data = {
            group_id: data for group_id, data in filtered_data.items()
            if len(data['locales']) < len(locales)
        }
    
    
    # Apply page name filter
    if page_name_filter:
        filtered_data = {
            group_id: data for group_id, data in filtered_data.items()
            if any(
                page_name_filter.lower() in loc_data.get('story_name', '').lower()
                for loc_data in data['locales'].values()
            )
        }
    
    # Apply content type filter
    if content_type_filter:
        filtered_data = {
            group_id: data for group_id, data in filtered_data.items()
            if any(
                data['locales'][locale]['raw'].get('content_type') == content_type_filter
                for locale in data['locales']
            )
        }
    
    return filtered_data

def get_page_name(data, locales):
    """
    Get the best available page name from locales data
    
    Args:
        data: Dictionary containing locales data
        locales: List of available locales in priority order
    
    Returns:
        String representing the page name
    """
    for locale in locales:
        if locale in data['locales']:
            return data['locales'][locale].get('story_name', '')
    return ''

def get_published_locales(data, locales):
    """
    Args:
        data: Dictionary containing locales data
        locales: List of available locales
    """
    return len([locale for locale in locales if locale in data['locales'] and data['locales'][locale]['published']])

def get_draft_locales(data, locales):
    """
    Get the best available draft locales from locales data
    
    Args:
        data: Dictionary containing locales data
        locales: List of available locales
    """
    return len([locale for locale in locales if locale in data['locales'] and not data['locales'][locale]['published']])

def get_content_type(data, locales):
    """
    Get the best available content type from locales data
    
    Args:
        data: Dictionary containing locales data
        locales: List of available locales
    """
    content_types = []
    for locale in locales:
        if locale in data['locales']:
            ct=data['locales'][locale]["raw"].get('content_type', '')
            if ct not in content_types:
                content_types.append(ct)
    return ', '.join(content_types)

def create_table_data(filtered_data, locales, show_anayltics_on_each_locale, show_group_id):
    """
    Create table data from filtered grouped data
    
    Args:
        filtered_data: Filtered dictionary of grouped story data
        locales: List of available locales
    
    Returns:
        List of dictionaries representing table rows
    """
    table_data = []
    for group_id, data in filtered_data.items():
        # Count available locales
        available_locales_count = len(data['locales'])
        row = {}
        if show_group_id:
            row = {'Group ID': group_id}
        row = {
            **row,
            'Page Name': get_page_name(data, locales),
            'Available Locales': available_locales_count,
            'Published locales': get_published_locales(data, locales),
            'Draft locales': get_draft_locales(data, locales),
            'Content Type': get_content_type(data, locales),
        }
        
        total_visitors = 0
        total_pageviews = 0
        # Add locale columns
        for locale in locales:
            if locale in data['locales']:
                locale_data = data['locales'][locale]
                label = "📝"
                if locale_data['published']:
                    label = "🚀"
                row[LOCALE_TO_ICON[locale]] = f"[{label}]({locale_data['link']})"
                # Handle potential NaN/None values in visitor/pageview data
                visitors = locale_data.get('visitors', 0) or 0
                pageviews = locale_data.get('pageviews', 0) or 0
                if show_anayltics_on_each_locale:
                    row[f"{LOCALE_TO_ICON[locale]} 👤"] = int(visitors)
                    row[f"{LOCALE_TO_ICON[locale]} 🔍"] = int(pageviews)
                total_visitors += int(visitors)
                total_pageviews += int(pageviews)
            else:
                row[LOCALE_TO_ICON[locale]] = "❌"
                # Set missing locale visitor/pageview columns to 0
                if show_anayltics_on_each_locale:
                    row[f"{LOCALE_TO_ICON[locale]} 👤"] = 0
                    row[f"{LOCALE_TO_ICON[locale]} 🔍"] = 0
        row['Total Visitors'] = total_visitors
        row['Total Pageviews'] = total_pageviews
        table_data.append(row)
    
    return table_data

def calculate_summary_metrics(grouped_data, locales):
    """
    Calculate summary metrics for the grouped data
    
    Args:
        grouped_data: Dictionary of grouped story data
        locales: List of available locales
    
    Returns:
        Dictionary containing summary metrics
    """
    total_groups = len(grouped_data)
    total_pages = sum(len(data['locales']) for data in grouped_data.values())
    published_pages = sum(
        sum(1 for loc_data in data['locales'].values() if loc_data['published'])
        for data in grouped_data.values()
    )
    total_visitors = sum(data.get('visitors', 0) for data in grouped_data.values())
    total_pageviews = sum(data.get('pageviews', 0) for data in grouped_data.values())
    coverage = (total_pages / (total_groups * len(locales))) * 100 if grouped_data else 0
    
    return {
        'total_groups': total_groups,
        'total_pages': total_pages,
        'published_pages': published_pages,
        'coverage': coverage,
        'total_visitors': total_visitors,
        'total_pageviews': total_pageviews
    }

def display_summary_metrics(metrics):
    """
    Display summary metrics in Streamlit
    
    Args:
        metrics: Dictionary containing summary metrics
    """
    col1, col2, col3 = st.columns(3)
    col4, col5 , col6 = st.columns(3)
    
    with col1:
        st.metric("Total Groups", metrics['total_groups'])
    
    with col2:
        st.metric("Total Pages", metrics['total_pages'])
    
    with col3:
        st.metric("Published Pages", metrics['published_pages'])
    
    with col4:
        st.metric("Coverage", f"{metrics['coverage']:.1f}%")

    with col5:
        st.metric("Total Visitors", metrics['total_visitors'])
    
    with col6:
        st.metric("Total Pageviews", metrics['total_pageviews'])
    
def reset_pagination_if_needed(total_pages):
    """
    Reset pagination to page 1 if current page is out of bounds
    
    Args:
        total_pages: Total number of pages available
    """
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 1
    elif st.session_state.current_page > total_pages:
        st.session_state.current_page = 1

def display_paginated_table(df_sorted, items_per_page):
    """
    Display a paginated table in Streamlit with simple navigation
    
    Args:
        df_sorted: Sorted pandas DataFrame
        items_per_page: Number of items to display per page
    
    Returns:
        DataFrame slice for current page
    """
    # Apply pagination
    total_items = len(df_sorted)
    total_pages = (total_items + items_per_page - 1) // items_per_page
    
    if total_pages <= 1:
        # No pagination needed
        st.info(f"📊 Showing all {total_items} groups")
        # Format numeric columns to display as integers
        df_formatted = format_numeric_columns(df_sorted)
        st.table(df_formatted)
        return df_sorted
    
    # Reset pagination if needed (e.g., after filtering)
    reset_pagination_if_needed(total_pages)
    
    current_page = st.session_state.current_page
    
    # Calculate start and end indices
    start_idx = (current_page - 1) * items_per_page
    end_idx = min(start_idx + items_per_page, total_items)
    
    # Display pagination info
    st.info(f"📊 Showing {start_idx + 1}-{end_idx} of {total_items} groups")
    
    # Pagination controls
    col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])
    
    with col1:
        if st.button("⏮️", disabled=(current_page == 1), key="first_page"):
            st.session_state.current_page = 1
            st.rerun()
    
    with col2:
        if st.button("⬅️", disabled=(current_page == 1), key="prev_page"):
            st.session_state.current_page = current_page - 1
            st.rerun()
    
    with col3:
        st.markdown(f"<div style='text-align: center; padding: 0.5rem;'><strong>Page {current_page} of {total_pages}</strong></div>", 
                   unsafe_allow_html=True)
    
    with col4:
        if st.button("➡️", disabled=(current_page == total_pages), key="next_page"):
            st.session_state.current_page = current_page + 1
            st.rerun()
    
    with col5:
        if st.button("⏭️", disabled=(current_page == total_pages), key="last_page"):
            st.session_state.current_page = total_pages
            st.rerun()
    
    # Get the current page data and display table
    df_page = df_sorted.iloc[start_idx:end_idx]
    # Format numeric columns to display as integers
    df_page_formatted = format_numeric_columns(df_page)
    st.table(df_page_formatted)
    
    return df_page

def by_group_view(stories, analytics):
    # Process stories to group by group_id
    grouped_data = {}
    locales = ['en', 'en-US', 'fr', 'nl', 'es']
    content_types = [""]
    for story in stories:
        group_id = story.get('group_id')
        if group_id:
            if group_id not in grouped_data:
                grouped_data[group_id] = {
                    'group_id': group_id,
                    'locales': {}
                }
            
            # Extract locale from full_slug
            full_slug = story.get('full_slug', '')
            story_id = story.get('id')
            locale = None
            
            for loc in locales:
                if full_slug.startswith(loc + '/') or full_slug == loc:
                    locale = loc
                    break
            
            if locale:
                grouped_data[group_id]['locales'][locale] = {
                    'available': True,
                    'link': f"https://app.storyblok.com/#/me/spaces/171339/stories/0/0/{story_id}",
                    'story_id': story.get('id'),
                    'story_name': story.get('name'),
                    'published': story.get('published', False),
                    "raw": story,
                    "visitors": story.get('visitors', 0),
                    "pageviews": story.get('pageviews', 0),
                    "parent_id": story.get('parent_id')
                }
            if story.get('content_type') not in content_types:
                content_types.append(story.get('content_type'))
    
    # Create DataFrame for display
    if grouped_data:
        # Summary metrics
        st.subheader("📊 Summary")
        metrics = calculate_summary_metrics(grouped_data, locales)
        display_summary_metrics(metrics)
        
        # Filters and controls
        st.subheader("🔧 Filters & Controls")
        
        # Basic filters
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            show_published_only = st.checkbox("Show only published pages", value=False)
            show_draft_only = st.checkbox("Show only those with draft", value=False)
        
        with col2:
            show_group_id = st.checkbox("Show group_id in table", value=False)
            show_anayltics_on_each_locale = st.checkbox("Show analytics on each locale", value=False)
        
        with col3:
            show_missing_locales = st.checkbox("Show only groups with missing locales", value=False)
        
        with col4:
            sort_order = st.selectbox(
                "Sort by Available Locales",
                [
                    "Descending (Most visitors first)",
                    "Ascending (Least visitors first)",
                    "Descending (Most pageviews first)",
                    "Ascending (Least pageviews first)",
                    "Descending (Most locales first)", 
                    "Ascending (Least locales first)",
                    "Descending (Most published locales first)",
                    "Ascending (Least published locales first)",
                    "Descending (Most draft locales first)",
                    "Ascending (Least draft locales first)",
                ],
                index=0
            )
        with col5:
            items_per_page = st.selectbox(
                "Items per page",
                [10, 25, 50, 100],
                index=1
            )
        
        # Column-specific filters
        st.subheader("🔍 Column Filters")
        col1, col2 = st.columns(2)
        
        with col1:
            page_name_filter = st.text_input("Filter by Page Name", placeholder="Enter part of page name...")
        with col2:
            content_type_filter = st.selectbox("Filter by Content Type", content_types, index=0)
        
        # Apply filters using the helper function
        filtered_data = apply_filters(
            grouped_data,
            show_published_only,
            show_draft_only,
            show_missing_locales,
            page_name_filter,
            content_type_filter,
            locales
        )
        
        # Create table data using helper function
        table_data = create_table_data(filtered_data, locales, show_anayltics_on_each_locale, show_group_id)
        # Create and sort DataFrame
        df = pd.DataFrame(table_data)
        column_to_sort = 'Available Locales'
        ascending = False
        if sort_order == "Descending (Most locales first)":
            column_to_sort = 'Available Locales'
            ascending = False
        elif sort_order == "Ascending (Least locales first)":
            column_to_sort = 'Available Locales'
            ascending = True
        if sort_order == "Descending (Most published locales first)":
            column_to_sort = 'Published locales'
            ascending = False
        elif sort_order == "Ascending (Least published locales first)":
            column_to_sort = 'Published locales'
            ascending = True
        elif sort_order == "Descending (Most draft locales first)":
            column_to_sort = 'Draft locales'
            ascending = False
        elif sort_order == "Ascending (Least draft locales first)":
            column_to_sort = 'Draft locales'
            ascending = True
        elif sort_order == "Descending (Most visitors first)":
            column_to_sort = 'Total Visitors'
            ascending = False
        elif sort_order == "Ascending (Least visitors first)":
            column_to_sort = 'Total Visitors'
            ascending = True
        elif sort_order == "Descending (Most pageviews first)":
            column_to_sort = 'Total Pageviews'
            ascending = False
        elif sort_order == "Ascending (Least pageviews first)":
            column_to_sort = 'Total Pageviews'
            ascending = True
            
        if df.shape[0] > 0:
            df_sorted = df.sort_values(column_to_sort, ascending=ascending)
        else:
            df_sorted = df
        
        # Display paginated table
        display_paginated_table(df_sorted, items_per_page)
    else:
        st.warning("🔍 No pages with group_id found in your stories.")

def get_visitor_pageview_data(page, analytics):
    for item in analytics:
        if item.get('page') == page:
            return item.get('visitors'), item.get('pageviews')
    if len(page.split("/")) == 2:
        print(f"No analytics found for {page}")
    return 0, 0

@st.dialog("🔗 Confirm Page Grouping")
def confirm_grouping_dialog(page_ids, page_names):
    """Dialog to confirm page grouping"""
    st.markdown("**Are you sure you want to group these pages?**")
    st.markdown("This action will assign a new group_id to all selected pages.")
    
    st.markdown("**Pages to be grouped:**")
    for name in page_names:
        st.markdown(f"• {name}")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("✅ Yes, Group Pages", type="primary"):
            # Execute grouping
            with st.spinner("🔄 Grouping pages..."):
                new_group_id = group_pages(page_ids)
            
            if new_group_id:
                st.success(f"✅ Pages grouped successfully with group_id: {new_group_id}")
                st.cache_data.clear()
            else:
                st.error("❌ Failed to group pages. Please try again.")
            
            st.rerun()
    
    with col2:
        if st.button("❌ Cancel"):
            st.rerun()

def by_page_view(stories, analytics):
    page_data = []
    content_types = [""]
    for story in stories:
        page_data.append({
            'Group ID': story.get('group_id', ''),
            'Page Name': story.get('name'),
            'Page ID': story.get('id'),
            'Page Link': f"https://app.storyblok.com/#/me/spaces/171339/stories/0/0/{story.get('id')}",
            'Page Published': story.get('published', False),
            'Page Content Type': story.get('content_type', ''),
            'Page Slug': story.get('full_slug', ''),
            'Page Visitors': story.get('visitors', "NA"),
            'Page Pageviews': story.get('pageviews', "NA"),
        })
        if story.get('content_type') not in content_types:
            content_types.append(story.get('content_type'))
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        st.subheader("Group ID")
        group_id_filter_page_level = st.text_input("Filter by Group ID (Page level)", placeholder="Enter part of group ID...")
    with col2:
        st.subheader("Page Name")
        page_name_filter_page_level = st.text_input("Filter by Page Name (Page level)", placeholder="Enter part of page name...")
    with col3:
        st.subheader("Page ID")
        page_id_filter_page_level = st.text_input("Filter by Page ID (Page level)", placeholder="Enter part of page ID...")
    with col4:
        st.subheader("Page Published")
        show_published_only_page_level = st.checkbox("Show only published pages (Page level)", value=False)
    with col5:
        st.subheader("Page Content Type")
        content_type_filter_page_level = st.selectbox("Filter by Content Type (Page level)", content_types, index=0)
    with col6:
        st.subheader("Page Slug")
        page_slug_filter_page_level = st.text_input("Filter by Page Slug (Page level)", placeholder="Enter part of page slug...")

    if group_id_filter_page_level:
        page_data = [page for page in page_data if page.get('Group ID') == group_id_filter_page_level]
    if page_name_filter_page_level:
        page_data = [page for page in page_data if page.get('Page Name') == page_name_filter_page_level]
    if page_id_filter_page_level:
        page_data = [page for page in page_data if page.get('Page ID') == page_id_filter_page_level]
    if show_published_only_page_level:
        page_data = [page for page in page_data if page.get('Page Published')]
    if content_type_filter_page_level:
        page_data = [page for page in page_data if page.get('Page Content Type') == content_type_filter_page_level]
    if page_slug_filter_page_level:
        page_data = [page for page in page_data if page.get('Page Slug') == page_slug_filter_page_level]

    if page_data:
        df = pd.DataFrame(page_data)
        # Format numeric columns to display as integers
        df_formatted = format_numeric_columns(df)
        event = st.dataframe(
            df_formatted, 
            hide_index=True,
            on_select="rerun",
            selection_mode="multi-row"
        )
        if event.selection.get('rows'):
            # Prepare selected pages data
            page_ids = []
            page_names = []
            for i in event.selection.get('rows'):
                page = df.iloc[i]
                page_ids.append(page.get('Page ID'))
                page_names.append(f"[{page.get('Page Name')}](https://dashdoc.com/{page.get('Page Slug')})")
            
            st.markdown(f"**Selected pages for grouping:** {', '.join(page_names)}")
            
            # Button to open confirmation dialog
            if st.button("🚀 Group Selected Pages", type="primary"):
                confirm_grouping_dialog(page_ids, page_names)
    else:
        st.warning("🔍 No pages found in your stories.")

def by_analytics_view(analytics):
    st.subheader("📈 Analytics")
    st.write("Coming soon...")

def page_language_grouping_app(stories, analytics, dev_mode=False):
    """Page Language Grouping Tool"""
    print("Loading Page Language Grouping App...")
    st.header("🌍 Page Language Grouping")
    st.markdown("View and manage pages grouped by language across different locales")
    for story in stories:
        if story.get('full_slug')[-1] == "/":
            story['full_slug'] = story.get('full_slug')[:-1]
        visitors, pageviews = get_visitor_pageview_data("/" + story.get('full_slug'), analytics)
        story['visitors'] = visitors
        story['pageviews'] = pageviews
    if not stories:
        st.warning("⚠️ No stories found or error occurred while fetching.")
        return

    if dev_mode:
        st.json(stories[0])
    
    group_tab, page_tab, analytics_tab = st.tabs(["By Group", "Each page level", "Analytics"])
    with group_tab:
        by_group_view(stories, analytics)
    with page_tab:
        by_page_view(stories, analytics)
    with analytics_tab:
        by_analytics_view(analytics)