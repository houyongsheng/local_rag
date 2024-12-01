import streamlit as st
import requests
import uuid
from datetime import datetime
import time

# 配置页面
st.set_page_config(
    page_title="离线文件夹问答",
    page_icon="🤖",
    layout="wide"
)

# 设置样式
st.markdown("""
<style>
    .stTextInput>div>div>input {
        background-color: #f0f2f6;
    }
    .stButton>button {
        width: 100%;
    }
    
    /* 调整标题位置 */
    header {
        padding-top: 0;
    }
    
    /* 优化侧边栏布局 */
    section[data-testid="stSidebar"] > div {
        padding-top: 0;  /* 移除顶部padding */
    }
    section[data-testid="stSidebar"] [data-testid="stMarkdown"] {
        margin: 0.5rem 0;
    }
    /* 调整侧边栏第一个标题的位置 */
    section[data-testid="stSidebar"] > div > div:first-child {
        margin-top: -3rem;  /* 让第一个div往上移 */
    }
    
    /* 固定底部输入区域 */
    [data-testid="stVerticalBlock"]:has(> div > [data-testid="stChatInput"]) {
        position: fixed !important;
        bottom: 1rem;
        right: 0;
        left: 26rem;  /* 留出侧边栏宽度 */
        padding: 1rem;
        padding-bottom: 1rem;
        background: linear-gradient(180deg, #FFFFFF 0%, #FFFFFF 100%);
        border-top: 1px solid #ddd;
        z-index: 100;
    }
    
    /* 遮罩层，防止内容显示在输入框下方 */
    [data-testid="stVerticalBlock"]:has(> div > [data-testid="stChatInput"])::after {
        content: "";
        position: fixed;
        bottom: 0;
        right: 0;
        left: 26rem;
        height: 2rem;
        background: white;
        z-index: 99;
    }
    
    /* 聊天区域留出底部空间 */
    [data-testid="stChatMessageContainer"] {
        margin-bottom: 12rem;  /* 增加底部边距，确保内容不会被遮挡 */
        padding-bottom: 2rem;
    }
    
    /* 近期会话按钮样式 */
    .recent-chat-button {
        background: transparent;
        border: none;
        text-align: left;
        padding: 0.5rem;
        cursor: pointer;
        width: 100%;
        transition: background-color 0.3s;
    }
    .recent-chat-button:hover {
        background-color: #f0f2f6;
    }
</style>
""", unsafe_allow_html=True)

# 初始化会话状态
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'thread_id' not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
if 'recent_threads' not in st.session_state:
    st.session_state.recent_threads = []
if 'last_save_time' not in st.session_state:
    st.session_state.last_save_time = time.time()

# 自动保存会话的函数
def auto_save_thread():
    current_time = time.time()
    # 如果距离上次保存超过10秒且有消息
    if current_time - st.session_state.last_save_time > 10 and st.session_state.messages:
        # 移除相同ID的历史会话
        st.session_state.recent_threads = [
            t for t in st.session_state.recent_threads 
            if t['id'] != st.session_state.thread_id
        ]
        # 保存当前会话
        st.session_state.recent_threads.append({
            "id": st.session_state.thread_id,
            "messages": st.session_state.messages.copy(),
            "time": datetime.now().strftime("%Y-%m-%d %H:%M")
        })
        # 只保留最近5个会话
        if len(st.session_state.recent_threads) > 5:
            st.session_state.recent_threads.pop(0)
        # 更新保存时间
        st.session_state.last_save_time = current_time
        # 刷新页面以显示更新后的近期会话
        st.rerun()

# 页面标题
st.markdown('<h1 style="margin-top: -4rem;">💬 离线大模型问答助手</h1>', unsafe_allow_html=True)

# 侧边栏
with st.sidebar:
    # 1. 文档设置
    st.markdown('<h3 style="margin-top: -3rem;">📁 文档设置</h3>', unsafe_allow_html=True)
    docs_dir = st.text_input("文档目录路径", value="/Users/wilson/ai/local_rag/test/")
    if st.button("更新文档目录"):
        with st.spinner("正在更新文档..."):
            try:
                response = requests.post(
                    "http://localhost:8000/update_docs",
                    json={"docs_dir": docs_dir}
                )
                response.raise_for_status()
                st.success("文档目录更新成功!")
            except Exception as e:
                st.error(f"更新文档目录失败: {str(e)}")
    
    st.divider()
    
    # 2. 会话管理
    st.markdown('<h3>💭 会话管理</h3>', unsafe_allow_html=True)
    if st.button("开始新会话"):
        # 保存当前会话到近期会话列表
        if st.session_state.messages:
            # 如果当前会话已经在recent_threads中，先移除它
            st.session_state.recent_threads = [
                t for t in st.session_state.recent_threads 
                if t['id'] != st.session_state.thread_id
            ]
            # 添加当前会话到recent_threads
            st.session_state.recent_threads.append({
                "id": st.session_state.thread_id,
                "messages": st.session_state.messages.copy(),
                "time": datetime.now().strftime("%Y-%m-%d %H:%M")
            })
            # 只保留最近5个会话
            if len(st.session_state.recent_threads) > 5:
                st.session_state.recent_threads.pop(0)
        
        # 创建新会话
        st.session_state.messages = []
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.last_save_time = time.time()
        st.rerun()
    
    # 显示当前会话ID
    st.markdown(f"**当前会话ID**: `{st.session_state.thread_id}`")
    
    # 3. 近期会话
    if st.session_state.recent_threads:
        st.markdown('<h3>📜 近期会话</h3>', unsafe_allow_html=True)
        for idx, thread in enumerate(reversed(st.session_state.recent_threads)):
            # 使用索引和时间戳作为key，避免与会话ID冲突
            timestamp = thread['time'].replace(' ', '_').replace(':', '-')
            button_key = f"thread_btn_{idx}_{timestamp}"
            
            # 获取最后一条消息预览
            last_msg = ""
            if thread['messages']:
                last_msg = thread['messages'][-1]['content'][:50] + "..."
            
            # 创建按钮，显示时间和最后一条消息预览
            button_label = f"🕒 {thread['time']}"
            if st.button(button_label, key=button_key, help="点击加载此会话"):
                # 加载选中的会话
                st.session_state.messages = thread['messages'].copy()
                st.session_state.thread_id = thread['id']
                st.rerun()

# 显示聊天历史
chat_container = st.container()
with chat_container:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# 创建底部输入区域
input_container = st.container()
with input_container:
    # 快捷操作按钮行
    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("📑 总结文件夹内容", use_container_width=True):
            with chat_container:
                with st.chat_message("assistant"):
                    with st.spinner("正在生成总结..."):
                        try:
                            response = requests.post("http://localhost:8000/summary")
                            response.raise_for_status()
                            summary = response.json()["summary"]
                            st.session_state.messages.append({"role": "assistant", "content": summary})
                            st.markdown(summary)
                            auto_save_thread()
                        except Exception as e:
                            st.error(f"生成总结失败: {str(e)}")
    
    # 用户输入
    if prompt := st.chat_input("输入你的问题...", key="user_input"):
        # 添加用户消息到历史
        st.session_state.messages.append({"role": "user", "content": prompt})
        with chat_container:
            with st.chat_message("user"):
                st.markdown(prompt)

        # 调用API获取回答
        with chat_container:
            with st.chat_message("assistant"):
                with st.spinner("思考中..."):
                    try:
                        response = requests.post(
                            "http://localhost:8000/chat",
                            json={
                                "question": prompt,
                                "thread_id": st.session_state.thread_id
                            }
                        )
                        response.raise_for_status()
                        answer = response.json()["answer"]
                        st.session_state.messages.append({"role": "assistant", "content": answer})
                        st.markdown(answer)
                        auto_save_thread()
                    except Exception as e:
                        st.error(f"发生错误: {str(e)}")
