import streamlit as st
import os

# folder to store uploaded cvs
UPLOAD_FOLDER = "cv_documents"

# create folder if it doesnt exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

st.title("📄 HR AI ASSISTANT TOOL")
st.write("Upload CVs in PDF, DOCX, or TXT format. The tool will process them and create a store for comparison.")

uploaded_files = st.file_uploader(
    "Choose CV files to upload",
    type=["pdf", "docx", "txt"],
    accept_multiple_files=True
)

if uploaded_files:
    st.write(f"**{len(uploaded_files)} files selected**")

    with st.spinner("Saving files..."):
        for uploaded_file in uploaded_files:
            #Build the full path to save the file
            save_path = os.path.join(UPLOAD_FOLDER, uploaded_file.name)

            # Save file to folder
            with open(save_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

    st.success("✅ All files uploaded successfully!")

    # process 

else:
    st.warning("👉 Please upload at least one CV file to proceed.")