"""Streamlit UI application."""
import sys
from pathlib import Path

# Add the src directory to sys.path for direct script execution
sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
import streamlit as st

from config.settings import get_settings

# Get settings
try:
    settings = get_settings()
    api_url = f"http://{settings.api.host}:{settings.api.port}/api"
except:
    api_url = "http://localhost:8000/api"

st.set_page_config(
    page_title="Code Coverage Agent",
    page_icon="🤖",
    layout="wide",
)

st.title("🤖 Code Coverage Agent")
st.markdown("Automated code coverage improvement with LangGraph agents")

# Sidebar for configuration
with st.sidebar:
    st.header("Configuration")
    
    repo_url = st.text_input(
        "Repository URL",
        placeholder="https://dev.azure.com/org/project/_git/repo"
    )
    
    sonar_key = st.text_input(
        "SonarQube Project Key",
        placeholder="my-project"
    )
    
    threshold = st.slider(
        "Coverage Threshold (%)",
        min_value=0,
        max_value=100,
        value=90,
        step=5
    )
    
    start_button = st.button("🚀 Start Workflow", type="primary")

# Main content
tab1, tab2 = st.tabs(["Current Workflow", "Workflow History"])

with tab1:
    st.header("Current Workflow")
    
    if start_button:
        if not repo_url or not sonar_key:
            st.error("Please provide Repository URL and SonarQube Project Key")
        else:
            with st.spinner("Starting workflow..."):
                try:
                    response = requests.post(
                        f"{api_url}/workflow/start",
                        json={
                            "repo_url": repo_url,
                            "sonar_project_key": sonar_key,
                            "coverage_threshold": threshold
                        }
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    st.session_state.workflow_id = data["workflow_id"]
                    st.success(f"Workflow started! ID: {data['workflow_id']}")
                except Exception as e:
                    st.error(f"Failed to start workflow: {e}")
    
    # Display current workflow status
    if "workflow_id" in st.session_state:
        workflow_id = st.session_state.workflow_id
        
        try:
            response = requests.get(f"{api_url}/workflow/{workflow_id}")
            response.raise_for_status()
            workflow = response.json()
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                status_color = {
                    "pending": "🟡",
                    "running": "🔵",
                    "success": "🟢",
                    "failed": "🔴"
                }.get(workflow["status"], "⚪")
                
                st.metric("Status", f"{status_color} {workflow['status'].upper()}")
            
            with col2:
                if workflow.get("coverage_before"):
                    st.metric("Coverage Before", f"{workflow['coverage_before']:.1f}%")
            
            with col3:
                if workflow.get("current_step"):
                    st.metric("Current Step", workflow["current_step"].replace("_", " ").title())
            
            # Show PR link if available
            if workflow.get("pr_url"):
                st.success("✅ Pull Request Created!")
                st.markdown(f"[View Pull Request →]({workflow['pr_url']})")
            
            # Show errors if any
            if workflow.get("errors"):
                st.error("Errors:")
                for error in workflow["errors"]:
                    st.write(f"- {error}")
            
            # Refresh button
            if st.button("🔄 Refresh Status"):
                st.rerun()
        
        except Exception as e:
            st.error(f"Failed to fetch workflow status: {e}")

with tab2:
    st.header("Workflow History")
    
    try:
        response = requests.get(f"{api_url}/workflow/")
        response.raise_for_status()
        data = response.json()
        
        workflows = data.get("workflows", [])
        
        if workflows:
            for wf in reversed(workflows[-10:]):  # Show last 10
                with st.expander(f"Workflow {wf['workflow_id'][:8]}... - {wf.get('status', 'unknown')}"):
                    st.write(f"**Created:** {wf.get('created_at', 'N/A')}")
                    st.write(f"**Status:** {wf.get('status', 'N/A')}")
                    
                    if wf.get("request"):
                        st.write("**Configuration:**")
                        st.json(wf["request"])
                   
                    if wf.get("pr_url"):
                        st.markdown(f"[View PR]({wf['pr_url']})")
        else:
            st.info("No workflows found")
    
    except Exception as e:
        st.error(f"Failed to fetch workflow history: {e}")

# Footer
st.markdown("---")
st.markdown("*Powered by LangGraph, FastAPI, and Streamlit*")
