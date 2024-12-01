from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph, END, START, MessagesState
from typing import TypedDict, Annotated, Sequence
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode
from langgraph.prebuilt.tool_node import tools_condition
from langgraph.checkpoint.memory import MemorySaver
import operator
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# FastAPI app
app = FastAPI(title="RAG API", description="API for RAG-based question answering system")

# Request/Response models
class ChatRequest(BaseModel):
    question: str
    thread_id: str = "default"

class ChatResponse(BaseModel):
    answer: str
    thread_id: str

class UpdateDocsRequest(BaseModel):
    docs_dir: str

class SummaryResponse(BaseModel):
    summary: str

# Global variables to store initialized components
vectorstore = None
graph = None
llm = None

def ask(question: str, thread_id: str = "default") -> str:
    """Ask a question and get a response."""
    global graph
    if graph is None:
        raise RuntimeError("RAG system not initialized. Please wait for initialization to complete.")
    
    config = {"configurable": {"thread_id": thread_id}}
    response = graph.invoke(
        {"messages": [{"role": "user", "content": question}]},
        config=config
    )
    return response["messages"][-1].content

def init_rag_system(docs_dir: str = "/Users/wilson/ai/local_rag/test/"):
    """Initialize the RAG system components."""
    global vectorstore, graph, llm
    
    # 1. Load documents
    loader = DirectoryLoader(
        docs_dir,
        glob="**/*.txt",
        loader_cls=TextLoader,
        loader_kwargs={"autodetect_encoding": True}
    )
    docs = loader.load()

    # 2. Split documents
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
    )
    splits = text_splitter.split_documents(docs)

    # 3. Create embeddings and vector store
    embeddings = OllamaEmbeddings(model="bge-m3")
    
    # 使用持久化的向量存储
    try:
        if vectorstore is not None:
            # 如果存在,则删除collection
            vectorstore._client.delete_collection(name="default")
    except ValueError:
        # 如果collection不存在,忽略错误
        pass
        
    # 使用from_documents创建新的向量存储
    vectorstore = Chroma.from_documents(
        documents=splits,
        embedding=embeddings,
        persist_directory="./chroma_db",
        collection_name="default"
    )

    # 4. Create LLM
    llm = ChatOllama(model="qwen2.5:3b")

    # 5. Create prompt
    system_template = """You are a helpful AI assistant. Given the following context and chat history, answer the user's question. 
If you cannot find the answer in the context, say so. Use the language of the source material - if the source is in Chinese, respond in Chinese.
If it's a follow-up question, use the chat history to understand the context.

Context: {context}

Chat History: {history}

Current Question: {question}

Instructions:
1. First, analyze if this is a follow-up question. If so, use the chat history to understand what it refers to.
2. If the question is vague or unclear, look at the available context to see if it might be referring to something specific.
3. Provide a direct and concise answer based on the context.
4. If you truly cannot find relevant information in the context, say so clearly.
"""

    human_template = """Please answer my question: {question}"""

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_template),
        ("human", human_template)
    ])

    # 6. Define retrieval tool
    @tool(response_format="content_and_artifact")
    def retrieve(query: str):
        """Retrieve information related to a query."""
        retrieved_docs = vectorstore.similarity_search(query, k=2)
        serialized = "\n\n".join(
            (f"Source: {doc.metadata}\n"f"Content: {doc.page_content}")
            for doc in retrieved_docs
        )
        return serialized, retrieved_docs

    # 7. Define state and steps
    def query_or_respond(state: MessagesState):
        """Generate tool call for retrieval or respond."""
        # Create a system message that helps with query generation
        system_message = """You are a helpful AI assistant. Your task is to either:
        1. Generate a search query to find relevant information to answer the user's question, or
        2. Respond directly if the question is a greeting or can be answered without retrieval.
        
        For follow-up questions, look at the chat history to understand the context and generate an appropriate query."""
        
        messages = [{"role": "system", "content": system_message}]
        messages.extend(state["messages"])
        
        llm_with_tools = llm.bind_tools([retrieve])
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    # Execute the retrieval
    tools = ToolNode([retrieve])

    def generate(state: MessagesState):
        """Generate answer."""
        # Get generated ToolMessages
        recent_tool_messages = []
        for message in reversed(state["messages"]):
            if message.type == "tool":
                recent_tool_messages.append(message)
            else:
                break
        tool_messages = recent_tool_messages[::-1]

        # Get chat history
        chat_history = []
        for message in state["messages"]:
            if message.type in ("human", "ai") and not (message.type == "ai" and message.tool_calls):
                chat_history.append(message)

        # Format into prompt
        docs_content = "\n\n".join(doc.content for doc in tool_messages)
        history_str = "\n".join(f"{msg.type.capitalize()}: {msg.content}" for msg in chat_history[:-1])
        
        # Run
        messages = prompt.invoke({
            "context": docs_content,
            "history": history_str,
            "question": chat_history[-1].content
        })
        response = llm.invoke(messages)
        return {"messages": [response]}

    # 8. Create and compile graph with memory
    graph_builder = StateGraph(MessagesState)
    graph_builder.add_node("query_or_respond", query_or_respond)
    graph_builder.add_node("tools", tools)
    graph_builder.add_node("generate", generate)

    graph_builder.set_entry_point("query_or_respond")
    graph_builder.add_conditional_edges(
        "query_or_respond",
        tools_condition,
        {END: END, "tools": "tools"},
    )
    graph_builder.add_edge("tools", "generate")
    graph_builder.add_edge("generate", END)

    # Add memory saver for persistence
    memory = MemorySaver()
    graph = graph_builder.compile(checkpointer=memory)

def get_all_txt_content(docs_dir: str) -> str:
    """读取文件夹内所有txt文件并拼接内容"""
    loader = DirectoryLoader(
        docs_dir,
        glob="**/*.txt",
        loader_cls=TextLoader,
        loader_kwargs={"autodetect_encoding": True}
    )
    docs = loader.load()
    
    # 使用分隔符拼接所有文档内容
    contents = []
    for doc in docs:
        contents.append(doc.page_content)
    return "\n======\n".join(contents)

# API endpoints
@app.on_event("startup")
async def startup_event():
    """Initialize the RAG system on startup."""
    init_rag_system()

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat endpoint that handles questions and maintains conversation history."""
    try:
        response = ask(request.question, request.thread_id)
        return ChatResponse(
            answer=response,
            thread_id=request.thread_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/update_docs")
async def update_docs(request: UpdateDocsRequest):
    """Update the document directory and reinitialize the RAG system."""
    try:
        init_rag_system(request.docs_dir)
        return {"status": "success", "message": f"Successfully updated docs directory to: {request.docs_dir}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/summary")
async def get_summary():
    """获取文档总结"""
    try:
        # 获取当前文档目录的所有内容
        content = get_all_txt_content("/Users/wilson/ai/local_rag/test/")
        
        # 创建总结提示
        prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个专业的文档总结助手。请对给定的文档内容进行全面但简洁的总结。
                         内容之间用'======'分隔,代表不同的文档。
                         总结要点包括:
                         1. 文档的主要主题和目的
                         2. 重要的观点和结论
                         3. 如果有多个文档,说明它们之间的关联
                         
                         请用中文回复。
                      """),
            ("human", "{content}")
        ])
        
        # 使用LLM生成总结
        chain = prompt | llm | StrOutputParser()
        summary = chain.invoke({"content": content})
        
        return SummaryResponse(summary=summary)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Remove the test code
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
