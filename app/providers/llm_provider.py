from abc import ABC, abstractmethod
from typing import Dict, Any, List
import re
from app.config import get_settings

settings = get_settings()


class LLMProvider(ABC):
    @abstractmethod
    def generate_plan(self, task: str) -> Dict[str, Any]:
        """Generates a structured execution plan from a task prompt."""
        pass

    @abstractmethod
    def draft_outreach(self, task: str, research_data: Dict[str, Any]) -> Dict[str, Any]:
        """Drafts proposed action and evidence from research findings."""
        pass


class HeuristicLLMProvider(LLMProvider):
    """
    High-fidelity heuristic/mock LLM provider.
    
    Generates intelligent, context-aware plans and personalized outreach drafts
    without requiring external API keys or incurring rate limits/costs.
    """

    def generate_plan(self, task: str) -> Dict[str, Any]:
        # Extract target company or subject from task
        company = self._extract_company_name(task)
        return {
            "target": company,
            "goal": f"Conduct strategic intelligence gathering on {company} and formulate outreach.",
            "steps": [
                {
                    "step_id": 1,
                    "name": "gather_intelligence",
                    "tool": "search_company_web",
                    "description": f"Gather corporate background, leadership, and pain points for {company}.",
                    "risk": "SAFE",
                },
                {
                    "step_id": 2,
                    "name": "synthesize_profile",
                    "tool": "extract_company_profile",
                    "description": f"Synthesize findings into strategic outreach angles.",
                    "risk": "SAFE",
                },
                {
                    "step_id": 3,
                    "name": "draft_communication",
                    "tool": "internal_drafter",
                    "description": "Formulate personalized outreach proposal and identify recipient.",
                    "risk": "SAFE",
                },
                {
                    "step_id": 4,
                    "name": "request_human_approval",
                    "tool": "approval_gate",
                    "description": "Halt workflow and present proposal with evidence for human authorization.",
                    "risk": "GATE",
                },
                {
                    "step_id": 5,
                    "name": "dispatch_external_action",
                    "tool": "send_email",
                    "description": "Execute approved outreach via communication gateway.",
                    "risk": "REQUIRES_APPROVAL",
                },
            ],
        }

    def draft_outreach(self, task: str, research_data: Dict[str, Any]) -> Dict[str, Any]:
        company = research_data.get("company", self._extract_company_name(task))
        executives = research_data.get("executives", [])
        
        if executives and len(executives) > 0:
            target_exec = executives[0]
            recipient_name = target_exec.get("name", "Leadership Team")
            recipient_email = target_exec.get("email", f"contact@{company.lower().replace(' ', '')}.com")
            role = target_exec.get("role", "Executive")
        else:
            recipient_name = "Leadership Team"
            recipient_email = f"contact@{company.lower().replace(' ', '')}.com"
            role = "Executive Leadership"

        pain_points = research_data.get("pain_points", [
            "Scaling human oversight across autonomous systems",
            "Ensuring strict compliance and auditability in automated pipelines"
        ])
        pain_point_str = pain_points[0] if pain_points else "governance for automated AI workflows"

        subject = f"Solving {pain_point_str} at {company}"
        body = (
            f"Hi {recipient_name},\n\n"
            f"I noticed your work as {role} at {company} and your focus on {pain_point_str.lower()}.\n\n"
            f"At ApprovalFlow, we have developed a stateful human-in-the-loop workflow engine that allows "
            f"autonomous AI agents to execute multi-step research and planning while strictly gating all consequential "
            f"actions (like external communications, financial transactions, and database modifications) behind explicit human checkpoints.\n\n"
            f"Would you be open to a brief 10-minute chat next Tuesday to see how this can safeguard {company}'s automation initiatives?\n\n"
            f"Best regards,\n"
            f"AI Automation Lead"
        )

        return {
            "action": {
                "tool": "send_email",
                "parameters": {
                    "recipient": recipient_email,
                    "subject": subject,
                    "body": body,
                },
            },
            "reason": (
                f"Engage {recipient_name} ({role}) at {company} with a targeted value proposition addressing "
                f"their operational pain point: {pain_point_str}."
            ),
            "evidence": {
                "company": company,
                "recipient": f"{recipient_name} <{recipient_email}>",
                "role": role,
                "recent_news": research_data.get("recent_news", "Active modernization"),
                "value_proposition": research_data.get("value_proposition", "Enterprise infrastructure"),
                "identified_pain_point": pain_point_str,
                "source": research_data.get("source", "company_research_database"),
            },
            "consequences": (
                f"An external communication email will be dispatched to {recipient_email}. "
                f"Once sent, the message is irreversible."
            ),
            "risk_level": "REQUIRES_APPROVAL",
        }

    def _extract_company_name(self, task: str) -> str:
        # Match patterns like "Research Company X and..." or "Research Stripe..."
        m = re.search(r"research\s+(?:company\s+)?([A-Za-z0-9\.\s]+?)(?:\s+and|\s+for|\s+to|\.|$)", task, re.IGNORECASE)
        if m:
            name = m.group(1).strip()
            # Clean up common trailing words
            name = re.sub(r"\b(and|prepare|draft|email)\b.*", "", name, flags=re.IGNORECASE).strip()
            if name:
                return name
        return "Acme Corp"


def get_llm_provider() -> LLMProvider:
    """Returns the configured LLM provider."""
    # We default to HeuristicLLMProvider which guarantees zero-dependency offline reliability
    return HeuristicLLMProvider()
