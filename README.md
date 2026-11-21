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
