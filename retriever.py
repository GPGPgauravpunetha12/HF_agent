# retriever.py
from functools import lru_cache

from datasets import load_dataset
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document
from langfuse import observe  # <-- CHANGED THIS LINE


# ==========================================================
# Conversation Starters
# ==========================================================

def generate_conversation_starters(name: str, description: str) -> str:
    """
    Generate a simple conversation starter based on the guest profile.
    """
    description = description.lower()

    if "mathematics" in description or "analytical engine" in description:
        return (
            "Ask about mathematical theories "
            "or Charles Babbage's computing machines."
        )

    if "tesla" in name.lower() or "wireless energy" in description:
        return (
            "Discuss wireless energy transmission "
            "or his interest in pigeons."
        )

    if "curie" in name.lower() or "radioactivity" in description:
        return (
            "Ask about pioneering chemistry research "
            "and radioactivity."
        )

    return (
        "Welcome them warmly and ask how they "
        "are enjoying the event."
    )


# ==========================================================
# Document Builder
# ==========================================================

def create_document(guest: dict) -> Document:
    """
    Convert guest record into a LangChain document.
    """
    content = f"""
Name: {guest['name']}
Relation: {guest['relation']}
Description: {guest['description']}
Email: {guest['email']}
Conversation Starter:
{generate_conversation_starters(guest['name'], guest['description'])}
"""

    return Document(
        page_content=content.strip(),
        metadata={
            "name": guest["name"],
            "relation": guest["relation"],
        },
    )


# ==========================================================
# Dataset Loader
# ==========================================================

@lru_cache(maxsize=1)
@observe(as_type="span", name="load_guest_dataset_from_hf")
def load_guest_documents():
    """
    Load dataset once and cache it.
    """
    dataset = load_dataset("agents-course/unit3-invitees", split="train")

    documents = [create_document(dict(row)) for row in dataset]
    return documents


# ==========================================================
# Retriever Factory
# ==========================================================

@lru_cache(maxsize=1)
def get_bm25_retriever():
    """
    Create and cache BM25 retriever.
    """
    documents = load_guest_documents()

    retriever = BM25Retriever.from_documents(documents)
    retriever.k = 3

    return retriever


# ==========================================================
# Public Retriever
# ==========================================================

bm25_retriever = get_bm25_retriever()


# ==========================================================
# Quick Test
# ==========================================================

if __name__ == "__main__":
    @observe(name="retriever_standalone_test")
    def run_test():
        results = bm25_retriever.invoke("Ada Lovelace")
        for doc in results:
            print("=" * 50)
            print(doc.page_content)

    run_test()