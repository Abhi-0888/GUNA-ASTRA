"""
Agent 4: Research Agent
Performs research using DuckDuckGo (no API key needed) and summarizes findings.
"""

import requests

from agents.base_agent import BaseAgent

SYSTEM_PROMPT = """You are the Research Agent for GUNA-ASTRA.

Your job:
1. Analyze the research topic given to you.
2. Summarize the search results into clear, structured information.
3. Always provide key facts, main points, and a concise summary.
4. Format your response with sections: KEY FACTS, SUMMARY, SOURCES (if available).

Be factual, neutral, and thorough.
"""

DDGO_URL = "https://api.duckduckgo.com/"


class ResearchAgent(BaseAgent):
    def __init__(self):
        super().__init__("ResearchAgent", SYSTEM_PROMPT)

    def run(self, task: dict) -> dict:
        description = task.get("description", "")
        self.logger.info(f"Researching: {description}")

        # 1. Try to get search results
        search_results = self._search(description)

        # 2. Ask LLM to synthesize
        if search_results:
            prompt = f"""Research topic: {description}

Here are some search snippets:
{search_results}

Please provide a comprehensive research summary with key facts and conclusions."""
        else:
            prompt = f"""Research topic: {description}

No live search results available. Please provide the best knowledge-based summary you can on this topic.
Include key facts, explanations, and relevant details."""

        response = self.think(prompt)
        self.logger.info("Research complete.")
        return self.report("success", response, task)

    def _search(self, query: str) -> str:
        """Search for info. Tries duckduckgo_search library first, then Instant Answer API."""
        # v2: Try duckduckgo_search library (more comprehensive results)
        try:
            from duckduckgo_search import DDGS

            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=5))
            if results:
                return "\n".join(
                    f"• {r['title']}: {r['body'][:200]}" for r in results[:3]
                )
        except Exception:
            pass

        # Fallback: DuckDuckGo Instant Answer API
        try:
            params = {"q": query, "format": "json", "no_redirect": "1", "no_html": "1"}
            r = requests.get(DDGO_URL, params=params, timeout=10)
            data = r.json()

            results = []
            if data.get("Abstract"):
                results.append(f"Summary: {data['Abstract']}")
            for topic in data.get("RelatedTopics", [])[:5]:
                if isinstance(topic, dict) and topic.get("Text"):
                    results.append(f"- {topic['Text']}")

            return "\n".join(results) if results else ""
        except Exception as e:
            self.logger.warning(f"DuckDuckGo search failed: {e}")
            return ""

    def _search_wikipedia(self, topic: str) -> str:
        """Search Wikipedia REST API for topic summaries."""
        try:
            from urllib.parse import quote

            url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote(topic)}"
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                data = r.json()
                extract = data.get("extract", "")
                if extract:
                    return f"Wikipedia: {extract[:500]}"
            return ""
        except Exception as e:
            self.logger.warning(f"Wikipedia search failed: {e}")
            return ""

    def _search_weather(self, topic: str) -> str:
        """Check if topic is weather-related and fetch from wttr.in."""
        weather_words = ["weather", "temperature", "forecast", "climate"]
        if not any(w in topic.lower() for w in weather_words):
            return ""
        try:
            import re as _re

            city = _re.sub(
                r"(weather|temperature|forecast|climate|in|the|what|is|of)\s*",
                "",
                topic,
                flags=_re.IGNORECASE,
            ).strip()
            from urllib.parse import quote_plus

            url = f"https://wttr.in/{quote_plus(city)}?format=j1"
            r = requests.get(url, timeout=10, headers={"User-Agent": "curl/7.0"})
            if r.status_code == 200:
                data = r.json()
                current = data.get("current_condition", [{}])[0]
                return (
                    f"Weather: {current.get('weatherDesc', [{}])[0].get('value', '?')}, "
                    f"Temp: {current.get('temp_C', '?')}°C, "
                    f"Humidity: {current.get('humidity', '?')}%, "
                    f"Wind: {current.get('windspeedKmph', '?')} km/h"
                )
            return ""
        except Exception:
            return ""

    def research_and_summarize(self, topic: str, depth: str = "normal") -> str:
        """
        Research with configurable depth.
        depth: "quick" (1 source), "normal" (2-3 sources), "deep" (all sources)
        """
        self.logger.info(f"Researching '{topic}' at depth: {depth}")
        sources = []

        # Always try DuckDuckGo
        ddg = self._search(topic)
        if ddg:
            sources.append(ddg)

        if depth in ("normal", "deep"):
            wiki = self._search_wikipedia(topic)
            if wiki:
                sources.append(wiki)
            weather = self._search_weather(topic)
            if weather:
                sources.append(weather)

        combined = "\n\n".join(sources) if sources else ""

        if combined:
            prompt = f"""Research topic: {topic}

Here are search results from multiple sources:
{combined}

Provide a {'brief' if depth == 'quick' else 'comprehensive'} research summary."""
        else:
            prompt = f"""Research topic: {topic}

No live search results available. Provide the best knowledge-based summary."""

        return self.think(prompt)
