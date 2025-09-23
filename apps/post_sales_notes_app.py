import streamlit as st
import os
import tempfile
import json
import hashlib
from datetime import datetime, timezone
from openai import OpenAI
from utils.hubspot import get_hubspot_company_data, send_company_data_to_hubspot, get_tms_list_for_field, create_contact_in_hubspot, associate_contact_to_company
# Initialize OpenAI client
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

TMS_LIST = [""] + get_tms_list_for_field()

# OpenAI Structured Output JSON Schema for sales data extraction
SALES_DATA_SCHEMA = {
    "name": "sales_notes_extraction",
    "schema": {
        "type": "object",
        "properties": {
            "company_org_key_people": {
                "type": "string",
                "description": "Company organizational structure and key stakeholders. Include: decision makers, project sponsors, technical contacts, operations managers, finance contacts, and their roles/responsibilities. Note reporting structures, who has budget authority, who will be day-to-day users, and any internal politics or dynamics that could impact implementation success."
            },
            "project_manager_firstname": {
                "type": "string",
                "description": "Project manager first name"
            },
            "project_manager_lastname": {
                "type": "string",
                "description": "Project manager last name"
            },
            "decision_maker_firstname": {
                "type": "string",
                "description": "Decision maker first name"
            },
            "decision_maker_lastname": {
                "type": "string",
                "description": "Decision maker last name"
            },
            "warning_note": {
                "type": "string",
                "description": "Critical warnings, red flags, or risk factors that Customer Success should be aware of. Include: difficult personalities, previous implementation failures, budget constraints, timeline pressures, internal resistance, compliance issues, technical limitations, or any behavioral patterns that could impact project success. This helps CS prepare appropriate strategies and expectations."
            },
            "current_tms": {
                "type": "string",
                "description": "Current Transport Management System in use. Include: system name, version, how long they've used it, satisfaction level, specific pain points, integration capabilities, data migration challenges, and why they're looking to change. This helps CS understand technical migration complexity and potential integration requirements.",
                "enum": TMS_LIST,
            },
            "start_date_constraints": {
                "type": "string",
                "description": "Project timeline and implementation constraints. Include: desired start date, hard deadlines, seasonal business patterns, budget cycles, regulatory compliance dates, contract renewals, or any time-sensitive factors. Note if there are flexibility windows or if dates are negotiable. This helps CS plan realistic implementation schedules. THE FORMAT MUST BE DD/MM/YYYY",
                "pattern": "^(0[1-9]|[12][0-9]|3[01])/(0[1-9]|1[0-2])/\\d{4}$",
            },
            "number_sites_entities": {
                "type": "integer",
                "minimum": 0,
                "description": "Total number of physical locations, warehouses, distribution centers, or business entities that will be involved in the implementation. Include details about geographic distribution, operational differences between sites, and whether all sites need to go live simultaneously or can be phased. This impacts implementation complexity and resource planning."
            },
            "number_truckers": {
                "type": "integer",
                "minimum": 0,
                "description": "Total number of drivers/truckers who will use the system. Include: full-time vs part-time drivers, seasonal variations, driver turnover rates, technology comfort levels, training requirements, and whether drivers are employees or contractors. This helps CS plan user adoption strategies and training programs."
            },
            "activities_transport_details": {
                "type": "string",
                "description": "Specific transportation activities and cargo types handled. Include: types of goods transported, special handling requirements, temperature-controlled shipments, hazardous materials, international vs domestic routes, delivery patterns, customer requirements, and any unique operational needs. This helps CS understand feature requirements and customization needs."
            },
            "group_network_details": {
                "type": "string",
                "description": "Company's network affiliations and group memberships. Include: pallet networks, industry associations, partner relationships, franchise structures, parent company relationships, and any external dependencies that could affect implementation. Note if they have standardized processes from networks or if they need to maintain compatibility with partner systems."
            },
            "cross_dock_details": {
                "type": "string",
                "description": "Cross-docking operations and tracking requirements. Include: cross-dock facility details, volume of cross-docked shipments, tracking label requirements, status update needs at each dock passage, integration with existing systems, and any specific operational workflows. This helps CS understand complex operational requirements and potential integration challenges."
            }
        },
        "required": [
            "company_org_key_people",
            "project_manager_firstname",
            "project_manager_lastname",
            "decision_maker_firstname",
            "decision_maker_lastname",
            "warning_note",
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
    "project_manager_firstname": "Project Manager First Name",
    "project_manager_lastname": "Project Manager Last Name",
    "decision_maker_firstname": "Decision Maker First Name",
    "decision_maker_lastname": "Decision Maker Last Name",
    "warning_note": "Warnings Note",
    "current_tms": "Current TMS",
    "start_date_constraints": "Start Date & Constraints",
    "number_sites_entities": "Number of Sites/Entities",
    "number_truckers": "Number of Truckers",
    "activities_transport_details": "Activities/Transport Details",
    "group_network_details": "Group/Network Details",
    "cross_dock_details": "Cross Dock Details"
}

SALES_DATA_SCHEMA_TO_COMPANY_HUBSPOT_FIELDS_MAPPING = {
    "company_org_key_people": "company_org___key_people",
    "warning_note": "warning_note",
    "current_tms": "tms",
    "start_date_constraints": "mrr_start_date",
    "number_sites_entities": "nombre_d_agences",
    "number_truckers": "nom_de_conducteurs_total",
    "activities_transport_details": "activity_notes",
    "group_network_details": "group___network_detail",
    "cross_dock_details": "cross_dock_notes"
}

SYSTEM_PROMPT = """
You are an expert sales assistant that extracts structured information from sales conversations and notes.
Your task is to analyze the transcript and fill in the fields of the schema with the most relevant information for the Customer Success team.

Instructions:

Output only the value for each field (no extra phrasing like "The X is…").

If multiple values apply, list them separated by commas.

If information is missing, leave the field empty.

Do not add explanations, assumptions, or commentary outside the schema.

Maintain the exact field names from the schema.

Focus on capturing information that will help Customer Success:
- Understand implementation complexity and risks
- Plan appropriate onboarding strategies
- Identify potential challenges and mitigation strategies
- Prepare for technical requirements and integrations
- Understand organizational dynamics and decision-making processes
- Plan realistic timelines and resource allocation

CONTEXT: TODAY IS {TODAY_DATE}
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

def extract_structured_data(transcript, existing_data=None):
    """Extract structured sales data from transcript using OpenAI Structured Outputs"""
    try:
        # Build context about existing data
        existing_context = ""
        if existing_data:
            existing_context = f"""

CURRENT ACCUMULATED DATA:
{json.dumps(existing_data, indent=2)}

IMPORTANT: Use the current data as a baseline and only update fields with NEW information from the transcript. 
- If a field already has meaningful data, only update it if the transcript provides MORE SPECIFIC or CORRECTED information
- If a field is empty or contains placeholder values, fill it with relevant information from the transcript
- Preserve existing data unless the transcript explicitly contradicts or provides better information
- For numeric fields, only update if the transcript provides a specific number (don't overwrite with 0 unless explicitly mentioned)
- For the 'current_tms' field: Only update if the transcript explicitly mentions a specific TMS system name. If no TMS is mentioned or the mention is unclear, leave the field empty to preserve existing data.
- Available TMS options: {', '.join(TMS_LIST[:10])}{'...' if len(TMS_LIST) > 10 else ''}
"""

        messages = [
            {
                "role": "system", 
                "content": SYSTEM_PROMPT.strip().format(TODAY_DATE=datetime.now().strftime("%Y-%m-%d")) + existing_context
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
        # For integer fields, only consider negative numbers as invalid
        # 0 is a valid value that should not be considered empty
        return value <= 0
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
            # For integer fields, only consider negative numbers as invalid
            # 0 is a valid value that should be preserved
            return value < 0
        return False
    
    def is_valid_tms_value(value):
        """Check if TMS value is valid (exists in TMS_LIST)"""
        if not value or not isinstance(value, str):
            return False
        return value.strip() in TMS_LIST
    
    for key, value in new_data.items():
        # Special handling for TMS field
        if key == 'current_tms':
            # Only update TMS if the new value is valid and not empty
            if is_valid_tms_value(value) and not is_empty_value(value):
                merged_data[key] = value
            # If existing TMS is valid, preserve it even if new value is empty/invalid
            elif is_valid_tms_value(existing_data.get(key)):
                # Keep existing value, don't overwrite with empty/invalid
                pass
        else:
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


def initialize_empty_structured_data():
    """Initialize all structured data fields to empty values"""
    all_required_fields = SALES_DATA_SCHEMA.get("schema").get("properties").keys()
    empty_data = {}
    
    for field in all_required_fields:
        field_properties = SALES_DATA_SCHEMA.get("schema").get("properties").get(field)
        field_type = field_properties.get("type")
        
        if field_type == "integer":
            empty_data[field] = 0
        elif field_type == "string":
            empty_data[field] = ""
        else:
            empty_data[field] = ""
    
    return empty_data

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
    
    # Initialize empty structured data
    st.session_state.accumulated_structured_data = initialize_empty_structured_data()
    
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
            with col22:
                company_data = get_hubspot_company_data(hubspot_id_input)
                company_name = company_data.get('properties', {}).get('name', "")
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


def process_audio_input(audio_bytes, dev_mode=False):
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
            existing_data = st.session_state.get('accumulated_structured_data', {})
            new_structured_data = extract_structured_data(transcript, existing_data)
            if new_structured_data:
                # Debug: Show what's being merged (can be enabled for debugging)
                if dev_mode:
                    st.write("🔍 Debug - Existing TMS:", existing_data.get('current_tms', 'None'))
                    st.write("🔍 Debug - New TMS:", new_structured_data.get('current_tms', 'None'))
                
                st.session_state.accumulated_structured_data = merge_structured_data(existing_data, new_structured_data)
                st.success("✅ Audio automatically processed, summary updated!")
            else:
                st.error("❌ Failed to extract structured data")


def render_audio_input_section(dev_mode=False):
    """Render the audio input and processing section"""
    st.subheader("🎤 Record Notes")
    
    # Start Over button - placed before audio input to prevent conflicts
    if st.button("🔄 Start Over", help="Clear all accumulated notes, summaries, and structured data", type="secondary"):
        clear_all_data()
        return  # Early return to prevent audio processing after clearing data
    
    # Audio recorder widget
    audio_bytes = st.audio_input("Record your notes or conversation")
    
    # Process audio if provided
    process_audio_input(audio_bytes, dev_mode)


def create_field_input(label, key, col_obj, structured_data, optional=False):
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
        # Handle the default value properly for integer fields
        default_value = 0
        if isinstance(value, (int, float)) and value > 0:
            default_value = int(value)
        elif input_value and input_value.isdigit():
            default_value = int(input_value)
        
        new_value = col_obj.number_input(
            label if not is_empty or optional else f"⚠️ {label}",
            value=default_value,
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
            label if not is_empty or optional else f"⚠️ {label}",
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
        st.markdown("#### Decision Maker")
        col1, col2 = st.columns(2)
        with col1:
            create_field_input("First Name", 'decision_maker_firstname', col1, structured_data)
        with col2:
            create_field_input("Decision Maker Last Name", 'decision_maker_lastname', col2, structured_data)
       
        st.markdown("#### Project Manager")
        col1, col2 = st.columns(2)
        with col1:
            create_field_input("First Name", 'project_manager_firstname', col1, structured_data)
        with col2:
            create_field_input("Last Name", 'project_manager_lastname', col2, structured_data)
        
        st.markdown("#### Company Org & Key People")
        col1, col2 = st.columns(2)
        with col1:
            create_field_input("Company Org & Key People", 'company_org_key_people', col1, structured_data)
        with col2:
            create_field_input("Warnings/Disclaimers", 'warnings_disclaimers', col2, structured_data)
        
       
        # Stack section
        st.markdown("### ⚙️ STACK")
        create_field_input("Current TMS", 'current_tms', st, structured_data)
        
        # Project size/complexity section
        st.markdown("### 📏 PROJECT SIZE / CONTEXT")
        col1, col2 = st.columns(2)
        
        with col1:
            create_field_input("Start Date & Constraints", 'start_date_constraints', col1, structured_data)
            create_field_input("Number of Sites/Entities", 'number_sites_entities', col1, structured_data)
            create_field_input("Group/Network Details", 'group_network_details', col1, structured_data)
        
        with col2:
            create_field_input("Number of Truckers", 'number_truckers', col2, structured_data)
            create_field_input("Activities/Transport Details", 'activities_transport_details', col2, structured_data)
            create_field_input("Cross Dock Details", 'cross_dock_details', col2, structured_data)
        
        if dev_mode:
            # Show raw JSON data
            with st.expander("Raw JSON Data", expanded=False):
                st.json(structured_data)

        if st.session_state.get("accumulated_structured_data"):
            if st.button("Save notes to HubSpot"):
                data_to_send = {}
                for key, value in st.session_state.accumulated_structured_data.items():
                    if key in SALES_DATA_SCHEMA_TO_COMPANY_HUBSPOT_FIELDS_MAPPING:
                        hubspot_field = SALES_DATA_SCHEMA_TO_COMPANY_HUBSPOT_FIELDS_MAPPING[key]
                        
                        # Convert date fields to timestamp format for HubSpot
                        if key == 'start_date_constraints' and value:
                            try:
                                # Convert DD/MM/YYYY to timestamp at midnight UTC for HubSpot
                                date_obj = datetime.strptime(value, "%d/%m/%Y")
                                # Create timezone-aware datetime at midnight UTC
                                midnight_utc = datetime.combine(date_obj.date(), datetime.min.time(), timezone.utc)
                                timestamp_ms = int(midnight_utc.timestamp() * 1000)
                                data_to_send[hubspot_field] = timestamp_ms
                            except ValueError:
                                print(f"⚠️ Invalid date format for start_date_constraints: {value}")
                                data_to_send[hubspot_field] = value
                        else:
                            data_to_send[hubspot_field] = value
                try:
                    # Send company data to HubSpot
                    send_company_data_to_hubspot(st.session_state.hubspot_company_id, data_to_send)
                    st.success("✅ Company data sent to HubSpot")
                except Exception as e:
                    st.error(f"❌ Error sending company data to HubSpot: {str(e)}")
                try:
                    if structured_data.get("project_manager_firstname") and structured_data.get("project_manager_lastname"):
                        project_manager_data = {
                            "firstname": structured_data.get("project_manager_firstname"),
                            "lastname": structured_data.get("project_manager_lastname"),
                            "hs_buying_role": "Project manager"
                        }
                        # Send contact data to HubSpot
                        project_manager_hs_contact = create_contact_in_hubspot(project_manager_data)
                        associate_contact_to_company(project_manager_hs_contact["id"], st.session_state.hubspot_company_id)
                        st.success("✅ Project Manager data sent to HubSpot")
                    else:
                        st.warning("❌ Project Manager data not sent to HubSpot (Missing information)")
                except Exception as e:
                    st.error(f"❌ Error sending project manager data to HubSpot: {str(e)}")
                try:
                    if structured_data.get("decision_maker_firstname") and structured_data.get("decision_maker_lastname"):
                        decision_maker_data = {
                            "firstname": structured_data.get("decision_maker_firstname"),
                            "lastname": structured_data.get("decision_maker_lastname"),
                            "hs_buying_role": "DECISION_MAKER"
                        }
                        # Send contact data to HubSpot
                        decision_maker_hs_contact = create_contact_in_hubspot(decision_maker_data)
                        associate_contact_to_company(decision_maker_hs_contact["id"], st.session_state.hubspot_company_id)
                        st.success("✅ Decision Maker data sent to HubSpot")
                    else:
                        st.warning("❌ Decision Maker data not sent to HubSpot (Missing information)")
                except Exception as e:
                    st.error(f"❌ Error sending decision maker data to HubSpot: {str(e)}")

def render_sales_notes_data_tab(dev_mode=False):
    """Render the sales notes data tab"""
    st.subheader("📝 Sales Notes Data")
    
    structured_data = st.session_state.get('accumulated_structured_data', {})
    # Always render the form, even if data is empty (initialized)
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
    # Initialize empty structured data if not already present
    if 'accumulated_structured_data' not in st.session_state:
        st.session_state.accumulated_structured_data = initialize_empty_structured_data()
    
    # Render header and get HubSpot ID
    render_app_header(hs_id)
    
    # Render instructions
    render_instructions()
    
    # Main content layout
    col3, col4 = st.columns([1, 1])
    
    with col3:
        render_audio_input_section(dev_mode)
        render_checklist_section()
    with col4:
        render_data_display_tabs(dev_mode)
       