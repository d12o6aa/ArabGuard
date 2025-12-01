
import streamlit as st
from normalizer import normalize_input

st.title("🔧 Smart Injection Normalizer — Pipeline View")

user_input = st.text_area("ادخل أي جملة فيها Base64 / Hex / ROT13 / كلام طبيعي / عربي / Emojis:")

if st.button("Normalize"):
    final, steps = normalize_input(user_input, debug_steps=True)

    st.subheader("📌 Original Input")
    st.write(user_input)

    st.subheader("🔧 Pipeline Steps Output")
    for step, val in steps.items():
        st.markdown(f"### 🔹 {step}")
        st.code(val)

    st.subheader("🎯 Final Normalized Output")
    st.code(final)
