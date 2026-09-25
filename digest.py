import json
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
import os

# ============================================================
# CONFIGURATION
# ============================================================
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
# Updated model name to ensure compatibility with current Groq API
GROQ_MODEL = "llama-3.1-8b-instant" 

RSS_FEEDS = {
    "OpenAI Blog": "https://openai.com/news/rss.xml",
    "Google AI Blog": "https://ai.googleblog.com/feeds/posts/default",
    "TechCrunch AI": "https://techcrunch.com/category/artificial-intelligence/feed/",
    "The Verge AI": "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml",
    "MIT Tech Review AI": "https://www.technologyreview.com/topic/artificial-intelligence/feed/",
}

GITHUB_TRENDING_URL = "https://raw.githubusercontent.com/isboyjc/github-trending-api/main/data/daily/all.json"

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
        return articles[:5]
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
        return ai_repos[:5]
    except Exception as e:
        print(f"Error fetching GitHub trending: {e}")
        return []

def call_groq(prompt, system_prompt):
    """Generic function to call Groq API"""
    if not GROQ_API_KEY:
        return "(API Key missing. Please check GitHub Secrets.)"
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 300
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
        return "(Summarizer unavailable — raw text below)\n" + prompt[:300]

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

    seen_titles = set()
    unique_articles = []
    for a in all_articles:
        if a["title"].lower() not in seen_titles:
            seen_titles.add(a["title"].lower())
            unique_articles.append(a)

    # 1. Summarize News
    print("Summarizing news...")
    for a in unique_articles[:6]: # Limit to 6 for speed
        raw_text = f"Title: {a['title']}\nDescription: {a['description']}"
        sys_prompt = "Rewrite the following AI news in 2-3 simple sentences for a beginner. Avoid jargon. Be concise."
        a["summary"] = call_groq(raw_text, sys_prompt)

    # 2. Generate AI Tool of the Day
    print("Finding AI Tool of the Day...")
    news_context = " | ".join([a["title"] for a in unique_articles[:6]])
    tool_prompt = f"Based on today's AI news: {news_context}. Suggest ONE specific AI tool. Format: **Tool Name:** [Name]. **What it does:** [1 sentence]. **Link (if applicable):** [URL]."
    ai_tool = call_groq(tool_prompt, "You are an AI tools expert. Suggest exactly one tool in the requested format.")

    # 3. Generate B.Tech Student Task
    print("Generating B.Tech Task...")
    task_prompt = f"Based on today's AI news: {news_context}. Create ONE practical 30-60 minute task for a 2nd-year B.Tech student to improve their AI skills. Must be free and beginner-friendly. Format: **Task:** [Description]. **Why this helps:** [Reason]. **Steps:** [1-2 steps]."
    ai_task = call_groq(task_prompt, "You are an AI mentor for a 2nd-year B.Tech student. Give practical, free, hands-on tasks.")

    # 4. Fetch GitHub Trending
    print("Fetching GitHub trending...")
    github_repos = fetch_github_trending()

    # ============================================================
    # BUILD THE DIGEST (NEW FORMAT)
    # ============================================================
    today = datetime.utcnow().strftime("%Y-%m-%d")
    lines = []
    lines.append(f"# 🤖 Daily AI Digest — {today}\n")
    lines.append("Welcome to your daily AI update! Here is everything you need to know today.\n")

    # --- SECTION 1: AI NEWS ---
    lines.append("---")
    lines.append("## 📰 AI News (Simple Summary)\n")
    for a in unique_articles[:6]:
        lines.append(f"### {a['title']}")
        lines.append(f"*Source: {a['source_name']}*\n")
        lines.append(f"{a.get('summary', 'No summary available.')}\n")
        lines.append(f"[Read original]({a['link']})\n")

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