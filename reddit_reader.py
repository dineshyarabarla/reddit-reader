"""Read-only Reddit reader (PRAW, application-only). Output is JSON lines."""
import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

MAX_LIMIT = 25
MIN_DELAY = 1.5
MAX_CALLS = 30
DEFAULT_UA = "reddit-reader/0.1 (personal read-only research)"
ALLOWLIST_FILE = Path(__file__).with_name("allowlist.txt")


class ReaderError(Exception):
    pass


class Throttle:
    """Sleeps at least MIN_DELAY between API calls; refuses more than MAX_CALLS."""

    def __init__(self, sleep=time.sleep, clock=time.monotonic):
        self.calls, self._last, self._sleep, self._clock = 0, None, sleep, clock

    def tick(self):
        if self.calls >= MAX_CALLS:
            raise ReaderError(f"call cap of {MAX_CALLS} per run reached")
        if self._last is not None:
            wait = MIN_DELAY - (self._clock() - self._last)
            if wait > 0:
                self._sleep(wait)
        self._last = self._clock()
        self.calls += 1


def load_allowlist(path=ALLOWLIST_FILE):
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    return {l.strip().lower() for l in lines if l.strip() and not l.startswith("#")}


def check_subreddit(name, allowed):
    if name.lower() not in allowed:
        raise ReaderError(f"subreddit '{name}' is not on the allow-list ({', '.join(sorted(allowed))})")
    return name


def clamp(limit):
    return max(1, min(int(limit), MAX_LIMIT))


def make_client(env=os.environ):
    cid, secret = env.get("REDDIT_CLIENT_ID"), env.get("REDDIT_CLIENT_SECRET")
    if not cid or not secret:
        raise ReaderError("set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET in the environment")
    import praw  # imported lazily so tests need no praw install

    reddit = praw.Reddit(client_id=cid, client_secret=secret,
                         user_agent=env.get("REDDIT_USER_AGENT") or DEFAULT_UA)
    reddit.read_only = True
    return reddit


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def record(item, fetched_at):
    """Plain-data record; text is untrusted and is only ever serialised."""
    body = getattr(item, "selftext", None)
    if body is None:
        body = getattr(item, "body", "")
    return {
        "title": getattr(item, "title", ""),
        "selftext": body,
        "author": str(item.author) if getattr(item, "author", None) else "[unknown]",
        "score": item.score,
        "created_utc": item.created_utc,
        "permalink": "https://www.reddit.com" + item.permalink,
        "fetched_at": fetched_at,
        "subreddit": str(item.subreddit),
    }


def run(args, reddit, allowed, throttle):
    fetched = _now()
    limit = clamp(getattr(args, "limit", 10))
    if args.cmd == "comments":
        throttle.tick()
        post = reddit.submission(id=args.post_id)
        check_subreddit(str(post.subreddit), allowed)
        throttle.tick()
        post.comments.replace_more(limit=0)
        items = list(post.comments.list())[:limit]
    else:
        sub = reddit.subreddit(check_subreddit(args.subreddit, allowed))
        throttle.tick()
        if args.cmd == "top":
            items = list(sub.top(time_filter=args.time, limit=limit))
        elif args.cmd == "new":
            items = list(sub.new(limit=limit))
        else:
            items = list(sub.search(args.query, limit=limit))
    return [record(i, fetched) for i in items]


def build_parser():
    p = argparse.ArgumentParser(prog="reddit-reader", description=__doc__)
    p.add_argument("--out", help="also append JSON lines to this file")
    sp = p.add_subparsers(dest="cmd", required=True)
    t = sp.add_parser("top")
    t.add_argument("subreddit")
    t.add_argument("--time", choices=["day", "week", "month"], default="week")
    n = sp.add_parser("new")
    n.add_argument("subreddit")
    s = sp.add_parser("search")
    s.add_argument("subreddit")
    s.add_argument("query")
    c = sp.add_parser("comments")
    c.add_argument("post_id")
    for x in (t, n, s, c):
        x.add_argument("--limit", type=int, default=10, help=f"max {MAX_LIMIT}")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        allowed = load_allowlist()
        reddit = make_client()
        rows = run(args, reddit, allowed, Throttle())
    except ReaderError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    lines = [json.dumps(r, ensure_ascii=False) for r in rows]
    print("\n".join(lines))
    if args.out and lines:
        with open(args.out, "a", encoding="utf-8") as f:  # user-supplied path only
            f.write("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
