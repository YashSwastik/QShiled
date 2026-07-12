/**
 * projectsApi.ts — typed API functions for Organizations, Projects, Applications.
 */
import api from './api';

// ── Types ─────────────────────────────────────────────────────────────────────

export type ProjectStatus = 'active' | 'archived' | 'completed';
export type BusinessCriticality = 'critical' | 'high' | 'medium' | 'low';
export type Environment = 'production' | 'staging' | 'development' | 'research';
export type DataSensitivity = 'top_secret' | 'restricted' | 'internal' | 'public';
export type ConfidentialityRequirement = 'long_term' | 'medium_term' | 'short_term';

export interface Organization {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface Project {
  id: string;
  organization_id: string;
  name: string;
  description: string | null;
  status: ProjectStatus;
  created_at: string;
  updated_at: string;
}

export interface Application {
  id: string;
  project_id: string;
  name: string;
  description: string | null;
  tech_stack: string | null;
  business_criticality: BusinessCriticality;
  environment: Environment;
  internet_exposed: boolean;
  data_sensitivity: DataSensitivity;
  confidentiality_requirement: ConfidentialityRequirement;
  data_lifetime_years: number;
  owner_team: string | null;
  created_at: string;
  updated_at: string;
}

export interface PagedResponse<T> {
  total: number;
  items: T[];
}

// ── Organization API ──────────────────────────────────────────────────────────

export async function createOrganization(data: {
  name: string;
  slug: string;
  description?: string;
}): Promise<Organization> {
  const res = await api.post<Organization>('/api/organizations', data);
  return res.data;
}

export async function listOrganizations(): Promise<Organization[]> {
  const res = await api.get<Organization[]>('/api/organizations');
  return res.data;
}

// ── Project API ───────────────────────────────────────────────────────────────

export async function createProject(data: {
  organization_id: string;
  name: string;
  description?: string;
  status?: ProjectStatus;
}): Promise<Project> {
  const res = await api.post<Project>('/api/projects', data);
  return res.data;
}

export async function listProjects(params?: {
  organization_id?: string;
  page?: number;
  page_size?: number;
}): Promise<PagedResponse<Project>> {
  const res = await api.get<PagedResponse<Project>>('/api/projects', { params });
  return res.data;
}

export async function getProject(id: string): Promise<Project> {
  const res = await api.get<Project>(`/api/projects/${id}`);
  return res.data;
}

// ── Application API ───────────────────────────────────────────────────────────

export interface ApplicationCreate {
  project_id: string;
  name: string;
  description?: string;
  tech_stack?: string;
  business_criticality?: BusinessCriticality;
  environment?: Environment;
  internet_exposed?: boolean;
  data_sensitivity?: DataSensitivity;
  confidentiality_requirement?: ConfidentialityRequirement;
  data_lifetime_years?: number;
  owner_team?: string;
}

export async function createApplication(data: ApplicationCreate): Promise<Application> {
  const res = await api.post<Application>('/api/applications', data);
  return res.data;
}

export async function listApplications(params?: {
  project_id?: string;
  page?: number;
  page_size?: number;
}): Promise<PagedResponse<Application>> {
  const res = await api.get<PagedResponse<Application>>('/api/applications', { params });
  return res.data;
}

export async function getApplication(id: string): Promise<Application> {
  const res = await api.get<Application>(`/api/applications/${id}`);
  return res.data;
}

export async function updateApplication(
  id: string,
  data: Partial<Omit<ApplicationCreate, 'project_id'>>
): Promise<Application> {
  const res = await api.patch<Application>(`/api/applications/${id}`, data);
  return res.data;
}

// ── Health ────────────────────────────────────────────────────────────────────

export async function checkHealth(): Promise<{ status: string; version: string }> {
  const res = await api.get('/api/v1/health');
  return res.data;
}
