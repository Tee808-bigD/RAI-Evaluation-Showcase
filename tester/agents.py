"""
agents.py — The 3-agent research swarm
Planner → Researcher → Synthesizer
"""

import os
import json
import httpx
from typing import AsyncGenerator
from dotenv import load_dotenv

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient

load_dotenv()


# ── Azure OpenAI client (shared) ──────────────────────────────────────────────
def get_model_client() -> AzureOpenAIChatCompletionClient:
    return AzureOpenAIChatCompletionClient(
        azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT"],
        model="gpt-4o",
        api_version=os.environ["AZURE_OPENAI_API_VERSION"],
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
    )


# ── Bing web search tool ──────────────────────────────────────────────────────
async def bing_search(query: str, count: int = 5) -> str:
    """Search the web via Bing and return a JSON string of results."""
    url = "https://api.bing.microsoft.com/v7.0/search"
    headers = {"Ocp-Apim-Subscription-Key": os.environ["BING_SEARCH_API_KEY"]}
    params = {"q": query, "count": count, "responseFilter": "Webpages"}

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

    pages = data.get("webPages", {}).get("value", [])
    results = [
        {"title": p["name"], "url": p["url"], "snippet": p["snippet"]}
        for p in pages
    ]
    return json.dumps(results, indent=2)


# ── Agent definitions ─────────────────────────────────────────────────────────
def make_planner(model_client: AzureOpenAIChatCompletionClient) -> AssistantAgent:
    return AssistantAgent(
        name="Planner",
        model_client=model_client,
        system_message="""You are the Planner agent in a research swarm.

Your job: take the user's research question and break it into exactly 3 focused 
sub-questions that together will produce a comprehensive answer.

Output ONLY valid JSON in this format — nothing else:
{
  "original_question": "<the user's question>",
  "subtasks": [
    {"id": 1, "query": "<focused sub-question 1>"},
    {"id": 2, "query": "<focused sub-question 2>"},
    {"id": 3, "query": "<focused sub-question 3>"}
  ]
}

Make the sub-questions specific, distinct, and searchable.""",
    )


def make_researcher(model_client: AzureOpenAIChatCompletionClient) -> AssistantAgent:
    return AssistantAgent(
        name="Researcher",
        model_client=model_client,
        tools=[bing_search],
        system_message="""You are the Researcher agent in a research swarm.

You receive a single focused query. You MUST:
1. Call the bing_search tool with that query
2. Read the results carefully
3. Extract the most relevant facts, figures, and insights

Output ONLY valid JSON in this format:
{
  "query": "<the query you researched>",
  "findings": [
    {"point": "<key finding>", "source": "<url>"},
    ...
  ],
  "summary": "<2-3 sentence summary of what you found>"
}""",
    )


def make_synthesizer(model_client: AzureOpenAIChatCompletionClient) -> AssistantAgent:
    return AssistantAgent(
        name="Synthesizer",
        model_client=model_client,
        system_message="""You are the Synthesizer agent in a research swarm.

You receive the original question and findings from 3 research tasks.
Produce a comprehensive, well-structured answer.

Output ONLY valid JSON in this format:
{
  "question": "<original question>",
  "answer": "<full markdown answer with headers and bullet points>",
  "key_takeaways": ["<takeaway 1>", "<takeaway 2>", "<takeaway 3>"],
  "sources": ["<url1>", "<url2>", "..."]
}""",
    )


# ── Swarm orchestration ───────────────────────────────────────────────────────
async def run_swarm(question: str) -> AsyncGenerator[dict, None]:
    """
    Orchestrate the 3-agent pipeline and yield status events.
    Each event is a dict that gets sent to the frontend via WebSocket/SSE.
    """
    model_client = get_model_client()

    planner = make_planner(model_client)
    researcher = make_researcher(model_client)
    synthesizer = make_synthesizer(model_client)

    # ── Step 1: Planner ───────────────────────────────────────────────────────
    yield {"agent": "Planner", "status": "running", "message": "Breaking down your question..."}

    planner_result = await planner.run(
        task=f"Research question: {question}"
    )
    planner_text = planner_result.messages[-1].content

    try:
        plan = json.loads(planner_text)
    except json.JSONDecodeError:
        # Try to extract JSON from markdown fences if model wraps it
        import re
        match = re.search(r"\{.*\}", planner_text, re.DOTALL)
        plan = json.loads(match.group()) if match else {"subtasks": []}

    yield {
        "agent": "Planner",
        "status": "done",
        "message": "Plan created",
        "data": plan,
    }

    # ── Step 2: Researcher (3 sub-tasks) ──────────────────────────────────────
    all_findings = []

    for subtask in plan.get("subtasks", []):
        query = subtask.get("query", "")
        yield {
            "agent": "Researcher",
            "status": "running",
            "message": f"Researching: {query}",
            "subtask_id": subtask.get("id"),
        }

        research_result = await researcher.run(
            task=f"Research this query: {query}"
        )
        research_text = research_result.messages[-1].content

        try:
            findings = json.loads(research_text)
        except json.JSONDecodeError:
            import re
            match = re.search(r"\{.*\}", research_text, re.DOTALL)
            findings = json.loads(match.group()) if match else {"query": query, "findings": [], "summary": ""}

        all_findings.append(findings)

        yield {
            "agent": "Researcher",
            "status": "done",
            "message": f"Found {len(findings.get('findings', []))} insights",
            "subtask_id": subtask.get("id"),
            "data": findings,
        }

    # ── Step 3: Synthesizer ───────────────────────────────────────────────────
    yield {"agent": "Synthesizer", "status": "running", "message": "Synthesizing all findings..."}

    synth_input = json.dumps({
        "original_question": question,
        "research_results": all_findings,
    }, indent=2)

    synth_result = await synthesizer.run(task=synth_input)
    synth_text = synth_result.messages[-1].content

    try:
        synthesis = json.loads(synth_text)
    except json.JSONDecodeError:
        import re
        match = re.search(r"\{.*\}", synth_text, re.DOTALL)
        synthesis = json.loads(match.group()) if match else {"answer": synth_text, "key_takeaways": [], "sources": []}

    yield {
        "agent": "Synthesizer",
        "status": "done",
        "message": "Answer ready",
        "data": synthesis,
    }

    yield {"agent": "system", "status": "complete", "message": "Research complete"}
