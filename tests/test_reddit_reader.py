import re
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace as NS

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import reddit_reader as rr  # noqa: E402

ALLOWED = {"localllama", "localllm", "claudeai"}


def post(i=1):
    return NS(title=f"t{i}", selftext="body", author=None, score=5, created_utc=1.0,
              permalink=f"/r/LocalLLaMA/comments/abc{i}/x/", subreddit="LocalLLaMA")


class FakeSub:
    def __init__(self):
        self.seen = []

    def top(self, time_filter, limit):
        self.seen.append(limit)
        return [post(i) for i in range(limit)]

    def new(self, limit):
        self.seen.append(limit)
        return [post(1)]

    def search(self, q, limit):
        return [post(1)]


class FakeReddit:
    def __init__(self):
        self.sub = FakeSub()

    def subreddit(self, name):
        return self.sub


def parse(argv):
    return rr.build_parser().parse_args(argv)


class Tests(unittest.TestCase):
    def test_no_write_methods_in_source(self):
        src = (ROOT / "reddit_reader.py").read_text()
        banned = ["submit", "reply", "upvote", "downvote", "crosspost", "message",
                  "report", "delete", "edit", "award", "block", "friend", "hide", "save",
                  "username", "password"]
        for w in banned:
            self.assertIsNone(re.search(rf"\b{w}", src, re.I), w)

    def test_allowlist_rejects(self):
        with self.assertRaises(rr.ReaderError):
            rr.run(parse(["top", "funny"]), FakeReddit(), ALLOWED, rr.Throttle(lambda s: None))

    def test_default_allowlist_file(self):
        self.assertEqual(rr.load_allowlist(), ALLOWED)

    def test_limit_capped_and_record_fields(self):
        rd = FakeReddit()
        rows = rr.run(parse(["top", "LocalLLaMA", "--limit", "999"]), rd, ALLOWED,
                      rr.Throttle(lambda s: None))
        self.assertEqual(rd.sub.seen, [25])
        self.assertEqual(len(rows), 25)
        r = rows[0]
        self.assertTrue(r["permalink"].startswith("https://"))
        self.assertEqual(r["author"], "[unknown]")
        for k in ("title", "selftext", "score", "created_utc", "fetched_at", "subreddit"):
            self.assertIn(k, r)

    def test_throttle_sleeps_and_caps(self):
        t = [0.0]
        sleeps = []
        th = rr.Throttle(sleep=sleeps.append, clock=lambda: t[0])
        th.tick()
        th.tick()
        self.assertEqual(sleeps, [1.5])
        with self.assertRaises(rr.ReaderError):
            for _ in range(rr.MAX_CALLS):
                th.tick()

    def test_missing_env_fails(self):
        with self.assertRaises(rr.ReaderError):
            rr.make_client(env={})

    def test_search_and_new(self):
        th = rr.Throttle(lambda s: None)
        self.assertEqual(len(rr.run(parse(["new", "ClaudeAI"]), FakeReddit(), ALLOWED, th)), 1)
        self.assertEqual(len(rr.run(parse(["search", "ClaudeAI", "q"]), FakeReddit(), ALLOWED, th)), 1)


if __name__ == "__main__":
    unittest.main()
