"""
search_document.py — Document Search using OpenAI Vector Store & File Search Tool

Demonstrates the full flow:
  1. Upload a document to OpenAI
  2. Create a Vector Store
  3. Add the file to the Vector Store (auto chunks, embeds & indexes)
  4. Create an Agent with FileSearchTool
  5. Run a query against the document

Usage:
    import asyncio
    from search_document import search

    result = asyncio.run(search("company_policy.pdf", "What is the remote work policy?"))
    print(result)
"""

from openai import OpenAI
from agents import Agent, Runner, FileSearchTool

client = OpenAI()


async def search(file_path: str, query: str, store_name: str = "Document Store") -> str:
    """
    Upload a document, create a vector store, and search it with a query.

    Args:
        file_path:   Path to the document (PDF, TXT, DOCX).
        query:       The question to ask about the document.
        store_name:  Name for the vector store on OpenAI.

    Returns:
        The agent's answer grounded in the document content.
    """
    # Step 1: Upload document to OpenAI
    file = client.files.create(
        file=open(file_path, "rb"),
        purpose="assistants"
    )

    # Step 2: Create Vector Store
    vector_store = client.vector_stores.create(
        name=store_name
    )

    # Step 3: Add file to Vector Store
    # OpenAI auto chunks, embeds & indexes
    client.vector_stores.files.create(
        vector_store_id=vector_store.id,
        file_id=file.id
    )

    # Step 4: Create Agent with File Search
    agent = Agent(
        name="Document Search Assistant",
        instructions=(
            "Answer questions using the uploaded documents. "
            "Only use facts found via the file search tool; never invent information."
        ),
        tools=[FileSearchTool(
            vector_store_ids=[vector_store.id]
        )]
    )

    # Step 5: Run query
    result = await Runner.run(agent, query)

    return result.final_output
