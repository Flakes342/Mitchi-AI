import os
import uuid
import logging
import chromadb
import requests
from agent.llm import llm
from chromadb import Client
from datetime import datetime, timedelta
from chromadb.config import Settings
from langchain.vectorstores import Chroma
from chromadb.utils import embedding_functions
from langchain.embeddings import HuggingFaceEmbeddings
from agent.llm import build_rag_prompt, generate_context_summary
from langchain.text_splitter import RecursiveCharacterTextSplitter


logger = logging.getLogger(__name__)

try:
    embedding_func = HuggingFaceEmbeddings(
        model_name="/home/ayush/Documents/bitbud/models/paraphrase-MiniLM-L3-v2/"
    )
    logger.info("Embedding function initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize embedding function: {e}")
    embedding_func = None

vectorstore = None
about_store = None

try:
    vectorstore = Chroma(
        collection_name="bitbud",
        embedding_function=embedding_func,
        persist_directory="./bitbud_memory"
    )
    logger.info("Main vectorstore initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize main vectorstore: {e}")

try:
    about_store = Chroma(
        collection_name="about_user",
        embedding_function=embedding_func,
        persist_directory="./chroma_about"
    )
    logger.info("About vectorstore initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize about vectorstore: {e}")


ABOUT_FILE = "ABOUT.md"
_about_last_modified = None
_current_session_id = None
_last_interaction_time = None

def _get_current_session_id():
    """Generate session ID based on time gaps (1 hour = new session)"""
    global _current_session_id, _last_interaction_time

    now = datetime.now()

    if (_last_interaction_time is None or
        (now - _last_interaction_time).total_seconds() > 3600):
        # New session if no last interaction or more than 1 hour gap
        _current_session_id = str(uuid.uuid4())[:8] # Shorten UUID for session ID
        print(f"[Memory] New session started: {_current_session_id}")

    _last_interaction_time = now
    return _current_session_id

def _load_about_if_changed():
    """Load the ABOUT.md file if it has changed since last load."""
    global _about_last_modified, about_store

    if not os.path.exists(ABOUT_FILE):
        print(f"[Memory] About file '{ABOUT_FILE}' not found.")
        return

    _current_mod_time = os.path.getmtime(ABOUT_FILE)

    # Reloading if the file was modified
    if _about_last_modified != _current_mod_time:
        print(f"[Memory] About file '{ABOUT_FILE}' was modified, reloading...")
        _about_last_modified = _current_mod_time

        with open(ABOUT_FILE, "r") as f:
            about_text = f.read().strip()
            if about_text:
                splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
                chunks = splitter.split_text(about_text)
                about_store.add_texts(chunks)
                print(f"[Memory] Loaded {len(chunks)} chunks from ABOUT.md")
            else:
                chunks = []
                print("[Memory] About file was found empty, no chunks added.")

        about_store.delete_collection()
        about_store = Chroma(
            collection_name="about_user",
            embedding_function=embedding_func,
            persist_directory="./chroma_about"
        )
        about_store.add_texts(chunks)

def is_worth_storing(text: str) -> bool:
    """Filter out trivial messages that don't need long-term storage"""
    text_lower = text.lower().strip()

    # Skip common greetings/acknowledgments
    trivial_patterns = [
        "hi", "hello", "hey", "thanks", "thank you", "ok", "okay", 
        "yes", "no", "sure", "good", "great", "nice", "cool",
        "bye", "goodbye", "see you", "lol", "haha", "hmm", "oh",
        "got it", "understood", "will do", "sounds good", "alright",
        "no problem", "you too", "take care", "have a nice day",
        "i see", "interesting", "right", "exactly", "absolutely",
        "i agree", "i understand", "that's fine", "that's okay",
    ]
    
    # message is just trivial words >> skip
    words = text_lower.split()
    if all(word in trivial_patterns for word in words) or text_lower in trivial_patterns:
        return False
    
    return True

def cleanup_old_memories(days_to_keep=45):
    """Remove memories older than 45 days"""
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    cutoff_iso = cutoff_date.isoformat()
    
    try:
        all_docs = vectorstore.get()
        
        # Find old documents
        old_doc_ids = []
        for i, metadata in enumerate(all_docs['metadatas']):
            if metadata and 'timestamp' in metadata:
                if metadata['timestamp'] < cutoff_iso:
                    old_doc_ids.append(all_docs['ids'][i])
        
        # Delete old documents
        if old_doc_ids:
            vectorstore.delete(old_doc_ids)
            print(f"[Memory] Cleaned up {len(old_doc_ids)} old memories")
            
    except Exception as e:
        print(f"[Memory] Cleanup failed: {e}")


def store_to_memory(text: str, metadata: dict = None):

    # Skip trivial messages
    if not is_worth_storing(text):
        print(f"[Memory] Skipped storing trivial message: {text}")
        return

    context = generate_context_summary(text)

    # Prepare metadata with session info
    metadata = metadata or {}
    metadata["context"] = context
    metadata["timestamp"] = datetime.now().isoformat()
    metadata["session_id"] = _get_current_session_id()
    metadata["source"] = "conversation"

    vectorstore.add_texts(
        texts=[text],
        metadatas=[metadata]
    )

    print(f"[Memory] Stored: {text} with metadata: {metadata}")


def retrieve_context(query: str, k=5, score_threshold=0.75) -> list[str]:
    docs = vectorstore.similarity_search(query, k=k*2)
    
    query_context = generate_context_summary(query)
    current_session = _get_current_session_id()

    scored_docs = []
    
    for doc in docs:
        relevance_score = 1.0  # Base score
        
        # Boost recent conversations
        if doc.metadata.get("session_id") == current_session:
            relevance_score *= 1.5
        
        # Boost by recency (last 24 hours get higher scores)
        if 'timestamp' in doc.metadata:
            try:
                doc_time = datetime.fromisoformat(doc.metadata['timestamp'])
                hours_ago = (datetime.now() - doc_time).total_seconds() / 3600
                if hours_ago < 24:
                    relevance_score *= (1.2 - hours_ago/100)  # Recency boost
            except:
                pass

        # Context matching boost
        if query_context:
            query_tokens = set(query_context.lower().split())
            context_meta = doc.metadata.get("context", "").lower()
            if any(token in context_meta for token in query_tokens):
                relevance_score *= 1.3

        scored_docs.append((doc, relevance_score))

    # Retrieve top k docs with a score above the threshold
    scored_docs.sort(key=lambda x: x[1], reverse=True)
    final_docs = [doc for doc, score in scored_docs[:k]]
    
    results = [doc.page_content for doc in final_docs]
    print(f"[Memory] Retrieved {len(results)} relevant memories")
    return results

def retrieve_about_context(query: str, k=3) -> list[str]:
    results = about_store.similarity_search(query, k=k)
    return [doc.page_content for doc in results]



# --- Main handler
def handle_user_input(user_input: str) -> str:

    try:
        # Load ABOUT.md if it changed
        _load_about_if_changed()
        
        # Periodic cleanup (every 100 interactions)
        if _last_interaction_time and datetime.now().hour == 3:  # 3 AM cleanup
            cleanup_old_memories()

        # Store user input (with filtering)
        store_to_memory(user_input)

        # Retrieve relevant context
        memory_context = retrieve_context(user_input)
        about_context = retrieve_about_context(user_input)

        prompt = build_rag_prompt(user_input, memory_context, about_context)

        reply = llm.invoke(prompt).strip()

        # Store reply (with filtering)
        store_to_memory(reply, metadata={"source": "BitBud"})

        return reply

    except Exception as e:
        logger.error(f"Error in handle_user_input: {e}")
        return "I encountered an error processing your request. Please try rephrasing or try again later."