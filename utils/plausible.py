import requests
import streamlit as st
from typing import List, Dict, Any, Optional


@st.cache_data(ttl=300)
def get_page_visits_custom_date_range(
    site_id: str = "dashdoc.com",
    start_date: str = None,
    end_date: str = None,
    api_key: Optional[str] = None,
    limit: int = 10000,
    page_size: int = 1000
) -> List[Dict[str, Any]]:
    """
    Query Plausible Stats API to get total visits for all pages in a custom date range.
    Automatically handles pagination to retrieve all results up to the specified limit.
    
    Args:
        site_id: The domain of the site on Plausible (default: "dashdoc.com")
        start_date: Start date in ISO8601 format (e.g., "2024-01-01")
        end_date: End date in ISO8601 format (e.g., "2024-01-31")
        api_key: Plausible API key. If None, will try to get from Streamlit secrets
        limit: Maximum number of results to return (default: 10000)
        page_size: Number of results per API request (default: 1000)
    
    Returns:
        List of dictionaries containing page data with visits and pageviews
        
    Raises:
        ValueError: If API key is missing, dates are invalid, or response processing fails
        ConnectionError: If API request fails
    """
    
    # Get API key from Streamlit secrets if not provided
    if api_key is None:
        try:
            api_key = st.secrets["PLAUSIBLE_API_KEY"]
        except KeyError as exc:
            raise ValueError("PLAUSIBLE_API_KEY not found in Streamlit secrets") from exc
    
    if not start_date or not end_date:
        raise ValueError("Both start_date and end_date are required for custom date range")
    
    # Plausible Stats API endpoint
    url = "https://plausible.io/api/v2/query"
    
    # Request headers
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Collect all results across multiple pages
    all_results = []
    offset = 0
    
    try:
        while len(all_results) < limit:
            # Calculate how many results to fetch in this request
            remaining_limit = limit - len(all_results)
            current_page_size = min(page_size, remaining_limit)
            
            # Query payload for custom date range
            query_payload = {
                "site_id": site_id,
                "metrics": ["visitors", "pageviews"],
                "date_range": [start_date, end_date],
                "dimensions": ["event:page"],
                "order_by": [["pageviews", "desc"]],
                "pagination": {
                    "limit": current_page_size,
                    "offset": offset
                }
            }
            
            # Make the API request
            response = requests.post(url, headers=headers, json=query_payload, timeout=30)
            response.raise_for_status()
            
            # Parse the response
            data = response.json()
            
            # Extract results and format them
            page_results = []
            for result in data.get("results", []):
                metrics = result.get("metrics", [])
                dimensions = result.get("dimensions", [])
                
                if len(metrics) >= 2 and len(dimensions) >= 1:
                    page_data = {
                        "page": dimensions[0],  # event:page dimension
                        "visitors": metrics[0],  # visitors metric
                        "pageviews": metrics[1]  # pageviews metric
                    }
                    page_results.append(page_data)
            
            # If no more results, break the loop
            if not page_results:
                break
                
            all_results.extend(page_results)
            
            # If we got fewer results than requested, we've reached the end
            if len(page_results) < current_page_size:
                break
                
            # Move to next page
            offset += current_page_size
        print( "Found", len(all_results), "results")
        return all_results
        
    except requests.exceptions.RequestException as e:
        raise ConnectionError(f"Failed to query Plausible API: {str(e)}") from e
    except (KeyError, IndexError, ValueError) as e:
        raise ValueError(f"Error processing Plausible API response: {str(e)}") from e

