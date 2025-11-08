import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from pathlib import Path
import tempfile
import requests
import base64
import os
import re
from dotenv import load_dotenv
import pypyodbc as odbc
import google.generativeai as genai
import joblib
from catboost import CatBoostClassifier, Pool
import json  # Added for dashboard generator
import plotly.express as px  # Added for dashboard generator

# Try to import pbixray
try:
    from pbixray import PBIXRay
except ImportError:
    st.error("Could not import `pbixray`. Please install it using: `pip install pbixray`")
    st.stop()

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
    try:
        with open(bin_file, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except FileNotFoundError:
        st.warning(f"Background image file not found: {bin_file}. Skipping background.")
        return None

def set_background(png_file):
    bin_str = get_base64_of_bin_file(png_file)
    if bin_str:
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

set_background("ITI_Background17601951402362703.png")

# ------------------------------
# LOGO SETUP
# ------------------------------
def get_base64_image(image_path):
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except FileNotFoundError:
        st.warning(f"Logo file not found: {image_path}. Skipping logo.")
        return None

logo_path = "Gemini_Generated_Image_pwn1v3p13472503787887624.png"
logo_base64 = get_base64_image(logo_path)

# --- Header ---
if logo_base64:
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
else:
    st.title("🎓 ITI Examination System Web Application")


# --- Session state ---
if 'pbi_model' not in st.session_state:
    st.session_state.pbi_model = None
if 'file_path' not in st.session_state:
    st.session_state.file_path = ""

# =====================================================================
# 🧠 SHARED LOGIC (API KEYS, HELPERS, SCHEMAS)
# =====================================================================

# ============================================
# 🔐 Load Gemini API Key
# ============================================
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    GOOGLE_API_KEY = st.text_input("🔑 Enter your Gemini API Key:", type="password")

if not GOOGLE_API_KEY:
    st.warning("Please provide your Gemini API key to continue.")
    st.stop()

genai.configure(api_key=GOOGLE_API_KEY)

# ============================================
# ⚙️ Helper Functions
# ============================================
@st.cache_resource
def load_gemini_model():
    return genai.GenerativeModel("models/gemini-2.5-pro")

def get_gemini_response(prompt, input_text):
    model = load_gemini_model()
    response = model.generate_content([prompt, input_text])
    return response.text.strip()

def read_sql_query(query, database):
    """Connect dynamically to either ITIExaminationSystem or ITI_DW"""
    DRIVER_NAME = 'SQL Server'
    SERVER_NAME = 'HIMA' # <!> IMPORTANT: Make sure this server name is correct
    CONNECTION_STRING = f'DRIVER={{{DRIVER_NAME}}};SERVER={SERVER_NAME};DATABASE={database};Trusted_Connection=yes;'

    try:
        connection = odbc.connect(CONNECTION_STRING)
        df = pd.read_sql(query, connection)
        connection.close()
        return df
    except Exception as e:
        st.error(f"Database Error: {e}")
        st.info(f"Connection String Used: {CONNECTION_STRING}")
        return None

# ============================================
# 📚 Schema Definitions (for AI Context)
# ============================================

# Schema 1: ITI Examination System (Transactional)
schema_examination = """
SCHEMA: ITIExaminationSystem
Tables:
Instructor(Instructor_ID, Instructor_Fname, Instructor_Lname, Instructor_Gender, Instructor_Birthdate, Instructor_Marital_Status, Instructor_Salary, Instructor_Contract_Type, Instructor_Email, Department_ID)
- Instructor_Phone(Instructor_ID, Phone)
- Department(Department_ID, Department_Name, Manager_ID)
- Intake(Intake_ID, Intake_Name, Intake_Type, Intake_Start_Date, Intake_End_Date)
- Branch(Branch_ID, Branch_Location, Branch_Name, Branch_Start_Date)
- Track(Track_ID, Track_Name, Department_ID)
- Group(Group_ID, Intake_ID, Branch_ID, Track_ID)
- Student(Student_ID, Student_Mail, Student_Address, Student_Gender, Student_Marital_Status, Student_Fname, Student_Lname, Student_Birthdate, Student_Faculty, Student_Faculty_Grade, Student_ITI_Status, Intake_Branch_Track_ID)
- Failed_Students(Student_ID, Failure_Reason)
- Student_Phone(Student_ID, Phone)
- Student_Social(Student_ID, Social_Type, Social_Url)
- Freelance_Job(Job_ID, Student_ID, Job_Earn, Job_Date, Job_Site, Description)
- Certificate(Certificate_ID, Student_ID, Certificate_Name, Certificate_Provider, Certificate_Cost, Certificate_Date)
- Company(Company_ID, Company_Name, Company_Location, Company_Type)
- Student_Company(Student_ID, Company_ID, Salary, Position, Contract_Type, Hire_Date, Leave_Date)
- Course(Course_ID, Course_Name)
- Track_Course(Track_ID, Course_ID)
- Instructor_Course(Instructor_ID, Course_ID)
- Student_Course(Student_ID, Course_ID, Course_StartDate, Course_EndDate)
- Exam(Exam_ID, Course_ID, Instructor_ID, Exam_Date, Exam_Duration_Minutes, Exam_Type)
- Question_Bank(Question_ID, Course_ID, Question_Type, Question_Description, Question_Model_Answer)
- Question_Choice(Question_Choice_ID, Question_ID, Choice_Text)
- Exam_Questions(Exam_ID, Question_ID)
- Student_Exam_Answer(Exam_ID, Question_ID, Student_ID, Student_Answer, Student_Grade)
- Rating(Student_ID, Instructor_ID, RatingValue)
- Topic(Topic_ID, Topic_Name, Course_ID)
"""

# Schema 2: ITI_DW_v5 (Data Warehouse)
schema_dw = """
SCHEMA: ITI_DW
Dimension Tables: DimDate, DimStudent, DimInstructor, DimCourse, DimDepartment, DimTrack, DimBranch, DimIntake, DimCompany
Fact Tables: FactStudentPerformance, FactStudentOutcomes, FactStudentRating, FactFreelanceJob, FactCertificate, FactStudentFailure
Use Dim and Fact relationships to build analytical dashboards.

FactStudentOutcomes(StudentKey, CompanyKey, HireDateKey, Salary, DaysToHire)
FactStudentRating(StudentKey, InstructorKey, RatingValue, RateDateKey)
FactStudentPerformance(StudentKey, CourseKey, InstructorKey, ExamKey, QuestionKey, ExamDateKey, Student_Grade)
DimStudent(StudentKey, Student_FullName, TrackKey, BranchKey, IntakeKey)
DimTrack(TrackKey, Track_Name)
DimCompany(CompanyKey, Company_Name)
DimDate(DateKey, FullDate)
"""

# =====================================================================
# --- TABS DEFINITION ---
# =====================================================================

tab1, tab2, tab3, tab4 = st.tabs([
    "🧠 Text-to-SQL",
    "📊 Intelligent Dashboard",
    "⚙️ Employment Predictor",
    "🤖 Grade Predictor"
])


# =====================================================================
# 🧠 TAB 1: Text to SQL using Gemini
# =====================================================================

with tab1:
    st.subheader("🧩 Text-to-SQL Assistant (ITIExaminationSystem)")

    user_question = st.text_input("💬 Ask a question about the ITI Examination System:")
    if st.button("Generate SQL and Execute"):
        if not user_question.strip():
            st.warning("Please enter a question.")
        else:
            sql_prompt = f"""
You are a senior SQL Server expert helping to translate natural language questions into valid T-SQL queries.
Rules:
- Use SQL Server syntax only.
- Use explicit JOINs.
- Avoid reserved keywords.
- Return only executable SQL (no markdown).
Schema:

{schema_examination}
"""
            with st.spinner("Generating SQL Query..."):
                response = get_gemini_response(sql_prompt, user_question)
                cleaned_query = re.sub(r"--.*", "", response)
                cleaned_query = cleaned_query.replace("```sql", "").replace("```", "").strip()

            st.subheader("🧠 Generated SQL Query")
            st.code(cleaned_query, language="sql")

            try:
                with st.spinner("Executing query..."):
                    df = read_sql_query(cleaned_query, "ITIExaminationSystem")
                    if df is not None:
                        st.success("✅ Query executed successfully!")
                        st.dataframe(df)
            except Exception as e:
                st.error(f"❌ Error executing SQL query: {e}")

# =====================================================================
# 📊 TAB 2: Intelligent Dashboard Generator
# =====================================================================
with tab2:
    st.subheader("📊 Intelligent Dashboard Generator (ITI_DW)")

    dashboard_description = st.text_input(
        "📝 Describe the dashboard you want to generate:",
        placeholder="Example: Show average student grades by department and track"
    )

    if st.button("Generate Dashboard"):
        if not dashboard_description.strip():
            st.warning("Please describe the dashboard.")
        else:
            dashboard_prompt = f"""
You are an expert data visualization and SQL assistant.
Given a database schema and a dashboard description, return ONLY valid JSON with chart definitions.

Rules:
- Use these exact names in SQL queries.
- Always use SQL Server syntax (TOP N instead of LIMIT).
- Join Fact and Dim tables properly.
- Return only valid SQL queries (no markdown).

Output format:
[
{{
    "title": "Chart Title",
    "chart_type": "bar | line | pie | table | kpi",
    "sql": "SQL Server query string"
}}
]

Rules:
- Use ITI_DW star schema.
- Use SQL Server syntax only (no LIMIT; use TOP N instead).
- Ensure joins between Fact and Dim tables are logical.
Schema:
{schema_dw}
"""
            try:
                with st.spinner("Generating dashboard definition..."):
                    model = load_gemini_model()
                    response = model.generate_content([dashboard_prompt, dashboard_description])
                    content = response.text.strip().replace("```json", "").replace("```", "").strip()
                    charts = json.loads(content)

                st.success("✅ Dashboard generated successfully!")

                # Layout for a true dashboard look
                cols = st.columns(2)
                for i, chart in enumerate(charts):
                    with cols[i % 2]:
                        st.markdown(f"### {chart['title']}")
                        st.code(chart['sql'], language="sql")

                        try:
                            with st.spinner(f"Loading chart: {chart['title']}..."):
                                df = read_sql_query(chart["sql"], "ITI_DW")
                                
                                if df is None:
                                    st.error(f"Query for '{chart['title']}' failed to execute.")
                                    continue

                                if chart["chart_type"] == "table":
                                    st.dataframe(df)
                                    
                                elif chart["chart_type"] == "bar":
                                    fig = px.bar(df, x=df.columns[0], y=df.columns[1], title=chart['title'])
                                    # --- ADDED LINES ---
                                    fig.update_layout(
                                        paper_bgcolor='rgba(0,0,0,0)', # Transparent outer background
                                        plot_bgcolor='rgba(0,0,0,0)',  # Transparent plot area
                                        font_color='white'             # Text color for readability
                                    )
                                    # --- END ADDED LINES ---
                                    st.plotly_chart(fig, use_container_width=True)

                                elif chart["chart_type"] == "line":
                                    fig = px.line(df, x=df.columns[0], y=df.columns[1], title=chart['title'])
                                    # --- ADDED LINES ---
                                    fig.update_layout(
                                        paper_bgcolor='rgba(0,0,0,0)',
                                        plot_bgcolor='rgba(0,0,0,0)',
                                        font_color='white'
                                    )
                                    # --- END ADDED LINES ---
                                    st.plotly_chart(fig, use_container_width=True)

                                elif chart["chart_type"] == "pie":
                                    fig = px.pie(df, names=df.columns[0], values=df.columns[1], title=chart['title'])
                                    # --- ADDED LINES ---
                                    fig.update_layout(
                                        paper_bgcolor='rgba(0,0,0,0)',
                                        plot_bgcolor='rgba(0,0,0,0)',
                                        font_color='white'
                                    )
                                    # --- END ADDED LINES ---
                                    st.plotly_chart(fig, use_container_width=True)

                                elif chart["chart_type"] == "kpi":
                                    # Note: st.metric doesn't support transparency, 
                                    # but we can style the 'kpi' title text.
                                    # For a truly transparent KPI, you'd use Plotly Indicator.
                                    st.metric(label=chart["title"], value=float(df.iloc[0, 0]))

                        except Exception as e:
                            st.error(f"⚠️ Could not execute/render chart '{chart['title']}': {e}")

            except Exception as e:
                st.error(f"⚠️ Could not parse Gemini response: {e}")
                st.write("Raw output:")
                st.code(response.text if 'response' in locals() else "No response received.")

# =====================================================================
# ⚙️ TAB 3: AI Student Employment Predictor
# =====================================================================
with tab3:
    # -----------------------------
    # 2. Load trained CatBoost model
    # -----------------------------
    @st.cache_resource
    def load_employment_model():
        try:
            return joblib.load("catboost_employment_model.pkl")
        except FileNotFoundError:
            st.error("Model file 'catboost_employment_model.pkl' not found.")
            st.stop()

    model = load_employment_model()

    # -----------------------------
    # 3. Define categorical mappings
    # -----------------------------
    categorical_features = ["student_faculty", "student_gender", "student_marital_status", "grade_bucket"]

    faculty_grade_map = {'Pass': 3, 'Good': 2, 'Very Good': 1, 'Excellent': 0}
    iti_status_map = {'Failed to Graduate': 1, 'Graduated': 0}

    # -----------------------------
    # 4. App Title
    # -----------------------------
    st.markdown("<h2 style='text-align:center;'>⚙️ Student Employment Predictor</h2>", unsafe_allow_html=True)

    st.markdown("<p style='text-align:center;'> Predict Whether a Student is Likely To Be Employed After Completing ITI Program.</p>", unsafe_allow_html=True)

    st.divider()

    # -----------------------------
    # 5. Input Section
    # -----------------------------
    st.header("📋 Student Details")

    col1, col2 = st.columns(2)

    with col1:
        student_faculty_grade = st.selectbox("Faculty Grade", list(faculty_grade_map.keys()))
        student_iti_status = st.selectbox("ITI Status", list(iti_status_map.keys()))
        total_grade = st.number_input("Total Grade", min_value=0.0, max_value=100.0, step=0.1)
        grade_bucket = st.selectbox("Grade Bucket", ['Low', 'Medium', 'High', 'Top'])

    with col2:
        student_faculty = st.selectbox("Faculty", [
            'Faculty of Computers Sciences', 'Faculty of Engineering', 'Faculty of Information Systems',
            'Faculty of Business Administration', 'Faculty of Commerce', 'Faculty of Agriculture',
            'Faculty of Science', 'Faculty of Fine Arts', 'Faculty of Applied Arts',
            'Faculty of Arts', 'Faculty of Economics and Political Science', 'Faculty of Education'
        ])
        student_gender = st.selectbox("Gender", ['Male', 'Female'])
        student_marital_status = st.selectbox("Marital Status", ['Single', 'Married'])

    st.divider()

    # -----------------------------
    # 6. Prepare input for prediction
    # -----------------------------
    input_dict = {
        "student_faculty_grade": [faculty_grade_map[student_faculty_grade]],
        "student_iti_status": [iti_status_map[student_iti_status]],
        "total_grade": [total_grade],
        "student_faculty": [student_faculty],
        "student_gender": [student_gender],
        "student_marital_status": [student_marital_status],
        "grade_bucket": [grade_bucket]
    }

    input_df = pd.DataFrame(input_dict)

    # -----------------------------
    # 7. Prediction Section
    # -----------------------------
    if st.button("🔍 Predict Employment Status", use_container_width=True):
        with st.spinner("Analyzing student profile..."):
            input_pool = Pool(input_df, cat_features=categorical_features)
            prediction = model.predict(input_pool)[0]
            prediction_proba = model.predict_proba(input_pool)[0]

        st.divider()
        st.header("📊 Prediction Result")

        if prediction == 1:
            st.success("✅ **The student is likely to be Employed**")
        else:
            st.error("❌ **The student is likely to be Unemployed**")

        st.subheader("🔢 Prediction Probabilities")
        col_a, col_b = st.columns(2)
        col_a.metric("Employed Probability", f"{prediction_proba[1]*100:.1f} %")
        col_b.metric("Unemployed Probability", f"{prediction_proba[0]*100:.1f} %")

        st.caption("⚙️ Model: CatBoostClassifier | Based on academic and demographic inputs")

# =====================================================================
# 🤖 TAB 4: Student Grade Predictor
# =====================================================================
with tab4:
        
    st.markdown("<h2 style='text-align:center;'>🤖 Student Grade Predictor</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;'>Use this app to predict a student's final grade based on their academic and demographic profile.</p>", unsafe_allow_html=True)
    st.divider()

    # -----------------------------
    # 1. Load Model
    # -----------------------------
    @st.cache_resource
    def load_grade_model():
        # Load the pipeline we just built
        try:
            model = joblib.load("iti_grade_predictor_pipeline.pkl")
            return model
        except FileNotFoundError:
            st.error("Model file 'iti_grade_predictor_pipeline.pkl' not found.")
            st.stop()
        except Exception as e:
            st.error(f"Error loading model: {e}")
            st.stop()

    model = load_grade_model()

    # -----------------------------
    # 2. Helper Functions & Mappings
    # -----------------------------

    # This mapping is CRITICAL. Our pipeline expects the mapped number.
    FACULTY_GRADE_MAP = {'Excellent': 0, 'Very Good': 1, 'Good': 2, 'Pass': 3}
    
    # --- IMPORTANT: Update this list with all your real branch names ---
    BRANCH_NAMES = ['Sohag', 'Smart Village', 'Zagazig', 'Damanhour', 'Qena', 'Tanta',
       'El Menoufia', 'El Mansoura', 'Aswan', 'El Minia',
       'Cairo University', 'Ismailia', 'New Capital', 'Beni Sweif',
       'El Fayoum', 'Alexandria', 'Assiut', 'Port Said', 'New Valley',
       'Benha', 'Al Arish']
    
    # This function is CRITICAL. Our pipeline expects the 'faculty_group' feature.
    def faculty_group(faculty):
        stem = ['Faculty of Computers Sciences', 'Faculty of Engineering', 'Faculty of Information Systems', 'Faculty of Science']
        business = ['Faculty of Business Administration', 'Faculty of Commerce', 'Faculty of Economics and Political Science']
        arts = ['Faculty of Fine Arts', 'Faculty of Applied Arts', 'Faculty of Arts']
        applied = ['Faculty of Agriculture', 'Faculty of Education']
        if faculty in stem:
            return 'STEM'
        elif faculty in business:
            return 'Business'
        elif faculty in arts:
            return 'Arts'
        elif faculty in applied:
            return 'Applied'
        else:
            return 'Other'

    # -----------------------------
    # 3. Input Section (MODIFIED)
    # -----------------------------
    st.header("📋 Student Profile")

    col1, col2 = st.columns(2)

    with col1:
        student_faculty = st.selectbox("Faculty", [
            'Faculty of Computers Sciences', 'Faculty of Engineering', 'Faculty of Information Systems',
            'Faculty of Business Administration', 'Faculty of Commerce', 'Faculty of Agriculture',
            'Faculty of Science', 'Faculty of Fine Arts', 'Faculty of Applied Arts',
            'Faculty of Arts', 'Faculty of Economics and Political Science', 'Faculty of Education'
        ], key="grade_faculty") # Added key to avoid widget collision
        
        student_gender = st.selectbox("Gender", ['Male', 'Female'], key="grade_gender")
        
        # --- NEW INPUT ---
        branch_name = st.selectbox("Branch Name", BRANCH_NAMES)
        
    with col2:
        student_faculty_grade_str = st.selectbox("Faculty Grade", list(FACULTY_GRADE_MAP.keys()), key="grade_faculty_grade")
        
        student_marital_status = st.selectbox("Marital Status", ['Single', 'Married'], key="grade_marital_status")

        year_str = st.selectbox("Year", ['2023', '2024'])

    st.divider()
    
    # -----------------------------
    # 4. Prepare input for prediction (MODIFIED)
    # -----------------------------

    try:
        faculty_grade_num = FACULTY_GRADE_MAP[student_faculty_grade_str]
        faculty_group_str = faculty_group(student_faculty)
        # We don't need 'year_str = str(year_num)' anymore

        # Create the dictionary that matches our pipeline's feature names
        input_dict = {
            "student_faculty_grade": [faculty_grade_num],
            "student_gender": [student_gender],
            "student_marital_status": [student_marital_status],
            "faculty_group": [faculty_group_str],
            "branch_name": [branch_name], 
            "year": [year_str]          # --- This now uses the selectbox value directly ---
        }

        input_df = pd.DataFrame(input_dict)
    except Exception as e:
        st.error(f"Error preparing input data: {e}")
        st.stop()


    # -----------------------------
    # 5. Prediction Section (MODIFIED)
    # -----------------------------
    if st.button("🔍 Predict Final Grade", use_container_width=True):
        with st.spinner("Calculating grade..."):
            
            # --- DEFINE YOUR REAL MIN/MAX GRADE ---
            TOTAL_MIN_GRADE = 0.0
            TOTAL_MAX_GRADE = 120.0 # 12 subjects * 10 marks
            
            # Use the pipeline to predict. It handles all preprocessing.
            prediction_raw = model.predict(input_df)[0] # [0] to get the single value

            # --- Clamp the prediction to the realistic 0-120 range ---
            prediction_clamped = max(TOTAL_MIN_GRADE, min(prediction_raw, TOTAL_MAX_GRADE))
            
            # --- Calculate percentage ---
            prediction_percentage = (prediction_clamped / TOTAL_MAX_GRADE) * 100

        st.divider()
        st.header("📊 Predicted Grade")

        # --- NEW: Show percentage and raw score in columns ---
        col_res_1, col_res_2 = st.columns(2)
        
        with col_res_1:
            # Display the percentage result in a clean metric box
            st.metric(label="Predicted Grade (Percentage)", value=f"{prediction_percentage:.1f} %")
        
        with col_res_2:
            # Display the raw score
            st.metric(label="Predicted Score (out of 120)", value=f"{prediction_clamped:.1f} pts")

        
        st.success(f"The model predicts a final grade of **{prediction_clamped:.1f} / {TOTAL_MAX_GRADE}**.")

        # Show a warning if the model's raw prediction was unrealistic
        if prediction_raw != prediction_clamped:
            st.warning(f"Note: The model's raw prediction was {prediction_raw:.1f}, "
                       f"but it has been capped to the realistic range of {TOTAL_MIN_GRADE}-{TOTAL_MAX_GRADE}.")