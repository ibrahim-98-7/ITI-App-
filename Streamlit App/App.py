import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from pathlib import Path
import tempfile
import requests
import base64
import os
import re
#from dotenv import load_dotenv
#import pypyodbc as odbc
#import joblib
#from catboost import CatBoostClassifier, Pool
import time
import random
import json
from pbixray import PBIXRay


# --- Page setup (set ONCE) ---
st.set_page_config(
    page_title="ITI Examination System Dashboard",
    page_icon="🎓",
    layout="wide",
)

# ------------------------------
# BACKGROUND IMAGE SETUP
# ------------------------------
def get_base64_of_bin_file(bin_file):
    if bin_file.startswith(("http://", "https://")):
        # If it's a URL, download the content
        try:
            response = requests.get(bin_file)
            response.raise_for_status() # Raise exception for bad status codes
            data = response.content
        except requests.exceptions.RequestException as e:
            st.error(f"Error: Could not download background image from URL: {e}")
            return None
    else:
        # If it's a local path
        if not os.path.exists(bin_file):
            st.error(f"Error: Background image file not found at {bin_file}")
            return None
        with open(bin_file, 'rb') as f:
            data = f.read()

    return base64.b64encode(data).decode()
def set_background(png_file):
    bin_str = get_base64_of_bin_file(png_file)
    if bin_str is None:
        return
    page_bg_img = f"""
    <style>
    .stApp {{
        background-image: url("data:image/png;base64,{bin_str}");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }}
    </style>
    """
    st.markdown(page_bg_img, unsafe_allow_html=True)

# Try to set background
set_background("https://github.com/ibrahim-98-7/ITI-App-/blob/main/Streamlit%20App/ITI_Background17601951402362703.png")

# ------------------------------
# UNIFIED CSS STYLING
# ------------------------------
st.markdown("""
    <style>
    /* --- 1. Global Text --- */
    h1, h2, h3, h4, h5, h6, p, .stMarkdown, .stInfo, .stSuccess, .stWarning, .stError {
        color: #FFFFFF !important; /* Make all text white */
    }
    /* Fix info/success box text color */
    [data-testid="stInfo"] p, [data-testid="stSuccess"] p {
        color: #FFFFFF !important;
    }
    
    /* --- 2. Widget Labels (Radio, Selectbox, etc.) --- */
    [data-testid="stWidgetLabel"], .stRadio > label, .stRadio div[role='radiogroup'] label {
        color: white !important;
        font-weight: 600;
        font-size: 18px;
    }
    
    /* --- 3. Components (Expanders, DataFrames) --- */
    [data-testid="stExpander"] {
        background-color: rgba(0, 0, 0, 0.5);
        border-radius: 10px;
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    [data-testid="stExpander"] > div[role="button"] > div {
         color: #FFFFFF !important; /* Expander title */
    }
    [data-testid="stDataFrame"] {
        background-color: rgba(0, 0, 0, 0.4);
        border-radius: 8px;
    }
    [data-testid="stDataFrame"] .col-header, 
    [data-testid="stDataFrame"] .cell-value {
        color: #FFFFFF !important;
        background-color: transparent !important;
    }
    
    /* --- 4. Firebase Exam Styling --- */
    /* Make radio choice text white */
    .stRadio [data-baseweb="radio"] div label {
        color: #FFFFFF !important;
    }
    /* Make question text white and bold */
    [data-testid="stForm"] [data-testid="stMarkdown"] p {
        font-size: 1.15rem;
        font-weight: 600;
        color: #FFFFFF;
    }
    
    </style>
""", unsafe_allow_html=True)


# Try to import pbixray
try:
    from pbixray import PBIXRay
except ImportError:
    st.error("Could not import `pbixray`. Please install it using: `pip install pbixray`")
    st.stop()

# ------------------------------
# LOGO SETUP
# ------------------------------
def get_base64_image(image_path):
    if image_path.startswith(("http://", "https://")):
        try:
            response = requests.get(image_path)
            response.raise_for_status()
            return base64.b64encode(response.content).decode()
        except requests.exceptions.RequestException as e:
            st.error(f"Error: Could not download logo from URL: {e}")
            return ""
    else:
        # Local file path logic
        if not os.path.exists(image_path):
            st.error(f"Error: Logo file not found at {image_path}")
            return ""
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()

logo_path = "Gemini_Generated_Image_pwn1v3p13472503787887624.png"
logo_base64 = get_base64_image(logo_path)

# --- Header ---
if logo_base64: # Only show header if logo was found
    st.markdown(
        f"""
        <style>
        .header-container {{
            display: flex;
            align-items: center;
            justify-content: center; /* Centers content horizontally */
            gap: 15px; /* Space between logo and title */
            margin-bottom: 25px;
        }}
        .header-container img {{
            height: 160px;  /* Increased logo size */
            margin-right: 25px;
            border-radius: 12px;
        }}
        .header-title {{
            font-size: 36px;
            font-weight: 800;
            color: white;
            letter-spacing: 0.5px;
        }}
        </style>

        <div class="header-container">
            <img src="data:image/png;base64,{logo_base64}" alt="Logo">
            <div class="header-title">🎓 ITI Examination System Web Application</div>
        </div>
        """,
        unsafe_allow_html=True
    )

# --- Session state ---
if 'pbi_model' not in st.session_state:
    st.session_state.pbi_model = None
if 'file_path' not in st.session_state:
    st.session_state.file_path = ""

# --- Tabs ---
FireBase, SSRS_Report, tab_dashboard, tab_inspector = st.tabs([
    "✏️ Examination ",
    "📝 SSRS Report",
    "📊 Visualization Dashboards",
    "🧩 PBIX Inspector"
    
])

# =====================================================================
# 🔷 COMBINED TAB 1: Power BI & Tableau (with toggle)
# =====================================================================
with tab_dashboard:
    st.markdown("<h2 style='text-align:center;'>📊 ITI Examination System Dashboards</h2>", unsafe_allow_html=True)
    st.divider()

    # Let the user choose which dashboard to view
    dashboard_choice = st.radio(
        "Select a dashboard to view:",
        ("Power BI Dashboard", "Tableau Dashboard"),
        horizontal=True
    )

    # POWER BI SECTION
    if dashboard_choice == "Power BI Dashboard":
        st.markdown("<h3 style='text-align:center;'>📊 Power BI Dashboard</h3>", unsafe_allow_html=True)
        report_url = "https://app.powerbi.com/reportEmbed?reportId=f4db1c94-1880-4411-9985-631532e8a5db&autoAuth=true&ctid=0ffeb7b8-177f-48b0-809f-2499efab9107"
        components.iframe(report_url, height=850, scrolling=True)
        st.info("This is a live Power BI report. You can interact with filters and visuals directly.")

    # ========================
    # --- TABLEAU SECTION ---
    # ========================
    elif dashboard_choice == "Tableau Dashboard":
        st.markdown("<h3 style='text-align:center;'>📈 Tableau Dashboards</h3>", unsafe_allow_html=True)
        
        # --- Nested selection for the three Tableau dashboards ---
        tableau_selection = st.selectbox(
            "Select a Tableau dashboard to display:",
            ( "Failure Dashboard", "Employee And Freelance")
        )

        # --- 2. Failure Dashboard (Responsive-Width) ---
        if tableau_selection == "Failure Dashboard":
            # URL from your embed code's 'path' parameter
            tableau_url = "https://public.tableau.com/shared/Y6FYPWHXT?:showVizHome=no&:embed=true"
            # Height based on your embed script's min/max values (887-987)
            DASH_HEIGHT = 900 

            iframe_html = f"""
            <div style="width:100%; height:{DASH_HEIGHT}px; border-radius:12px; overflow:hidden;">
                <iframe src="{tableau_url}" width="100%" height="100%" frameborder="0" style="border-radius:12px;"></iframe>
            </div>
            """
            components.html(iframe_html, height=DASH_HEIGHT + 20)
            st.info("This view is published from Tableau Public.")

        # --- 3. Employee And Freelance (Responsive-Width) ---
        elif tableau_selection == "Employee And Freelance":
            # URL from your embed code's 'name' parameter
            tableau_url = "https://public.tableau.com/views/ITIGraduationProject/EmployeeAndFreelance?:showVizHome=no&:embed=true"
            # Height based on your embed script's min/max values
            DASH_HEIGHT = 900 

            iframe_html = f"""
            <div style="width:100%; height:{DASH_HEIGHT}px; border-radius:12px; overflow:hidden;">
                <iframe src="{tableau_url}" width="100%" height="100%" frameborder="0" style="border-radius:12px;"></iframe>
            </div>
            """
            components.html(iframe_html, height=DASH_HEIGHT + 20)
            st.info("This view is published from Tableau Public.")

# =====================================================================
# 🧩 TAB 2: PBIX Inspector
# =====================================================================
with tab_inspector:
    st.markdown("<h2 style='text-align:center;'>🧠 PBIX Model Inspector</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;'>Automatically analyzes your ITI Examination System Power BI model.</p>", unsafe_allow_html=True)
    st.divider()
    github_pbix_url = (
        "https://github.com/Ahmed-Arab95734/Graduation-Project-ITI-Examination-System/"
        "raw/main/Ibrahim/Streamlit%20Application/ITI_Dashboard_Graduaton_Project.pbix"
    )

    def auto_load_pbix(url):
        try:
            with st.spinner("📥 Downloading PBIX file from GitHub..."):
                response = requests.get(url)
                response.raise_for_status()
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pbix") as tmp_file:
                    tmp_file.write(response.content)
                    tmp_path = Path(tmp_file.name)
            with st.spinner("🔍 Analyzing PBIX file..."):
                model = PBIXRay(tmp_path)
                st.session_state.pbi_model = model
                st.session_state.file_path = str(tmp_path)
            st.success("✅ PBIX file loaded successfully!")
        except Exception as e:
            st.error(f"❌ Error loading PBIX file: {e}")

    if st.session_state.pbi_model is None:
        auto_load_pbix(github_pbix_url)

    if not st.session_state.pbi_model:
        st.warning("⚠️ PBIX model could not be loaded.")
    else:
        model = st.session_state.pbi_model
        st.success("✅ PBIX model analyzed successfully!")

        # --- DAX Measures ---
        with st.expander("🧮 DAX Measures", expanded=True):
            try:
                dax_df = model.dax_measures
                st.dataframe(dax_df if not dax_df.empty else pd.DataFrame(["No DAX measures found."]), use_container_width=True)
            except Exception as e:
                st.error(f"Error reading DAX: {e}")

        # --- Power Query ---
        with st.expander("⚙️ Power Query (M) Code"):
            try:
                m_df = model.power_query
                st.dataframe(m_df if not m_df.empty else pd.DataFrame(["No Power Query found."]), use_container_width=True)
            except Exception as e:
                st.error(f"Error reading Power Query: {e}")

        # --- Schema ---
        with st.expander("🧱 Data Model Schema"):
            try:
                schema_df = model.schema
                st.dataframe(schema_df if not schema_df.empty else pd.DataFrame(["No Schema found."]), use_container_width=True)
            except Exception as e:
                st.error(f"Error reading Schema: {e}")

        # --- Relationships ---
        with st.expander("🔗 Model Relationships", expanded=True):
            try:
                rel_df = model.relationships
                if rel_df is not None and not rel_df.empty:
                    st.dataframe(rel_df, use_container_width=True)
                else:
                    st.info("No relationships found in this PBIX model.")
            except Exception as e:
                st.error(f"Error reading relationships: {e}")


# =====================================================================
# 🧮 TAB 3: Firebase Connection And Examination system
# =====================================================================
with FireBase:
  #  load_dotenv()

    # --- Page Configuration & URLs ---
    st.markdown("<h2 style='text-align:center;'>✏️ ITI Student Exam Portal </h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;'>Automatically Generates your ITI Exam.</p>", unsafe_allow_html=True)
    st.divider()

    # --- Firebase Configuration ---
    FIREBASE_URL = "https://iti-examination-default-rtdb.firebaseio.com"


    if not FIREBASE_URL:
        st.error("FIREBASE_URL not set in .env")
        st.stop()

    def fb_url(path):
        auth ="" # Add auth token if needed: ?auth={token}
        return f"{FIREBASE_URL.rstrip('/')}/{path}.json{auth}"

    # --- Firebase Helper Functions ---
    def fb_get(path):
        url = fb_url(path)
        try:
            r = requests.get(url)
            r.raise_for_status()  # Raise an exception for bad status codes
            return r.json() or {}
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data from Firebase path '{path}': {e}") # Use print for backend errors
            return {}
        except json.JSONDecodeError:
            print(f"Error decoding JSON from Firebase path '{path}'. Response was: {r.text}")
            return {}

    def fb_post(path, payload):
        url = fb_url(path)
        try:
            r = requests.post(url, json=payload)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.RequestException as e:
            print(f"Error posting data to Firebase path '{path}': {e}")
            return None

    def fb_put(path, payload):
        url = fb_url(path)
        try:
            r = requests.put(url, json=payload)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.RequestException as e:
            print(f"Error putting data to Firebase path '{path}': {e}")
            return None

    # --- Data Loading ---
    @st.cache_resource
    def load_all_data():
        # This function runs inside st.spinner, so no need for toasts
        def process_to_id_map(raw_data, id_field_name):
            processed_map = {}
            if isinstance(raw_data, dict):
                for key, val in raw_data.items():
                    if not (val and isinstance(val, dict)): continue
                    cid = val.get(id_field_name)
                    if cid: processed_map[str(cid)] = val
                    elif key.isdigit(): processed_map[key] = val
            elif isinstance(raw_data, list):
                for idx, val in enumerate(raw_data):
                    if not (val and isinstance(val, dict)): continue
                    cid = val.get(id_field_name)
                    if cid: processed_map[str(cid)] = val
                    else: processed_map[str(idx)] = val
            return processed_map

        courses = process_to_id_map(fb_get("courses"), "Course_ID")
        exams = process_to_id_map(fb_get("exams"), "Exam_ID")
        questions = process_to_id_map(fb_get("questions"), "Question_ID")

        student_courses_raw = fb_get("student_courses")
        student_courses_map = {}
        if isinstance(student_courses_raw, dict):
            student_courses_map = student_courses_raw
        elif isinstance(student_courses_raw, list):
            for idx, val in enumerate(student_courses_raw):
                if val: student_courses_map[str(idx)] = val
        
        choices = fb_get("choices")
        
        def get_as_dict(path):
            data = fb_get(path)
            if isinstance(data, dict): return data or {}
            if isinstance(data, list):
                converted_dict = {}
                for idx, val in enumerate(data):
                    if val: converted_dict[str(idx)] = val
                return converted_dict
            print(f"Data at path '{path}' was not a dictionary or list. Using empty map.")
            return {}

        exam_questions_grouped = get_as_dict("exam_questions_grouped")
        choices_by_question = get_as_dict("choices_by_question")
        
        return {
            "courses": courses,
            "student_courses": student_courses_map,
            "exams": exams,
            "questions": questions,
            "choices": choices,
            "exam_questions_grouped": exam_questions_grouped,
            "choices_by_question": choices_by_question
        }

    # --- GUI Styling ---
    # REMOVED: All CSS from here is now consolidated at the top of the file.
    
    # --- Load Data with Spinner ---
    with st.spinner("Connecting to Exam Database..."):
        data = load_all_data()

    # --- Session State Initialization ---
    if "step" not in st.session_state: st.session_state.step = 1
    if "student_id" not in st.session_state: st.session_state.student_id = None
    if "selected_course_id" not in st.session_state: st.session_state.selected_course_id = None
    if "exam_id" not in st.session_state: st.session_state.exam_id = None
    if "exam_questions" not in st.session_state: st.session_state.exam_questions = []
    if "answers" not in st.session_state: st.session_state.answers = {}
    if "end_time" not in st.session_state: st.session_state.end_time = None
    if "duration_minutes" not in st.session_state: st.session_state.duration_minutes = 0

    # --- UI Functions (Steps) ---
    def step1_ui():
        st.subheader("Step 1 — Student Authentication")
        st.write("Please enter your Student ID to find your available exams.")
        sid = st.text_input("Enter Your Student ID", key="student_id_input", label_visibility="collapsed")
        
        if st.button("Find My Exams"):
            if not sid:
                st.warning("Please enter your Student ID.")
                return
            st.session_state.student_id = sid
            st.session_state.step = 2
            st.rerun()

    def step2_ui():
        st.subheader("Step 2 — Course Selection")
        sid = st.session_state.student_id
        st.info(f"Welcome, Student ID: **{sid}**")
        st.write("Please select an exam from your available courses.")

        sc_map = data["student_courses"] or {}
        courses_map = data["courses"] or {}

        available = []
        if isinstance(sc_map, dict):
            for key, sc in sc_map.items():
                try: sc_student = str(sc.get("Student_ID") or sc.get("student_id") or sc.get("StudentID"))
                except Exception: sc_student = None
                
                if sc_student == str(sid):
                    cid = str(sc.get("Course_ID"))
                    course = courses_map.get(cid) 
                    if course:
                        available.append((cid, course.get("Course_Name")))
        else:
            st.error("Student courses data is not in the expected dictionary format.")

        if not available:
            st.error("No courses found for this Student ID. Please contact your administrator.")
            return

        options = {name: cid for cid, name in available if name}
        if not options:
            st.error("Courses found, but they have no names. Please contact your administrator.")
            return
            
        choice = st.selectbox("Select an Available Exam", options=list(options.keys()))
        
        if st.button("Start Selected Exam"):
            st.session_state.selected_course_id = options[choice]
            st.session_state.step = 3
            st.rerun()

    def start_exam_for_course(course_id):
        exams_map = data["exams"]
        matching = [eid for eid, e in exams_map.items() if str(e.get("Course_ID")) == str(course_id)]
        if not matching: return None
        chosen = random.choice(matching)
        return chosen

    def step3_ui():
        st.subheader("Step 3 — Exam In Progress")
        course_id = st.session_state.selected_course_id

        if not st.session_state.exam_id:
            exam_id = start_exam_for_course(course_id)
            if not exam_id:
                st.error("No exam found for this course.")
                return
            st.session_state.exam_id = exam_id
            exam_info = data["exams"].get(str(exam_id), {})
            
            dur = exam_info.get("Exam_Duration_Minutes") or exam_info.get("Exam_Duration")
            try: dur = int(dur)
            except (ValueError, TypeError): dur = 30 # Default
            
            st.session_state.duration_minutes = dur
            st.session_state.end_time = time.time() + dur * 60
            st.session_state.exam_questions = data["exam_questions_grouped"].get(str(exam_id), [])
            st.session_state.answers = {str(qid): None for qid in st.session_state.exam_questions}

        if st.session_state.exam_id:
            st.caption(f"Student ID: {st.session_state.student_id} | Exam ID: {st.session_state.exam_id}")

        remaining = int(st.session_state.end_time - time.time())
        if remaining <= 0:
            st.warning("Time is up. Submitting...")
            st.toast("Time's up! Automatically submitting your exam.", icon="⏰")
            submit_answers()
            st.rerun() 
            return
            
        minutes = remaining // 60
        seconds = remaining % 60
        st.markdown(f"**Time remaining: {minutes:02d}:{seconds:02d}**")

        questions_map = data["questions"]
        choices_by_q = data["choices_by_question"]

        st.write("---")
        with st.form(key="exam_form"):
            for idx, qid in enumerate(st.session_state.exam_questions, start=1):
                qid_s = str(qid)
                q = questions_map.get(qid_s)
                if not q:
                    st.error(f"Question {qid_s} not found.")
                    continue
                
                st.write(f"**Q{idx}. {q.get('Question_Description')}**")
                qtype = q.get("Question_Type")
                key = f"q_{qid_s}"
                
                current_val = st.session_state.answers.get(qid_s)
                
                if qtype == "MCQ":
                    choices_list = choices_by_q.get(qid_s) or []
                    labels = [c.get("Choice_Text") for c in choices_list if c]
                    if not labels:
                        st.warning(f"No choices found for question {qid_s}")
                        continue
                    
                    try: default_index = labels.index(current_val)
                    except ValueError: default_index = None
                        
                    sel = st.radio("Select one", labels, index=default_index, key=key,label_visibility="collapsed")
                    st.session_state.answers[qid_s] = sel
                    
                elif qtype == "True/False":
                    opts = ["True", "False"]
                    try: default_index = opts.index(current_val)
                    except ValueError: default_index = None

                    sel = st.radio("Select one", opts, index=default_index, key=key,label_visibility="collapsed")
                    st.session_state.answers[qid_s] = sel
                    
                else: # fallback: free text
                    txt = st.text_input("Answer", value=current_val if current_val else "", key=key)
                    st.session_state.answers[qid_s] = txt
                st.write("---")
            
            submitted = st.form_submit_button("Submit Exam")
            if submitted:
                submit_answers()
                st.rerun()
                return

        time.sleep(1)
        st.rerun()

    def submit_answers():
        st.toast("Submitting your answers...")
        sid = st.session_state.student_id
        exam_id = st.session_state.exam_id
        answers = st.session_state.answers
        
        all_answered = all(ans is not None and ans != "" for ans in answers.values())
        if not all_answered:
            st.warning("You have not answered all questions, but submitting anyway.")

        payloads = []
        for qid, ans in answers.items():
            record = {
                "Exam_ID": int(exam_id) if str(exam_id).isdigit() else exam_id,
                "Question_ID": int(qid) if str(qid).isdigit() else qid,
                "Student_ID": int(sid) if str(sid).isdigit() else sid,
                "Student_Answer": ans if ans is not None else "N/A",
                "Submitted_At": int(time.time())
            }
            payloads.append(record)

        results = []
        with st.spinner("Submitting your answers to the database..."):
            for rec in payloads:
                res = fb_post("student_answers", rec)
                if res: results.append(res.get("name"))
                else: st.error(f"Failed to submit answer for Question ID: {rec['Question_ID']}")

        st.session_state.step = 4
        st.session_state.submitted_results = results

    def step4_ui():
        st.subheader("Step 4 — Submission Complete")
        st.success("Your answers have been submitted successfully. You may now close this window.")
        st.balloons()
        
        # Clear sensitive session state
        st.session_state.student_id = None
        st.session_state.selected_course_id = None
        st.session_state.exam_id = None
        st.session_state.exam_questions = []
        st.session_state.answers = {}
        st.session_state.end_time = None
        
        st.info("If you need to take another exam, please REFRESH the page to log in again.")
        
        res = st.session_state.get("submitted_results", None)
        if res:
            with st.expander("View Submission Summary (Technical Details)"):
                st.json(res)

    # --- Main App Flow ---
    if "step" in st.session_state:
        if st.session_state.step == 1: step1_ui()
        elif st.session_state.step == 2: step2_ui()
        elif st.session_state.step == 3: step3_ui()
        elif st.session_state.step == 4: step4_ui()
    else:
        step1_ui() # Default

# =====================================================================
# 🧮 TAB 4: SSRS Reporting (Optimized + No Sidebar)
# =====================================================================
with SSRS_Report:
    # --- PAGE TITLE ---
    st.markdown("<h2 style='text-align:center;'>📝 SSRS Reporting</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;'>Explore cloud-hosted SSRS reports for the ITI Examination System.</p>", unsafe_allow_html=True)
    st.divider()

    # --- STYLING ---
    # REMOVED: All CSS from here is now consolidated at the top of the file.
    # The unified CSS will make all text white.


    # --- REPORT LINKS ---
    REPORTS = {
        "Course Topics": "https://app.powerbi.com/rdlEmbed?reportId=c415569d-8ceb-4aae-bbcd-69de90e9ff1e&autoAuth=true&ctid=0ffeb7b8-177f-48b0-809f-2499efab9107&experience=power-bi&rs:embed=true",
        "Instructor Courses & Number of Students": "https://app.powerbi.com/rdlEmbed?reportId=8ca9c034-34f4-4a44-9b72-e6958dae8e33&autoAuth=true&ctid=0ffeb7b8-177f-48b0-809f-2499efab9107&experience=power-bi&rs:embed=true",
        "Exam Questions": "https://app.powerbi.com/rdlEmbed?reportId=499f71c2-4480-43b5-8051-5d2ab9690c9f&autoAuth=true&ctid=0ffeb7b8-177f-48b0-809f-2499efab9107&experience=power-bi&rs:embed=true",
        "Student Exam Answers": "https://app.powerbi.com/rdlEmbed?reportId=51d593f5-6d84-448a-870c-fc87c6ac9226&autoAuth=true&ctid=0ffeb7b8-177f-48b0-809f-2499efab9107&experience=power-bi&rs:embed=true",
        "Student Grades": "https://app.powerbi.com/rdlEmbed?reportId=04d7f8b2-14e4-4d20-b8f8-36b2aea2657d&autoAuth=true&ctid=0ffeb7b8-177f-48b0-809f-2499efab9107&experience=power-bi&rs:embed=true",
        "Student Details by Track": "https://app.powerbi.com/rdlEmbed?reportId=7d2cf478-032e-4428-abdd-2bd31d4e43cc&autoAuth=true&ctid=0ffeb7b8-177f-48b0-809f-2499efab9107&experience=power-bi&rs:embed=true",
    }

    # --- CENTERED SELECT BOX ---
    st.markdown("<h4 style='text-align:center;'>Select a Report:</h4>", unsafe_allow_html=True)
    selected_report = st.selectbox(
        "Select a Report", # Label for accessibility
        options=list(REPORTS.keys()),
        index=0,
        key="ssrs_report_select",
        label_visibility="collapsed" # Hide label as we have a header
    )

    # --- DISPLAY SELECTED REPORT ---
    report_url = REPORTS[selected_report]
    st.markdown(f"<h4 style='text-align:center;'>Currently Viewing: {selected_report}</h4>", unsafe_allow_html=True)

    iframe_html = f"""
    <div style="width:1300px; height:850px; margin:0 auto; border-radius:12px; overflow:hidden;">
        <iframe src="{report_url}" width="100%" height="100%" frameborder="0" style="border-radius:12px;"></iframe>
    </div>
    """
    components.html(iframe_html, height=870)

    st.info("This SSRS report is embedded directly from the Power BI Service (Paginated Report).")


