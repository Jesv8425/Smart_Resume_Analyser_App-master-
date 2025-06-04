import streamlit as st
import nltk
import spacy
import pandas as pd
import base64, random
import time, datetime
from pyresparser import ResumeParser
from pdfminer3.layout import LAParams, LTTextBox
from pdfminer3.pdfpage import PDFPage
from pdfminer3.pdfinterp import PDFResourceManager
from pdfminer3.pdfinterp import PDFPageInterpreter
from pdfminer3.converter import TextConverter
import io, random
from streamlit_tags import st_tags
from PIL import Image
import psycopg2
from Courses import ds_course, web_course, android_course, ios_course, uiux_course, resume_videos, interview_videos
import plotly.express as px
import yt_dlp as youtube_dl
from test import extract_text_from_pdf, extract_skills
import time
from pdf2image import convert_from_path
import pytesseract
import io
import re


# YouTube video links
resume_videos = [
    "https://youtu.be/y8YH0Qbu5h4?si=ElkTBTRDrRsHvmd",
    "https://youtu.be/Tt08KmFfIYQ?si=T6u_FSsVBMt7xYSV"   # Indeed Career Guide
]

interview_videos = [
    "https://youtu.be/gDN7cJ3Rt80?si=upLexEql1HR_RtIi",  # CareerVidz
    "https://youtu.be/fr-mwiyhZAo?si=MNFkhFapBoH_rJDE"   # Linda Raynier
]

# Function to fetch YouTube video title
def fetch_yt_video(link):
    try:
        ydl_opts = {"quiet": True, "noplaylist": True}
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(link, download=False)
            return info.get("title", "Unknown Title")
    except Exception as e:
        st.error(f"Error fetching video title: {e}")
        return "Video Title Not Found"

# Function to generate a download link for a DataFrame
def get_table_download_link(df, filename, text):
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">{text}</a>'
    return href

# Function to read text from a PDF file
# def pdf_reader(file):
#     resource_manager = PDFResourceManager()
#     fake_file_handle = io.StringIO()
#     converter = TextConverter(resource_manager, fake_file_handle, laparams=LAParams())
#     page_interpreter = PDFPageInterpreter(resource_manager, converter)
#     with open(file, 'rb') as fh:
#         for page in PDFPage.get_pages(fh, caching=True, check_extractable=True):
#             page_interpreter.process_page(page)
#         text = fake_file_handle.getvalue()
#     converter.close()
#     fake_file_handle.close()
#     return text

def pdf_reader(file):
    resource_manager = PDFResourceManager()
    fake_file_handle = io.StringIO()
    converter = TextConverter(resource_manager, fake_file_handle, laparams=LAParams())
    page_interpreter = PDFPageInterpreter(resource_manager, converter)
    text = ""

    try:
        # Attempt to extract text from each page of the PDF
        with open(file, 'rb') as fh:
            for page_number, page in enumerate(PDFPage.get_pages(fh, caching=True, check_extractable=True), start=1):
                page_interpreter.process_page(page)
                page_text = fake_file_handle.getvalue().strip()
                if page_text:  # If text is found, append it
                    text += page_text + "\n"
                else:  # If no text is found, treat the page as an image
                    images = convert_from_path(file, first_page=page_number, last_page=page_number)
                    for image in images:
                        text += pytesseract.image_to_string(image) + "\n"
                fake_file_handle.truncate(0)
                fake_file_handle.seek(0)
    except Exception as e:
        print(f"Error processing PDF: {e}")

    converter.close()
    fake_file_handle.close()

    # Clean the text to remove special characters, Markdown, and extra whitespace
    pure_text = re.sub(r'[^\w\s]', '', text)  # Remove all non-alphanumeric characters except spaces and newlines
    pure_text = re.sub(r'\s+', ' ', pure_text)  # Replace multiple spaces/newlines with a single space
    pure_text = pure_text.strip()  # Remove leading and trailing whitespace

    # Return the cleaned text
    return pure_text

# Function to display a PDF file in the app
def show_pdf(file_path):
    with open(file_path, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode('utf-8')
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="700" height="1000" type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)

# Function to recommend courses
def course_recommender(course_list):
    st.subheader("**Courses & Certificates🎓 Recommendations**")
    c = 0
    rec_course = []
    no_of_reco = st.slider('Choose Number of Course Recommendations:', 1, 10, 4)
    random.shuffle(course_list)
    for c_name, c_link in course_list:
        c += 1
        st.markdown(f"({c}) [{c_name}]({c_link})")
        rec_course.append(c_name)
        if c == no_of_reco:
            break
    return rec_course

# Database connection
connection = psycopg2.connect(host='localhost', user='jesvanth', password='jesvanth@11', dbname='sra')
cursor = connection.cursor()

# Function to insert data into the database
def insert_data(name, email, res_score, timestamp, no_of_pages, reco_field, cand_level, skills, recommended_skills, courses):
    DB_table_name = 'user_data'
    name = name if name is not None else "Unknown"
    check_query = f"SELECT * FROM {DB_table_name} WHERE email_id = %s"
    cursor.execute(check_query, (email,))
    existing_record = cursor.fetchone()

    if existing_record:
        st.warning("This email already exists in the database. Skipping insertion.")
    else:
        insert_sql = f"""
        INSERT INTO {DB_table_name} (name, email_id, resume_score, timestamp, page_no, predicted_field, user_level, actual_skills, recommended_skills, recommended_courses) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        rec_values = (name, email, str(res_score), timestamp, str(no_of_pages), reco_field, cand_level, skills, recommended_skills, courses)
        try:
            cursor.execute(insert_sql, rec_values)
            connection.commit()
            st.success("Data inserted successfully!")
        except Exception as e:
            print("Error inserting data:", e)

# Streamlit app configuration
st.set_page_config(
    page_title="Smart Resume Analyzer",
    page_icon='./Logo/RESUME.ico',
)

# Main function to run the app
def run():
    st.title(" AI-POWERED RESUME SCREENING USING NLP AND MACHINE LEARNING")
    st.sidebar.markdown("# Choose User")
    activities = ["Normal User", "Admin"]
    choice = st.sidebar.selectbox("Choose among the given options:", activities)
    img = Image.open('./Logo/RESUME.jpg')
    img = img.resize((850, 450))
    st.image(img)

    # Create table in the database if it doesn't exist
    DB_table_name = 'user_data'
    table_sql = f"""
    CREATE TABLE IF NOT EXISTS {DB_table_name} (
        ID SERIAL NOT NULL,
        Name varchar(100) NOT NULL,
        Email_ID VARCHAR(50) NOT NULL,
        resume_score VARCHAR(8) NOT NULL,
        Timestamp VARCHAR(50) NOT NULL,
        Page_no VARCHAR(5) NOT NULL,
        Predicted_Field VARCHAR(25) NOT NULL,
        User_level VARCHAR(30) NOT NULL,
        Actual_skills VARCHAR(300) NOT NULL,
        Recommended_skills VARCHAR(300) NOT NULL,
        Recommended_courses VARCHAR(600) NOT NULL,
        PRIMARY KEY (ID)
    );
    """
    cursor.execute(table_sql)

    if choice == 'Normal User':
        user_name = st.text_input("Enter your name:")
        pdf_file = st.file_uploader("Choose your Resume", type=["pdf"])
        
        if pdf_file is not None:
            global resume_path
            resume_path = './Uploaded_Resumes/' + pdf_file.name
            with open(resume_path, "wb") as f:
                f.write(pdf_file.getbuffer())

            show_pdf(resume_path)

            resume_data = ResumeParser(resume_path, skills_file="./skills.csv").get_extracted_data()
            print(resume_data)

            if resume_data:
                resume_text = pdf_reader(resume_path)

                st.header("**Resume Analysis**")
                st.success("Hello " + (user_name if user_name else "Candidate"))
                st.subheader("**Your Basic info**")
                try:
                    st.text('Name: ' + user_name)
                    st.text('Email: ' + resume_data['email'])
                    st.text('Contact: ' + resume_data['mobile_number'])
                    st.text('Resume pages: ' + str(resume_data['no_of_pages']))
                except Exception as e:
                    print(f'Exception occured: {e} ')

                cand_level = ''
                if resume_data['no_of_pages'] == 1:
                    cand_level = "Fresher"
                    st.markdown('''<h4 style='text-align: left; color: #d73b5c;'>You are looking Fresher.</h4>''',
                                unsafe_allow_html=True)
                elif resume_data['no_of_pages'] == 2:
                    cand_level = "Intermediate"
                    st.markdown('''<h4 style='text-align: left; color: #1ed760;'>You are at intermediate level!</h4>''',
                                unsafe_allow_html=True)
                elif resume_data['no_of_pages'] >= 3:
                    cand_level = "Experienced"
                    st.markdown('''<h4 style='text-align: left; color: #fba171;'>You are at experience level!''',
                                unsafe_allow_html=True)

                st.subheader("**Skills Recommendation💡**")
                if 'skills' in resume_data and resume_data['skills']:
                    global extracted_skills
                    print(resume_path)
                    text = extract_text_from_pdf(resume_path)
                    extracted_skills = extract_skills(text)
                    extracted_skills = [skill.lower() for skill in extracted_skills]
                    st.markdown('''<h4 style='text-align: left; color: #1ed760;'>Skills extracted from your resume:</h4>''',
                                unsafe_allow_html=True)
                    keywords = st_tags(label='### Skills that you have',
                                       text='See our skills recommendation',
                                       value=extracted_skills, key='1')
                else:
                    st.warning("No skills found in the resume. Please ensure your resume contains relevant skills.")

                ## Skill recommendation logic
                ds_keyword = ['tensorflow', 'keras', 'pytorch', 'machine learning', 'deep Learning', 'flask', 'streamlit']
                web_keyword = ['react', 'django', 'node jS', 'react js', 'php', 'laravel', 'magento', 'wordpress',
                               'javascript', 'angular js', 'c#', 'flask']
                android_keyword = ['android', 'android development', 'flutter', 'kotlin', 'xml', 'kivy']
                ios_keyword = ['ios', 'ios development', 'swift', 'cocoa', 'cocoa touch', 'xcode']
                uiux_keyword = ['ux', 'adobe xd', 'figma', 'zeplin', 'balsamiq', 'ui', 'prototyping', 'wireframes',
                                'storyframes', 'adobe photoshop', 'photoshop', 'editing', 'adobe illustrator',
                                'illustrator', 'adobe after effects', 'after effects', 'adobe premier pro',
                                'premier pro', 'adobe indesign', 'indesign', 'wireframe', 'solid', 'grasp',
                                'user research', 'user experience']

                recommended_skills = []
                reco_field = ''
                rec_course = ''

                if 'skills' in resume_data and resume_data['skills']:
                    for skill in extracted_skills:
                        if skill in ds_keyword:
                            reco_field = 'Data Science'
                            st.success("** Our analysis says you are looking for Data Science Jobs.**")
                            recommended_skills = ['Data Visualization', 'Predictive Analysis', 'Statistical Modeling',
                                                  'Data Mining', 'Clustering & Classification', 'Data Analytics',
                                                  'Quantitative Analysis', 'Web Scraping', 'ML Algorithms', 'Keras',
                                                  'Pytorch', 'Probability', 'Scikit-learn', 'Tensorflow', "Flask",
                                                  'Streamlit']
                            break
                        elif skill in web_keyword:
                            reco_field = 'Web Development'
                            st.success("** Our analysis says you are looking for Web Development Jobs **")
                            recommended_skills = ['React', 'Django', 'Node JS', 'React JS', 'php', 'laravel', 'Magento',
                                                  'wordpress', 'Javascript', 'Angular JS', 'c#', 'Flask', 'SDK']
                            break
                        # Add similar logic for other fields (Android, iOS, UI/UX)

                    # Debug: Print the recommended field
                    st.write(f"Recommended Field: {reco_field}")

                    if recommended_skills:
                        st.markdown('''<h4 style='text-align: left; color: #1ed760;'>Recommended skills for you:</h4>''',
                                    unsafe_allow_html=True)
                        recommended_keywords = st_tags(label='### Recommended skills for you.',
                                                       text='Recommended skills generated from System',
                                                       value=recommended_skills, key='2')
                        st.markdown(
                            '''<h4 style='text-align: left; color: #1ed760;'>Adding these skills to your resume will boost🚀 your chances of getting a Job💼</h4>''',
                            unsafe_allow_html=True)
                        
                        # Call course_recommender and display its output
                        if reco_field:
                            rec_course = course_recommender(ds_course if reco_field == 'Data Science' else
                                                           web_course if reco_field == 'Web Development' else
                                                           android_course if reco_field == 'Android Development' else
                                                           ios_course if reco_field == 'IOS Development' else
                                                           uiux_course)
                            st.write("Recommended Courses:", rec_course)  # Debug: Display recommended courses
                        else:
                            st.warning("No career field detected. Cannot recommend courses.")

                ## Insert into table
                ts = time.time()
                cur_date = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
                cur_time = datetime.datetime.fromtimestamp(ts).strftime('%H:%M:%S')
                timestamp = str(cur_date + '_' + cur_time)
                ### Resume writing recommendation
                st.subheader("**Resume Tips & Ideas💡**")
                resume_score = 0
                if 'Objective' in resume_text:
                    resume_score = resume_score + 20
                    st.markdown(
                        '''<h4 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added Objective</h4>''',
                        unsafe_allow_html=True)
                else:
                    st.markdown(
                        '''<h4 style='text-align: left; color: #fabc10;'>[-] According to our recommendation please add your career objective, it will give your career intension to the Recruiters.</h4>''',
                        unsafe_allow_html=True)

                if 'Declaration' in resume_text:
                    resume_score = resume_score + 20
                    st.markdown(
                        '''<h4 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added Delcaration✍/h4>''',
                        unsafe_allow_html=True)
                else:
                    st.markdown(
                        '''<h4 style='text-align: left; color: #fabc10;'>[-] According to our recommendation please add Declaration✍. It will give the assurance that everything written on your resume is true and fully acknowledged by you</h4>''',
                        unsafe_allow_html=True)

                if 'Hobbies' or 'Interests' in resume_text:
                    resume_score = resume_score + 20
                    st.markdown(
                        '''<h4 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added your Hobbies⚽</h4>''',
                        unsafe_allow_html=True)
                else:
                    st.markdown(
                        '''<h4 style='text-align: left; color: #fabc10;'>[-] According to our recommendation please add Hobbies⚽. It will show your persnality to the Recruiters and give the assurance that you are fit for this role or not.</h4>''',
                        unsafe_allow_html=True)

                if 'Achievements' in resume_text:
                    resume_score = resume_score + 20
                    st.markdown(
                        '''<h4 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added your Achievements🏅 </h4>''',
                        unsafe_allow_html=True)
                else:
                    st.markdown(
                        '''<h4 style='text-align: left; color: #fabc10;'>[-] According to our recommendation please add Achievements🏅. It will show that you are capable for the required position.</h4>''',
                        unsafe_allow_html=True)

                if 'Projects' in resume_text:
                    resume_score = resume_score + 20
                    st.markdown(
                        '''<h4 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added your Projects👨‍💻 </h4>''',
                        unsafe_allow_html=True)
                else:
                    st.markdown(
                        '''<h4 style='text-align: left; color: #fabc10;'>[-] According to our recommendation please add Projects👨‍💻. It will show that you have done work related the required position or not.</h4>''',
                        unsafe_allow_html=True)

                st.subheader("**Resume Score📝**")
                st.markdown(
                    """
                    <style>
                        .stProgress > div > div > div > div {
                            background-color: #d73b5c;
                        }
                    </style>""",
                    unsafe_allow_html=True,
                )
                my_bar = st.progress(0)
                score = 0
                for percent_complete in range(resume_score):
                    score += 1
                    time.sleep(0.1)
                    my_bar.progress(percent_complete + 1)
                st.success('** Your Resume Writing Score: ' + str(score) + '**')
                st.warning(
                    "** Note: This score is calculated based on the content that you have added in your Resume. **")
                st.balloons()

                # Insert data into the database
                insert_data(user_name, resume_data['email'], str(resume_score), timestamp,
                           str(resume_data['no_of_pages']), reco_field, cand_level, str(extracted_skills),
                           str(recommended_skills), str(rec_course))

                # Resume Writing Video
                st.header("**Bonus Video for Resume Writing Tips💡**")
                resume_vid = random.choice(resume_videos)
                print(f"Selected Resume Video: {resume_vid}") 
                res_vid_title = fetch_yt_video(resume_vid)
                st.subheader(f"✅ **{res_vid_title}**")
                st.video(resume_vid)

                # Interview Preparation Video
                st.header("**Bonus Video for Interview👨‍💼 Tips💡**")
                interview_vid = random.choice(interview_videos)
                print(f"Selected Interview Video: {interview_vid}")
                int_vid_title = fetch_yt_video(interview_vid)
                st.subheader(f"✅ **{int_vid_title}**")
                st.video(interview_vid)

                connection.commit()
            else:
                st.error('Something went wrong..')
    else:
        
        ## Admin Side
        st.success('Welcome to Admin Side')
        # st.sidebar.subheader('**ID / Password Required!**')

        ad_user = st.text_input("Username")
        ad_password = st.text_input("Password", type='password')
        if st.button('Login'):
            if ad_user == 'admin' and ad_password == 'admin123':
                st.success("Welcome Jesvanth")
                # Display Data
                cursor.execute('''SELECT*FROM user_data''')
                data = cursor.fetchall()
                st.header("**User's👨‍💻 Data**")
                df = pd.DataFrame(data, columns=['id', 'name', 'email_id', 'resume_score', 'timestamp', 'page_no',
                                 'predicted_field', 'user_level', 'actual_skills', 'recommended_skills',
                                 'recommended_courses'])
                st.dataframe(df)
                st.markdown(get_table_download_link(df, 'User_Data.csv', 'Download Report'), unsafe_allow_html=True)
                ## Admin Side Data
                query = 'select * from user_data;'
                plot_data = pd.read_sql(query, connection)

                ## Pie chart for predicted field recommendations
                labels = df['predicted_field'].unique()  # Use the correct column name
                print(labels)
                values = df['predicted_field'].value_counts()  # Use the correct column name
                print(values)
                st.subheader("📈 **Pie-Chart for Predicted Field Recommendations**")
                fig = px.pie(df, values=values, names=labels, title='Predicted Field according to the Skills')
                st.plotly_chart(fig)

                ### Pie chart for User's👨‍💻 Experienced Level
                labels = df['user_level'].unique()  # Use the correct column name
                values = df['user_level'].value_counts()  # Use the correct column name
                st.subheader("📈 ** Pie-Chart for User's👨‍💻 Experienced Level**")
                fig = px.pie(df, values=values, names=labels, title="Pie-Chart📈 for User's👨‍💻 Experienced Level")
                st.plotly_chart(fig)


            else:
                st.error("Wrong ID & Password Provided")


# def main():
#     from llm_based_analysis import llm_resume_analysis
#     import json
#     st.title("LLM-Based Resume Analysis")
#     st.write("Upload your resume in PDF format for analysis.")
#     # Create a directory for uploaded resumes if it doesn't exist
#     pdf_file = st.file_uploader("Upload your resume (PDF)", type=["pdf"])
#     if pdf_file is not None:
#         resume_path = './Uploaded_Resumes/' + pdf_file.name
#         with open(resume_path, "wb") as f:
#             f.write(pdf_file.getbuffer())

#         show_pdf(resume_path)

#         # Extract text from the uploaded PDF
#         resume_text = pdf_reader(resume_path)

#         # Use the LLM-based analysis
#         llm_json_response = llm_resume_analysis(resume_text)
#         try:
#             response = json.loads(llm_json_response)
#             st.header("**LLM-Based Resume Analysis**")
#             st.subheader("Predicted Field")
#             st.success(response.get("predicted_field", "N/A"))

#             st.subheader("Extracted Skills")
#             st.write(", ".join(response.get("extracted_skills", [])))

#             st.subheader("Resume Score")
#             st.progress(response.get("resume_score", 0))

#             st.subheader("Suggestions for Improvement")
#             for suggestion in response.get("suggestions", []):
#                 st.markdown(f"- {suggestion}")
#         except json.JSONDecodeError:
#             st.error("Error: Unable to parse the LLM response.")
# run()

# main()

def updated_main():
    from llm_based_analysis import llm_resume_analysis
    import json
    st.title("AI-POWERED RESUME SCREENING USING NLP AND MACHINE LEARNING")
    st.sidebar.markdown("# Choose User")
    activities = ["Normal User", "Admin"]
    choice = st.sidebar.selectbox("Choose among the given options:", activities)
    img = Image.open('./Logo/RESUME.jpg')
    img = img.resize((850, 450))
    st.image(img)

    # Create table in the database if it doesn't exist
    DB_table_name = 'user_data'
    table_sql = f"""
    CREATE TABLE IF NOT EXISTS {DB_table_name} (
        ID SERIAL NOT NULL,
        Name varchar(100) NOT NULL,
        Email_ID VARCHAR(50) NOT NULL,
        resume_score VARCHAR(8) NOT NULL,
        Timestamp VARCHAR(50) NOT NULL,
        Page_no VARCHAR(5) NOT NULL,
        Predicted_Field VARCHAR(25) NOT NULL,
        User_level VARCHAR(30) NOT NULL,
        Actual_skills VARCHAR(300) NOT NULL,
        Recommended_skills VARCHAR(300) NOT NULL,
        Recommended_courses VARCHAR(600) NOT NULL,
        PRIMARY KEY (ID)
    );
    """
    cursor.execute(table_sql)

    if choice == 'Normal User':
        #user_name = st.text_input("Enter your name:")
        pdf_file = st.file_uploader("Choose your Resume", type=["pdf"])

        if pdf_file is not None:
            resume_path = './Uploaded_Resumes/' + pdf_file.name
            with open(resume_path, "wb") as f:
                f.write(pdf_file.getbuffer())

            show_pdf(resume_path)

            # Extract text from the uploaded PDF
            resume_text = pdf_reader(resume_path)
            st.success(resume_text)
            llm_json_response = None
            max_retries = 10  # Maximum number of retries
            retry_interval = 2  # Time to wait between retries (in seconds)

            # Use the LLM-based analysis
            # llm_json_response = llm_resume_analysis(resume_text)
            for attempt in range(max_retries):
                llm_json_response = llm_resume_analysis(resume_text)
                # Remove the exact "JSON Response:" string if it exists
                if "JSON Response:" in llm_json_response:
                    llm_json_response = llm_json_response.replace("JSON Response:", "", 1).strip()
                if llm_json_response:  # Check if the response is received
                    break
                time.sleep(retry_interval) 

            try:
                if llm_json_response and resume_text:
                    st.success(llm_json_response)
                    response = json.loads(llm_json_response)
                    # st.success(response)
                    # Add custom CSS styles
                    # Add custom CSS styles
                    st.markdown("""
             <style>
        /* From Uiverse.io by Lakshay-art */
        .grid {
            height: 800px;
            width: 800px;gi
            background-image: linear-gradient(to right, #0f0f10 1px, transparent 1px),
                linear-gradient(to bottom, #0f0f10 1px, transparent 1px);
            background-size: 1rem 1rem;
            background-position: center center;
            position: absolute;
            z-index: -1;
            filter: blur(1px);
        }
        .white,
        .border,
        .darkBorderBg,
        .glow {
            max-height: 70px;
            max-width: 314px;
            height: 100%;
            width: 100%;
            position: absolute;
            overflow: hidden;
            z-index: -1;
            border-radius: 12px;
            filter: blur(3px);
        }
        .input {
            background-color: #a1c7a1;
            border: none;
            width: 301px;
            height: 56px;
            border-radius: 10px;
            color: white;
            padding-inline: 59px;
            font-size: 18px;
        }
        .input::placeholder {
            color: #878487;
        }
        .input:focus {
            outline: none;
        }
        .success-box {
            background-color: #ded7d7;
            border: 5px solid transparent;
            border-image: linear-gradient(to right, #ff7f50, #1ed760, #6495ed);
            border-image-slice: 1;
            border-radius: 12px;
            padding: 15px;
            margin-bottom: 20px;
            font-size: 18px;
            color: #0d0c0d;
            box-shadow: 0px 4px 15px rgba(255, 255, 255, 0.1);
            transition: background-color 0.3s ease, box-shadow 0.3s ease;
        }
        .success-box:hover {
            background-color:#b0d1ce;
            box-shadow: 0px 4px 20px rgba(255, 255, 255, 0.3);
        }
        .success-box:active {
            background-color: #f7e479;
            color: #000000;
            box-shadow: 0px 4px 25px rgba(255, 215, 0, 0.5);
        }
    </style>
        """, unsafe_allow_html=True)

                    # Display LLM-Based Resume Analysis
                    st.header("**LLM-Based Resume Analysis**")

                    # Name
                    st.markdown('<div class="section-header">Name:</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="success-box">{response.get("name", "N/A")}</div>', unsafe_allow_html=True)

                    # Email
                    st.markdown('<div class="section-header">Email:</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="success-box">{response.get("email", "N/A")}</div>', unsafe_allow_html=True)

                    # User Level
                    st.markdown('<div class="section-header">User Level:</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="success-box">{response.get("user_level", "N/A")}</div>', unsafe_allow_html=True)

                    # Predicted Field
                    st.markdown('<div class="section-header">Predicted Field:</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="success-box">{response.get("predicted_field", "N/A")}</div>', unsafe_allow_html=True)

                    # Extracted Skills
                    st.markdown('<div class="section-header">Extracted Skills:</div>', unsafe_allow_html=True)
                    extracted_skills = ", ".join(response.get("extracted_skills", []))
                    st.markdown(f'<div class="success-box">{extracted_skills}</div>', unsafe_allow_html=True)
                    

                    # Recommended Skills
                    st.markdown('<div class="section-header">Recommended Skills:</div>', unsafe_allow_html=True)
                    recommended_skills = ", ".join(response.get("recommended_skills", []))
                    st.markdown(f'<div class="success-box">{recommended_skills}</div>', unsafe_allow_html=True)

                    # Resume Score
                    st.markdown('<div class="section-header">Resume Score:</div>', unsafe_allow_html=True)
                    st.progress(response.get("resume_score", 0))

                   
                    st.subheader("Suggestions for Improvement")
                    for suggestion in response.get("suggestions", []):
                        st.markdown(f"- {suggestion}")

                    st.subheader("Recommended Courses")
                    for suggestion in response.get("recommended_courses", []):
                        st.markdown(f"- {suggestion}")
                    ts = time.time()
                    cur_date = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
                    cur_time = datetime.datetime.fromtimestamp(ts).strftime('%H:%M:%S')
                    timestamp = str(cur_date + '_' + cur_time)
                    insert_data(response.get('name', 'N/A'), response.get('email', 'N/A'), response.get('resume_score', 'N/A'), timestamp,
                           '0', response.get('predicted_field', 'N/A'), response.get('user_level', 'N/A'), response.get('extracted_skills', 'N/A'),
                           response.get('recommended_skills', 'N/A'), response.get('recommended_courses', 'N/A'))
                else:
                    st.error("Error: Unable to parse the LLM response or resume text.")
            except json.JSONDecodeError:
                st.error("Error: Unable to parse the LLM response.")

    else:
        st.success('Welcome to Admin Side')
        ad_user = st.text_input("Username")
        ad_password = st.text_input("Password", type='password')
        if st.button('Login'):
            if ad_user == 'admin' and ad_password == 'admin123':
                st.success("Welcome Jesvanth")
                # Display Data
                cursor.execute('''SELECT * FROM user_data''')
                data = cursor.fetchall()
                st.header("**User's👨‍💻 Data**")
                df = pd.DataFrame(data, columns=['id', 'name', 'email_id', 'resume_score', 'timestamp', 'page_no',
                                                'predicted_field', 'user_level', 'actual_skills', 'recommended_skills',
                                                'recommended_courses'])
                st.dataframe(df)
                st.markdown(get_table_download_link(df, 'User_Data.csv', 'Download Report'), unsafe_allow_html=True)

                # Pie chart for predicted field recommendations
                labels = df['predicted_field'].unique()
                values = df['predicted_field'].value_counts()
                st.subheader("📈 **Pie-Chart for Predicted Field Recommendations**")
                fig = px.pie(df, values=values, names=labels, title='Predicted Field according to the Skills')
                st.plotly_chart(fig)

                # Pie chart for User's Experienced Level
                labels = df['user_level'].unique()
                values = df['user_level'].value_counts()
                st.subheader("📈 **Pie-Chart for User's👨‍💻 Experienced Level**")
                fig = px.pie(df, values=values, names=labels, title="Pie-Chart📈 for User's👨‍💻 Experienced Level")
                st.plotly_chart(fig)
            else:
                st.error("Wrong ID & Password Provided")


# Run the app
# run()
updated_main()