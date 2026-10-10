from typing import List
from backend.app.evaluation.ground_truth_schema import GroundTruthEmail, GroundTruthMeeting

BENCHMARK_DATASET: List[GroundTruthEmail] = [
    GroundTruthEmail(
        id="BENCH-001",
        sender="coe@university.edu",
        subject="URGENT: End-Semester Question Paper Submission Deadline",
        body=(
            "Dear Faculty Members,\n\n"
            "This is an urgent reminder from the Controller of Examinations. All course coordinators must "
            "submit two sets of question papers along with the detailed scheme of valuation for the upcoming "
            "End-Semester Examinations. The absolute deadline for submission is September 25, 2026 at 5:00 PM. "
            "Please ensure that the question papers follow the revised Bloom's taxonomy guidelines and are hand-delivered "
            "in sealed envelopes to the CoE Confidential Section.\n\n"
            "Late submissions will not be entertained.\n\n"
            "Regards,\nProf. R. K. Sharma\nController of Examinations"
        ),
        received_at="2026-09-10T09:00:00",
        expected_category="Examination",
        expected_priority="HIGH",
        expected_priority_reason="Official examination directive with strict final submission deadline from Controller of Examinations.",
        expected_deadline="2026-09-25",
        expected_meeting=None,
        expected_actions=[
            "submit two sets of question papers along with the detailed scheme of valuation",
            "ensure that the question papers follow the revised Bloom's taxonomy guidelines"
        ],
        expected_summary=(
            "Controller of Examinations mandates submission of two question paper sets with scheme of valuation "
            "by September 25, 2026 at 5:00 PM in sealed envelopes following Bloom's taxonomy."
        ),
        grounded_spans=[
            "September 25, 2026",
            "submit two sets of question papers along with the detailed scheme of valuation",
            "Controller of Examinations",
            "CoE Confidential Section"
        ],
        domain="Examination & Assessment",
        difficulty="Standard"
    ),
    GroundTruthEmail(
        id="BENCH-002",
        sender="dean.academics@university.edu",
        subject="Mandatory Faculty Meeting: Preparation for NAAC Peer Team Visit",
        body=(
            "Dear Colleagues,\n\n"
            "In view of the upcoming NAAC Peer Team Visit, a mandatory briefing meeting has been convened by the Dean "
            "of Academic Affairs on September 18, 2026 at 02:30 PM in the Main Auditorium.\n\n"
            "All department heads and faculty members are requested to attend without fail. Please bring your updated "
            "course files, mentoring records, and research publication indices. Kindly submit your department criterion files "
            "to the IQAC office before the meeting.\n\n"
            "Sincerely,\nDr. Aruna Sengupta\nDean of Academic Affairs"
        ),
        received_at="2026-09-12T11:15:00",
        expected_category="Administrative",
        expected_priority="HIGH",
        expected_priority_reason="Mandatory meeting convened by Dean of Academics for institutional accreditation visit.",
        expected_deadline="2026-09-18",
        expected_meeting=GroundTruthMeeting(
            title="Preparation for NAAC Peer Team Visit",
            date="2026-09-18",
            time="02:30 PM",
            location="Main Auditorium",
            preparation="bring your updated course files, mentoring records, and research publication indices"
        ),
        expected_actions=[
            "attend the mandatory briefing meeting on September 18, 2026",
            "bring your updated course files, mentoring records, and research publication indices",
            "submit your department criterion files to the IQAC office"
        ],
        expected_summary=(
            "Dean of Academic Affairs convened a mandatory faculty meeting on September 18, 2026 at 2:30 PM in the "
            "Main Auditorium for NAAC visit preparation. Faculty must bring course files and submit criterion files."
        ),
        grounded_spans=[
            "September 18, 2026",
            "02:30 PM",
            "Main Auditorium",
            "NAAC Peer Team Visit",
            "Dean of Academic Affairs"
        ],
        domain="Accreditation & Governance",
        difficulty="Standard"
    ),
    GroundTruthEmail(
        id="BENCH-003",
        sender="hod.cse@university.edu",
        subject="Department Curriculum Revision Committee (CRC) Session",
        body=(
            "Hello Faculty,\n\n"
            "We will be holding our quarterly Curriculum Revision Committee session on September 22, 2026 from 10:00 AM "
            "in Department Conference Room B. We will review proposed elective courses for the 2027 academic year.\n\n"
            "Please review the syllabus draft circulated last week and email your comments to the committee secretary "
            "by September 20, 2026.\n\n"
            "Best regards,\nProf. V. Raman\nHead, Department of Computer Science & Engineering"
        ),
        received_at="2026-09-13T14:30:00",
        expected_category="Academic",
        expected_priority="MEDIUM",
        expected_priority_reason="Departmental committee session with syllabus review deadline.",
        expected_deadline="2026-09-20",
        expected_meeting=GroundTruthMeeting(
            title="Curriculum Revision Committee Session",
            date="2026-09-22",
            time="10:00 AM",
            location="Department Conference Room B",
            preparation="review the syllabus draft circulated last week"
        ),
        expected_actions=[
            "review the syllabus draft circulated last week",
            "email your comments to the committee secretary by September 20, 2026"
        ],
        expected_summary=(
            "CSE Department Curriculum Revision Committee session scheduled for September 22, 2026 at 10:00 AM "
            "in Conference Room B. Syllabus review comments are due by September 20, 2026."
        ),
        grounded_spans=[
            "September 22, 2026",
            "10:00 AM",
            "Department Conference Room B",
            "September 20, 2026",
            "Curriculum Revision Committee"
        ],
        domain="Departmental Administration",
        difficulty="Standard"
    ),
    GroundTruthEmail(
        id="BENCH-004",
        sender="rd.cell@university.edu",
        subject="Call for Research Proposals: SERB Core Research Grant (CRG) 2026-27",
        body=(
            "Dear Faculty Colleagues,\n\n"
            "The Science and Engineering Research Board (SERB) has announced the call for project proposals under the "
            "Core Research Grant (CRG) scheme. Interested faculty investigators may formulate proposals in frontier areas "
            "of science and engineering.\n\n"
            "Internal institutional endorsement requests must be submitted through the R&D Portal on or before "
            "October 15, 2026. Please forward a copy of the budget summary and bio-sketch to the R&D Dean office.\n\n"
            "Warm regards,\nR&D Cell, University Secretariat"
        ),
        received_at="2026-09-14T10:00:00",
        expected_category="Research",
        expected_priority="MEDIUM",
        expected_priority_reason="Competitive external research grant announcement with institutional review deadline.",
        expected_deadline="2026-10-15",
        expected_meeting=None,
        expected_actions=[
            "submit internal institutional endorsement requests through the R&D Portal",
            "forward a copy of the budget summary and bio-sketch to the R&D Dean office"
        ],
        expected_summary=(
            "SERB Core Research Grant call announced. Institutional endorsement requests must be submitted through "
            "the R&D Portal by October 15, 2026 along with budget summary and bio-sketch."
        ),
        grounded_spans=[
            "October 15, 2026",
            "SERB Core Research Grant",
            "R&D Portal",
            "budget summary and bio-sketch"
        ],
        domain="Research & Sponsored Projects",
        difficulty="Standard"
    ),
    GroundTruthEmail(
        id="BENCH-005",
        sender="tpo@university.edu",
        subject="Immediate Action Required: TechCorp Campus Drive Student Shortlist Verification",
        body=(
            "Dear Final Year Mentors and Faculty Advisors,\n\n"
            "TechCorp will conduct their campus placement interview rounds on September 19, 2026. "
            "Attached is the initial shortlist of 84 eligible candidates based on CGPA criteria.\n\n"
            "Kindly verify that none of these students have active academic backlogs or disciplinary warnings. "
            "Any discrepancies must be flagged to the Placement Cell by tomorrow, September 15, 2026 at 1:00 PM.\n\n"
            "Thank you,\nTPO Placement Office"
        ),
        received_at="2026-09-14T15:00:00",
        expected_category="Placement",
        expected_priority="HIGH",
        expected_priority_reason="Time-sensitive student placement eligibility verification with 24-hour turnaround.",
        expected_deadline="2026-09-15",
        expected_meeting=None,
        expected_actions=[
            "verify that none of these students have active academic backlogs or disciplinary warnings",
            "flag discrepancies to the Placement Cell by September 15, 2026 at 1:00 PM"
        ],
        expected_summary=(
            "TPO requests immediate verification of 84 shortlisted candidates for TechCorp campus interviews. "
            "Discrepancies regarding backlogs or disciplinary issues must be reported by September 15, 2026 at 1:00 PM."
        ),
        grounded_spans=[
            "September 15, 2026",
            "TechCorp",
            "Placement Cell",
            "active academic backlogs"
        ],
        domain="Placement & Industry Relations",
        difficulty="Complex"
    ),
    GroundTruthEmail(
        id="BENCH-006",
        sender="library@university.edu",
        subject="Annual Book and E-Resource Recommendation Drive 2026",
        body=(
            "Dear Faculty,\n\n"
            "The Central Library invites recommendations for new textbooks, reference handbooks, and subscriptions "
            "for the upcoming academic calendar. Faculty members may fill out the online requisition form available on the "
            "library intranet portal at their convenience before November 30, 2026.\n\n"
            "Thank you for your ongoing support to enrich our library repository.\n\n"
            "Best,\nChief Librarian"
        ),
        received_at="2026-09-11T08:30:00",
        expected_category="Administrative",
        expected_priority="LOW",
        expected_priority_reason="Routine informational circular with non-urgent, extended requisition timeline.",
        expected_deadline="2026-11-30",
        expected_meeting=None,
        expected_actions=[
            "fill out the online requisition form available on the library intranet portal"
        ],
        expected_summary=(
            "Central Library invites book and e-resource recommendations for the upcoming calendar via the intranet "
            "portal by November 30, 2026."
        ),
        grounded_spans=[
            "November 30, 2026",
            "Central Library",
            "online requisition form"
        ],
        domain="Campus Facilities & Library",
        difficulty="Standard"
    ),
    GroundTruthEmail(
        id="BENCH-007",
        sender="student.affairs@university.edu",
        subject="Invitation: Annual Cultural Fest 'Aura 2026' Inaugural Ceremony",
        body=(
            "Respected Faculty,\n\n"
            "The Student Cultural Council cordially invites you and your family to the Inaugural Ceremony of Aura 2026 "
            "on September 26, 2026 at 06:00 PM in the Open Air Theatre. Join us for an evening of musical performances, "
            "art showcases, and traditional welcome dances.\n\n"
            "High tea will be served following the inaugural address.\n\n"
            "Cordially,\nCultural Committee & Student Council"
        ),
        received_at="2026-09-13T16:00:00",
        expected_category="General Notice",
        expected_priority="LOW",
        expected_priority_reason="Social invitation and extracurricular campus event with optional attendance.",
        expected_deadline=None,
        expected_meeting=GroundTruthMeeting(
            title="Inaugural Ceremony of Aura 2026",
            date="2026-09-26",
            time="06:00 PM",
            location="Open Air Theatre",
            preparation=None
        ),
        expected_actions=[],
        expected_summary=(
            "Student Cultural Council invites faculty to the inaugural ceremony of Aura 2026 on September 26, 2026 "
            "at 6:00 PM in the Open Air Theatre."
        ),
        grounded_spans=[
            "September 26, 2026",
            "06:00 PM",
            "Open Air Theatre",
            "Aura 2026"
        ],
        domain="Student Affairs & Events",
        difficulty="Standard"
    ),
    GroundTruthEmail(
        id="BENCH-008",
        sender="iqac@university.edu",
        subject="Action Required: Upload Course Attainment Data for Odd Semester 2026",
        body=(
            "Dear Faculty Members,\n\n"
            "As part of our internal quality assurance protocols, all course instructors are required to compute "
            "and upload the Course Outcome (CO) and Program Outcome (PO) direct attainment matrices on the ERP system. "
            "The ERP portal will remain open for data entry until September 28, 2026.\n\n"
            "Please ensure that assessment rubrics and indirect feedback surveys are duly attached before final submission.\n\n"
            "Regards,\nDirector, Internal Quality Assurance Cell (IQAC)"
        ),
        received_at="2026-09-12T13:00:00",
        expected_category="Administrative",
        expected_priority="HIGH",
        expected_priority_reason="Institutional compliance mandate with fixed ERP portal closure deadline.",
        expected_deadline="2026-09-28",
        expected_meeting=None,
        expected_actions=[
            "compute and upload Course Outcome and Program Outcome direct attainment matrices on ERP",
            "ensure assessment rubrics and indirect feedback surveys are attached"
        ],
        expected_summary=(
            "IQAC directs all faculty instructors to compute and upload CO-PO direct attainment matrices on ERP "
            "by September 28, 2026 along with rubrics and feedback surveys."
        ),
        grounded_spans=[
            "September 28, 2026",
            "Course Outcome",
            "Program Outcome",
            "Internal Quality Assurance Cell"
        ],
        domain="Quality Assurance & Accreditation",
        difficulty="Standard"
    ),
    GroundTruthEmail(
        id="BENCH-009",
        sender="scholar.priya@university.edu",
        subject="Request for Ph.D. Research Progress Review Meeting",
        body=(
            "Respected Professor,\n\n"
            "I have compiled the experimental results for my doctoral dissertation chapter on deep generative networks. "
            "Could we please schedule a Doctoral Advisory Committee progress review meeting sometime next week? "
            "I have uploaded my draft chapter and benchmark comparison graphs to the shared drive.\n\n"
            "Please let me know if September 21, 2026 at 11:30 AM in your office suits your schedule.\n\n"
            "Respectfully,\nPriya Nair\nResearch Scholar, Roll No. 2022PHD042"
        ),
        received_at="2026-09-14T09:45:00",
        expected_category="Research",
        expected_priority="MEDIUM",
        expected_priority_reason="Ph.D. scholar research advisement and doctoral committee review scheduling request.",
        expected_deadline="2026-09-21",
        expected_meeting=GroundTruthMeeting(
            title="Doctoral Advisory Committee progress review meeting",
            date="2026-09-21",
            time="11:30 AM",
            location="faculty office",
            preparation="review draft chapter and benchmark comparison graphs on shared drive"
        ),
        expected_actions=[
            "schedule a Doctoral Advisory Committee progress review meeting",
            "review draft chapter and benchmark comparison graphs on shared drive"
        ],
        expected_summary=(
            "Ph.D. scholar Priya Nair requests a progress review meeting proposed for September 21, 2026 at 11:30 AM "
            "to evaluate experimental results on deep generative networks."
        ),
        grounded_spans=[
            "September 21, 2026",
            "11:30 AM",
            "Priya Nair",
            "Doctoral Advisory Committee"
        ],
        domain="Research Advising",
        difficulty="Standard"
    ),
    GroundTruthEmail(
        id="BENCH-010",
        sender="finance.accounts@university.edu",
        subject="Notice: Submission of Conference Travel Grant Reimbursement Claims",
        body=(
            "Dear Faculty Members,\n\n"
            "Faculty who availed institutional travel grants for national or international conferences during "
            "Quarter 2 must submit their finalized expense vouchers, original boarding passes, and participation "
            "certificates to the Accounts Office. The deadline for claiming reimbursement is September 30, 2026.\n\n"
            "Claims submitted after this date will lapse into the next financial year.\n\n"
            "Finance & Accounts Section"
        ),
        received_at="2026-09-10T14:15:00",
        expected_category="Administrative",
        expected_priority="MEDIUM",
        expected_priority_reason="Financial claim reimbursement deadline with financial lapse consequences.",
        expected_deadline="2026-09-30",
        expected_meeting=None,
        expected_actions=[
            "submit finalized expense vouchers, original boarding passes, and participation certificates to Accounts"
        ],
        expected_summary=(
            "Accounts Office requires submission of Q2 conference travel reimbursement claims including boarding passes "
            "and vouchers by September 30, 2026."
        ),
        grounded_spans=[
            "September 30, 2026",
            "Accounts Office",
            "original boarding passes",
            "travel grants"
        ],
        domain="Financial Administration",
        difficulty="Standard"
    )
]
