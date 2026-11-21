import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import reddit_reader as rr  # noqa: E402
import tool_api  # noqa: E402
from test_reddit_reader import ALLOWED, FakeReddit, post  # noqa: E402


def call(name, args, reddit=None):
    out = tool_api.call_tool(name, args, reddit or FakeReddit(), ALLOWED, rr.Throttle(lambda s: None))
    return json.loads(out)


class ToolTests(unittest.TestCase):
    def test_unknown_tool(self):
        self.assertIn("unknown tool", call("reddit_post", {})["error"])

    def test_extra_keys_and_types(self):
        self.assertIn("unknown argument", call("reddit_new", {"subreddit": "ClaudeAI", "x": 1})["error"])
        self.assertIn("must be int", call("reddit_new", {"subreddit": "ClaudeAI", "limit": "5"})["error"])
        self.assertIn("must be str", call("reddit_new", {"subreddit": 5})["error"])
        self.assertIn("missing", call("reddit_search", {"subreddit": "ClaudeAI"})["error"])
        self.assertIn("error", call("reddit_new", "nope"))

    def test_limit_clamped(self):
        rd = FakeReddit()
        out = call("reddit_top", {"subreddit": "LocalLLaMA", "limit": 999}, rd)
        self.assertEqual(rd.sub.seen, [25])
        self.assertEqual(len(out["results"]), 25)

    def test_not_allowlisted(self):
        self.assertIn("allow-list", call("reddit_top", {"subreddit": "funny"})["error"])

    def test_untrusted_marker(self):
        out = call("reddit_new", {"subreddit": "ClaudeAI"})
        self.assertIs(out["untrusted"], True)
        self.assertEqual(out["notice"], tool_api.NOTICE)
        self.assertEqual(out["source"], "reddit")
        self.assertNotIn("truncated", out)

    def test_truncation(self):
        rd = FakeReddit()
        rd.sub.new = lambda limit: [type(post())(**{**vars(post()), "selftext": "x" * 50000})]
        out = call("reddit_new", {"subreddit": "ClaudeAI"}, rd)
        self.assertIs(out["truncated"], True)
        self.assertLessEqual(len(json.dumps(out, ensure_ascii=False)), tool_api.MAX_CHARS)
        self.assertGreater(len(out["results"][0]["selftext"]), 0)

    def test_schema_matches_dispatch(self):
        defs = tool_api.tool_definitions()
        self.assertEqual({d["function"]["name"] for d in defs}, set(tool_api.TOOLS))
        for d in defs:
            self.assertEqual(d["type"], "function")
            self.assertIn("untrusted", d["function"]["description"])
            props = d["function"]["parameters"]["properties"]
            self.assertEqual(set(props), set(tool_api.TOOLS[d["function"]["name"]][1]))

    def test_no_write_methods_in_tool_api(self):
        src = (ROOT / "tool_api.py").read_text()
        for w in ["submit", "reply", "upvote", "downvote", "crosspost", "report", "delete",
                  "award", "friend", "hide", "save", "username", "password"]:
            self.assertIsNone(re.search(rf"\b{w}", src, re.I), w)

    def test_stdin_mode_bad_input(self):
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = rr.tool_mode(io.StringIO("not json"))
        self.assertEqual(code, 2)
        self.assertIn("error", json.loads(buf.getvalue()))


if __name__ == "__main__":
    unittest.main()
