import streamlit as st
from .cognito_utils import logout


def display_sidebar():
    # If user is logged in, display a logout button
    if st.session_state.get("auth_username", None):
        sidebar = st.sidebar
        check1 = sidebar.button("Logout")
        if check1:
            logout()
            st.rerun()
