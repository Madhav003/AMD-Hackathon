import streamlit as st
from security import scrub_sensitive_data

# 1. PAGE SETUP
st.set_page_config(page_title="SafeStudy AI", page_icon="🛡️", layout="wide")

# 2. INITIALIZE SESSION STATE (Memory)
if "stats" not in st.session_state:
    st.session_state.stats = {
        "Identity": 0,
        "Financial/ID": 0,
        "Academic": 0,
        "Security Threat": 0
    }
if "total_scanned" not in st.session_state:
    st.session_state.total_scanned = 0
if "messages" not in st.session_state:
    st.session_state.messages = []

# 3. SIDEBAR: STATISTICAL ANALYSIS
st.sidebar.title("📊 Statistical Analysis")
st.sidebar.write("Data detected by category:")
st.sidebar.table(st.session_state.stats)

st.sidebar.divider()
st.sidebar.metric("Total Interactions Scanned", st.session_state.total_scanned)

# 4. MAIN UI
st.title("🛡️ SafeStudy AI")
st.markdown("### Secure Academic Assistant")
st.info("Privacy Shield Active: All PII is redacted locally before AI processing.")

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 5. USER INPUT & LOGIC
if prompt := st.chat_input("Ask a study question..."):
    # Increment total scanned
    st.session_state.total_scanned += 1
    
    # Display user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Run the Security Shield
    with st.spinner("Analyzing for PII..."):
        report = scrub_sensitive_data(prompt)
        
        # Update Statistics memory
        for category in report["categories"]:
            st.session_state.stats[category] += 1
        
        # Determine Response
        if report["is_threat"]:
            answer = f"🚨 **Security Warning:** {report['clean_text']}"
            st.error("Malicious intent detected. Event logged.")
        else:
            answer = f"**Sent to AI (Scrubbed):** {report['clean_text']}"
            if report["categories"]:
                st.warning(f"Note: {', '.join(report['categories'])} data was redacted for your safety.")

        # Show assistant message
        with st.chat_message("assistant"):
            st.markdown(answer)
        st.session_state.messages.append({"role": "assistant", "content": answer})
        
    # Refresh sidebar to show updated counts
    st.rerun()