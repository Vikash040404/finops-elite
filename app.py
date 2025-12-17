import streamlit as st
import pdfplumber
import openai
from jinja2 import Template
import json
import base64

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(
    page_title="FinOps Elite | Automated Accounting",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. SESSION STATE SETUP (Login & Theme) ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'username' not in st.session_state:
    st.session_state['username'] = ''
if 'theme' not in st.session_state:
    st.session_state['theme'] = 'Light' # Default

# --- 3. USERS (Username : Password) ---
USERS = {
    "vikas": "admin8521",
    "client1": "tally2025",
    "demo": "tryme"
}

# --- 4. DYNAMIC CSS (Dark/Light Logic) ---
def apply_theme():
    if st.session_state['theme'] == 'Dark':
        # DARK MODE CSS
        st.markdown("""
        <style>
        .stApp { background-color: #0e1117; color: white; }
        .stSidebar { background-color: #262730; }
        
        /* Metrics & Cards (Dark) */
        div[data-testid="stMetric"] {
            background-color: #1f2937; 
            border: 1px solid #374151;
            color: white !important;
        }
        div[data-testid="stMetricLabel"] { color: #9ca3af !important; }
        div[data-testid="stMetricValue"] { color: white !important; }
        
        /* Contact Card (Dark) */
        .contact-card {
            background-color: #1e293b;
            border-left: 5px solid #3b82f6;
            color: #e2e8f0;
            padding: 15px;
            border-radius: 8px;
        }
        
        /* Input Fields (Dark) */
        .stTextInput>div>div>input {
            color: white;
            background-color: #374151;
        }
        
        /* Headers */
        h1, h2, h3 { color: #f8fafc !important; }
        </style>
        """, unsafe_allow_html=True)
        
    else:
        # LIGHT MODE CSS (Default Professional)
        st.markdown("""
        <style>
        .stApp { background-color: #f4f6f9; color: black; }
        
        /* Metrics & Cards (Light) */
        div[data-testid="stMetric"] {
            background-color: #ffffff; 
            border: 1px solid #e2e8f0;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
        }
        
        /* Contact Card (Light) */
        .contact-card {
            background-color: #e3f2fd;
            border-left: 5px solid #1e88e5;
            color: #0f172a;
            padding: 15px;
            border-radius: 8px;
        }
        </style>
        """, unsafe_allow_html=True)

    # GLOBAL STYLES (Buttons always look good)
    st.markdown("""
    <style>
    .stButton>button {
        background-color: #2563eb; 
        color: white; 
        border-radius: 8px; 
        height: 3em; 
        font-weight: 600;
        border: none;
    }
    .stButton>button:hover { background-color: #1d4ed8; }
    </style>
    """, unsafe_allow_html=True)

# Apply the selected theme immediately
apply_theme()

# --- 5. SIDEBAR ---
with st.sidebar:
    st.title("🏢 FinOps Elite")
    st.caption("v3.0 | Enterprise Edition")
    st.markdown("---")
    
    # THEME TOGGLE SWITCH
    st.subheader("🎨 Appearance")
    mode = st.radio("Theme", ["Light", "Dark"], horizontal=True)
    if mode != st.session_state['theme']:
        st.session_state['theme'] = mode
        st.rerun()

    st.markdown("---")
    
    # Contact Info
    st.markdown("""
    <div class="contact-card">
        <b>📞 Support Line:</b><br>+91 85216 92245<br><br>
        <b>📧 Business Email:</b><br>vikashkumar43443@gmail.com
    </div>
    """, unsafe_allow_html=True)
    
    # API Settings
    with st.expander("⚙️ System Settings"):
        api_key = st.text_input("Groq API Key (gsk_...)", type="password")

# --- 6. MAIN APP LOGIC ---

# LOGIN SCREEN
if not st.session_state['logged_in']:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("## 🔐 Secure Login")
        st.info("Please verify your credentials to access FinOps Elite.")
        
        user_input = st.text_input("Username")
        pass_input = st.text_input("Password", type="password")
        
        if st.button("Access Dashboard"):
            if user_input in USERS and USERS[user_input] == pass_input:
                st.session_state['logged_in'] = True
                st.session_state['username'] = user_input
                st.rerun()
            else:
                st.error("❌ Invalid Username or Password")

# DASHBOARD (AFTER LOGIN)
else:
    # Header & Logout
    c1, c2 = st.columns([6, 1])
    with c1:
        st.title(f"🚀 Dashboard | {st.session_state['username'].title()}")
    with c2:
        if st.button("Log Out"):
            st.session_state['logged_in'] = False
            st.rerun()

    st.markdown("---")
    
    # Upload Section
    uploaded_files = st.file_uploader(
        "📂 Drag & Drop Invoices (PDF or Images)", 
        type=["pdf", "png", "jpg", "jpeg"], 
        accept_multiple_files=True
    )

    def encode_image(image_file):
        return base64.b64encode(image_file.read()).decode('utf-8')

    if uploaded_files and api_key:
        if st.button(f"⚡ Auto-Process {len(uploaded_files)} Documents"):
            
            progress_bar = st.progress(0)
            status_area = st.empty()
            all_vouchers = []
            total_val = 0
            
            client = openai.OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")

            for index, file in enumerate(uploaded_files):
                status_area.markdown(f"**Scanning:** `{file.name}`...")
                extracted_data = None
                
                try:
                    # PDF HANDLING (Text)
                    if "pdf" in file.type:
                        with pdfplumber.open(file) as pdf:
                            text_data = "".join([page.extract_text() or "" for page in pdf.pages])
                        
                        prompt = f"""
                        Extract invoice data into JSON. Date format: YYYYMMDD.
                        Fields: Date, VendorName, TotalAmount (number only), LedgerName.
                        Text: {text_data}
                        """
                        response = client.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=[{"role": "user", "content": prompt}],
                            response_format={ "type": "json_object" }
                        )
                        extracted_data = json.loads(response.choices[0].message.content)

                    # IMAGE HANDLING (Vision) - Llama 4 Scout
                    else:
                        base64_img = encode_image(file)
                        response = client.chat.completions.create(
                            model="meta-llama/llama-4-scout-17b-16e-instruct",
                            messages=[
                                {
                                    "role": "user",
                                    "content": [
                                        {"type": "text", "text": "Extract invoice JSON: Date (YYYYMMDD), VendorName, TotalAmount, LedgerName."},
                                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}}
                                    ]
                                }
                            ],
                            response_format={ "type": "json_object" }
                        )
                        extracted_data = json.loads(response.choices[0].message.content)

                    # Success Logic
                    if extracted_data:
                        all_vouchers.append(extracted_data)
                        try:
                            total_val += float(extracted_data.get("TotalAmount", 0))
                        except:
                            pass

                except Exception as e:
                    st.error(f"⚠️ Error in {file.name}: {str(e)}")
                
                progress_bar.progress((index + 1) / len(uploaded_files))

            # SUMMARY & DOWNLOAD
            status_area.success("✅ Processing Complete!")
            
            # KPI Cards
            m1, m2, m3 = st.columns(3)
            m1.metric("Documents", len(uploaded_files))
            m2.metric("Total Value", f"₹ {total_val:,.0f}")
            m3.metric("Status", "Ready for Tally")

            # XML Template
            xml_template = """<ENVELOPE>
            <HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER>
            <BODY><IMPORTDATA><REQUESTDESC><REPORTNAME>Vouchers</REPORTNAME></REQUESTDESC>
            <REQUESTDATA><TALLYMESSAGE xmlns:UDF="TallyUDF">
            {% for v in vouchers %}
            <VOUCHER VCHTYPE="Purchase" ACTION="Create">
                <DATE>{{ v.Date }}</DATE>
                <PARTYLEDGERNAME>{{ v.VendorName }}</PARTYLEDGERNAME>
                <ALLLEDGERENTRIES.LIST>
                    <LEDGERNAME>{{ v.LedgerName }}</LEDGERNAME>
                    <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
                    <AMOUNT>-{{ v.TotalAmount }}</AMOUNT>
                </ALLLEDGERENTRIES.LIST>
                <ALLLEDGERENTRIES.LIST>
                    <LEDGERNAME>{{ v.VendorName }}</LEDGERNAME>
                    <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
                    <AMOUNT>{{ v.TotalAmount }}</AMOUNT>
                </ALLLEDGERENTRIES.LIST>
            </VOUCHER>
            {% endfor %}
            </TALLYMESSAGE></REQUESTDATA></IMPORTDATA></BODY></ENVELOPE>"""

            t = Template(xml_template)
            final_xml = t.render(vouchers=all_vouchers)

            st.download_button(
                "📥 Download Tally XML File", 
                final_xml, 
                "tally_import.xml", 
                "application/xml"
            )

    elif not api_key:
        st.warning("⚠️ System Halted: Please enter the API Key in Sidebar Settings.")