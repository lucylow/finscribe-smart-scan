import streamlit as st
import requests
import time

API = "http://localhost:8000"

st.title("📄 FinScribe Smart Scan")

uploaded = st.file_uploader("Upload invoice or receipt", type=["png", "jpg", "jpeg", "pdf"])

if uploaded:
    with st.spinner("Uploading & processing..."):
        r = requests.post(
            f"{API}/api/v1/analyze",
            files={"file": (uploaded.name, uploaded.getvalue())},
        )
        job_id = r.json()["job_id"]

    st.success(f"Job submitted: {job_id}")

    result = None
    for _ in range(20):
        time.sleep(1)
        res = requests.get(f"{API}/api/v1/results/{job_id}")
        if res.status_code == 200:
            result = res.json()
            break

    if result:
        st.json(result)
    else:
        st.warning("Still processing… check back later.")

