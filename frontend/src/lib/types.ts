export interface User {
  id: number;
  username: string;
  email: string;
  is_admin: boolean;
}

export interface AdminUser extends User {
  is_active: boolean;
  created_at: string;
}

export interface AppConfig {
  gmail_draft_enabled: boolean;
}

export interface LoginChallenge {
  challenge_id: string;
  masked_email: string;
  expires_in_seconds: number;
  development_code?: string | null;
}

export interface Patient {
  row_number: number;
  nombrePaciente: string;
  ciPaciente: string;
  doctor: string;
  recipientEmail?: string | null;
}

export interface ReportForm {
  recordData: string;
  ciPaciente: string;
  nombrePaciente: string;
  doctor_gender: 'Dr.' | 'Dra.';
  doctor: string;
  fecha: string;
  measures: string;
  texto: string;
  driveUrl: string;
  recipientEmail: string;
  createGmailDraft: boolean;
  approved: boolean;
}

export interface PublishResult {
  document_id: string;
  document_url: string;
  pdf_id: string;
  pdf_url: string;
  gmail_draft_id?: string | null;
}
