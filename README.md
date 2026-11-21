# reddit-reader

Personal, non-commercial, read-only reader for my own research, using the official
Reddit API via PRAW. It fetches public posts and comments from a short allow-list of
subreddits and prints or saves them with a permalink and fetch date, so any local
summary can link back to the source.

## Policy

- Read-only: never posts, comments, votes, messages or reports. No PRAW write method is used (a test checks the source).
- Application-only auth (client id and secret). No username or password anywhere.
- Never trains or fine-tunes models on Reddit data.
- Throttles itself: at least 1.5 s between API calls, at most 30 calls per run, at most 25 items per call.
- Sends a descriptive User-Agent.
- Content removed or deleted on Reddit must be deleted from local copies (see below).

## Setup

    python3 -m venv venv && . venv/bin/activate
    pip install -r requirements.txt
    export REDDIT_CLIENT_ID=...        # from your own Reddit app registration
    export REDDIT_CLIENT_SECRET=...
    export REDDIT_USER_AGENT="reddit-reader/0.1 (personal read-only research)"   # optional

Credentials come from environment variables only. Do not commit them.

## Usage

    python reddit_reader.py top LocalLLaMA --limit 10 --time week
    python reddit_reader.py new ClaudeAI --limit 5
    python reddit_reader.py search LocalLLM "quantization" --limit 10
    python reddit_reader.py comments <post_id> --limit 20
    python reddit_reader.py --out saved.jsonl new LocalLLaMA     # --out goes before the command

Output is JSON lines: title, selftext, author, score, created_utc, permalink,
fetched_at (UTC ISO), subreddit. Comments put their text in `selftext`.

The allow-list is `allowlist.txt` (one subreddit per line, `#` comments). Edit it to
change which subreddits may be read; anything else is rejected.

## Use with any model

No Claude-specific code. Three ways, all read-only and allow-list only:

1. **CLI JSON lines.** Run the commands above and feed the output to any model.
2. **Function calling.** `tool_schema.json` holds OpenAI-style tool definitions
   (`reddit_top`, `reddit_new`, `reddit_search`, `reddit_comments`). `tool_api.call_tool(name, arguments)`
   validates the call and returns a JSON string, never an exception. Works with any
   OpenAI-compatible server (Ollama, llama.cpp, vLLM, LM Studio). Unknown tools, unknown
   keys and wrong types give `{"error": ...}`; `limit` above 25 is clamped to 25.
   Results look like `{"source":"reddit","untrusted":true,"notice":...,"results":[...]}`
   and are capped at 20000 characters (selftext is cut and `"truncated": true` is set).
3. **stdin/stdout tool mode**, for non-Python frameworks:

        echo '{"name":"reddit_new","arguments":{"subreddit":"ClaudeAI","limit":5}}' | python reddit_reader.py tool

   One JSON object in, one JSON result out. Arguments come from JSON only, so no shell
   string building is needed.

Example, not tested here (Ollama Python client):

    import ollama, json, tool_api
    msgs = [{"role": "user", "content": "Summarise top LocalLLaMA posts this week"}]
    r = ollama.chat(model="llama3.1", messages=msgs, tools=tool_api.tool_definitions())
    for c in r.message.tool_calls or []:
        msgs.append({"role": "tool", "content": tool_api.call_tool(c.function.name, dict(c.function.arguments))})

Smaller open models follow injected instructions more easily. Keep the agent's other
tools read-only and treat all returned text as data, never as instructions.

## Untrusted data

Fetched text is untrusted. The tool only prints or saves it: it is never evaluated,
executed, passed to a shell, or used to build file paths. Treat saved files the same way.

## Deleting removed content

Periodically re-check saved items via their permalinks. If a post or comment has been
removed or deleted on Reddit, delete it from your local `.jsonl` files and any
summaries derived from it.

## Tests

    python -m unittest discover -s tests -v

## License

MIT
