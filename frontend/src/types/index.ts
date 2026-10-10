// Shared TypeScript Interfaces for Faculty Email Intelligence Platform

export type PriorityLevel = 'HIGH' | 'MEDIUM' | 'LOW';

export type AcademicCategory =
  | 'Academic'
  | 'Administrative'
  | 'Examination'
  | 'Meeting'
  | 'Student'
  | 'Department'
  | 'Event'
  | 'Research'
  | 'Placement'
  | 'General';

export type RelationshipType =
  | 'DUE_ON'
  | 'PREPARE_BEFORE'
  | 'ATTEND_BY'
  | 'COMMUNICATE_BY'
  | 'STANDALONE';

export type ValidationStatus =
  | 'VERIFIED'
  | 'INFERRED'
  | 'PARTIAL'
  | 'UNSUPPORTED';

export interface Email {
  id: number;
  sender: string;
  recipient: string;
  subject: string;
  body: string;
  received_at: string;
  is_read: boolean;
  created_at: string;
}

export interface EmailSummary {
  id: number;
  sender: string;
  recipient: string;
  subject: string;
  body_preview: string;
  received_at: string;
  is_read: boolean;
  created_at: string;
  has_analysis: boolean;
  category: AcademicCategory | null;
  priority: PriorityLevel | null;
  priority_reason: string | null;
  action_items_count: number;
  meetings_count: number;
  has_deadline: boolean;
}

export interface Evidence {
  id: number;
  analysis_id: number;
  field_name: string;
  extracted_value: string;
  source_text: string;
  confidence: number;
  validation_status: ValidationStatus;
  char_start?: number | null;
  char_end?: number | null;
  grounding_method?: string | null;
}

export interface AIAnalysis {
  id: number;
  email_id: number;
  summary: string;
  category: AcademicCategory;
  priority: PriorityLevel;
  priority_reason: string;
  processed_at: string;
  evidences?: Evidence[];
  deadline_date?: string | null;
  deadline_status?: 'UPCOMING' | 'DUE_TODAY' | 'EXPIRED' | null;
  reply_expected?: boolean;
  reply_reason?: string | null;
  suggested_reply?: string | null;
}

export interface ActionItem {
  id: number;
  email_id: number;
  email_subject?: string | null;
  email_sender?: string | null;
  description: string;
  due_date: string | null;
  priority: PriorityLevel;
  completed: boolean;
  relationship_type: RelationshipType | string;
  target_event?: string | null;
  relationship_reason?: string | null;
  binding_confidence?: number | null;
}

export interface Meeting {
  id: number;
  email_id: number;
  email_subject?: string | null;
  email_sender?: string | null;
  title: string;
  meeting_date: string | null;
  meeting_time: string | null;
  location: string | null;
  preparation: string | null;
}

export interface Entity {
  id: number;
  email_id: number;
  entity_type: string;
  entity_value: string;
}

export interface EmailDetail extends Email {
  analysis?: AIAnalysis | null;
  action_items: ActionItem[];
  meetings: Meeting[];
  entities: Entity[];
}

export interface DashboardMetrics {
  total_emails: number;
  unread_emails: number;
  high_priority_count: number;
  medium_priority_count?: number;
  low_priority_count?: number;
  upcoming_deadlines_count: number;
  expired_deadlines_count?: number;
  upcoming_meetings_count: number;
  pending_actions_count: number;
}

export interface DeadlineItem {
  id: number;
  email_id: number;
  email_subject: string;
  email_sender: string;
  task_description: string;
  due_date: string;
  priority: PriorityLevel;
  completed: boolean;
  relationship_type: string;
  target_event?: string | null;
  relationship_reason?: string | null;
  deadline_status?: 'UPCOMING' | 'DUE_TODAY' | 'EXPIRED' | string | null;
  relative_status?: string | null;
}

export interface DashboardData {
  metrics: DashboardMetrics;
  priority_emails: EmailSummary[];
  upcoming_deadlines: DeadlineItem[];
  expired_deadlines?: DeadlineItem[];
  upcoming_meetings: Meeting[];
  pending_tasks: ActionItem[];
  recent_emails: EmailSummary[];
}

export interface CategoryCount {
  category: string;
  count: number;
}

export interface AnalysisResponse {
  status: string;
  message: string;
  steps: string[];
  analysis: AIAnalysis;
}

export interface AssertionVerification {
  is_valid: boolean;
  validation_status: ValidationStatus;
  confidence: number;
  grounded_sentence?: string | null;
  char_start?: number | null;
  char_end?: number | null;
  grounding_method: string;
  audit_explanation: string;
}

export interface EmailProviderStatus {
  configured_provider: string;
  active_provider: string;
  is_authenticated: boolean;
  available_providers: string[];
  fallback_active: boolean;
  gmail_configured: boolean;
  gmail_authenticated: boolean;
  gmail_oauth?: GmailOAuthStatus;
}

export interface GmailOAuthStatus {
  connected: boolean;
  email: string | null;
  provider: string;
  scope: string;
  configured: boolean;
  college_account: string;
}

export interface EmailSyncResult {
  success: boolean;
  message: string;
  data: {
    status: string;
    provider: string;
    fetched: number;
    imported: number;
    skipped: number;
    fallback_active: boolean;
  };
}

export interface RelatedEmail {
  id: number;
  subject: string;
  sender: string;
  recipient: string;
  received_at: string | null;
  category: AcademicCategory | string | null;
  priority: PriorityLevel | string;
  relationship_type: string;
  relevance_score: number;
  relationship_reasons: string[];
  actions_count: number;
  has_meeting: boolean;
}

export interface TimelineItem {
  type: 'EMAIL_RECEIVED' | 'MEETING' | 'DEADLINE';
  date: string;
  time: string;
  title: string;
  source_email_id: number;
  is_current: boolean;
  details: string;
}

export interface CrossEmailAction {
  id: number;
  email_id: number;
  email_subject: string;
  description: string;
  due_date: string | null;
  priority: PriorityLevel | string;
  completed: boolean;
  relationship_type: string;
  is_from_current_email: boolean;
}

export interface CrossEmailIntelligence {
  email_id: number;
  thread_count: number;
  related_emails: RelatedEmail[];
  timeline: TimelineItem[];
  cross_actions: CrossEmailAction[];
  insights: string[];
}

export interface TopicCluster {
  cluster_id: number;
  topic_title: string;
  normalized_topic: string;
  category: AcademicCategory | string;
  highest_priority: PriorityLevel | string;
  email_count: number;
  emails: {
    id: number;
    subject: string;
    sender: string;
    received_at: string | null;
    is_read: boolean;
  }[];
  participants: string[];
  total_action_items: number;
  pending_action_items: number;
  meetings_count: number;
  latest_received_at: string | null;
}

export interface FacultyPreference {
  id: number;
  faculty_name: string;
  role: string;
  department: string;
  priority_mode: string;
  high_priority_categories: string;
  custom_keywords_high: string;
  custom_keywords_low: string;
  deadline_urgency_days: number;
  authority_weight: number;
  deadline_weight: number;
  updated_at: string;
}

export interface FacultyPreferenceUpdate {
  faculty_name?: string;
  role?: string;
  department?: string;
  priority_mode?: string;
  high_priority_categories?: string;
  custom_keywords_high?: string;
  custom_keywords_low?: string;
  deadline_urgency_days?: number;
  authority_weight?: number;
  deadline_weight?: number;
}
