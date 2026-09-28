import { api } from './client'

export interface Connector {
  id: string; tenant_id: string; name: string; type: 'rest' | 'file' | 'webhook';
  base_url: string | null; auth_type: string; status: string; config: Record<string, unknown>
}
export interface Mapping {
  id?: string; source_field: string; target_field: string; transform: Record<string, unknown>; required: boolean
}
export interface Shipment {
  id: string; shipment_no: string; status: string; origin: string | null; destination: string | null;
  planned_departure_time: string | null; planned_arrival_time: string | null; driver_id: string | null;
  vehicle_id: string | null; raw_data: Record<string, unknown>; created_at: string
}
export interface LogisticsException {
  id: string; shipment_id: string; type: string; level: string; status: string; reason: string;
  ai_analysis: string | null; suggestion: string | null; detected_at: string
}
export interface Page<T> { total: number; items: T[] }
export interface ImportResult { imported: number; updated: number; rejected: number; errors: string[] }

export const platform = {
  connectors: async () => (await api.get<Connector[]>('/connectors')).data,
  connector: async (id: string) => (await api.get<Connector>(`/connectors/${id}`)).data,
  createConnector: async (payload: Record<string, unknown>) => (await api.post<Connector>('/connectors', payload)).data,
  deleteConnector: async (id: string) => api.delete(`/connectors/${id}`),
  testConnector: async (id: string) => (await api.post(`/connectors/${id}/test`)).data,
  sampleConnector: async (id: string) => (await api.post<{fields: string[]; rows: Record<string, unknown>[]}>(`/connectors/${id}/sample`)).data,
  syncConnector: async (id: string) => (await api.post<ImportResult>(`/connectors/${id}/sync`)).data,
  fileSample: async (id: string, file: File) => { const body = new FormData(); body.append('file', file); return (await api.post<{fields: string[]; rows: Record<string, unknown>[]}>(`/connectors/${id}/file-sample`, body)).data },
  uploadConnector: async (id: string, file: File) => { const body = new FormData(); body.append('file', file); return (await api.post<ImportResult>(`/connectors/${id}/upload`, body)).data },
  importJson: async (id: string, rows: Record<string, unknown>[]) => (await api.post<ImportResult>(`/connectors/${id}/import`, rows)).data,
  mappings: async (id: string) => (await api.get<Mapping[]>(`/connectors/${id}/mappings`)).data,
  saveMappings: async (id: string, mappings: Mapping[]) => (await api.put<Mapping[]>(`/connectors/${id}/mappings`, { mappings })).data,
  shipments: async (params: Record<string, string | number> = {}) => (await api.get<Page<Shipment>>('/shipments', { params })).data,
  shipment: async (id: string) => (await api.get<Shipment & { tracking_events: Record<string, unknown>[]; exceptions: LogisticsException[]; driver: Record<string, unknown> | null; vehicle: Record<string, unknown> | null; route: Record<string, unknown> | null }>(`/shipments/${id}`)).data,
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
}
