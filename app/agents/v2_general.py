"""
V2 General Agent — Conversation, Summarization, Multi-Task Synthesis.

Uses GENERALIST role. Handles greetings, meta-questions, and
synthesizes multi-agent execution logs into unified responses.
"""

from app.core.llm_v2 import MultiModelClient, AgentRole


GENERAL_SYSTEM_PROMPT = """You are the General Intelligence component of Omni-Agent V2.
Handle greetings, general conversation, and explain the system's capabilities.

System Capabilities (V2):
1. Analyst: Fetches latest news/research with verifiable sources.
2. Archivist: Metadata-tagged memory system for storing and retrieving knowledge.
3. Organizer: Task management with priority, status, and due dates.
4. Coder: Code generation, debugging, and technical implementation.
5. Researcher: Deep multi-step research with reasoning and synthesis.

Keep responses professional, helpful, and concise."""

SUMMARIZER_PROMPT = """You are the Context Synthesizer. Produce a CONCISE, ACTIONABLE summary.
- Extract key entities (names, dates, numbers).
- Extract sentiment or findings.
- Maximum 2 sentences."""

SYNTHESIZER_PROMPT = """You are the Omni-Agent V2 Voice. Provide a 'Unified Summary' of the completed tasks.
If the tasks include research, news, or factual lookups, PRESERVE the detailed findings, bullet points, and markdown structure from the logs.
Do NOT compress or omit the details if the user asked for information/news.
Format your response clearly using Markdown. Be professional and direct."""


class V2GeneralAgent:
    def __init__(self):
        self.llm = MultiModelClient()

    def handle_query(self, user_input: str, processed_query: str = None) -> str:
        effective_query = processed_query if processed_query else user_input
        return self.llm.generate(
            prompt=effective_query,
            system_instruction=GENERAL_SYSTEM_PROMPT,
            role=AgentRole.GENERALIST,
            max_tokens=1024,
        )

    def summarize_context(self, raw_data: str) -> str:
        """Compress large agent output into concise context for next agent."""
        return self.llm.generate(
            prompt=f"Raw Report:\n{raw_data}",
            system_instruction=SUMMARIZER_PROMPT,
            role=AgentRole.GENERALIST,
            max_tokens=256,
        )

    def synthesize_final_response(self, original_query: str, execution_log: list) -> str:
        """Create unified response from multi-agent execution results."""
        log_text = "\n".join([
            f"Agent {item['intent']}: {item['response']}"
            for item in execution_log
        ])
        return self.llm.generate(
            prompt=f"Original Query: {original_query}\nExecution Log:\n{log_text}",
            system_instruction=SYNTHESIZER_PROMPT,
            role=AgentRole.GENERALIST,
            max_tokens=1024,
        )
