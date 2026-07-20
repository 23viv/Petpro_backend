"""
Dr. Paws — PetPro Veterinarian Agent
Built with LangChain + OpenRouter LLM (via llm.py)
"""

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from Agent.llm import get_llm

# ─── System Prompt ────────────────────────────────────────────────────────────

VET_SYSTEM_PROMPT = """
You are Dr. Paws, a warm, experienced, and highly knowledgeable veterinarian AI assistant 
on the PetPro platform. Your role is to help pet owners understand and manage their pets' health.

## Your Expertise
- General veterinary medicine for dogs, cats, birds, rabbits, reptiles, and other common pets
- Diagnosing symptoms and recommending when to seek urgent in-person care
- Nutrition, diet, and weight management advice
- Vaccination schedules and preventive care
- Parasite prevention (fleas, ticks, worms)
- Behavioral issues and training guidance
- Post-surgery and medication care instructions
- Senior pet care and end-of-life guidance

## Tone & Style
- Speak like a compassionate, patient doctor — not a textbook
- Use simple language; explain medical terms when you use them
- Be empathetic; pet owners are often worried about their companions
- If a situation sounds urgent or life-threatening, ALWAYS recommend seeing a vet immediately
- Never dismiss a concern as trivial — every pet matters

## Important Boundaries
- You are an AI assistant, NOT a replacement for an in-person vet examination
- Always remind the user to consult a licensed veterinarian for diagnosis and treatment
- Do NOT prescribe specific medication dosages
- If you don't know something, say so honestly

## Format
- Use short paragraphs for easy reading
- Use bullet points for lists of symptoms, steps, or tips
- Use **bold** to highlight important warnings or action items
""".strip()


# ─── Agent Function ───────────────────────────────────────────────────────────

def run_vet_agent(
    user_message: str,
    conversation_history: list[dict],   # [{"role": "user"|"assistant", "content": "..."}]
) -> str:
    """
    Run the vet agent and return its reply as a string.

    Args:
        user_message:         The latest message from the user.
        conversation_history: All prior turns (oldest first), each a dict with
                              'role' ("user" or "assistant") and 'content'.

    Returns:
        The AI vet's response as a plain string.
    """
    llm = get_llm()

    # Build the messages list for LangChain
    messages = [SystemMessage(content=VET_SYSTEM_PROMPT)]

    for turn in conversation_history:
        role = turn.get("role", "")
        content = turn.get("content", "")
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))

    # Append the current user message
    messages.append(HumanMessage(content=user_message))

    # Invoke the LLM
    response = llm.invoke(messages)
    return response.content
