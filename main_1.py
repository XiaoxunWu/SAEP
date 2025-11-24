import gradio as gr 
from fastapi import FastAPI
from gradio_ui2 import create_ui
# demo = create_ui()
# 启动 Gradio Web 应用
if __name__ == "__main__":
    demo = create_ui()
    demo.queue()
#     # demo.launch(server_name="0.0.0.0", server_port=7860)
    demo.launch(server_name='127.0.0.1', server_port=7860, inbrowser=True, share=True)
