import os
import abc
from langchain.chat_models import init_chat_model
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_community.document_loaders import JSONLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_core.tools import tool
from typing_extensions import List, TypedDict
from langgraph.graph import START, END, StateGraph, MessagesState
from langchain_core.messages import SystemMessage
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver

def make_retrieve_tool(vector_store):
    @tool
    def retrieve(query: str):
        """Retrieve information related to a query."""
        retrieved_docs = vector_store.similarity_search(query, k=2)
        serialized = "\n\n".join(
            (f"Source: {doc.metadata}\n" f"Content: {doc.page_content}")
            for doc in retrieved_docs
        )
        return serialized, retrieved_docs

    return retrieve

class Openai_Bot:

    def __init__(self, data_dir):
        self.set_up()
        self.create_db()
        self.retrieve_tool = make_retrieve_tool(self.vector_store)
        self.tools = ToolNode([self.retrieve_tool])
        self.graph = self.create_graph()
        base_dir = os.path.dirname(__file__)
        data_path = os.path.join(base_dir, data_dir)
        self.data_dir = data_path

    def set_up(self):
        # if not os.environ.get("OPENAI_API_KEY"):
        base_dir = os.path.dirname(__file__)
        key_path = os.path.join(base_dir, "api_keys", "openai_key.txt")
        with open(key_path) as file:
            key = file.readline().strip()
            os.environ["OPENAI_API_KEY"] = key
        self.llm = init_chat_model("gpt-4o-mini", model_provider="openai")
        

    def create_db(self):
        embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
        base_dir = os.path.dirname(__file__)
        vector_path = os.path.join(base_dir, "chroma_vector_db")
        print("looking for db at:", vector_path)
        db_exists = os.path.exists(vector_path)
        vector_store = Chroma(
            collection_name="example_collection",
            embedding_function=embeddings,
            persist_directory= vector_path,
        )
        # self.fill_vector_db(data_dir, vector_store)
        if not db_exists:
            print("creating vector database at", vector_path)
        
        else:
            print("database found at", vector_path)
        self.vector_store = vector_store

    def fill_vector_db(self):
        json_files = [os.path.join(self.data_dir, f) for f in os.listdir(self.data_dir) if f.endswith('.json')]
        # Initialize a list to collect all documents
        all_docs = []

        # Loop through each JSON file and load its content
        for file_path in json_files:
            loader = JSONLoader(
                file_path=file_path,
                jq_schema='.[]',  # Adjust if your JSON structure differs
                text_content=False
            )
            docs = loader.load()
            all_docs.extend(docs)

        # (Optional) Split the loaded documents into chunks
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        all_splits = text_splitter.split_documents(all_docs)

        print(f"Split docs into {len(all_splits)} sub-documents.")

        return self.vector_store.add_documents(documents=all_splits)

    
    
    def generate(self, state: MessagesState):
        # Get generated ToolMessages
        recent_tool_messages = []
        for message in reversed(state["messages"]):
            if message.type == "tool":
                recent_tool_messages.append(message)
            else:
                break
        tool_messages = recent_tool_messages[::-1]

        # Format into prompt
        docs_content = "\n\n".join(doc.content for doc in tool_messages)
        system_message_content = (
            "You are an assistant for question-answering tasks. "
            "Use the following pieces of retrieved context to answer "
            "the question. If you don't know the answer, say that you "
            "don't know. If asked about a game you do not have documents for, say you do not know the game. "
            "Use three sentences maximum and keep the answer concise."
            "\n\n"
            f"{docs_content}"
        )
        conversation_messages = [
            message
            for message in state["messages"]
            if message.type in ("human", "system")
            or (message.type == "ai" and not message.tool_calls)
        ]
        prompt = [SystemMessage(system_message_content)] + conversation_messages

        # Run
        response = self.llm.invoke(prompt)
        return {"messages": [response]}
    
    def query_or_respond(self, state: MessagesState):
        """Generate tool call for retrieval or respond."""
        llm_with_tools = self.llm.bind_tools([self.retrieve_tool])
        response = llm_with_tools.invoke(state["messages"])
        # MessagesState appends messages to state instead of overwriting
        return {"messages": [response]}

    def create_graph(self):
        graph_builder = StateGraph(MessagesState)
        graph_builder.add_node(self.query_or_respond)
        graph_builder.add_node(self.tools)
        graph_builder.add_node(self.generate)
        graph_builder.set_entry_point("query_or_respond")
        graph_builder.add_conditional_edges(
            "query_or_respond",
            tools_condition,
            {END: END, "tools": "tools"},
        )
        graph_builder.add_edge("tools", "generate")
        graph_builder.add_edge("generate", END)
        memory = MemorySaver()
        return graph_builder.compile(checkpointer=memory)

from langchain_anthropic import ChatAnthropic
class Anothrpic_Bot(Openai_Bot):

    def set_up(self):
        if not os.environ.get("ANTHROPIC_API_KEY"):
            base_dir = os.path.dirname(__file__)
            key_path = os.path.join(base_dir, "api_keys", "anthropic_key.txt")

            with open(key_path) as file:
                key = file.readline().strip()
                os.environ["ANTHROPIC_API_KEY"] = key

        # Replace OpenAI Chat Model with Claude
        self.llm = ChatAnthropic(model="claude-3-opus-20240229", temperature=0.0)

from langchain.chat_models import init_chat_model
class Perplexity_Bot(Openai_Bot):

    def set_up(self):
        if not os.environ.get("PPLX_API_KEY"):
            base_dir = os.path.dirname(__file__)
            key_path = os.path.join(base_dir, "api_keys", "perplexity_key.txt")

            with open(key_path) as file:
                key = file.readline().strip()
                os.environ["PPLX_API_KEY"] = key

        self.llm = init_chat_model("llama-3.1-sonar-small-128k-online", model_provider="perplexity")

    def query_or_respond(self, state: MessagesState):
        """Directly respond without tool invocation (Perplexity doesn't support tools)."""
        response = self.llm.invoke(state["messages"])
        return {"messages": [response]}