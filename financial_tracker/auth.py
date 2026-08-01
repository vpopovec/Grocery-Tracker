import os
import streamlit as st


def get_current_user_id():
    """Identity comes from Caddy's forward_auth gate, which sets X-Person-Id after
    verifying the Flask session cookie against g_tracker's /internal/verify-session.
    DEV_PERSON_ID lets `streamlit run` work standalone (no Caddy in front) for local dev.
    """
    person_id = st.context.headers.get("X-Person-Id")
    if person_id is not None:
        try:
            return int(person_id)
        except (TypeError, ValueError):
            pass

    dev_person_id = os.environ.get("DEV_PERSON_ID")
    if dev_person_id:
        return int(dev_person_id)

    st.error("Not authenticated. Please log in via the main app first.")
    st.stop()
