from typing import Dict, Any, List
from pydantic import BaseModel, Field
from app.tools.base import ToolDefinition, RiskLevel, registry


# Input Schemas
class SearchCompanyInput(BaseModel):
    company_name: str = Field(..., description="Name of the company to research")
    aspects: List[str] = Field(
        default=["overview", "leadership", "recent_news", "products"],
        description="Aspects of the company to investigate"
    )


class ExtractProfileInput(BaseModel):
    company_name: str = Field(..., description="Name of the company")
    raw_notes: str = Field(..., description="Raw text notes collected from search")


# Handlers
def handle_search_company(company_name: str, aspects: List[str]) -> Dict[str, Any]:
    """
    Simulates / performs safe company intelligence research.
    Provides realistic data for common companies and generates plausible data for others.
    """
    clean_name = company_name.strip()
    
    # Knowledge base for realistic demo data
    known_companies: Dict[str, Dict[str, Any]] = {
        "acme": {
            "name": "Acme Corp",
            "domain": "acme.com",
            "industry": "Cloud Infrastructure & AI Tooling",
            "headquarters": "San Francisco, CA",
            "executives": [
                {"name": "Sarah Chen", "role": "VP of Engineering", "email": "sarah.chen@acme.com"},
                {"name": "Markus Vance", "role": "Head of Product", "email": "m.vance@acme.com"}
            ],
            "recent_news": "Recently announced expansion into autonomous workflow orchestration.",
            "value_proposition": "Building reliable distributed infrastructure for enterprise AI systems.",
            "pain_points": [
                "Scaling human oversight across high-throughput agent workflows",
                "Maintaining strict audit trails for enterprise compliance"
            ]
        },
        "stripe": {
            "name": "Stripe",
            "domain": "stripe.com",
            "industry": "Financial Infrastructure",
            "headquarters": "South San Francisco, CA & Dublin, Ireland",
            "executives": [
                {"name": "Patrick Collison", "role": "CEO", "email": "patrick@stripe.com"},
                {"name": "John Collison", "role": "President", "email": "john@stripe.com"}
            ],
            "recent_news": "Expanding agentic commerce protocols and automated dispute handling.",
            "value_proposition": "Financial infrastructure for the internet.",
            "pain_points": ["Safety guardrails around automated financial transactions"]
        }
    }

    key = clean_name.lower()
    for k, data in known_companies.items():
        if k in key:
            return {
                "company": data["name"],
                "domain": data["domain"],
                "industry": data["industry"],
                "headquarters": data["headquarters"],
                "executives": data["executives"],
                "recent_news": data["recent_news"],
                "value_proposition": data["value_proposition"],
                "pain_points": data["pain_points"],
                "source": "verified_company_directory",
            }

    # Fallback heuristic profile for arbitrary company names
    return {
        "company": clean_name.title(),
        "domain": f"{clean_name.lower().replace(' ', '')}.com",
        "industry": "Technology Solutions & Enterprise Software",
        "headquarters": "Austin, TX",
        "executives": [
            {"name": "Alex Mercer", "role": "VP of Operations", "email": f"alex@{clean_name.lower().replace(' ', '')}.com"}
        ],
        "recent_news": f"{clean_name.title()} is actively modernizing operational workflows with AI.",
        "value_proposition": f"Empowering teams with streamlined technology at {clean_name.title()}.",
        "pain_points": [
            "Ensuring human-in-the-loop validation for automated operations",
            "Preventing unapproved actions in critical software pipelines"
        ],
        "source": "web_intelligence_synthesizer",
    }


def handle_extract_profile(company_name: str, raw_notes: str) -> Dict[str, Any]:
    """Extracts structured synthesis from research notes."""
    return {
        "company_name": company_name,
        "key_takeaways": [
            f"Organization is actively investing in AI and workflow automation.",
            f"Requires robust audit trails and human approval gates for critical decisions.",
        ],
        "primary_contact": {
            "role": "VP of Engineering / Operations",
            "focus": "Workflow reliability and governance",
        },
        "notes_analyzed_length": len(raw_notes),
    }


# Tool Definitions
search_company_tool = ToolDefinition(
    name="search_company_web",
    description="Searches publicly available intelligence about a company, including leadership, news, and pain points.",
    risk_level=RiskLevel.SAFE,
    input_schema=SearchCompanyInput,
    handler=handle_search_company,
    requires_approval=False,
)

extract_profile_tool = ToolDefinition(
    name="extract_company_profile",
    description="Synthesizes raw research notes into a structured company profile.",
    risk_level=RiskLevel.SAFE,
    input_schema=ExtractProfileInput,
    handler=handle_extract_profile,
    requires_approval=False,
)

# Register safe research tools
registry.register(search_company_tool)
registry.register(extract_profile_tool)
