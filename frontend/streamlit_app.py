import streamlit as st 
import requests

st.title("streamlit frontend is running")
st.write("if you see thtis text,streamlit is working correctly")

BACKEND = st.secrets.get("BACKEND_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="ClauseWise – IBM Granite", layout="wide") 
st.title("ClauseWise – IBM Watson & Granite ")

col1, col2 = st.columns(2)

with col1: 
    st.header("Analyze Contract") 
    up = st.file_uploader("Upload contract (.txt)", type=["txt"], key="one") 
    if up and st.button("Analyze"): 
        files = {"file": up.getvalue()} 
        r = requests.post(f"{BACKEND}/analyze", files=files) 
        data = r.json()
        st.caption(f"Granite: {data['uses_granite']} | Watson NLU: {data['uses_watson_nlu']}")
        st.subheader("Detected Language") 
        st.code(data["language"]) 
        st.subheader("Type") 
        st.write(data["contract_type"]) 
        st.subheader("Summary") 
        st.write(data["summary"]) 
        st.subheader("Simplified Clauses (Samples)") 
        for s in data["simplified_examples"]:
             st.write("- ", s)
        st.subheader("Entities / Keywords")
        st.json(data["entities"]) 
        st.subheader("Risks") 
        st.write("\n".join(data["risks"]) or "None found")
        st.subheader("Smart Alerts (60 days)") 
        st.json(data["alerts"]) 
        st.subheader("Clauses")
        for i, c in enumerate(data["clauses"][:30]): 
            with st.expander(f"Clause {i+1}"): 
                st.write(c)

with col2:
     st.header("Ask the Document (chat)")
     up2 = st.file_uploader("Upload same or another contract (.txt)", type=["txt"], key="two")

st.markdown("*Voice input* (Web Speech API – Chrome/Edge)")
st.components.v1.html(
    """
    <div style='padding:8px;border:1px solid #ddd;border-radius:8px'>
      <button id="start">🎤 Start</button>
      <button id="stop">⏹ Stop</button>
      <p>Transcript: <span id="out"></span></p>
      <script>
        let rec; const out = document.getElementById('out');
        if ('webkitSpeechRecognition' in window) {
          rec = new webkitSpeechRecognition();
          rec.continuous = true; rec.interimResults = true; rec.lang='';
          rec.onresult = (e)=>{ let t=''; for(let i=0;i<e.results.length;i++){t+=e.results[i][0].transcript+' ';} out.textContent=t; };
        }
        document.getElementById('start').onclick = ()=> rec && rec.start();
        document.getElementById('stop').onclick = ()=> rec && rec.stop();
      </script>
    </div>
    """,
    height=140,
)

q = st.text_input("Your question")
if up2 and q and st.button("Ask"):
    files = {"file": up2.getvalue()}
    r = requests.post(f"{BACKEND}/ask", files=files, data={"question": q})
    st.subheader("Answer")
    st.write(r.json().get("answer", ""))

st.divider()

st.header("Cross-Contract Comparison") 
left, right = st.columns(2) 
with left: 
    a = st.file_uploader("Contract A (.txt)", type=["txt"], key="a") 
with right: 
    b = st.file_uploader("Contract B (.txt)", type=["txt"], key="b") 
if a and b and st.button("Compare"): 
    files = {"file_a": a.getvalue(), "file_b": b.getvalue()}
    r = requests.post(f"{BACKEND}/compare", files=files) 
    data = r.json() 
    st.subheader("Language (A/B)") 
    
    st.write(data["lang_a"], "/", data["lang_b"]) 
    st.subheader("Cosine Similarity") 
    st.write(data["cosine_similarity"]) 
    st.subheader("Diff (Unified)") 
    st.code(data["diff"][:10000]) 
    st.subheader("Clause Overlaps (top 50)") 
    st.dataframe(data["overlaps"])
