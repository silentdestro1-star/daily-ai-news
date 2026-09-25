import json
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime
import os

# ============================================================
# CONFIGURATION
# ============================================================
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

GROQ_MODEL = "llama-3.1-8b-instant"
OPENROUTER_MODEL = "openrouter/free"  # Auto-routes to a free model

RSS_FEEDS = {
    "OpenAI Blog": "https://openai.com/news/rss.xml",
    "Google AI Blog": "https://ai.googleblog.com/feeds/posts/default",
    "TechCrunch AI": "https://techcrunch.com/category/artificial-intelligence/feed/",
    "The Verge AI": "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml",
    "MIT Tech Review AI": "https://www.technologyreview.com/topic/artificial-intelligence/feed/",
}

GITHUB_TRENDING_URL = "https://raw.githubusercontent.com/isboyjc/github-trending-api/main/data/daily/all.json"

# Scoring keywords for relevance filtering
PR_KEYWORDS = ["academy", "partnership", "sales", "united nations", "speech",
               "anniversary", "cyber", "legal", "case study", "enterprise",
               "customer story", "pricing", "acquisition"]
TECH_KEYWORDS = ["model", "paper", "framework", "tool", "research", "benchmark",
                 "release", "update", "open-source", "api", "embedding",
                 "fine-tuning", "llm", "training", "inference", "agent"]

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def fetch_rss(feed_url):
    """Fetch and parse an RSS feed, returning a list of articles."""
    try:
        req = urllib.request.Request(feed_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as response:
            xml_data = response.read()
        root = ET.fromstring(xml_data)
        articles = []
        for item in root.iter("item"):
            title = item.findtext("title", "").strip()
            link = item.findtext("link", "").strip()
            description = item.findtext("description", "").strip()
            if title and link:
                articles.append({
                    "title": title,
                    "link": link,
                    "description": description[:300],
                    "source": feed_url.split("/")[2]
                })
        return articles
    except Exception as e:
        print(f"Error fetching {feed_url}: {e}")
        return []


def fetch_github_trending():
    """Fetch trending GitHub repos and filter for AI-related ones."""
    try:
        req = urllib.request.Request(GITHUB_TRENDING_URL,
                                     headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode())

        ai_keywords = ["ai", "ml", "llm", "gpt", "neural", "machine-learning",
                       "deep-learning", "langchain", "transformer", "diffusion",
                       "agent", "rag", "embedding", "model"]
        ai_repos = []

        # Handle different possible structures from the API
        items = data.get("items", data.get("repos", data.get("data", [])))
        if isinstance(items, dict):
            items = items.get("items", items.get("repos", []))

        for repo in items[:60]:
            url = repo.get("url", repo.get("link", repo.get("html_url", "")))
            # Fix: Extract clean owner/repo name from URL
            if "github.com/" in url:
                name = url.split("github.com/")[-1].strip("/")
            else:
                name = repo.get("name", repo.get("repo", repo.get("full_name", "")))
            desc = repo.get("description", "") or ""
            combined = (name + " " + desc).lower()

            if any(kw in combined for kw in ai_keywords):
                ai_repos.append({
                    "name": name,
                    "description": desc[:200],
                    "url": url,
                    "stars": repo.get("stars", repo.get("starCount",
                             repo.get("stargazers_count", 0)))
                })
        return ai_repos[:5]
    except Exception as e:
        print(f"Error fetching GitHub trending: {e}")
        return []


def call_groq(prompt, system_prompt):
    """Attempt to call Groq API. Returns (success, response_text)."""
    if not GROQ_API_KEY:
        return False, "GROQ_API_KEY missing"

    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 400
    }
    try:
        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/chat/completions",
            data=json.dumps(payload).encode(),
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode())
        text = result["choices"][0]["message"]["content"].strip()
        if text:
            return True, text
        return False, "Empty response from Groq"
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        print(f"Groq HTTP {e.code}: {error_body[:200]}")
        return False, f"Groq HTTP {e.code}"
    except Exception as e:
        print(f"Groq error: {e}")
        return False, str(e)


def call_openrouter(prompt, system_prompt):
    """Attempt to call OpenRouter API. Returns (success, response_text)."""
    if not OPENROUTER_API_KEY:
        return False, "OPENROUTER_API_KEY missing"

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 400
    }
    try:
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/chat/completions",
            data=json.dumps(payload).encode(),
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/silentdestro1-star/daily-ai-news",
                "X-OpenRouter-Title": "Daily AI Digest"
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode())
        text = result["choices"][0]["message"]["content"].strip()
        if text:
            return True, text
        return False, "Empty response from OpenRouter"
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        print(f"OpenRouter HTTP {e.code}: {error_body[:200]}")
        return False, f"OpenRouter HTTP {e.code}"
    except Exception as e:
        print(f"OpenRouter error: {e}")
        return False, str(e)


def call_llm(prompt, system_prompt):
    """Try Groq first, fall back to OpenRouter, then to a raw-text fallback."""
    print("  -> Trying Groq...")
    success, result = call_groq(prompt, system_prompt)
    if success:
        print("  -> Groq succeeded.")
        return result

    print(f"  -> Groq failed ({result}). Trying OpenRouter...")
    success, result = call_openrouter(prompt, system_prompt)
    if success:
        print("  -> OpenRouter succeeded.")
        return result

    print(f"  -> Both APIs failed. Last error: {result}")
    # Return the raw text as last resort so the digest still has content
    return f"*(Summary unavailable — showing raw text)*\n\n{prompt[:400]}"


def load_seen_articles():
    """Load previously seen article URLs to avoid duplicates."""
    if os.path.exists("data/seen_articles.json"):
        try:
            with open("data/seen_articles.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                # Support both list and dict formats
                if isinstance(data, dict):
                    return set(data.get("urls", []))
                return set(data)
        except Exception:
            return set()
    return set()


def save_seen_articles(seen_set):
    """Save seen article URLs, keeping only the last 500 to prevent file bloat."""
    os.makedirs("data", exist_ok=True)
    # Keep only the most recent 500 URLs
    urls = list(seen_set)[-500:]
    with open("data/seen_articles.json", "w", encoding="utf-8") as f:
        json.dump(urls, f, indent=2)


# ============================================================
# MAIN WORKFLOW
# ============================================================

def main():
    today = datetime.utcnow().strftime("%Y-%m-%d")
    print(f"=== Starting Daily AI Digest for {today} ===")

    # ---- STEP 1: Fetch all articles ----
    print("\n[1/5] Fetching AI news from RSS feeds...")
    all_articles = []
    for source_name, feed_url in RSS_FEEDS.items():
        articles = fetch_rss(feed_url)
        for a in articles:
            a["source_name"] = source_name
        all_articles.extend(articles)
        print(f"  {source_name}: {len(articles)} articles")

    print(f"  Total raw articles: {len(all_articles)}")

    # ---- STEP 2: Deduplicate against seen articles ----
    print("\n[2/5] Deduplicating against previously seen articles...")
    seen_urls = load_seen_articles()
    new_articles = [a for a in all_articles if a["link"] not in seen_urls]
    print(f"  New articles (not seen before): {len(new_articles)}")

    # If we filtered everything out, fall back to all articles
    if len(new_articles) < 3:
        print("  Too few new articles — using all fetched articles.")
        new_articles = all_articles

    # ---- STEP 3: Score and filter by relevance ----
    print("\n[3/5] Scoring articles by relevance...")
    for a in new_articles:
        text = (a["title"] + " " + a["description"]).lower()
        score = sum(2 for kw in TECH_KEYWORDS if kw in text)
        score -= sum(3 for kw in PR_KEYWORDS if kw in text)
        a["score"] = score

    new_articles.sort(key=lambda x: x["score"], reverse=True)
    top_articles = new_articles[:6]

    print("  Top articles selected:")
    for a in top_articles:
        print(f"    [{a['score']:+d}] {a['title'][:70]}...")

    # Mark these as seen
    for a in top_articles:
        seen_urls.add(a["link"])
    save_seen_articles(seen_urls)

    # ---- STEP 4: Generate AI content ----
    print("\n[4/5] Generating AI summaries and content...")

    # Build context from top articles
    news_context = "\n".join([
        f"- {a['title']}: {a['description'][:150]}"
        for a in top_articles
    ])

    # 4a. Summarize each news item individually
    print("  Summarizing news items...")
    for a in top_articles:
        raw_text = f"Title: {a['title']}\nDescription: {a['description']}"
        sys_prompt = (
            "Summarize this for a B.Tech AI/ML student in 2-3 simple sentences. "
            "Focus on what changed, why it matters, and skip PR language. "
            "Be direct and technical but clear."
        )
        a["summary"] = call_llm(raw_text, sys_prompt)

    # 4b. AI Tool of the Day
    print("  Generating AI Tool of the Day...")
    tool_prompt = (
        f"Today's AI news headlines:\n{news_context}\n\n"
        "Pick exactly ONE specific AI tool, library, or framework mentioned in or "
        "related to these stories. "
        "Format your response exactly like this:\n"
        "**Tool Name:** [name]\n"
        "**What it does:** [one clear sentence]\n"
        "**How a B.Tech student can use it:** [one practical sentence]\n"
        "**Link:** [URL if available, otherwise write 'Search on GitHub']"
    )
    tool_sys = (
        "You are an AI tools expert. Pick exactly one specific, real, "
        "currently-existing tool. Do not invent tools. Follow the format exactly."
    )
    ai_tool = call_llm(tool_prompt, tool_sys)

    # 4c. B.Tech 2nd Year Task
    print("  Generating B.Tech task...")
    task_prompt = (
        f"Today's AI news headlines:\n{news_context}\n\n"
        "Create ONE practical 30-60 minute hands-on task for a 2nd-year B.Tech "
        "student to improve their AI skills today. "
        "The task must be: (1) completely free, (2) doable with just a laptop and "
        "internet, (3) beginner-friendly. "
        "Format your response exactly like this:\n"
        "**Task:** [clear description]\n"
        "**Why this helps:** [one sentence]\n"
        "**Steps:** [1-2 concrete steps to follow]"
    )
    task_sys = (
        "You are an AI mentor for a 2nd-year B.Tech student. "
        "Give practical, free, hands-on tasks only. Follow the format exactly."
    )
    ai_task = call_llm(task_prompt, task_sys)

    # ---- STEP 5: Fetch GitHub trending ----
    print("\n[5/5] Fetching GitHub trending AI repos...")
    github_repos = fetch_github_trending()
    print(f"  Found {len(github_repos)} AI repos")

    # ============================================================
    # BUILD THE DIGEST
    # ============================================================
    lines = []
    lines.append(f"# 🤖 Daily AI Digest — {today}\n")
    lines.append("Welcome to your daily AI update! Here is everything you need to know today.\n")

    # --- SECTION 1: AI NEWS ---
    lines.append("---")
    lines.append("## 📰 AI News (Simple Summary)\n")
    if top_articles:
        for a in top_articles:
            lines.append(f"### {a['title']}")
            lines.append(f"*Source: {a['source_name']}*\n")
            lines.append(f"{a.get('summary', 'No summary available.')}\n")
            lines.append(f"[Read original]({a['link']})\n")
    else:
        lines.append("No new AI news found today. Check back tomorrow!\n")

    # --- SECTION 2: AI TOOL OF THE DAY ---
    lines.append("---")
    lines.append("## 🛠️ AI Tool of the Day\n")
    lines.append(ai_tool)
    lines.append("\n")

    # --- SECTION 3: NEW GITHUB REPOS ---
    lines.append("---")
    lines.append("## 🐙 New AI GitHub Repos\n")
    if github_repos:
        for repo in github_repos:
            lines.append(f"### [{repo['name']}]({repo['url']})")
            lines.append(f"{repo['description'][:200]}\n")
            lines.append(f"⭐ {repo['stars']} stars\n")
    else:
        lines.append("No AI-related repos found today. Check back tomorrow!\n")

    # --- SECTION 4: B.TECH STUDENT TASK ---
    lines.append("---")
    lines.append("## 🎓 B.Tech 2nd Year AI Task\n")
    lines.append(ai_task)
    lines.append("\n")

    lines.append("---")
    lines.append("*Generated automatically by GitHub Actions*")

    digest = "\n".join(lines)

    os.makedirs("digests", exist_ok=True)
    filename = f"digests/{today}.md"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(digest)

    print(f"\n✅ Digest saved to {filename}")
    print("=== Done ===")


if __name__ == "__main__":
    main()