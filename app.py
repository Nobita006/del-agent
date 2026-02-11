import streamlit as st
import os
import shutil
from src.agent import ExcelAgent

st.set_page_config(page_title="Availability Data Excel Agent", page_icon="ðŸ“Š", layout="wide")

# Initialize Session State
if "messages" not in st.session_state:
    st.session_state.messages = []
if "agent" not in st.session_state:
    st.session_state.agent = ExcelAgent("data")

def main():
    st.title("Availability Data Excel Agent")
    
    # Sidebar: File Upload
    with st.sidebar:
        st.header("Data Upload")
        uploaded_file = st.file_uploader("Upload Weekly Excel", type=["xlsx", "xls"])
        
        if uploaded_file:
            # Save file to data directory
            os.makedirs("data", exist_ok=True)
            file_path = os.path.join("data", uploaded_file.name)
            
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
                
            st.success(f"Saved: {uploaded_file.name}")
            
            # Reload Agent
            msg = st.session_state.agent.load_data()
            st.info(msg)

    # Main Chat Interface
    
    # Init agent if not loaded
    if st.session_state.agent.df is None:
        # Try loading defaults
        msg = st.session_state.agent.load_data()
        if "Error" in msg and "No Excel file" in msg:
            st.warning("Please upload an Excel file to begin.")
        else:
            st.success(f"Ready! {msg}")

    # Display Chat History
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if "explanation" in message and message["explanation"]:
                with st.expander("Show Verification Steps"):
                    st.info(message["explanation"])

    # Chat Input
    if prompt := st.chat_input("Ask a question about the data..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate Response
        with st.chat_message("assistant"):
            with st.spinner("Analyzing..."):
                response_dict = st.session_state.agent.run(prompt)
                result = response_dict["result"]
                explanation = response_dict["explanation"]
                
                # Format Response
                st.markdown(f"**Answer:** {result}")
                if explanation:
                    with st.expander("Show Verification Steps"):
                        st.info(explanation)
                
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": f"**Answer:** {result}",
                    "explanation": explanation
                })

if __name__ == "__main__":
    main()
