import re
from typing import List
from backend.app.schemas.ai_schema import AIEntityOutput

class EntityExtractionService:
    """Specialized agent sub-service for extracting academic named entities."""

    DEPARTMENTS = [
        "Computer Science & Engineering", "Information Technology",
        "Electronics & Communication", "Mechanical Engineering",
        "Civil Engineering", "Electrical Engineering", "Applied Sciences"
    ]

    ORGANIZATIONS = [
        "NAAC", "NBA", "AICTE", "UGC", "SERB", "DST", "IEEE", "ACM",
        "Google", "Amazon", "Microsoft", "TCS", "Infosys"
    ]

    COMMITTEES = [
        "Board of Studies", "Academic Council", "Library Advisory Committee",
        "Project Coordination Committee", "Anti-Ragging Committee",
        "Institution Innovation Council", "Internal Quality Assurance Cell", "IQAC"
    ]

    DOCUMENTS = [
        "Question Paper", "Mark Sheet", "Course File", "APAR", "Self-Appraisal",
        "Curriculum", "Syllabus", "Concept Note", "Medical Certificate"
    ]

    def extract_entities(self, text: str, sender: str) -> List[AIEntityOutput]:
        entities: List[AIEntityOutput] = []
        seen = set()

        def add_entity(etype: str, evalue: str):
            key = (etype, evalue.strip().lower())
            if key not in seen and len(evalue.strip()) > 1:
                seen.add(key)
                entities.append(AIEntityOutput(type=etype, value=evalue.strip()))

        # 1. Course Code regex (e.g. CS2204, CS501, IT302)
        course_codes = re.findall(r'\b([A-Z]{2,4}\s*\d{3,4})\b', text)
        for cc in course_codes:
            add_entity("COURSE_CODE", cc)

        # 2. Departments
        for dept in self.DEPARTMENTS:
            if re.search(rf'\b{re.escape(dept)}\b', text, re.IGNORECASE):
                add_entity("DEPARTMENT", dept)

        # 3. Organizations / Bodies
        for org in self.ORGANIZATIONS:
            if re.search(rf'\b{re.escape(org)}\b', text):
                add_entity("ORGANIZATION", org)

        # 4. Committees
        for comm in self.COMMITTEES:
            if re.search(rf'\b{re.escape(comm)}\b', text, re.IGNORECASE):
                add_entity("COMMITTEE", comm)

        # 5. Documents
        for doc in self.DOCUMENTS:
            if re.search(rf'\b{re.escape(doc)}\b', text, re.IGNORECASE):
                add_entity("DOCUMENT", doc)

        # 6. Officials / Roles
        official_roles = [
            ("Head of Department", r'\b(?:Head of Department|HOD)\b'),
            ("Controller of Examinations", r'\b(?:Controller of Examinations|COE)\b'),
            ("Dean (Academic Affairs)", r'\bDean\s*(?:\(Academic Affairs\))?\b'),
            ("Registrar", r'\bRegistrar\b'),
            ("Vice Chancellor", r'\bVice Chancellor\b'),
            ("Principal Investigator", r'\bPrincipal Investigator\b'),
            ("Student", r'\b(?:Roll No|Student)\b')
        ]
        for role_name, role_regex in official_roles:
            if re.search(role_regex, text, re.IGNORECASE) or re.search(role_regex, sender, re.IGNORECASE):
                add_entity("OFFICIAL_ROLE", role_name)

        return entities
