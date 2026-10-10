"""Realistic Synthetic Faculty Email Dataset & Seeding Utility.

All emails represent fictional academic scenarios. No private real email data is used.
"""

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from backend.app.database.session import engine, init_db, reset_db, SessionLocal
from backend.app.models import Email, AIAnalysis, ActionItem, Meeting, Evidence, Entity

# Reference epoch for realistic relative time resolutions
BASE_DATE = datetime(2026, 9, 6, 9, 30, 0)

SAMPLE_EMAILS = [
    # 1. HOD Office - Flagship Demo Email (from Specification Section 41)
    {
        "sender": "hod.cse@university.edu",
        "recipient": "faculty-cse@university.edu",
        "subject": "Internal Assessment Marks Submission",
        "body": (
            "Dear Faculty,\n\n"
            "All members are requested to submit the internal assessment marks before September 10. "
            "A review meeting will be conducted on September 8 at 10 AM in the Seminar Hall. "
            "Please bring the updated mark sheet and student attendance logs.\n\n"
            "Regards,\n"
            "Office of the Head of Department\n"
            "Computer Science & Engineering"
        ),
        "received_at": BASE_DATE - timedelta(hours=3),
        "is_read": False,
        "analysis": {
            "summary": "Faculty members must submit internal assessment marks before September 10 and attend a departmental review meeting on September 8 at 10 AM.",
            "category": "Academic",
            "priority": "HIGH",
            "priority_reason": "Mandatory academic submission with an approaching deadline and scheduled review meeting.",
            "evidences": [
                {
                    "field_name": "deadline",
                    "extracted_value": "2026-09-10",
                    "source_text": "All members are requested to submit the internal assessment marks before September 10.",
                    "confidence": 0.98
                },
                {
                    "field_name": "meeting",
                    "extracted_value": "2026-09-08 10:00 @ Seminar Hall",
                    "source_text": "A review meeting will be conducted on September 8 at 10 AM in the Seminar Hall.",
                    "confidence": 0.99
                },
                {
                    "field_name": "action_item",
                    "extracted_value": "Submit internal assessment marks",
                    "source_text": "All members are requested to submit the internal assessment marks before September 10.",
                    "confidence": 0.95
                },
                {
                    "field_name": "action_item",
                    "extracted_value": "Bring updated mark sheet",
                    "source_text": "Please bring the updated mark sheet and student attendance logs.",
                    "confidence": 0.92
                }
            ]
        },
        "action_items": [
            {
                "description": "Submit internal assessment marks to HOD office",
                "due_date": "2026-09-10",
                "priority": "HIGH",
                "completed": False,
                "relationship_type": "DUE_ON"
            },
            {
                "description": "Bring updated mark sheet and student attendance logs",
                "due_date": "2026-09-08",
                "priority": "MEDIUM",
                "completed": False,
                "relationship_type": "PREPARE_BEFORE"
            }
        ],
        "meetings": [
            {
                "title": "Internal Assessment Department Review Meeting",
                "meeting_date": "2026-09-08",
                "meeting_time": "10:00",
                "location": "Seminar Hall",
                "preparation": "Bring updated mark sheet and student attendance logs"
            }
        ],
        "entities": [
            {"entity_type": "DEPARTMENT", "entity_value": "Computer Science & Engineering"},
            {"entity_type": "ROLE", "entity_value": "Head of Department"},
            {"entity_type": "VENUE", "entity_value": "Seminar Hall"}
        ]
    },

    # 2. Controller of Examinations - High Priority Examination Deadline
    {
        "sender": "coe@university.edu",
        "recipient": "faculty-all@university.edu",
        "subject": "Confidential: Setting of Question Papers for End Semester Examinations",
        "body": (
            "Dear Professors,\n\n"
            "You are appointed as the Chief Question Paper Setter for your respective mapped courses. "
            "It is strictly mandatory to submit two distinct sets of manuscript question papers along with "
            "detailed answer schemes in sealed envelopes to the COE Confidential Section before September 15. "
            "Strict confidentiality must be maintained in accordance with institutional examination bylaws.\n\n"
            "Dr. M. S. Rao\n"
            "Controller of Examinations"
        ),
        "received_at": BASE_DATE - timedelta(hours=6),
        "is_read": False,
        "analysis": {
            "summary": "Mandatory submission of two sets of end-semester manuscript question papers with answer schemes to the COE office before September 15 under strict confidentiality.",
            "category": "Examination",
            "priority": "HIGH",
            "priority_reason": "High-authority statutory directive from Controller of Examinations with strict confidentiality and mandatory submission deadline.",
            "evidences": [
                {
                    "field_name": "deadline",
                    "extracted_value": "2026-09-15",
                    "source_text": "submit two distinct sets of manuscript question papers along with detailed answer schemes in sealed envelopes to the COE Confidential Section before September 15.",
                    "confidence": 0.99
                }
            ]
        },
        "action_items": [
            {
                "description": "Prepare two distinct sets of manuscript question papers with answer keys",
                "due_date": "2026-09-15",
                "priority": "HIGH",
                "completed": False,
                "relationship_type": "DUE_ON"
            },
            {
                "description": "Submit sealed envelopes to COE Confidential Section",
                "due_date": "2026-09-15",
                "priority": "HIGH",
                "completed": False,
                "relationship_type": "DUE_ON"
            }
        ],
        "meetings": [],
        "entities": [
            {"entity_type": "OFFICIAL", "entity_value": "Dr. M. S. Rao"},
            {"entity_type": "OFFICE", "entity_value": "COE Confidential Section"}
        ]
    },

    # 3. Dean of Academic Affairs - NAAC Accreditation Peer Visit
    {
        "sender": "dean.academics@university.edu",
        "recipient": "hods-criteria-heads@university.edu",
        "subject": "Urgent: NAAC Peer Team Visit Preparation & File Audit",
        "body": (
            "Respected Colleagues,\n\n"
            "In view of the upcoming NAAC Peer Team visit, a mandatory file audit and criterion progress review "
            "will be held on September 9 at 2:30 PM in the Main Board Room. All Criteria Heads and HODs must attend. "
            "Please ensure course files, mentor-mentee records, and CO-PO attainment matrices are updated.\n\n"
            "Prof. K. Narayanan\n"
            "Dean (Academic Affairs)"
        ),
        "received_at": BASE_DATE - timedelta(hours=14),
        "is_read": True,
        "analysis": {
            "summary": "Mandatory NAAC peer team preparation meeting on September 9 at 2:30 PM in the Main Board Room for Criteria Heads and HODs.",
            "category": "Administrative",
            "priority": "HIGH",
            "priority_reason": "Institutional accreditation review chaired by Dean Academics with immediate audit requirements.",
            "evidences": [
                {
                    "field_name": "meeting",
                    "extracted_value": "2026-09-09 14:30 @ Main Board Room",
                    "source_text": "mandatory file audit and criterion progress review will be held on September 9 at 2:30 PM in the Main Board Room.",
                    "confidence": 0.98
                }
            ]
        },
        "action_items": [
            {
                "description": "Update course files, mentor-mentee records, and CO-PO attainment matrices",
                "due_date": "2026-09-09",
                "priority": "HIGH",
                "completed": True,
                "relationship_type": "PREPARE_BEFORE"
            }
        ],
        "meetings": [
            {
                "title": "NAAC Peer Team Visit Preparation & File Audit",
                "meeting_date": "2026-09-09",
                "meeting_time": "14:30",
                "location": "Main Board Room",
                "preparation": "Updated course files, mentor-mentee records, and CO-PO attainment matrices"
            }
        ],
        "entities": [
            {"entity_type": "ACCREDITATION_BODY", "entity_value": "NAAC"},
            {"entity_type": "OFFICIAL", "entity_value": "Prof. K. Narayanan"},
            {"entity_type": "VENUE", "entity_value": "Main Board Room"}
        ]
    },

    # 4. Student Medical Leave & Re-test Appeal
    {
        "sender": "rahul.sharma.cs22@student.university.edu",
        "recipient": "faculty-incharge@university.edu",
        "subject": "Medical Leave Certificate & Request for Quiz 1 Re-test - Roll No CS2204",
        "body": (
            "Respected Professor,\n\n"
            "I was hospitalized due to viral fever from September 1 to September 4 and could not appear for the Quiz 1 "
            "in Advanced Algorithms. I have attached the medical fitness certificate approved by the University Health Center. "
            "Could you please allow me to take the make-up test before September 12 as per academic regulations?\n\n"
            "Thank you,\n"
            "Rahul Sharma (Roll No: CS2204)"
        ),
        "received_at": BASE_DATE - timedelta(hours=18),
        "is_read": False,
        "analysis": {
            "summary": "Student Rahul Sharma (CS2204) requests an approved make-up re-test for Quiz 1 before September 12 following medical hospitalization.",
            "category": "Student",
            "priority": "MEDIUM",
            "priority_reason": "Student academic appeal with documented medical certificate requiring faculty discretionary scheduling.",
            "evidences": [
                {
                    "field_name": "deadline",
                    "extracted_value": "2026-09-12",
                    "source_text": "Could you please allow me to take the make-up test before September 12 as per academic regulations?",
                    "confidence": 0.93
                }
            ]
        },
        "action_items": [
            {
                "description": "Verify medical certificate with Health Center and schedule Quiz 1 re-test for Rahul Sharma",
                "due_date": "2026-09-12",
                "priority": "MEDIUM",
                "completed": False,
                "relationship_type": "DUE_ON"
            }
        ],
        "meetings": [],
        "entities": [
            {"entity_type": "STUDENT", "entity_value": "Rahul Sharma"},
            {"entity_type": "ROLL_NO", "entity_value": "CS2204"},
            {"entity_type": "COURSE", "entity_value": "Advanced Algorithms"}
        ]
    },

    # 5. Board of Studies (BOS) Curriculum Meeting
    {
        "sender": "bos.chairperson@university.edu",
        "recipient": "faculty-cse@university.edu",
        "subject": "Board of Studies (BOS) Annual Curriculum Revision Meeting - Sept 14",
        "body": (
            "Dear Faculty Members,\n\n"
            "The 18th Board of Studies (BOS) meeting for curriculum modernization is scheduled for September 14 at 11:00 AM "
            "in Conference Hall B. External industry experts from Microsoft and Google will participate. "
            "Please review the attached draft syllabus for Cloud Computing and Generative AI electives prior to the meeting.\n\n"
            "Dr. Ananya Sen\n"
            "Chairperson, Board of Studies"
        ),
        "received_at": BASE_DATE - timedelta(days=1, hours=2),
        "is_read": True,
        "analysis": {
            "summary": "18th Board of Studies meeting on September 14 at 11:00 AM in Conference Hall B to review Cloud Computing and Generative AI curriculum drafts.",
            "category": "Meeting",
            "priority": "HIGH",
            "priority_reason": "Formal statutory academic board meeting with external industry experts requiring prior syllabus review.",
            "evidences": [
                {
                    "field_name": "meeting",
                    "extracted_value": "2026-09-14 11:00 @ Conference Hall B",
                    "source_text": "The 18th Board of Studies (BOS) meeting for curriculum modernization is scheduled for September 14 at 11:00 AM in Conference Hall B.",
                    "confidence": 0.98
                }
            ]
        },
        "action_items": [
            {
                "description": "Review draft syllabus for Cloud Computing and Generative AI electives",
                "due_date": "2026-09-14",
                "priority": "HIGH",
                "completed": False,
                "relationship_type": "PREPARE_BEFORE"
            }
        ],
        "meetings": [
            {
                "title": "18th Board of Studies (BOS) Curriculum Meeting",
                "meeting_date": "2026-09-14",
                "meeting_time": "11:00",
                "location": "Conference Hall B",
                "preparation": "Review attached draft syllabus for Cloud Computing and Generative AI electives"
            }
        ],
        "entities": [
            {"entity_type": "OFFICIAL", "entity_value": "Dr. Ananya Sen"},
            {"entity_type": "COMMITTEE", "entity_value": "Board of Studies"},
            {"entity_type": "VENUE", "entity_value": "Conference Hall B"}
        ]
    },

    # 6. R&D Cell - SERB Research Grant Proposal
    {
        "sender": "rnd.director@university.edu",
        "recipient": "faculty-researchers@university.edu",
        "subject": "Call for Project Proposals: SERB Core Research Grant (CRG) 2026",
        "body": (
            "Dear Faculty Colleagues,\n\n"
            "The Science and Engineering Research Board (SERB) has announced the Core Research Grant call for proposals. "
            "All eligible faculty members intending to apply as Principal Investigators must submit their project concept notes "
            "and preliminary budget estimates to the Dean R&D Office before September 25 for university endorsement.\n\n"
            "Directorate of Sponsored Research"
        ),
        "received_at": BASE_DATE - timedelta(days=1, hours=8),
        "is_read": False,
        "analysis": {
            "summary": "Eligible faculty must submit SERB Core Research Grant concept notes and budget estimates to R&D Office before September 25 for institutional endorsement.",
            "category": "Research",
            "priority": "HIGH",
            "priority_reason": "High-value external sponsored research funding opportunity with fixed national agency deadline.",
            "evidences": [
                {
                    "field_name": "deadline",
                    "extracted_value": "2026-09-25",
                    "source_text": "submit their project concept notes and preliminary budget estimates to the Dean R&D Office before September 25",
                    "confidence": 0.97
                }
            ]
        },
        "action_items": [
            {
                "description": "Submit SERB-CRG concept note and budget estimate to Dean R&D",
                "due_date": "2026-09-25",
                "priority": "HIGH",
                "completed": False,
                "relationship_type": "DUE_ON"
            }
        ],
        "meetings": [],
        "entities": [
            {"entity_type": "AGENCY", "entity_value": "SERB"},
            {"entity_type": "GRANT", "entity_value": "Core Research Grant"}
        ]
    },

    # 7. Training & Placement Cell - Campus Interview Duty
    {
        "sender": "placement.head@university.edu",
        "recipient": "faculty-mentors@university.edu",
        "subject": "Campus Placement Drive: Technical Interview Coordinator Allocation",
        "body": (
            "Dear Professors,\n\n"
            "Google and Amazon campus hiring commences next week. You have been designated as Technical Interview Coordinators. "
            "A briefing session is scheduled for September 11 at 9:00 AM in the Placement Auditorium. "
            "Kindly verify eligible shortlisted student resumes and laboratory terminal allocations beforehand.\n\n"
            "Training & Placement Directorate"
        ),
        "received_at": BASE_DATE - timedelta(days=2),
        "is_read": True,
        "analysis": {
            "summary": "Faculty assigned as Technical Interview Coordinators for campus placement drive; mandatory briefing on September 11 at 9:00 AM in Placement Auditorium.",
            "category": "Placement",
            "priority": "HIGH",
            "priority_reason": "Critical corporate campus recruitment coordination involving student career outcomes and direct employer engagement.",
            "evidences": [
                {
                    "field_name": "meeting",
                    "extracted_value": "2026-09-11 09:00 @ Placement Auditorium",
                    "source_text": "A briefing session is scheduled for September 11 at 9:00 AM in the Placement Auditorium.",
                    "confidence": 0.98
                }
            ]
        },
        "action_items": [
            {
                "description": "Verify shortlisted student resumes and lab terminal allocations",
                "due_date": "2026-09-11",
                "priority": "HIGH",
                "completed": False,
                "relationship_type": "PREPARE_BEFORE"
            }
        ],
        "meetings": [
            {
                "title": "Placement Drive Technical Coordinator Briefing",
                "meeting_date": "2026-09-11",
                "meeting_time": "09:00",
                "location": "Placement Auditorium",
                "preparation": "Review shortlisted student resumes and laboratory allocation charts"
            }
        ],
        "entities": [
            {"entity_type": "COMPANIES", "entity_value": "Google, Amazon"},
            {"entity_type": "VENUE", "entity_value": "Placement Auditorium"}
        ]
    },

    # 8. Registrar Office - Faculty Self-Appraisal
    {
        "sender": "registrar@university.edu",
        "recipient": "faculty-all@university.edu",
        "subject": "Annual Performance Appraisal Reports (APAR) Submission 2025-26",
        "body": (
            "Circular No. REG/2026/142\n\n"
            "All teaching staff are notified that the Annual Performance Appraisal Reports (APAR) for the academic year "
            "2025-26 must be submitted through the faculty portal before September 20. Completed dossiers with supporting "
            "publication reprints must be endorsed by the respective Department Head.\n\n"
            "Registrar"
        ),
        "received_at": BASE_DATE - timedelta(days=2, hours=5),
        "is_read": False,
        "analysis": {
            "summary": "Submission of Annual Performance Appraisal Reports (APAR) for AY 2025-26 through the faculty portal before September 20.",
            "category": "Administrative",
            "priority": "MEDIUM",
            "priority_reason": "Statutory annual compliance filing required for service records and career advancement promotion (CAS).",
            "evidences": [
                {
                    "field_name": "deadline",
                    "extracted_value": "2026-09-20",
                    "source_text": "Annual Performance Appraisal Reports (APAR) for the academic year 2025-26 must be submitted through the faculty portal before September 20.",
                    "confidence": 0.96
                }
            ]
        },
        "action_items": [
            {
                "description": "Upload APAR dossier and research publication proofs on faculty portal",
                "due_date": "2026-09-20",
                "priority": "MEDIUM",
                "completed": False,
                "relationship_type": "DUE_ON"
            }
        ],
        "meetings": [],
        "entities": [
            {"entity_type": "DOCUMENT", "entity_value": "APAR Form"},
            {"entity_type": "OFFICIAL", "entity_value": "Registrar"}
        ]
    },

    # 9. Innovation Cell - Smart India Hackathon
    {
        "sender": "innovation.cell@university.edu",
        "recipient": "faculty-mentors@university.edu",
        "subject": "Smart India Hackathon (SIH) 2026 - Internal Evaluation & Team Mentorship",
        "body": (
            "Dear Faculty,\n\n"
            "Student team nominations for Smart India Hackathon 2026 close on September 16. Each nominated team requires "
            "an officially registered faculty mentor. Please review student problem statement submissions and register as mentor "
            "on the AICTE portal by end of day September 16.\n\n"
            "Institution Innovation Council (IIC)"
        ),
        "received_at": BASE_DATE - timedelta(days=3),
        "is_read": True,
        "analysis": {
            "summary": "Faculty mentors must review student hackathon proposals and register as official mentors on the AICTE SIH portal before September 16.",
            "category": "Event",
            "priority": "MEDIUM",
            "priority_reason": "National-level student innovation contest with institutional ranking implications.",
            "evidences": [
                {
                    "field_name": "deadline",
                    "extracted_value": "2026-09-16",
                    "source_text": "register as mentor on the AICTE portal by end of day September 16.",
                    "confidence": 0.95
                }
            ]
        },
        "action_items": [
            {
                "description": "Register as faculty mentor on AICTE portal for nominated student teams",
                "due_date": "2026-09-16",
                "priority": "MEDIUM",
                "completed": True,
                "relationship_type": "DUE_ON"
            }
        ],
        "meetings": [],
        "entities": [
            {"entity_type": "EVENT", "entity_value": "Smart India Hackathon 2026"},
            {"entity_type": "ORGANIZATION", "entity_value": "AICTE / IIC"}
        ]
    },

    # 10. Department Library - Book Indent Recommendation
    {
        "sender": "librarian@university.edu",
        "recipient": "faculty-all@university.edu",
        "subject": "Department Library: Book Purchase Indents for Odd Semester 2026",
        "body": (
            "Dear Faculty,\n\n"
            "The library advisory committee invites indents for new textbooks, reference manuals, and e-book subscriptions "
            "for the upcoming semester. Please submit your recommended title lists using the attached template before September 30.\n\n"
            "Chief Librarian\n"
            "Central Library"
        ),
        "received_at": BASE_DATE - timedelta(days=3, hours=6),
        "is_read": True,
        "analysis": {
            "summary": "Submit textbook and journal indent recommendations for the upcoming semester to the Central Library before September 30.",
            "category": "Department",
            "priority": "LOW",
            "priority_reason": "Non-urgent routine resource acquisition request with a distant submission window.",
            "evidences": [
                {
                    "field_name": "deadline",
                    "extracted_value": "2026-09-30",
                    "source_text": "Please submit your recommended title lists using the attached template before September 30.",
                    "confidence": 0.95
                }
            ]
        },
        "action_items": [
            {
                "description": "Submit textbook indent recommendations to Department Library incharge",
                "due_date": "2026-09-30",
                "priority": "LOW",
                "completed": False,
                "relationship_type": "DUE_ON"
            }
        ],
        "meetings": [],
        "entities": [
            {"entity_type": "FACILITY", "entity_value": "Central Library"}
        ]
    },

    # 11. IEEE Conference Review Invitation (Un-analyzed - for testing live AI analysis)
    {
        "sender": "program.chairs@ieee-icc2026.org",
        "recipient": "faculty.member@university.edu",
        "subject": "Invitation to Review Manuscripts: IEEE International Conference on Cybernetics",
        "body": (
            "Dear Dr. Professor,\n\n"
            "Given your notable contributions to agentic artificial intelligence, the Technical Program Committee "
            "cordially invites you to review 3 submitted manuscripts for IEEE ICC 2026. If you accept, your peer-review "
            "evaluations must be submitted through EasyChair before September 18.\n\n"
            "Please confirm your availability by replying to this email.\n\n"
            "Warm regards,\n"
            "Prof. Elena Rostova\n"
            "TPC Chair, IEEE ICC 2026"
        ),
        "received_at": BASE_DATE - timedelta(days=4),
        "is_read": False,
        "analysis": None,
        "action_items": [],
        "meetings": [],
        "entities": []
    },

    # 12. Office Memorandum: Biometric Policy Update (Un-analyzed)
    {
        "sender": "admin.office@university.edu",
        "recipient": "faculty-all@university.edu",
        "subject": "Circular: Revised Biometric Attendance and Movement Register Procedures",
        "body": (
            "To All Faculty and Staff,\n\n"
            "Kindly note that effective September 15, the grace period for biometric punch-in will be revised to 15 minutes. "
            "Faculty leaving campus for official duty must record entries in the digital movement register located at Gate 1.\n\n"
            "By Order of the Vice Chancellor"
        ),
        "received_at": BASE_DATE - timedelta(days=4, hours=4),
        "is_read": False,
        "analysis": None,
        "action_items": [],
        "meetings": [],
        "entities": []
    },

    # 13. Capstone Project Committee (Un-analyzed)
    {
        "sender": "projects.coordinator@university.edu",
        "recipient": "faculty-cse@university.edu",
        "subject": "Capstone Project Phase-1 Evaluation Schedule and Rubrics",
        "body": (
            "Dear Faculty Mentors,\n\n"
            "The Phase-1 Capstone Project review presentations will be held on September 12 at 10:00 AM in Systems Lab 4. "
            "All project guides are requested to evaluate student teams using the rubrics uploaded on LMS. "
            "Consolidated marks sheets must be handed over to the project convener by 4 PM on the same day.\n\n"
            "Project Coordination Committee"
        ),
        "received_at": BASE_DATE - timedelta(days=5),
        "is_read": False,
        "analysis": None,
        "action_items": [],
        "meetings": [],
        "entities": []
    },

    # 14. Campus IT Infrastructure Maintenance (Un-analyzed)
    {
        "sender": "it.support@university.edu",
        "recipient": "campus-community@university.edu",
        "subject": "Scheduled Maintenance: Core Campus Wi-Fi & Firewall Upgrades",
        "body": (
            "Dear Campus Community,\n\n"
            "The IT Services team will perform scheduled firmware upgrades on core switches on September 7 starting at 11:00 PM. "
            "Campus Wi-Fi and access to internal ERP portals will be intermittently unavailable until 4:00 AM on September 8. "
            "We regret any inconvenience caused.\n\n"
            "IT Infrastructure Wing"
        ),
        "received_at": BASE_DATE - timedelta(days=5, hours=8),
        "is_read": True,
        "analysis": None,
        "action_items": [],
        "meetings": [],
        "entities": []
    },

    # 15. Faculty Development Program Invitation (Un-analyzed)
    {
        "sender": "fdp.cell@university.edu",
        "recipient": "faculty-engineering@university.edu",
        "subject": "AICTE-ATAL Faculty Development Program on Advanced LLMs & Agentic Systems",
        "body": (
            "Dear Faculty,\n\n"
            "Applications are open for the 5-day national FDP on 'Agentic AI and LLM Architectures' hosted from October 5 to 9. "
            "The program covers modern agent frameworks, RAG, and fine-tuning. Faculty interested in attending should secure "
            "HOD clearance and complete portal registration before September 14.\n\n"
            "Center for Continuing Education"
        ),
        "received_at": BASE_DATE - timedelta(days=6),
        "is_read": True,
        "analysis": None,
        "action_items": [],
        "meetings": [],
        "entities": []
    }
]


def seed_database(db: Session) -> int:
    """Populates the database with realistic synthetic faculty emails (idempotent)."""
    count = 0
    for data in SAMPLE_EMAILS:
        existing = db.query(Email).filter(
            Email.subject == data["subject"],
            Email.sender == data["sender"]
        ).first()
        if existing:
            continue

        email_obj = Email(
            user_id=1,
            sender=data["sender"],
            recipient=data["recipient"],
            subject=data["subject"],
            body=data["body"],
            received_at=data["received_at"],
            is_read=data["is_read"],
            created_at=data["received_at"]
        )
        db.add(email_obj)
        db.flush()  # Assigns email_obj.id

        # Add AIAnalysis and Evidence if pre-computed
        if data.get("analysis"):
            analysis_data = data["analysis"]
            analysis_obj = AIAnalysis(
                email_id=email_obj.id,
                summary=analysis_data["summary"],
                category=analysis_data["category"],
                priority=analysis_data["priority"],
                priority_reason=analysis_data["priority_reason"],
                processed_at=email_obj.received_at + timedelta(minutes=5)
            )
            db.add(analysis_obj)
            db.flush()

            for ev in analysis_data.get("evidences", []):
                src = ev["source_text"]
                c_start = None
                c_end = None
                if src in email_obj.body:
                    c_start = email_obj.body.find(src)
                    c_end = c_start + len(src)

                evidence_obj = Evidence(
                    analysis_id=analysis_obj.id,
                    field_name=ev["field_name"],
                    extracted_value=ev["extracted_value"],
                    source_text=src,
                    confidence=ev.get("confidence", 1.0),
                    validation_status=ev.get("validation_status", "VERIFIED"),
                    char_start=ev.get("char_start", c_start),
                    char_end=ev.get("char_end", c_end),
                    grounding_method=ev.get("grounding_method", "EXACT_SPAN")
                )
                db.add(evidence_obj)

        # Add Action Items
        for item in data.get("action_items", []):
            rel_type = item.get("relationship_type", "DUE_ON")
            target_ev = item.get("target_event")
            reason = item.get("relationship_reason")
            if not reason:
                if rel_type == "DUE_ON":
                    reason = f"Academic task bound to primary deadline {item.get('due_date')}."
                elif rel_type == "PREPARE_BEFORE":
                    reason = f"Prerequisite preparation bound to event on {item.get('due_date')}."
                elif rel_type == "ATTEND_BY":
                    reason = f"Mandatory attendance bound to scheduled event on {item.get('due_date')}."
                elif rel_type == "COMMUNICATE_BY":
                    reason = f"Communication requirement bound to deadline {item.get('due_date')}."
                else:
                    reason = "Routine academic task with no temporal constraint."

            action_obj = ActionItem(
                email_id=email_obj.id,
                description=item["description"],
                due_date=item["due_date"],
                priority=item.get("priority", "MEDIUM"),
                completed=item.get("completed", False),
                relationship_type=rel_type,
                target_event=target_ev,
                relationship_reason=reason,
                binding_confidence=item.get("binding_confidence", 0.95)
            )
            db.add(action_obj)

        # Add Meetings
        for mtg in data.get("meetings", []):
            meeting_obj = Meeting(
                email_id=email_obj.id,
                title=mtg["title"],
                meeting_date=mtg["meeting_date"],
                meeting_time=mtg["meeting_time"],
                location=mtg["location"],
                preparation=mtg.get("preparation")
            )
            db.add(meeting_obj)

        # Add Entities
        for ent in data.get("entities", []):
            entity_obj = Entity(
                email_id=email_obj.id,
                entity_type=ent["entity_type"],
                entity_value=ent["entity_value"]
            )
            db.add(entity_obj)

        count += 1

    db.commit()
    return count


if __name__ == "__main__":
    print("Initializing database tables...")
    reset_db()
    db = SessionLocal()
    try:
        inserted = seed_database(db)
        print(f"Successfully seeded {inserted} synthetic faculty emails with relational intelligence!")
    finally:
        db.close()
