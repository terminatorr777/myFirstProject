import streamlit as st
from openai import OpenAI
import PyPDF2
import docx
import os
import time

# ------------------ 初始化 ------------------
st.set_page_config(page_title="多文档问答助手", page_icon="📄")
st.title("📄 文档智能问答系统")

# 初始化 API（建议通过 secrets 或环境变量）
client = OpenAI(
    api_key=st.secrets["DEEPSEEK_API_KEY"],   # 从 secrets 获取
    base_url="https://api.deepseek.com/v1"
)


# client = OpenAI(
#     api_key="sk-219e4cd5af3041f9b9368fe4f06d7de5",  # 替换为DeepSeek实际密钥
#     base_url="https://api.deepseek.com/v1"  # 添加API端点
# )

# ------------------ 会话状态初始化 ------------------
if "history" not in st.session_state:
    st.session_state.history = []  # 保存所有问答记录

if "documents" not in st.session_state:
    st.session_state.documents = {}  # {filename: text}

# ------------------ 文件上传 ------------------
uploaded_files = st.sidebar.file_uploader("请上传 PDF 或 Word 文件（可多选）", type=["pdf", "docx"], accept_multiple_files=True)

def extract_text_with_pages(file):
    pages = []
    if file.name.endswith(".pdf"):
        try:
            pdf_reader = PyPDF2.PdfReader(file)
            for i, page in enumerate(pdf_reader.pages):
                content = page.extract_text()
                if content:
                    pages.append({"page": i + 1, "text": content.strip()})
        except Exception as e:
            st.error(f"解析 PDF 文件 {file.name} 时出错：{e}")
    elif file.name.endswith(".docx"):
        try:
            doc = docx.Document(file)
            for i, para in enumerate(doc.paragraphs):
                if para.text.strip():
                    pages.append({"page": i + 1, "text": para.text.strip()})
        except Exception as e:
            st.error(f"解析 Word 文件 {file.name} 时出错：{e}")
    return pages


# 解析并保存上传的文件
if uploaded_files:
    for file in uploaded_files:
        text = extract_text_with_pages(file)
        if text:
            st.session_state.documents[file.name] = text
    st.sidebar.success(f"共上传 {len(st.session_state.documents)} 份文档")

# ------------------ 展示聊天历史 ------------------
for msg in st.session_state.history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ------------------ 用户输入 ------------------
question = st.chat_input("请输入您的问题...")

if question:
    # 添加用户输入到聊天历史
    st.session_state.history.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    # 准备回答
    with st.spinner("思考中，请稍候..."):
        combined_response = ""

        for filename, pages in st.session_state.documents.items():
            full_text = "\n".join([p["text"] for p in pages])
            answer_default = '未发现该类内容！'

            prompt = (
                f"以下是文档《{filename}》的全部内容：\n"
                f"{full_text}\n\n"
                f"请根据这份文档内容回答以下问题：{question}\n"
                f"如果这份文档没有相关信息，请回答：{answer_default}。"
            )

            try:
                response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2
                )
                answer = response.choices[0].message.content.strip()


                match_answer = []
                for ans in answer.split():
                    if '**' in ans:
                        match_answer.append(ans.replace('*',''))
                    if len(match_answer)>10:
                        break

                print('>>>>>>>')
                print(answer)
                print(match_answer)


                if answer_default in answer:
                    continue

                # 🔍 查找答案中出现在哪一页
                matched_page = None
                for page in pages:
                    if any(kw in page["text"] for kw in match_answer):  # 用前10个词粗匹配
                        matched_page = page["page"]
                        break

                if matched_page:
                    combined_response += f"📄 **来自文档：{filename} - 第 {matched_page} 页**\n\n{answer}\n\n---\n"
                else:
                    combined_response += f"📄 **来自文档：{filename}**（未定位具体页）\n\n{answer}\n\n---\n"

            except Exception as e:
                combined_response += f"❌ 处理 {filename} 时出错：{e}\n\n"

        if combined_response=="":
            combined_response = "未发现该类内容！"

    # 显示并记录回答
    # with st.chat_message("assistant"):
    #     st.markdown(combined_response)

    import time

    with st.chat_message("assistant"):
        placeholder = st.empty()
        displayed_text = ""
        for char in combined_response:
            displayed_text += char
            placeholder.markdown(displayed_text)
            time.sleep(0.02)  # 控制打字速度，可调节

    # 保存到历史记录中
    st.session_state.history.append({"role": "assistant", "content": combined_response})


