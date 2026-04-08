from app.core.llm import GeminiClient

GENERAL_SYSTEM_PROMPT = """You are the General Intelligence component of Omni-Assistant. 
Your job is to handle greetings, general conversation, and explain the system's capabilities.

System Capabilities:
1. Analyst (News & Markets): Fetches latest financial news and provides synthesized briefings.
2. Archivist (Memory & Knowledge): Remembers facts for you and retrieves them later via long-term storage.
3. Organizer (Tasks & Scheduling): Manages your to-do lists, schedules tasks, and provides productivity advice.

Keep your responses professional, helpful, and concise."""

SUMMARIZER_PROMPT = """You are the Context Synthesizer. Your job is to take a raw report from an agent and produce a CONCISE, ACTIONABLE summary for the next agent in the sequence.
- Extract key entities (stocks, names, dates).
- Extract sentiment or direct findings.
- Maximum 2 sentences."""

SYNTHESIZER_PROMPT = """You are the Omni-Agent Voice. Your job is to provide a 'Unified Summary' of multiple completed tasks.
Format: 'I have [Action 1 Summary] and based on that, I have [Action 2 Summary].'
Be professional, helpful, and direct. No introductory fluff."""


class GeneralAgent:
    def __init__(self):
        self.llm = GeminiClient()

    def handle_query(self, user_input: str, processed_query: str = None) -> str:
        effective_query = processed_query if processed_query else user_input
        return self.llm.generate_response(
            prompt=effective_query,
            system_instruction=GENERAL_SYSTEM_PROMPT
        )

    def summarize_context(self, raw_data: str) -> str:
        """
        Compresses large agent output into a concise context for the next agent.
        """
        return self.llm.generate_response(
            prompt=f"Raw Report:\n{raw_data}",
            system_instruction=SUMMARIZER_PROMPT
        )

    def synthesize_final_response(self, original_query: str, execution_log: list) -> str:
        """
        Creates a unified, cohesive response from a sequence of agent results.
        """
        log_text = "\n".join([f"Agent {item['intent']}: {item['response']}" for item in execution_log])
        return self.llm.generate_response(
            prompt=f"Original Query: {original_query}\nExecution Log:\n{log_text}",
            system_instruction=SYNTHESIZER_PROMPT
        )
