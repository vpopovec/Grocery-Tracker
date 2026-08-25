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


def flask_base_url():
    """Base URL for links from Streamlit back into the Flask app.

    Behind Caddy the two share an origin (Flask at /, Streamlit under /analytics), so
    a root-relative link is correct. Running `streamlit run` standalone there is no
    Flask on :8501 — a root-relative link just hits Streamlit's own 404 — so point at
    the Flask dev server instead. GROCERY_APP_BASE_URL overrides both.
    """
    explicit = os.environ.get("GROCERY_APP_BASE_URL")
    if explicit is not None:
        return explicit.rstrip("/")

    behind_proxy = st.context.headers.get("X-Person-Id") is not None
    return "" if behind_proxy else "http://localhost:5000"
