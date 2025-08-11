"""Example of using Olive v1 with Temporal integration.

Olive v1 Features:
- Temporal integration for reliable, scalable tool execution
- Built-in retry policies and timeout handling
- Rich CLI with animations and progress tracking
- Configuration via .olive.yaml or environment variables
- Automatic local Temporal server management
- FastAPI server with automatic tool discovery

This example demonstrates:
1. Basic tool registration with @olive_tool
2. Custom Temporal settings (timeout, retry policy)
3. Async and sync tool implementations
4. Client SDK usage for calling tools
5. LangChain integration
"""

import asyncio

from olive import olive_tool, run_dev
from olive_client import OliveClient


# Mark functions as Olive tools with the decorator
@olive_tool
def translate(text: str, target_language: str = "es") -> dict:
    """Translate text to another language."""
    # This is a mock implementation
    translations = {
        "es": "Hola",
        "fr": "Bonjour",
        "de": "Hallo",
        "it": "Ciao",
    }

    if text.lower() == "hello":
        return {"original": text, "translated": translations.get(target_language, text), "language": target_language}

    return {"original": text, "translated": f"[{target_language}] {text}", "language": target_language}


@olive_tool(description="Analyze sentiment of text")
async def analyze_sentiment(text: str, detailed: bool = False) -> dict:
    """Perform sentiment analysis on text."""
    # Mock sentiment analysis
    await asyncio.sleep(0.1)  # Simulate processing

    # Simple mock logic
    positive_words = ["good", "great", "excellent", "happy", "love"]
    negative_words = ["bad", "terrible", "hate", "sad", "awful"]

    text_lower = text.lower()
    positive_count = sum(word in text_lower for word in positive_words)
    negative_count = sum(word in text_lower for word in negative_words)

    if positive_count > negative_count:
        sentiment = "positive"
        score = 0.8
    elif negative_count > positive_count:
        sentiment = "negative"
        score = 0.2
    else:
        sentiment = "neutral"
        score = 0.5

    result = {"sentiment": sentiment, "score": score, "text": text}

    if detailed:
        result["details"] = {
            "positive_words": positive_count,
            "negative_words": negative_count,
            "word_count": len(text.split()),
        }

    return result


@olive_tool
def extract_keywords(text: str, max_keywords: int = 5) -> list[str]:
    """Extract keywords from text."""
    # Very simple keyword extraction
    words = text.lower().split()
    # Filter out common words
    stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for"}
    keywords = [w for w in words if w not in stop_words and len(w) > 3]

    # Return unique keywords
    unique_keywords = list(dict.fromkeys(keywords))
    return unique_keywords[:max_keywords]


@olive_tool(
    description="Process large text documents (example with custom Temporal settings)",
    timeout_seconds=600,  # 10 minutes timeout
    retry_policy={"max_attempts": 5, "initial_interval": 2},
)
async def process_document(content: str, operation: str = "summarize") -> dict:
    """Process a document with configurable operations."""
    # This demonstrates custom Temporal settings for long-running operations
    await asyncio.sleep(0.5)  # Simulate processing

    operations = {
        "summarize": f"Summary of {len(content)} chars: {content[:100]}...",
        "wordcount": f"Word count: {len(content.split())}",
        "analyze": f"Analysis complete for {len(content)} characters",
    }

    return {
        "operation": operation,
        "result": operations.get(operation, "Unknown operation"),
        "processed_at": "2024-01-01T00:00:00Z",  # Mock timestamp
        "temporal_execution": True,
    }


async def demo_client():
    """Demonstrate using the OliveClient."""
    # Connect to the server
    async with OliveClient("http://localhost:8000") as client:
        # List available tools
        print("Available tools:")
        tools = await client.get_tools()
        for tool in tools:
            print(f"  - {tool['name']}: {tool['description']}")

        print("\n" + "=" * 50 + "\n")

        # Call some tools
        print("Translating 'Hello' to Spanish:")
        result = await client.call_tool("translate", {"text": "Hello", "target_language": "es"})
        print(f"  Result: {result}")

        print("\nAnalyzing sentiment:")
        result = await client.call_tool(
            "analyze_sentiment", {"text": "This is a great example of how Olive works!", "detailed": True}
        )
        print(f"  Result: {result}")

        print("\nExtracting keywords:")
        result = await client.call_tool(
            "extract_keywords",
            {
                "text": "FastAPI makes building APIs incredibly fast and easy with automatic documentation",
                "max_keywords": 3,
            },
        )
        print(f"  Keywords: {result}")

        print("\nProcessing document (with Temporal):")
        result = await client.call_tool(
            "process_document",
            {
                "content": "This is a test document that would be processed by Temporal workers. " * 10,
                "operation": "summarize",
            },
        )
        print(f"  Result: {result}")

        print("\n" + "=" * 50 + "\n")

        # Convert to LangChain tools
        print("Converting to LangChain tools...")
        lc_tools = await client.as_langchain_tools()
        print(f"Created {len(lc_tools)} LangChain tools")

        # Use with LangChain (example)
        print("\nUsing with LangChain:")
        translate_tool = lc_tools[0]  # First tool
        lc_result = await translate_tool.ainvoke({"text": "Hello", "target_language": "fr"})
        print(f"  LangChain result: {lc_result}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "client":
        # Run the client demo
        asyncio.run(demo_client())
    else:
        # Run the server using Olive v1 with Temporal
        print("Starting Olive v1 with Temporal integration...")
        print("This will start:")
        print("  - Local Temporal server (if needed)")
        print("  - Temporal worker for executing tools")
        print("  - FastAPI server at http://localhost:8000")
        print("\nRun 'python example.py client' in another terminal to test the client")

        run_dev()
