import re
from typing import Optional, List, Dict, Any

class SummarizationService:
    """Specialized agent sub-service for concise, grounded academic email summarization.
    
    Generates structured faculty intelligence answering:
    - What is this email about?
    - What is important and what does the recipient need to know?
    - What action is expected?
    - Is there an imminent deadline or consequence?
    
    Strictly grounded in subject and body. Never hallucinates dates, names, or actions.
    """

    def clean_body_text(self, body: str) -> List[str]:
        """Strip boilerplate headers, greetings, and signatures to isolate core content sentences."""
        lines = body.split("\n")
        cleaned_lines = []
        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue
            # Filter greetings
            if re.match(r'^(?:dear|hello|hi|respected|to all|greetings)\b', line_str, re.IGNORECASE):
                continue
            # Filter signoffs and signatures
            if re.match(r'^(?:regards|warm regards|thanks|thank you|sincerely|yours faithfully|best regards|cheers)\b', line_str, re.IGNORECASE):
                break
            if re.match(r'^(?:office of|department of|dean|hod|principal|coe)\b', line_str, re.IGNORECASE) and len(line_str.split()) < 6:
                continue
            cleaned_lines.append(line_str)

        full_clean = " ".join(cleaned_lines)
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', full_clean) if len(s.strip()) > 8]
        return sentences

    def summarize(
        self,
        subject: str,
        body: str,
        category: str = "General",
        deadline: Optional[str] = None,
        actions: Optional[List[Dict[str, Any]]] = None,
        meeting: Optional[Dict[str, Any]] = None
    ) -> str:
        """Synthesize a structured faculty-oriented summary."""
        sentences = self.clean_body_text(body)
        
        # 1. Synthesize 2-4 concise summary sentences
        summary_sentences = []

        # Find consequence or importance sentence if present
        consequence_sent = None
        for s in sentences:
            if re.search(r'\b(?:failure to|affect|penalty|consequence|critical|mandatory|important|strict|note that)\b', s, re.IGNORECASE):
                consequence_sent = s
                break

        # Action / Main Subject statement
        if actions and len(actions) > 0:
            act_desc = actions[0].get("description", str(actions[0]))
            # Format into clean imperative or statement
            if act_desc.endswith("."):
                act_desc = act_desc[:-1]
            main_statement = f"Faculty members are requested to {act_desc.lower() if not act_desc.startswith('Submit') and not act_desc.startswith('Complete') else act_desc}."
            if not main_statement.endswith("."):
                main_statement += "."
            summary_sentences.append(main_statement)
        elif sentences:
            summary_sentences.append(sentences[0])
        else:
            summary_sentences.append(f"Correspondence regarding {subject}.")

        # Meeting statement if present
        if meeting and meeting.get("date"):
            m_date = meeting.get("date")
            m_time = meeting.get("time")
            m_loc = meeting.get("location")
            m_title = meeting.get("title") or "Meeting"
            m_stmt = f"A {m_title.lower()} is scheduled on {m_date}"
            if m_time:
                m_stmt += f" at {m_time}"
            if m_loc:
                m_stmt += f" in {m_loc}"
            m_stmt += "."
            summary_sentences.append(m_stmt)
        elif deadline and not any(deadline in s for s in summary_sentences):
            summary_sentences.append(f"The required deadline is {deadline}.")

        # Consequence statement if present and not already included
        if consequence_sent and consequence_sent not in summary_sentences and len(summary_sentences) < 4:
            summary_sentences.append(consequence_sent)
        elif len(sentences) > 1 and len(summary_sentences) < 3:
            second_informative = next((s for s in sentences[1:] if s not in summary_sentences and len(s) > 20), None)
            if second_informative:
                summary_sentences.append(second_informative)

        concise_summary = " ".join(summary_sentences[:4]).strip()

        # 2. Format Structured Output
        output_parts = [f"Summary:\n{concise_summary}"]

        # Action section
        if actions and len(actions) > 0:
            first_action = actions[0].get("description", str(actions[0]))
            if first_action.endswith("."):
                first_action = first_action[:-1]
            output_parts.append(f"Action:\n{first_action}.")
        else:
            action_sent = next((s for s in sentences if re.search(r'\b(?:please|kindly|must|submit|attend|register|send|verify|upload)\b', s, re.IGNORECASE)), None)
            if action_sent:
                output_parts.append(f"Action:\n{action_sent}")
            else:
                output_parts.append("Action:\nNo immediate faculty action required.")

        # Deadline section
        if deadline:
            output_parts.append(f"Deadline:\n{deadline}")
        else:
            from backend.app.utils.date_parser import extract_actionable_deadline
            found_deadline, raw_dl, _ = extract_actionable_deadline(body)
            if found_deadline:
                output_parts.append(f"Deadline:\n{raw_dl or found_deadline}")
            else:
                output_parts.append("Deadline:\nNone specified.")

        return "\n\n".join(output_parts)

