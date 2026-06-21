export interface User {
  id: string;
  email: string;
  displayName: string;
}

export interface Organization {
  id: string;
  name: string;
  slug: string;
  type: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: {
    id: string;
    email: string;
    display_name: string;
  };
  organization: {
    id: string;
    name: string;
    slug: string;
    type: string;
  } | null;
}

export interface Project {
  id: string;
  organization_id: string;
  name: string;
  description: string | null;
  created_by: string;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface ProjectListResponse {
  items: Project[];
}

export interface Document {
  id: string;
  organization_id: string;
  project_id: string;
  name: string;
  current_version_id: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface DocumentListResponse {
  items: Document[];
}

export interface DocumentVersion {
  id: string;
  organization_id: string;
  document_id: string;
  version_number: number;
  blob_path: string;
  source_filename: string;
  mime_type: string;
  size_bytes: number;
  sha256: string;
  etag: string;
  storage_provider: string;
  status: 'pending_upload' | 'uploaded' | 'processing' | 'indexed' | 'failed' | 'deleted';
  created_at: string;
  updated_at: string;
}

export interface Citation {
  chunk_id: string;
  document_version_id: string;
  chunk_number: number;
  score: number;
  page_start: number | null;
  page_end: number | null;
  quote: string | null;
  citation_number?: number;
  document_id?: string | null;
  document_name?: string | null;
  source_filename?: string | null;
}

export interface MessageMetadata {
  citations?: Citation[];
  usage?: LlmUsage;
  [key: string]: unknown;
}

export type MessageStatus = 'STREAMING' | 'COMPLETE' | 'INTERRUPTED' | 'FAILED';
export type MessageRole = 'user' | 'assistant' | 'system';

export interface Message {
  id: string;
  conversation_id: string;
  role: MessageRole;
  content: string;
  metadata: MessageMetadata;
  status: MessageStatus;
  sequence_number: number;
  created_at: string;
}

export interface Conversation {
  id: string;
  organization_id: string;
  project_id: string;
  title: string;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface ConversationListResponse {
  items: Conversation[];
}

export interface LlmUsage {
  id: string;
  organization_id: string;
  conversation_id: string;
  message_id: string;
  provider: string;
  model: string;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  latency_ms: number;
  cost: number;
  created_at: string;
}

export interface ApiErrorDetail {
  type: string;
  title: string;
  status: number;
  detail: string;
  error_code: string;
}
