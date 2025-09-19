import streamlit as st
import os
import tempfile
import json
import hashlib
from openai import OpenAI
from utils.hubspot import get_hubspot_company_data, send_company_data_to_hubspot
# Initialize OpenAI client
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])



# OpenAI Structured Output JSON Schema for sales data extraction
SALES_DATA_SCHEMA = {
    "name": "sales_notes_extraction",
    "schema": {
        "type": "object",
        "properties": {
            "company_org_key_people": {
                "type": "string",
                "description": "Company organization and key people information"
            },
            "project_manager": {
                "type": "string", 
                "description": "Project manager details"
            },
            "decision_maker": {
                "type": "string",
                "description": "Decision maker information"
            },
            "warnings_disclaimers": {
                "type": "string",
                "description": "Any warnings or disclaimers about behavior or organization"
            },
            "current_tms": {
                "type": "string",
                "description": "Current TMS (Transport Management System)"
            },
            "start_date_constraints": {
                "type": "string",
                "description": "Start date of the project and any constraints or conditions"
            },
            "number_sites_entities": {
                "type": "integer",
                "minimum": 0,
                "description": "Number of sites/entities"
            },
            "number_truckers": {
                "type": "integer",
                "minimum": 0,
                "description": "How many truckers"
            },
            "activities_transport_details": {
                "type": "string",
                "description": "Activities they do (not the business sector, exactly what they transport)"
            },
            "group_network_details": {
                "type": "string",
                "description": "Part of a group? Member of a pallet network? Local influencer and other network details"
            },
            "cross_dock_details": {
                "type": "string",
                "description": "Cross dock functionality? Edition d'étiquettes de suivi? Suivi des statuts à chaque passage à quai?"
            }
        },
        "required": [
            "company_org_key_people",
            "project_manager", 
            "decision_maker",
            "warnings_disclaimers",
            "current_tms",
            "start_date_constraints",
            "number_sites_entities",
            "number_truckers",
            "activities_transport_details",
            "group_network_details",
            "cross_dock_details"
        ],
        "additionalProperties": False
    },
    "strict": True
}

FIELD_NAME_MAPPING = {
    "company_org_key_people": "Company Org & Key People",
    "project_manager": "Project Manager",
    "decision_maker": "Decision Maker",
    "warnings_disclaimers": "Warnings/Disclaimers",
    "current_tms": "Current TMS",
    "start_date_constraints": "Start Date & Constraints",
    "number_sites_entities": "Number of Sites/Entities",
    "number_truckers": "Number of Truckers",
    "activities_transport_details": "Activities/Transport Details",
    "group_network_details": "Group/Network Details",
    "cross_dock_details": "Cross Dock Details"
}

SALES_DATA_SCHEMA_TO_HUBSPOT_FIELDS_MAPPING = {
    "company_org_key_people": "company_org_key_people",
    "project_manager": "project_manager",
    "decision_maker": "decision_maker",
    "warnings_disclaimers": "warnings_disclaimers",
    "current_tms": "current_tms",
    "start_date_constraints": "start_date_constraints",
    "number_sites_entities": "number_sites_entities",
    "number_truckers": "number_truckers",
    "activities_transport_details": "activities_transport_details",
    "group_network_details": "group_network_details",
    "cross_dock_details": "cross_dock_details"
}

SYSTEM_PROMPT = """
You are an expert sales assistant that extracts structured information from sales conversations and notes.
Your task is to analyze the transcript and fill in the fields of the schema with the most relevant information.

Instructions:

Output only the value for each field (no extra phrasing like “The X is…”).

If multiple values apply, list them separated by commas.

If information is missing, leave the field empty.

Do not add explanations, assumptions, or commentary outside the schema.

Maintain the exact field names from the schema.
"""

def transcribe_audio(audio_file):
    """Transcribe audio using OpenAI Whisper API"""
    try:
        # Handle UploadedFile object from st.audio_input()
        if hasattr(audio_file, 'read'):
            # It's an UploadedFile object, read the bytes
            audio_bytes = audio_file.read()
            # Reset file pointer for potential reuse
            audio_file.seek(0)
        else:
            # It's already bytes
            audio_bytes = audio_file
        
        # Create a temporary file to store the audio
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            tmp_file.write(audio_bytes)
            tmp_file.flush()
            
            # Transcribe using OpenAI Whisper
            with open(tmp_file.name, "rb") as audio_file_handle:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file_handle
                )
            
            # Clean up temporary file
            os.unlink(tmp_file.name)
            return transcript.text
    except Exception as e:
        st.error(f"Error transcribing audio: {str(e)}")
        return None

def get_ai_response(messages):
    """Get response from OpenAI GPT model"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-2024-08-06",
            messages=messages,
            max_completion_tokens=500,
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Error getting AI response: {str(e)}")
        return None

def extract_structured_data(transcript):
    """Extract structured sales data from transcript using OpenAI Structured Outputs"""
    try:
        messages = [
            {
                "role": "system", 
                "content": SYSTEM_PROMPT.strip()
            },
            {
                "role": "user", 
                "content": f"Please extract structured sales information from the following transcript:\n\n{transcript}"
            }
        ]
        
        response = client.chat.completions.create(
            model="gpt-4o-2024-08-06",  # Using the model that supports structured outputs
            messages=messages,
            response_format={
                "type": "json_schema",
                "json_schema": SALES_DATA_SCHEMA
            }
        )
        
        # Parse the JSON response
        extracted_data = json.loads(response.choices[0].message.content)
        return extracted_data
            
    except Exception as e:
        st.error(f"Error extracting structured data: {str(e)}")
        return None

# Helper function to check if field is empty or contains placeholder text
def is_field_empty(value):
    if value is None:
        return True
    if isinstance(value, str):
        return not value or not value.strip()
    if isinstance(value, (int, float)):
        return value <= 0  # Negative numbers considered invalid
    return False


def merge_structured_data(existing_data, new_data):
    """Merge new structured data with existing data, updating only non-empty fields"""
    if not existing_data:
        return new_data
    
    merged_data = existing_data.copy()
    
    def is_empty_value(value):
        """Check if a value is considered empty"""
        if value is None:
            return True
        if isinstance(value, str):
            return not value.strip() or value.strip().lower() in ['not mentioned', 'n/a', 'none', '']
        if isinstance(value, (int, float)):
            return value < 0  # Negative numbers considered invalid
        return False
    
    for key, value in new_data.items():
        # Update field if new value is not empty
        if not is_empty_value(value):
            merged_data[key] = value
    
    return merged_data

def generate_summary(transcript):
    """Generate a concise summary of the transcribed audio"""
    try:
        messages = [
            {"role": "system", "content": "You are a helpful assistant that creates concise, professional summaries of conversations or notes. Focus on key points, action items, and important details."},
            {"role": "user", "content": f"Please provide a concise summary of the following transcript:\n\n{transcript}"}
        ]
        
        response = client.chat.completions.create(
            model="gpt-4o-2024-08-06",  # Using consistent model with structured outputs support
            messages=messages,
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Error generating summary: {str(e)}")
        return None


def clear_all_data():
    """Clear all accumulated data from session state"""
    keys_to_clear = [
        'accumulated_transcripts',
        'last_transcript', 
        'accumulated_summary',
        'accumulated_structured_data',
        'last_processed_audio_hash'
    ]
    
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    
    field_keys_to_clear = [
        'field_company_org_key_people',
        'field_project_manager',
        'field_decision_maker',
        'field_warnings_disclaimers',
        'field_current_tms',
        'field_start_date_constraints',
        'field_number_sites_entities',
        'field_number_truckers',
        'field_activities_transport_details',
        'field_group_network_details',
        'field_cross_dock_details'
    ]   
    for key in field_keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    
    st.success("All data cleared! You can start fresh.")
    st.rerun()


def render_app_header(hubspot_id=None):
    """Render the application header and HubSpot ID input"""
    col1, col2 = st.columns([5, 2])
    
    with col1:
        st.header("📝 Post Sales Notes - Audio Summary")
        st.markdown("Record audio notes and get an AI-generated summary automatically")
    
    with col2:
        hubspot_id_value = hubspot_id if hubspot_id else ""
        hubspot_id_input = st.text_input("Company Hubspot ID", value=hubspot_id_value, disabled=False)
        
        if hubspot_id_input:
            col21, col22 = st.columns([1, 1])
            with col21:
                st.markdown(f"[View in HubSpot](https://app.hubspot.com/contacts/9184177/record/0-2/{hubspot_id_input})")
                if st.session_state.get("accumulated_structured_data"):
                    if st.button("Save notes to HubSpot"):
                        print("Sending company data to HubSpot")
                        print(st.session_state.hubspot_company_id)
                        print(st.session_state.accumulated_structured_data)
                        data_to_send = {}
                        for key, value in st.session_state.accumulated_structured_data.items():
                            data_to_send[SALES_DATA_SCHEMA_TO_HUBSPOT_FIELDS_MAPPING[key]] = value
                        try:
                            # Send company data to HubSpot
                            # send_company_data_to_hubspot(st.session_state.hubspot_company_id, data_to_send)
                            st.success("✅ Company data sent to HubSpot")
                        except Exception as e:
                            st.error(f"❌ Error sending company data to HubSpot: {str(e)}")
            with col22:
                company_data = get_hubspot_company_data(hubspot_id_input)
                company_name = company_data.get('properties').get('name').get('value')
                st.success(f"🏢 {company_name}")
                st.session_state.hubspot_company_id = hubspot_id_input
                st.session_state.hubspot_company_name = company_name
        else:
            st.warning("No company HubSpot ID provided")
    
    return hubspot_id_input


def render_instructions():
    """Render the instructions expander"""
    with st.expander("🎙️ How to Use Voice Notes", expanded=False):
        st.markdown("""
        ### Simple 3-Step Process:
        
        **1. 🎤 Record Your Voice**
        - Click the microphone button and speak naturally about your customer call or meeting
        - Talk about what was discussed, customer needs, next steps, etc.
        - Click stop when you're done
        
        **2. ✏️ Review & Add More (Optional)**
        - The form below will automatically fill with your notes
        - Record more audio if you want to add additional information
        - Edit any field manually if needed
        
        **3. 💾 Save to HubSpot**
        - When you're happy with all the information, click "Save notes to HubSpot"
        - Your notes will be automatically organized and saved to the customer's record
        
        ---
        **💡 Tips:**
        - Speak naturally - the system understands conversational language even in french
        - You can record multiple times to add more details
        - Each new recording will update and improve your notes
        - Use "Start Over" if you want to begin fresh
        """)


def process_audio_input(audio_bytes):
    """Process audio input and update session state with results"""
    if not audio_bytes:
        return
    
    current_audio_hash = hashlib.md5(audio_bytes.getvalue()).hexdigest()
    audio_already_processed = st.session_state.get('last_processed_audio_hash') == current_audio_hash
    
    if audio_already_processed:
        st.info("✅ This audio has already been processed. Record new audio to add more information.")
        return
    
    with st.spinner("🔈 Auto-processing audio..."):
        # Transcribe audio
        with st.spinner("✍️ Transcribing audio..."):
            transcript = transcribe_audio(audio_bytes)
            if not transcript:
                st.error("❌ Failed to transcribe audio")
                return
        
        # Store the hash of processed audio to prevent double processing
        st.session_state.last_processed_audio_hash = current_audio_hash
        
        # Accumulate transcripts
        if hasattr(st.session_state, 'accumulated_transcripts'):
            st.session_state.accumulated_transcripts.append(transcript)
        else:
            st.session_state.accumulated_transcripts = [transcript]
        
        # Store the latest transcript for display
        st.session_state.last_transcript = transcript
        
        # Generate and accumulate summary
        with st.spinner("💬 Generating summary..."):
            summary = generate_summary(transcript)
            if summary:
                if hasattr(st.session_state, 'accumulated_summary') and st.session_state.accumulated_summary:
                    st.session_state.accumulated_summary += f"\n\n--- Additional Notes ---\n{summary}"
                else:
                    st.session_state.accumulated_summary = summary
        
        # Extract and merge structured data
        with st.spinner("🔍 Extracting data..."):
            new_structured_data = extract_structured_data(transcript)
            if new_structured_data:
                existing_data = st.session_state.get('accumulated_structured_data', {})
                st.session_state.accumulated_structured_data = merge_structured_data(existing_data, new_structured_data)
                st.success("✅ Audio automatically processed, summary updated!")
            else:
                st.error("❌ Failed to extract structured data")


def render_audio_input_section():
    """Render the audio input and processing section"""
    st.subheader("🎤 Record Notes")
    
    # Start Over button - placed before audio input to prevent conflicts
    if st.button("🔄 Start Over", help="Clear all accumulated notes, summaries, and structured data", type="secondary"):
        clear_all_data()
        return  # Early return to prevent audio processing after clearing data
    
    # Audio recorder widget
    audio_bytes = st.audio_input("Record your notes or conversation")
    
    # Process audio if provided
    process_audio_input(audio_bytes)


def create_field_input(label, key, col_obj, structured_data):
    """Create input field with warning styling for empty fields"""
    value = structured_data.get(key, '')
    is_empty = is_field_empty(value)
    
    # Format value based on type for display and editing
    def format_value_for_input(val):
        if val is None:
            return ""
        elif isinstance(val, (int, float)):
            return str(val) if val >= 0 else ""
        else:
            return str(val) if val and val.lower() not in ['not mentioned', 'n/a', 'none', 'not specified'] else ""
    
    input_value = format_value_for_input(value)
    
    # Create the input field
    if key in ['number_sites_entities', 'number_truckers']:
        # Handle integer fields
        new_value = col_obj.number_input(
            label if not is_empty else f"⚠️ {label}",
            value=int(input_value) if input_value and input_value.isdigit() else 0,
            min_value=0,
            key=f"field_{key}",
            help="Enter a number"
        )
        # Update session state if value changed
        if new_value != value:
            if 'accumulated_structured_data' not in st.session_state:
                st.session_state.accumulated_structured_data = {}
            st.session_state.accumulated_structured_data[key] = new_value
    else:
        # Handle text fields
        new_value = col_obj.text_area(
            label if not is_empty else f"⚠️ {label}",
            value=input_value,
            height=100,
            key=f"field_{key}",
            help="You can edit this field manually"
        )
        # Update session state if value changed
        if new_value != input_value:
            if 'accumulated_structured_data' not in st.session_state:
                st.session_state.accumulated_structured_data = {}
            st.session_state.accumulated_structured_data[key] = new_value


def render_data_completion_status(structured_data):
    """Render data completion status and progress - simplified version for forms"""
    if not structured_data:
        return
    
    all_required_fields = SALES_DATA_SCHEMA.get("schema").get("properties").keys()
    filled_count = sum(1 for field in all_required_fields if not is_field_empty(structured_data.get(field)))
    total_fields = len(all_required_fields)
    completion_percentage = (filled_count / total_fields) * 100 if total_fields > 0 else 0
    
    st.info(f"📊 Data Completion: {filled_count}/{total_fields} fields ({completion_percentage:.0f}%)")


def render_structured_data_form(structured_data, dev_mode=False):
    """Render the structured data form organized by categories"""
    with st.expander("View accumulated structured data", expanded=True):
        # Organization section
        st.markdown("### 👥 ORG")
        col1, col2 = st.columns(2)
        
        with col1:
            create_field_input("Company Org & Key People", 'company_org_key_people', col1, structured_data)
            create_field_input("Project Manager", 'project_manager', col1, structured_data)
        
        with col2:
            create_field_input("Decision Maker", 'decision_maker', col2, structured_data)
            create_field_input("Warnings/Disclaimers", 'warnings_disclaimers', col2, structured_data)
        
        # Stack section
        st.markdown("### ⚙️ STACK")
        create_field_input("Current TMS", 'current_tms', st, structured_data)
        
        # Project size/complexity section
        st.markdown("### 📏 PROJECT SIZE / COMPLEXITY")
        col1, col2 = st.columns(2)
        
        with col1:
            create_field_input("Start Date & Constraints", 'start_date_constraints', col1, structured_data)
            create_field_input("Number of Sites/Entities", 'number_sites_entities', col1, structured_data)
        
        with col2:
            create_field_input("Number of Truckers", 'number_truckers', col2, structured_data)
            create_field_input("Activities/Transport Details", 'activities_transport_details', col2, structured_data)
        
        # LTL section
        st.markdown("### 📦 LTL")
        col1, col2 = st.columns(2)
        
        with col1:
            create_field_input("Group/Network Details", 'group_network_details', col1, structured_data)
        
        with col2:
            create_field_input("Cross Dock Details", 'cross_dock_details', col2, structured_data)
        
        if dev_mode:
            # Show raw JSON data
            with st.expander("Raw JSON Data", expanded=False):
                st.json(structured_data)


def render_sales_notes_data_tab(dev_mode=False):
    """Render the sales notes data tab"""
    st.subheader("📝 Sales Notes Data")
    
    structured_data = st.session_state.get('accumulated_structured_data', {})
    
    if structured_data:
        render_data_completion_status(structured_data)
        render_structured_data_form(structured_data, dev_mode)

def get_human_readable_field_name(field_key):
    """Convert field keys to human-readable names"""
    return FIELD_NAME_MAPPING.get(field_key, field_key.replace('_', ' ').title())

def render_checklist_section():
    """Render the checklist section with improved visual indicators"""
    with st.expander("📋 Field Completion Status", expanded=True):
        structured_data = st.session_state.get("accumulated_structured_data", {})
        all_required_fields = SALES_DATA_SCHEMA.get("schema").get("properties").keys()
        
        # Calculate completion stats
        filled_fields = []
        empty_fields = []
        
        for field in all_required_fields:
            field_value = structured_data.get(field)
            human_name = get_human_readable_field_name(field)
            
            if is_field_empty(field_value):
                empty_fields.append(human_name)
            else:
                filled_fields.append(human_name)
        
        total_fields = len(all_required_fields)
        completion_percentage = (len(filled_fields) / total_fields) * 100 if total_fields > 0 else 0
        
        # Progress bar
        st.progress(completion_percentage / 100, text=f"Completion: {len(filled_fields)}/{total_fields} fields ({completion_percentage:.0f}%)")
        
        # Show filled fields
        if filled_fields:
            st.markdown("#### ✅ **Completed Fields**")
            for field_name in filled_fields:
                st.success(f"✅ {field_name}")
        
        # Show empty fields
        if empty_fields:
            st.markdown("#### ⚠️ **Missing Fields**")
            for field_name in empty_fields:
                st.error(f"❌ {field_name}")
        
        # Show completion message when all done
        if len(filled_fields) == total_fields:
            st.balloons()
            st.success("🎉 All fields completed! Ready to save to HubSpot.")

def render_transcript_summary_tab():
    """Render the transcript and summary tab"""
    # Display all accumulated transcripts
    if hasattr(st.session_state, 'accumulated_transcripts') and st.session_state.accumulated_transcripts:
        if len(st.session_state.accumulated_transcripts) > 1:
            with st.expander("View all transcripts", expanded=False):
                for i, transcript in enumerate(st.session_state.accumulated_transcripts, 1):
                    st.text_area(f"Transcript {i}:", value=transcript, height=100, disabled=True, key=f"transcript_{i}")
    
    # Summary text input section
    st.subheader("📋 Accumulated Summary")
    summary_value = st.session_state.get('accumulated_summary', '')
    new_summary = st.text_area(
        "Edit or review the accumulated summary:",
        value=summary_value,
        height=200,
        placeholder="The AI-generated summary will appear here after processing audio...",
        key="summary_editor",
        help="You can edit this summary manually"
    )
    
    # Update session state if summary changed
    if new_summary != summary_value:
        st.session_state.accumulated_summary = new_summary


def render_data_display_tabs(dev_mode=False):
    """Render the data display tabs (Sales Notes Data and Transcript & Summary)"""
    sales_notes_data_tab, transcript_summary_tab = st.tabs(["📝 Sales Notes Data", "📄 Transcript & Summary"])
    
    with sales_notes_data_tab:
        render_sales_notes_data_tab(dev_mode)
    
    with transcript_summary_tab:
        render_transcript_summary_tab()


def post_sales_notes_app(dev_mode=False, hs_id=None):
    """Main application function - orchestrates all components"""
    # Render header and get HubSpot ID
    render_app_header(hs_id)
    
    # Render instructions
    render_instructions()
    
    # Main content layout
    col3, col4 = st.columns([1, 1])
    
    with col3:
        render_audio_input_section()
        render_checklist_section()
    with col4:
        render_data_display_tabs(dev_mode)
       