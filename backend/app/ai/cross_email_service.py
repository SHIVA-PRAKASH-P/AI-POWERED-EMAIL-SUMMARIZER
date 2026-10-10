"""Cross-Email Intelligence & Thread/Topic Context Service.

Performs cross-email correlation, conversation thread linking, topic clustering,
and chronological deadline/action synthesis across the faculty inbox corpus.
Operates completely offline with zero-dependency deterministic algorithms.
"""

import re
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
from sqlalchemy.orm import Session

from backend.app.models.email import Email
from backend.app.models.analysis import AIAnalysis
from backend.app.models.action_item import ActionItem
from backend.app.models.meeting import Meeting
from backend.app.models.entity import Entity

class CrossEmailIntelligenceService:
    """Provides thread resolution, topic clustering, and timeline correlation across emails."""

    @staticmethod
    def normalize_subject(subject: Optional[str]) -> str:
        """Strip conversational prefixes (Re:, Fwd:, Urgent:, etc.) and normalize whitespace."""
        if not subject:
            return ""
        s = subject.strip()
        prev = ""
        while prev != s:
            prev = s
            s = re.sub(r"^(re|fwd|fw|urgent|confidential|notice|reminder)\s*:\s*", "", s, flags=re.IGNORECASE).strip()
            s = re.sub(r"^\[.*?\]\s*", "", s).strip()
        return " ".join(s.split()).lower()

    def find_related_emails(
        self,
        db: Session,
        email_id: int,
        limit: int = 10,
        user_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Identify related emails using thread matching, sender continuity, and entity overlap."""
        target_query = db.query(Email).filter(Email.id == email_id)
        if user_id is not None:
            target_query = target_query.filter(Email.user_id == user_id)
        target = target_query.first()
        if not target:
            return []

        target_norm_subj = self.normalize_subject(target.subject)
        target_entities: Set[str] = {
            e.entity_value.lower() for e in target.entities if e.entity_value
        }
        target_category = target.analysis.category if target.analysis else None

        # Fetch candidate emails (excluding target)
        candidates_query = db.query(Email).filter(Email.id != email_id)
        if user_id is not None:
            candidates_query = candidates_query.filter(Email.user_id == user_id)
        candidates = candidates_query.order_by(Email.received_at.asc()).all()

        scored_results = []
        for cand in candidates:
            score = 0.0
            reasons = []
            rel_type = "RELATED_TOPIC"

            cand_norm_subj = self.normalize_subject(cand.subject)
            cand_entities: Set[str] = {
                e.entity_value.lower() for e in cand.entities if e.entity_value
            }
            cand_category = cand.analysis.category if cand.analysis else None

            # 1. Thread Match (identical normalized subject)
            if target_norm_subj and cand_norm_subj and target_norm_subj == cand_norm_subj:
                score += 0.60
                if cand.received_at < target.received_at:
                    rel_type = "THREAD_PREDECESSOR"
                    reasons.append("Preceding message in the same thread")
                else:
                    rel_type = "THREAD_FOLLOWUP"
                    reasons.append("Subsequent follow-up message in the same thread")

            # 2. Sender continuity
            if cand.sender.lower() == target.sender.lower():
                score += 0.20
                reasons.append(f"Same sender ({target.sender})")

            # 3. Category & Topic overlap
            if target_category and cand_category and target_category == cand_category:
                score += 0.15
                reasons.append(f"Same academic domain ({target_category})")

            # 4. Entity overlap (e.g. shared student, venue, or committee)
            shared_entities = target_entities.intersection(cand_entities)
            if shared_entities:
                score += min(0.35, len(shared_entities) * 0.20)
                reasons.append(f"Shared entities: {', '.join(list(shared_entities)[:3])}")

            # 5. Subject keyword Jaccard overlap
            target_words = set(re.findall(r"\w{4,}", target_norm_subj))
            cand_words = set(re.findall(r"\w{4,}", cand_norm_subj))
            if target_words and cand_words:
                jaccard = len(target_words.intersection(cand_words)) / len(target_words.union(cand_words))
                if jaccard > 0.25:
                    score += jaccard * 0.30
                    if "Similar subject keywords" not in reasons:
                        reasons.append("High subject lexical similarity")

            if score >= 0.20:
                scored_results.append({
                    "id": cand.id,
                    "subject": cand.subject,
                    "sender": cand.sender,
                    "recipient": cand.recipient,
                    "received_at": cand.received_at.isoformat() if cand.received_at else None,
                    "category": cand_category,
                    "priority": cand.analysis.priority if cand.analysis else "LOW",
                    "relationship_type": rel_type,
                    "relevance_score": round(min(1.0, score), 2),
                    "relationship_reasons": reasons,
                    "actions_count": len(cand.action_items),
                    "has_meeting": len(cand.meetings) > 0
                })

        # Sort by relevance score descending, then by received_at descending
        scored_results.sort(key=lambda x: (x["relevance_score"], x["received_at"] or ""), reverse=True)
        return scored_results[:limit]

    def get_cross_email_insights(
        self,
        db: Session,
        email_id: int,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Generate timeline progression, cross-email action items, and topic context."""
        target_query = db.query(Email).filter(Email.id == email_id)
        if user_id is not None:
            target_query = target_query.filter(Email.user_id == user_id)
        target = target_query.first()
        if not target:
            return {
                "email_id": email_id,
                "thread_count": 0,
                "related_emails": [],
                "timeline": [],
                "cross_actions": [],
                "insights": []
            }

        related = self.find_related_emails(db, email_id, limit=8, user_id=user_id)
        related_ids = [r["id"] for r in related]
        all_ids = [email_id] + related_ids

        # Build chronological timeline of all meetings & deadlines in this cluster
        cluster_query = db.query(Email).filter(Email.id.in_(all_ids))
        if user_id is not None:
            cluster_query = cluster_query.filter(Email.user_id == user_id)
        cluster_emails = cluster_query.order_by(Email.received_at.asc()).all()

        timeline = []
        for em in cluster_emails:
            # Add email transmission milestone
            timeline.append({
                "type": "EMAIL_RECEIVED",
                "date": em.received_at.strftime("%Y-%m-%d") if em.received_at else "",
                "time": em.received_at.strftime("%H:%M") if em.received_at else "",
                "title": em.subject,
                "source_email_id": em.id,
                "is_current": (em.id == email_id),
                "details": f"From: {em.sender}"
            })

            # Add meetings
            for m in em.meetings:
                if m.meeting_date:
                    timeline.append({
                        "type": "MEETING",
                        "date": m.meeting_date,
                        "time": m.meeting_time or "",
                        "title": m.title,
                        "source_email_id": em.id,
                        "is_current": (em.id == email_id),
                        "details": f"Location: {m.location or 'Online/TBD'}"
                    })

            # Add deadlines
            for a in em.action_items:
                if a.due_date:
                    timeline.append({
                        "type": "DEADLINE",
                        "date": a.due_date,
                        "time": "23:59",
                        "title": a.description,
                        "source_email_id": em.id,
                        "is_current": (em.id == email_id),
                        "details": f"Priority: {a.priority} | Completed: {a.completed}"
                    })

        # Sort timeline chronologically
        timeline.sort(key=lambda x: (x["date"], x["time"]))

        # Aggregate cross-email action items
        cross_actions = []
        for em in cluster_emails:
            for a in em.action_items:
                cross_actions.append({
                    "id": a.id,
                    "email_id": em.id,
                    "email_subject": em.subject,
                    "description": a.description,
                    "due_date": a.due_date,
                    "priority": a.priority,
                    "completed": a.completed,
                    "relationship_type": a.relationship_type,
                    "is_from_current_email": (em.id == email_id)
                })

        # Synthesize explainable cross-email intelligence insights
        insights = []
        if len(related) > 0:
            top_rel = related[0]
            if top_rel["relationship_type"] in ["THREAD_PREDECESSOR", "THREAD_FOLLOWUP"]:
                insights.append(
                    f"This communication is part of a multi-message thread with {len(related)} related correspondence(s)."
                )
            
            pending_cluster_tasks = [a for a in cross_actions if not a["completed"]]
            if len(pending_cluster_tasks) > 1:
                insights.append(
                    f"There are {len(pending_cluster_tasks)} total pending action items across this topic cluster."
                )

            # Check if deadlines exist across multiple emails
            dates = [t["date"] for t in timeline if t["type"] in ["DEADLINE", "MEETING"] and t["date"]]
            if len(set(dates)) > 1:
                insights.append(
                    f"Cluster spans multiple critical dates from {min(dates)} to {max(dates)}."
                )
        else:
            insights.append("This communication appears to be a standalone topic with no prior correspondence in the current inbox.")

        return {
            "email_id": email_id,
            "thread_count": len(related) + 1,
            "related_emails": related,
            "timeline": timeline,
            "cross_actions": cross_actions,
            "insights": insights
        }

    def get_topic_clusters(self, db: Session, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Cluster all inbox emails into distinct academic topic groupings."""
        emails_query = db.query(Email)
        if user_id is not None:
            emails_query = emails_query.filter(Email.user_id == user_id)
        emails = emails_query.order_by(Email.received_at.desc()).all()
        if not emails:
            return []

        clusters_map: Dict[str, List[Email]] = {}

        for em in emails:
            norm_subj = self.normalize_subject(em.subject)
            # Find matching cluster key by significant token intersection
            matched_key = None
            em_tokens = set(re.findall(r"\w{4,}", norm_subj))

            for key in clusters_map.keys():
                key_tokens = set(re.findall(r"\w{4,}", key))
                if norm_subj == key:
                    matched_key = key
                    break
                elif em_tokens and key_tokens:
                    jaccard = len(em_tokens.intersection(key_tokens)) / len(em_tokens.union(key_tokens))
                    if jaccard >= 0.40:
                        matched_key = key
                        break

            if matched_key:
                clusters_map[matched_key].append(em)
            else:
                clusters_map[norm_subj] = [em]

        # Format clusters
        formatted_clusters = []
        cluster_id = 1
        for topic_key, cluster_emails in clusters_map.items():
            # Pick representative email (most recent)
            rep = cluster_emails[0]
            senders = list({e.sender for e in cluster_emails})
            
            # Count pending tasks and deadlines
            all_actions = [a for e in cluster_emails for a in e.action_items]
            pending_actions = [a for a in all_actions if not a.completed]
            meetings = [m for e in cluster_emails for m in e.meetings]

            priorities = [e.analysis.priority for e in cluster_emails if e.analysis]
            highest_prio = "LOW"
            if "HIGH" in priorities:
                highest_prio = "HIGH"
            elif "MEDIUM" in priorities:
                highest_prio = "MEDIUM"

            category = rep.analysis.category if rep.analysis else "Academic"

            formatted_clusters.append({
                "cluster_id": cluster_id,
                "topic_title": rep.subject,
                "normalized_topic": topic_key,
                "category": category,
                "highest_priority": highest_prio,
                "email_count": len(cluster_emails),
                "emails": [
                    {
                        "id": e.id,
                        "subject": e.subject,
                        "sender": e.sender,
                        "received_at": e.received_at.isoformat() if e.received_at else None,
                        "is_read": e.is_read
                    }
                    for e in cluster_emails
                ],
                "participants": senders,
                "total_action_items": len(all_actions),
                "pending_action_items": len(pending_actions),
                "meetings_count": len(meetings),
                "latest_received_at": rep.received_at.isoformat() if rep.received_at else None
            })
            cluster_id += 1

        # Sort clusters by email count descending, then by latest_received_at descending
        formatted_clusters.sort(key=lambda c: (c["email_count"], c["latest_received_at"] or ""), reverse=True)
        return formatted_clusters

# Global singleton
cross_email_service = CrossEmailIntelligenceService()
