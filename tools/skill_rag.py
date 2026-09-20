"""
Skill-RAG Engine using LangChain primitives.
Indexes the 15 procedural planning skills and routes relevant skills based on traveler persona.
"""
from typing import List, Dict, Any, Optional
from langchain_core.documents import Document
from data.skills_data import SKILLS_REGISTRY, export_skills_to_json
from config import settings
from models.schemas import TravelerProfile


class SkillRAG:
    """
    Skill-Augmented RAG Engine.
    Provides procedural problem-solving skills to the agentic orchestrator.
    """
    def __init__(self):
        self.skills = SKILLS_REGISTRY
        self.documents: List[Document] = []
        self._initialize_documents()
        # Export JSON files for inspection
        try:
            export_skills_to_json(settings.SKILLS_DIR)
        except Exception:
            pass

    def _initialize_documents(self):
        """Converts skill dictionaries into LangChain Document instances."""
        for skill in self.skills:
            content = f"SKILL: {skill['name']}\n"
            content += f"PURPOSE: {skill['purpose']}\n"
            content += f"WHEN TO USE: {skill['when_to_use']}\n"
            content += f"INPUTS: {', '.join(skill['inputs'])}\n"
            content += "PROCESS:\n" + "\n".join([f"{i+1}. {step}" for i, step in enumerate(skill['process'])]) + "\n"
            content += f"TOOLS: {', '.join(skill['tools'])}\n"
            content += f"OUTPUT: {skill['output']}"
            
            doc = Document(
                page_content=content,
                metadata={
                    "id": skill["id"],
                    "name": skill["name"],
                    "tools": skill["tools"],
                    "inputs": skill["inputs"]
                }
            )
            self.documents.append(doc)

    def route_skills(self, profile: TravelerProfile) -> List[Dict[str, Any]]:
        """
        Skill Router Agent Logic:
        Dynamically analyzes traveler constraints and selects the exact subset of skills needed.
        """
        selected_ids = {
            "destination_research",
            "attraction_recommendation",
            "itinerary_planning",
            "route_optimization",
            "itinerary_validation"
        }

        # Persona Routing
        if profile.age_group.lower() in ["family", "seniors", "kids"]:
            selected_ids.add("family_planning")
        elif profile.travelers_count == 1 or profile.age_group.lower() == "solo":
            selected_ids.add("solo_travel")
        elif profile.age_group.lower() in ["couple", "honeymoon"]:
            selected_ids.add("couple_planning")

        # Constraint Routing
        if profile.budget <= 15000:
            selected_ids.add("budget_optimization")

        if profile.walking_tolerance.lower() == "low":
            selected_ids.add("accessibility_planning")

        # Interest Routing
        interests_lower = [i.lower() for i in profile.interests]
        if any(food_kw in interests_lower for food_kw in ["food", "culinary", "dining", "street food"]):
            selected_ids.add("food_discovery")

        if profile.hidden_gems_preference or any(gem_kw in interests_lower for gem_kw in ["hidden gem", "offbeat", "secret"]):
            selected_ids.add("hidden_gems")

        # Always include crowd and weather adaptation for quality
        selected_ids.add("crowd_avoidance")
        selected_ids.add("weather_adaptation")
        selected_ids.add("time_optimization")

        matched_skills = [s for s in self.skills if s["id"] in selected_ids]
        return matched_skills

    def get_skill_by_id(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a specific skill definition by ID."""
        for skill in self.skills:
            if skill["id"] == skill_id:
                return skill
        return None

    def search_skills(self, query: str, top_k: int = 3) -> List[Document]:
        """Simple keyword/relevance match across skill documents."""
        q_tokens = query.lower().split()
        scored_docs = []
        for doc in self.documents:
            score = sum(1 for token in q_tokens if token in doc.page_content.lower())
            if score > 0:
                scored_docs.append((score, doc))
        
        scored_docs.sort(key=lambda x: x[0], reverse=True)
        return [doc for _, doc in scored_docs[:top_k]] or self.documents[:top_k]


# Global instance
skill_rag_engine = SkillRAG()
