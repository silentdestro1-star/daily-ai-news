import json
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
import os

# ============================================================
# CONFIGURATION
# ============================================================
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_MODEL = "llama-3.1-8b-instant"  # Valid model name for current Groq API

RSS_FEEDS = {
    "OpenAI Blog": "https://openai.com/news/rss.xml",
    "Google AI Blog": "https://ai.googleblog.com/feeds/posts/default",
    "TechCrunch AI": "https://techcrunch.com/category/artificial-intelligence/feed/",
    "The Verge AI": "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml",
    "MIT Tech Review AI": "https://www.technologyreview.com/topic/artificial-intelligence/feed/",
}

GITHUB_TRENDING_URL = "https://raw.githubusercontent.com/isboyjc/github-trending-api/main/data/daily/all.json"

# Keywords to filter out corporate PR and promote technical news
PR_KEYWORDS = ["academy", "partnership", "sales", "united nations", "speech", "anniversary", "cyber", "legal", "case study"]
TECH_KEYWORDS = ["model", "paper", "framework", "tool", "research", "benchmark", "release", "update", "open-source", "api"]

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def fetch_rss(feed_url):
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
    try:
        req = urllib.request.Request(GITHUB_TRENDING_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode())
        ai_keywords = ["ai", "ml", "llm", "gpt", "neural", "machine-learning", "deep-learning", "langchain", "transformer", "diffusion"]
        ai_repos = []
        for repo in data.get("items", data.get("repos", []))[:50]:
            # Fix: Extract proper repo name (owner/repo) from URL or field
            url = repo.get("url", repo.get("link", ""))
            name = repo.get("name") or repo.get("repo") or url.split("github.com/")[-1]
            desc = repo.get("description", "") or ""
            combined = (name + " " + desc).lower()
            if any(kw in combined for kw in ai_keywords):
                ai_repos.append({
                    "name": name,
                    "description": desc[:200],
                    "url": url,
                    "stars": repo.get("stars", repo.get("starCount", 0))
                })
        return ai_repos[:5]
    except Exception as e:
        print(f"Error fetching GitHub trending: {e}")
        return []

def call_groq(prompt, system_prompt):
    if not GROQ_API_KEY:
        return "⚠️ **Error:** GROQ_API_KEY is missing. Please add it to GitHub Secrets."
    
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
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode())
        return result["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Groq API error: {e}")
        return f"⚠️ **API Error:** {str(e)}. Check your Groq API key."

def load_seen_articles():
    if os.path.exists("data/seen_articles.json"):
        with open("data/seen_articles.json", "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()

def save_seen_articles(seen_set):
    os.makedirs("data", exist_ok=True)
    with open("data/seen_articles.json", "w", encoding="utf-8") as f:
        json.dump(list(seen_set), f, indent=2)

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

    # 1. Deduplication
    seen_urls = load_seen_articles()
    new_articles = [a for a in all_articles if a["link"] not in seen_urls]

    # 2. Relevance Scoring (Filter out PR, promote Tech)
    for a in new_articles:
        text = (a["title"] + " " + a["description"]).lower()
        score = sum(2 for kw in TECH_KEYWORDS if kw in text)
        score -= sum(3 for kw in PR_KEYWORDS if kw in text)
        a["score"] = score

    # Sort by score (highest first) and take top 6
    new_articles.sort(key=lambda x: x["score"], reverse=True)
    top_articles = new_articles[:6]

    # Save seen articles
    for a in top_articles:
        seen_urls.add(a["link"])
    save_seen_articles(seen_urls)

    # 3. Generate Summaries
    print("Summarizing news...")
    for a in top_articles:
        raw_text = f"Title: {a['title']}\nDescription: {a['description']}"
        sys_prompt = "Summarize this for a B.Tech AI/ML student in 2-3 simple sentences. Focus on what changed, why it matters, and skip PR language."
        a["summary"] = call_groq(raw_text, sys_prompt)

    # 4. Generate AI Tool of the Day
    print("Finding AI Tool of the Day...")
    context = " | ".join([a["title"] for a in top_articles])
    tool_prompt = f"Based on today's AI news: {context}. Pick ONE specific AI tool mentioned. Format exactly: **Tool Name:** [Name]. **What it does:** [1 sentence]. **How a B.Tech student can use it:** [1 sentence]. **Link:** [URL]."
    ai_tool = call_groq(tool_prompt, "You are an AI tools expert. Give exactly one tool in the requested format.")

    # 5. Generate B.Tech Student Task
    print("Generating B.Tech Task...")
    task_prompt = f"Based on today's AI news: {context}. Create ONE practical 30-60 minute task for a 2nd-year B.Tech student. Must be free and beginner-friendly. Format exactly: **Task:** [Description]. **Why this helps:** [Reason]. **Steps:** [1-2 steps]."
    ai_task = call_groq(task_prompt, "You are an AI mentor for a 2nd-year B.Tech student. Give practical, free, hands-on tasks.")

    # 6. Fetch GitHub Trending
    print("Fetching GitHub trending...")
    github_repos = fetch_github_trending()

    # ============================================================
    # BUILD THE DIGEST
    # ============================================================
    today = datetime.utcnow().strftime("%Y-%m-%d")
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

    print(f"Digest saved to {filename}")

if __name__ == "__main__":
    main()
