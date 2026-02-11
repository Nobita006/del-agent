import streamlit as st
import os
import shutil
import pandas as pd
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
            # Force rerun to update UI state
            st.rerun()

        if st.button("âš ï¸  Clear All Data"):
            if os.path.exists("data"):
                for f in os.listdir("data"):
                    os.remove(os.path.join("data", f))
            st.session_state.agent.df = None
            st.rerun()

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
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            content = msg["content"]
            
            # Handle different content types
            # 1. Charts
            if hasattr(content, 'figure') or hasattr(content, 'show'):
                 try:
                    st.pyplot(content)
                 except:
                    st.plotly_chart(content)
            # 2. DataFrames
            elif isinstance(content, (pd.DataFrame, pd.Series)):
                 st.dataframe(content)
            # 3. Text
            else:
                 st.markdown(content)
                 
            # Show explanation if exists and is assistant
            if msg["role"] == "assistant" and "explanation" in msg:
                 with st.expander("Show Verification Steps"):
                      st.info(msg["explanation"])

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
                
                # Handle different result types
                # 1. Charts (Matplotlib / Plotly)
                if hasattr(result, 'figure') or hasattr(result, 'show'): 
                    # Heuristic for plotly/matplotlib figures
                    try:
                        st.pyplot(result)
                    except:
                        st.plotly_chart(result)
                    st.write(explanation)
                    
                # 2. DataFrames / Lists (Exportable)
                elif isinstance(result, (pd.DataFrame, pd.Series, list)):
                    if isinstance(result, list):
                        result = pd.DataFrame(result)
                    
                    st.dataframe(result)
                    
                    # CSV Download
                    csv = result.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="Download as CSV",
                        data=csv,
                        file_name='agent_data_export.csv',
                        mime='text/csv',
                    )
                    st.write(f"Explanation: {explanation}")
                    
                # 3. Standard Text / String
                else:
                    st.markdown(result)
                    if explanation:
                        with st.expander("Show Verification Steps"):
                            st.info(explanation)
            
            # Save to history (store string rep for now to avoid pickle issues if needed, or just store object)
            # Storing object in session state is fine.
            st.session_state.messages.append({
                "role": "assistant", 
                "content": result,
                "explanation": explanation
            })

if __name__ == "__main__":
    main()
