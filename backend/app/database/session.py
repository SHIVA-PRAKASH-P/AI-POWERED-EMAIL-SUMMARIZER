from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from backend.app.config import settings
import os

# Ensure the database directory exists
db_url = settings.DATABASE_URL
if db_url.startswith("sqlite:///"):
    db_file_path = db_url.replace("sqlite:///", "")
    db_dir = os.path.dirname(db_file_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

# SQLite engine configuration
connect_args = {"check_same_thread": False} if "sqlite" in db_url else {}
engine = create_engine(
    db_url,
    connect_args=connect_args,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """FastAPI Dependency for database session management."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Create all database tables defined in models and apply non-destructive migrations."""
    # Import all models to ensure they are registered with Base.metadata
    from backend.app.models import User, Email, AIAnalysis, ActionItem, Meeting, Evidence, Entity, FacultyPreference  # noqa: F401
    Base.metadata.create_all(bind=engine)

    # Idempotent column additions and Stage 19B multi-user migration
    try:
        with engine.connect() as conn:
            from sqlalchemy import text
            # 1. Action Items columns
            result = conn.execute(text("PRAGMA table_info(action_items)")).fetchall()
            existing_cols = {row[1] for row in result}
            if existing_cols:
                if "target_event" not in existing_cols:
                    conn.execute(text("ALTER TABLE action_items ADD COLUMN target_event VARCHAR(255)"))
                if "relationship_reason" not in existing_cols:
                    conn.execute(text("ALTER TABLE action_items ADD COLUMN relationship_reason TEXT"))
                if "binding_confidence" not in existing_cols:
                    conn.execute(text("ALTER TABLE action_items ADD COLUMN binding_confidence FLOAT DEFAULT 1.0"))
            
            # 2. Evidences columns
            ev_result = conn.execute(text("PRAGMA table_info(evidences)")).fetchall()
            ev_cols = {row[1] for row in ev_result}
            if ev_cols:
                if "validation_status" not in ev_cols:
                    conn.execute(text("ALTER TABLE evidences ADD COLUMN validation_status VARCHAR(50) DEFAULT 'VERIFIED'"))
                if "char_start" not in ev_cols:
                    conn.execute(text("ALTER TABLE evidences ADD COLUMN char_start INTEGER"))
                if "char_end" not in ev_cols:
                    conn.execute(text("ALTER TABLE evidences ADD COLUMN char_end INTEGER"))
                if "grounding_method" not in ev_cols:
                    conn.execute(text("ALTER TABLE evidences ADD COLUMN grounding_method VARCHAR(50) DEFAULT 'EXACT_SPAN'"))

            # 3. Stage 19B & 19C Email column additions
            em_result = conn.execute(text("PRAGMA table_info(emails)")).fetchall()
            em_cols = {row[1] for row in em_result}
            if em_cols and "user_id" not in em_cols:
                conn.execute(text("ALTER TABLE emails ADD COLUMN user_id INTEGER REFERENCES users(id)"))
            if em_cols and "provider_message_id" not in em_cols:
                conn.execute(text("ALTER TABLE emails ADD COLUMN provider_message_id VARCHAR(255)"))

            pref_result = conn.execute(text("PRAGMA table_info(faculty_preferences)")).fetchall()
            pref_cols = {row[1] for row in pref_result}
            if pref_cols and "user_id" not in pref_cols:
                conn.execute(text("ALTER TABLE faculty_preferences ADD COLUMN user_id INTEGER REFERENCES users(id)"))

            # Stage 21 AIAnalysis columns (deadline & smart reply)
            ai_result = conn.execute(text("PRAGMA table_info(ai_analyses)")).fetchall()
            ai_cols = {row[1] for row in ai_result}
            if ai_cols:
                if "deadline_date" not in ai_cols:
                    conn.execute(text("ALTER TABLE ai_analyses ADD COLUMN deadline_date VARCHAR(50)"))
                if "deadline_status" not in ai_cols:
                    conn.execute(text("ALTER TABLE ai_analyses ADD COLUMN deadline_status VARCHAR(20)"))
                if "reply_expected" not in ai_cols:
                    conn.execute(text("ALTER TABLE ai_analyses ADD COLUMN reply_expected BOOLEAN DEFAULT 0"))
                if "reply_reason" not in ai_cols:
                    conn.execute(text("ALTER TABLE ai_analyses ADD COLUMN reply_reason TEXT"))
                if "suggested_reply" not in ai_cols:
                    conn.execute(text("ALTER TABLE ai_analyses ADD COLUMN suggested_reply TEXT"))

            # 4. Seed registered users (User 1 and User 2)
            users_count = conn.execute(text("SELECT count(*) FROM users")).scalar()
            if users_count == 0:
                conn.execute(text(
                    "INSERT INTO users (id, email, name, role, provider_type, created_at) VALUES "
                    "(1, 'mock.faculty@university.edu', 'Dr. Faculty (Mock / Demo)', 'Professor & Academic Incharge', 'mock', datetime('now')), "
                    "(2, 'shivaprakashp.cs24@bitsathy.ac.in', 'Shivaprakash P (College Account)', 'Faculty / Student Researcher', 'gmail', datetime('now'))"
                ))
            else:
                u1 = conn.execute(text("SELECT id FROM users WHERE id = 1")).fetchone()
                if not u1:
                    conn.execute(text(
                        "INSERT INTO users (id, email, name, role, provider_type, created_at) "
                        "VALUES (1, 'mock.faculty@university.edu', 'Dr. Faculty (Mock / Demo)', 'Professor & Academic Incharge', 'mock', datetime('now'))"
                    ))
                u2 = conn.execute(text("SELECT id FROM users WHERE id = 2 OR email = 'shivaprakashp.cs24@bitsathy.ac.in'")).fetchone()
                if not u2:
                    conn.execute(text(
                        "INSERT INTO users (id, email, name, role, provider_type, created_at) "
                        "VALUES (2, 'shivaprakashp.cs24@bitsathy.ac.in', 'Shivaprakash P (College Account)', 'Faculty / Student Researcher', 'gmail', datetime('now'))"
                    ))

            # 5. Backfill existing mock emails with user_id = 1 (Zero data loss)
            conn.execute(text("UPDATE emails SET user_id = 1 WHERE user_id IS NULL"))

            # 6. Backfill existing preferences with user_id = 1
            conn.execute(text("UPDATE faculty_preferences SET user_id = 1 WHERE user_id IS NULL AND id = 1"))

            # Ensure default preference for User 2 exists
            u2_pref = conn.execute(text("SELECT id FROM faculty_preferences WHERE user_id = 2")).fetchone()
            if not u2_pref:
                conn.execute(text(
                    "INSERT INTO faculty_preferences (user_id, faculty_name, role, department, priority_mode, high_priority_categories, custom_keywords_high, custom_keywords_low, deadline_urgency_days, authority_weight, deadline_weight, updated_at) "
                    "VALUES (2, 'Shivaprakash P', 'Faculty / Student Researcher', 'Computer Science & Engineering', 'BALANCED', 'Examination,Academic', 'marks,question paper,naac,accreditation,urgent', 'newsletter,invitation,webinar,sports', 3, 1.0, 1.0, datetime('now'))"
                ))

            conn.commit()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Non-destructive migration warning: {e}")

def reset_db():
    """Drop and recreate all database tables."""
    from backend.app.models import User, Email, AIAnalysis, ActionItem, Meeting, Evidence, Entity, FacultyPreference  # noqa: F401
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    init_db()

