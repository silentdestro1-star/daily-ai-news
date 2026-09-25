import json
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
import os

# ============================================================
# CONFIGURATION
# ============================================================
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")  # Comes from GitHub Secrets
GROQ_MODEL = "llama3-8b-8192"  # Free model on Groq

# RSS feeds to pull AI news from
RSS_FEEDS = {
    "OpenAI Blog": "https://openai.com/news/rss.xml",
    "Google AI Blog": "https://ai.googleblog.com/feeds/posts/default",
    "TechCrunch AI": "https://techcrunch.com/category/artificial-intelligence/feed/",
    "The Verge AI": "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml",
    "MIT Tech Review AI": "https://www.technologyreview.com/topic/artificial-intelligence/feed/",
}

# GitHub Trending API (free, no key)
GITHUB_TRENDING_URL = "https://raw.githubusercontent.com/isboyjc/github-trending-api/main/data/daily/all.json"

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def fetch_rss(feed_url):
    """Fetch and parse an RSS feed, returning list of articles."""
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
            pub_date = item.findtext("pubDate", "").strip()
            if title and link:
                articles.append({
                    "title": title,
                    "link": link,
                    "description": description[:300],  # Trim for summarizer
                    "source": feed_url.split("/")[2],
                    "pub_date": pub_date
                })
        return articles[:5]  # Take top 5 from each feed
    except Exception as e:
        print(f"Error fetching {feed_url}: {e}")
        return []

def fetch_github_trending():
    """Fetch today's trending GitHub repos."""
    try:
        req = urllib.request.Request(GITHUB_TRENDING_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode())
        # Filter for AI-related repos (check name/description for keywords)
        ai_keywords = ["ai", "ml", "llm", "gpt", "neural", "machine-learning",
                       "deep-learning", "langchain", "transformer", "diffusion"]
        ai_repos = []
        for repo in data.get("items", data.get("repos", []))[:50]:
            name = repo.get("name", "") or repo.get("repo", "")
            desc = repo.get("description", "") or ""
            combined = (name + " " + desc).lower()
            if any(kw in combined for kw in ai_keywords):
                ai_repos.append({
                    "name": name,
                    "description": desc[:200],
                    "url": repo.get("url", repo.get("link", "")),
                    "stars": repo.get("stars", repo.get("starCount", 0))
                })
        return ai_repos[:5]  # Top 5 AI repos
    except Exception as e:
        print(f"Error fetching GitHub trending: {e}")
        return []

def summarize_with_groq(text, prompt_type="summarize"):
    """Use Groq API to summarize text in simple language."""
    if not GROQ_API_KEY:
        return "(Summarizer not configured — raw text below)\n" + text[:500]

    prompts = {
        "summarize": "Rewrite the following AI news in 2-3 simple sentences that a beginner can understand. Avoid jargon. Be concise.",
        "task": "Based on the following AI news topics, suggest ONE practical AI task a beginner can do in 30 minutes to improve their skills. Format: **Task:** [description]. **Why:** [reason]."
    }

    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": prompts.get(prompt_type, prompts["summarize"])},
            {"role": "user", "content": text}
        ],
        "temperature": 0.7,
        "max_tokens": 300
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
        return result["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Summarizer error: {e}")
        return "(Summarizer unavailable — raw text below)\n" + text[:500]

# ============================================================
# MAIN WORKFLOW
# ============================================================

def main():
    print("Fetching AI news...")
    all_articles = []
    for source_name, feed_url in RSS_FEEDS.items():
        articles = fetch_rss(feed_url)
        for a in articles:
            a["source_name"] = source_name
        all_articles.extend(articles)
        print(f"  {source_name}: {len(articles)} articles")

    print(f"Total articles fetched: {len(all_articles)}")

    # Deduplicate by title
    seen_titles = set()
    unique_articles = []
    for a in all_articles:
        if a["title"].lower() not in seen_titles:
            seen_titles.add(a["title"].lower())
            unique_articles.append(a)

    # Summarize each article
    print("Summarizing articles...")
    for a in unique_articles[:10]:  # Limit to 10 for speed
        raw_text = f"Title: {a['title']}\nDescription: {a['description']}"
        a["summary"] = summarize_with_groq(raw_text, "summarize")
        print(f"  Summarized: {a['title'][:60]}...")

    # Fetch GitHub trending
    print("Fetching GitHub trending AI repos...")
    github_repos = fetch_github_trending()
    print(f"  Found {len(github_repos)} AI repos")

    # Generate the AI task
    all_titles = " | ".join([a["title"] for a in unique_articles[:8]])
    ai_task = summarize_with_groq(all_titles, "task")

    # ============================================================
    # BUILD THE DIGEST
    # ============================================================
    today = datetime.utcnow().strftime("%Y-%m-%d")
    lines = []
    lines.append(f"# 🤖 Daily AI Digest — {today}\n")

    # --- AI NEWS ---
    lines.append("## 📰 AI News (Simple Summary)\n")
    for a in unique_articles[:8]:
        lines.append(f"### {a['title']}")
        lines.append(f"*Source: {a['source_name']}*\n")
        lines.append(f"{a.get('summary', 'No summary available.')}\n")
        lines.append(f"[Read original]({a['link']})\n")

    # --- NEW GITHUB REPOS ---
    lines.append("\n## 🐙 New AI GitHub Repos\n")
    if github_repos:
        for repo in github_repos:
            lines.append(f"### {repo['name']}")
            lines.append(f"{repo['description'][:200]}\n")
            lines.append(f"⭐ {repo['stars']} stars | [View repo]({repo['url']})\n")
    else:
        lines.append("No AI-related repos found today. Check back tomorrow!\n")

    # --- AI TASK ---
    lines.append("\n## 🎯 Today's AI Task\n")
    lines.append(ai_task)
    lines.append("\n---")
    lines.append("*Generated automatically by GitHub Actions*")

    digest = "\n".join(lines)

    # Save to file
    os.makedirs("digests", exist_ok=True)
    filename = f"digests/{today}.md"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(digest)

    print(f"Digest saved to {filename}")
    print("Done!")

if __name__ == "__main__":
    main()