import axios from 'axios'

export function errorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string') return detail
    if (error.response?.status) return `请求失败（${error.response.status}）`
  }
  return error instanceof Error ? error.message : '操作失败'
}
