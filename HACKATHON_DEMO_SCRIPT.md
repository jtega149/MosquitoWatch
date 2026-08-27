# Demo script: semantic cache + RAG (≈30 seconds)

This assistant is Gemini RAG with RedisVL in front. We embed each question; if similarity is 0.95 or higher, Redis returns the cached answer and we skip Gemini—saving latency and cost. Misses retrieve app docs plus a dated forecast summary—mean, min, max, top ZIPs—then generate. Old vectors delete by `as_of_date`. Ask the highest-risk ZIP twice in different words and watch the **Cache hit** chip.
