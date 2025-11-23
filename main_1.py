import gradio as gr 
from fastapi import FastAPI
from gradio_ui3 import create_ui
# demo = create_ui()
# 启动 Gradio Web 应用
if __name__ == "__main__":
    demo = create_ui()
    demo.queue()
#     # demo.launch(server_name="0.0.0.0", server_port=7860)
    demo.launch(server_name='127.0.0.1', server_port=7860, inbrowser=True, share=True)

# # 优化启动配置，解决连接错误
#     demo.launch(
#         server_name='127.0.0.1', 
#         server_port=7860, 
#         inbrowser=True, 
#         share=True,  # 启用共享功能
#         show_api=False,  # 隐藏API文档
#         quiet=False,  # 显示详细日志
#         debug=False,  # 关闭调试模式
#         # enable_queue=True,  # 启用队列
#         max_threads=10  # 增加线程数
#     )