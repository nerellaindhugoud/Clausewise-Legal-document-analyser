import gradio as gr 
import requests

BACKEND = "http://127.0.0.1:8000"

def analyze_fn(file): 
    if file is None:
         return "Upload a file", None, None, None 
    with open(file.name, 'rb') as f: 
        res = requests.post(f"{BACKEND}/analyze", files={'file': f.read()}).json() 
    return ( 
        
        f"Type: {res['contract_type']}\nLanguage: {res['language']}\nRisks: {', '.join(res['risks'])}", 
        res['summary'], 
        "\n".join(res['simplified_examples']), 
        res['alerts'] )

def ask_fn(file, question): 
    if file is None or not question: 
        return "" 
    with open(file.name, 'rb') as f:
         res = requests.post(f"{BACKEND}/ask", files={'file': f.read()}, data={'question': question}).json() 
    return res['answer']

with gr.Blocks(title="ClauseWise – IBM Granite") as demo: 
    
    gr.Markdown("# ClauseWise – IBM Watson & Granite") 
    with gr.Tab("Analyze"): 
        up = gr.File(label="Upload contract (.txt)")
        out1 = gr.Textbox(label="Meta")
        out2 =gr.Textbox(label="summary")
        out3 = gr.Textbox(label="Simplified Clauses (samples)")
        out4 = gr.JSON(label="smart Alerts")
        btn = gr.Button("Analyze")
        btn.click(analyze_fn,inputs=[up],outputs=[out1,out2,out3,out4])
    with gr.Tab("Ask"):
        up2 = gr.File(label="Upload contract(.txt)")
        q = gr.Textbox(label="your question")
        a=gr.Textbox(label="answer")
        ask_btn = gr.Button("Ask")
        ask_btn.click(ask_fn,inputs=[up2,q],outputs=[a])
if __name__ == "__main__":
    demo.launch()            