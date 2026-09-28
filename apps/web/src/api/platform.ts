import { api } from './client'

export interface Connector {
  id: string; tenant_id: string; name: string; type: 'rest' | 'file' | 'webhook';
  base_url: string | null; auth_type: string; status: string; config: Record<string, unknown>
  credential_configured: boolean
  capabilities: {read: string[]; write: string[]}
}
export interface Mapping {
  id?: string; source_field: string; target_field: string; transform: Record<string, unknown>; required: boolean
}
export interface MappingField { name: string; label: string; type: string; required: boolean; options: string[] }
export interface MappingPreview { source: Record<string, unknown>; transformed: Record<string, unknown>; validation: {field: string; level: 'success' | 'warning' | 'error'; message: string}[] }
export interface SourceField { path: string; type: string; nullable: boolean; sample_value: unknown }
export interface SampleData { fields: string[]; field_details: SourceField[]; rows: Record<string, unknown>[] }
export interface TrackingMapping { id?: string; source_field: string; target_entity?: string; fields: Mapping[] }
export interface Shipment {
  id: string; shipment_no: string; status: string; origin: string | null; destination: string | null;
  planned_departure_time: string | null; planned_arrival_time: string | null; driver_id: string | null;
  vehicle_id: string | null; raw_data: Record<string, unknown>; created_at: string;
  source_connector_id: string | null; source_external_id: string | null; source_updated_at: string | null; last_synced_at: string | null
}
export interface LogisticsException {
  id: string; shipment_id: string; type: string; level: string; status: string; reason: string;
  ai_analysis: string | null; suggestion: string | null; detected_at: string
}
export interface Page<T> { total: number; items: T[] }
export interface ImportResult { imported: number; updated: number; rejected: number; total: number; success: number; failed: number; drivers_created: number; vehicles_created: number; routes_created: number; tracking_events_created: number; warnings: string[]; errors: string[] }
export interface SyncJob { id: string; connector_id: string; status: string; created_at: string; started_at: string | null; finished_at: string | null; total_count: number; success_count: number; failed_count: number; result: Partial<ImportResult>; error_message: string | null }
export interface SyncIssue { id: string; job_id: string; row_number: number | null; entity: string; external_id: string | null; level: string; code: string; message: string; created_at: string }

export const platform = {
  connectors: async () => (await api.get<Connector[]>('/connectors')).data,
  connector: async (id: string) => (await api.get<Connector>(`/connectors/${id}`)).data,
  createConnector: async (payload: Record<string, unknown>) => (await api.post<Connector>('/connectors', payload)).data,
  deleteConnector: async (id: string) => api.delete(`/connectors/${id}`),
  testConnector: async (id: string) => (await api.post<{ok: boolean; success: boolean; status_code: number; latency_ms: number; content_type: string}>(`/connectors/${id}/test`)).data,
  sampleConnector: async (id: string) => (await api.post<SampleData>(`/connectors/${id}/sample`)).data,
  syncConnector: async (id: string) => (await api.post<ImportResult>(`/connectors/${id}/sync`)).data,
  startSyncJob: async (id: string) => (await api.post<SyncJob>(`/connectors/${id}/sync-jobs`)).data,
  syncJobs: async (id: string) => (await api.get<SyncJob[]>(`/connectors/${id}/sync-jobs`)).data,
  syncJob: async (id: string, jobId: string) => (await api.get<SyncJob>(`/connectors/${id}/sync-jobs/${jobId}`)).data,
  syncIssues: async (id: string, jobId: string) => (await api.get<SyncIssue[]>(`/connectors/${id}/sync-jobs/${jobId}/issues`)).data,
  fileSample: async (id: string, file: File) => { const body = new FormData(); body.append('file', file); return (await api.post<SampleData>(`/connectors/${id}/file-sample`, body)).data },
  uploadConnector: async (id: string, file: File) => { const body = new FormData(); body.append('file', file); return (await api.post<ImportResult>(`/connectors/${id}/upload`, body)).data },
  importJson: async (id: string, rows: Record<string, unknown>[]) => (await api.post<ImportResult>(`/connectors/${id}/import`, rows)).data,
  mappings: async (id: string) => (await api.get<Mapping[]>(`/connectors/${id}/mappings`)).data,
  mappingFields: async () => (await api.get<MappingField[]>('/mapping/fields/shipment')).data,
  suggestMappings: async (fields: string[]) => (await api.post<{source_field: string; target_field: string; confidence: number}[]>('/mapping/suggestions', fields)).data,
  previewMapping: async (id: string, sample: Record<string, unknown>, mappings: Mapping[]) => (await api.post<MappingPreview>(`/connectors/${id}/mapping/preview`, { sample, mappings })).data,
  saveMappings: async (id: string, mappings: Mapping[]) => (await api.put<Mapping[]>(`/connectors/${id}/mappings`, { mappings })).data,
  trackingMapping: async (id: string) => (await api.get<TrackingMapping | null>(`/connectors/${id}/tracking-mapping`)).data,
  saveTrackingMapping: async (id: string, mapping: TrackingMapping) => (await api.put<TrackingMapping>(`/connectors/${id}/tracking-mapping`, mapping)).data,
  shipments: async (params: Record<string, string | number> = {}) => (await api.get<Page<Shipment>>('/shipments', { params })).data,
  shipment: async (id: string) => (await api.get<Shipment & { tracking_events: Record<string, unknown>[]; exceptions: LogisticsException[]; driver: Record<string, unknown> | null; vehicle: Record<string, unknown> | null; route: Record<string, unknown> | null; source_connector: {id: string; name: string} | null }>(`/shipments/${id}`)).data,
  exceptions: async (params: Record<string, string | number> = {}) => (await api.get<Page<LogisticsException>>('/exceptions', { params })).data,
  exception: async (id: string) => (await api.get<LogisticsException>(`/exceptions/${id}`)).data,
  resolveException: async (id: string) => (await api.post<LogisticsException>(`/exceptions/${id}/resolve`)).data,
  analyzeException: async (id: string) => (await api.post<LogisticsException>(`/exceptions/${id}/analyze`)).data,
  overview: async () => (await api.get<{shipments_today: number; in_transit: number; exception_count: number; high_risk_count: number; type_distribution: {type: string; count: number}[]; recent_exceptions: LogisticsException[]}>('/dashboard/overview')).data,
  trend: async () => (await api.get<{date: string; count: number}[]>('/dashboard/exception-trend')).data,
  routeRanking: async () => (await api.get<{route_id: string; route_name: string; exception_count: number}[]>('/dashboard/route-ranking')).data,
  summary: async () => (await api.get<{summary: string; provider: string}>('/dashboard/ai-summary')).data,
  chat: async (message: string, conversation_id?: string) => (await api.post<{conversation_id: string; answer: string; provider: string; grounding: Record<string, unknown>}>('/ai/chat', { message, conversation_id })).data,
  conversations: async () => (await api.get<{id: string; title: string}[]>('/ai/conversations')).data,
  conversation: async (id: string) => (await api.get<{id: string; title: string; messages: {role: string; content: string; provider: string | null}[]}>(`/ai/conversations/${id}`)).data,
  knowledge: async () => (await api.get<{id: string; title: string; source_type: string; metadata: Record<string, unknown>}[]>('/knowledge')).data,
  addKnowledgeText: async (title: string, content: string) => (await api.post('/knowledge/text', { title, content })).data,
  uploadKnowledge: async (file: File) => { const body = new FormData(); body.append('file', file); return (await api.post('/knowledge/upload', body)).data },
  deleteKnowledge: async (id: string) => api.delete(`/knowledge/${id}`),
  aiUsageDashboard: async () => (await api.get<AIUsageDashboard>('/ai/usage/dashboard')).data,
  aiUsageLogs: async (params: Record<string, string | number> = {}) => (await api.get<Page<AIUsageLog>>('/ai/usage/logs', { params })).data,
}

export interface AIUsageLog {
  id: string
  purpose: string
  entity_id: string | null
  provider: string
  model: string | null
  input_tokens: number
  output_tokens: number
  cost: number
  created_at: string
}

export interface AIUsageDashboard {
  summary: {
    total_calls: number
    total_input_tokens: number
    total_output_tokens: number
    total_tokens: number
    total_cost: number
    today_calls: number
    today_input_tokens: number
    today_output_tokens: number
    today_tokens: number
    today_cost: number
  }
  trend: {
    date: string
    calls: number
    tokens: number
    cost: number
  }[]
  distribution_by_purpose: {
    purpose: string
    calls: number
    tokens: number
  }[]
  distribution_by_model: {
    model: string
    calls: number
    tokens: number
  }[]
  models_info: {
    primary: {
      provider: string
      model: string
      base_url: string
      configured: boolean
    }
    fallback: {
      provider: string
      model: string
      base_url: string
      configured: boolean
    }
  }
  recent_logs: AIUsageLog[]
}
