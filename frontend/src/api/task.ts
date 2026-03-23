import { request } from './request'

export type TaskStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
export type TaskType = 'sync_tweets' | 'download_media' | 'export_data' | 'cleanup'

export interface Task {
  id: number
  task_type: TaskType
  status: TaskStatus
  progress: number
  total: number
  error_message?: string
  account_id?: number
  account_name?: string
  created_at: string
  started_at?: string
  completed_at?: string
}

export interface TaskListParams {
  page?: number
  page_size?: number
  status?: TaskStatus
  task_type?: TaskType
  account_id?: number
}

export interface TaskListResponse {
  items: Task[]
  total: number
  page: number
  page_size: number
}

export interface TaskStats {
  pending_count: number
  running_count: number
  completed_count: number
  failed_count: number
}

export const taskApi = {
  getTasks(params: TaskListParams): Promise<TaskListResponse> {
    return request.get('/tasks', { params })
  },

  getTask(id: number): Promise<Task> {
    return request.get(`/tasks/${id}`)
  },

  getTaskStats(): Promise<TaskStats> {
    return request.get('/tasks/stats')
  },

  cancelTask(id: number): Promise<Task> {
    return request.post(`/tasks/${id}/cancel`)
  },

  retryTask(id: number): Promise<Task> {
    return request.post(`/tasks/${id}/retry`)
  },

  createSyncTask(accountId: number): Promise<Task> {
    return request.post('/tasks/sync', { account_id: accountId })
  },

  createDownloadTask(params: { account_id?: number; media_type?: string }): Promise<Task> {
    return request.post('/tasks/download', params)
  }
}
