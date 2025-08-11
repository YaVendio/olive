"""Example Olive project."""

from olive import olive_tool, create_app

app = create_app()  # FastAPI app with Olive routes


@olive_tool(description="Translate text to another language")
async def translate(text: str, target_language: str = "es") -> dict:
    """Translate text to the target language."""
    # In a real app, you'd use a translation service
    translations = {
        "es": "Hola",
        "fr": "Bonjour",
        "de": "Hallo",
    }
    greeting = translations.get(target_language, "Hello")
    return {
        "original": text,
        "translated": f"{greeting}! (Translated: {text})",
        "language": target_language,
    }


@olive_tool(
    description="Analyze sentiment of text",
    timeout_seconds=30,
    retry_policy={"max_attempts": 3},
)
async def analyze_sentiment(text: str) -> dict:
    """Analyze the sentiment of the provided text."""
    # Simulate some processing
    import asyncio
    await asyncio.sleep(1)

    # In a real app, you'd use an NLP service
    positive_words = ["good", "great", "excellent", "happy", "love"]
    negative_words = ["bad", "terrible", "hate", "sad", "awful"]

    text_lower = text.lower()
    positive_count = sum(1 for word in positive_words if word in text_lower)
    negative_count = sum(1 for word in negative_words if word in text_lower)

    if positive_count > negative_count:
        sentiment = "positive"
        score = 0.8
    elif negative_count > positive_count:
        sentiment = "negative"
        score = 0.2
    else:
        sentiment = "neutral"
        score = 0.5

    return {
        "text": text,
        "sentiment": sentiment,
        "score": score,
        "confidence": 0.9,
    }


if __name__ == "__main__":
    # Run with: olive dev
    import olive
    olive.run_dev()
