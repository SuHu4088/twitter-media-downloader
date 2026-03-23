import { request } from './request'

export interface Media {
  id: number
  tweet_id: string
  media_type: 'image' | 'video' | 'gif'
  media_url: string
  local_path: string
  file_size: number
  width: number
  height: number
  duration?: number
  account_id: number
  account_name: string
  created_at: string
  downloaded_at?: string
}

export interface MediaListParams {
  page?: number
  page_size?: number
  media_type?: 'image' | 'video' | 'gif'
  account_id?: number
  start_date?: string
  end_date?: string
  keyword?: string
}

export interface MediaListResponse {
  items: Media[]
  total: number
  page: number
  page_size: number
}

export interface MediaStats {
  total_count: number
  total_size: number
  image_count: number
  video_count: number
  gif_count: number
}

export const mediaApi = {
  getMediaList(params: MediaListParams): Promise<MediaListResponse> {
    return request.get('/media', { params })
  },

  getMedia(id: number): Promise<Media> {
    return request.get(`/media/${id}`)
  },

  getMediaStats(): Promise<MediaStats> {
    return request.get('/media/stats')
  },

  deleteMedia(id: number): Promise<void> {
    return request.delete(`/media/${id}`)
  },

  batchDeleteMedia(ids: number[]): Promise<void> {
    return request.post('/media/batch-delete', { ids })
  },

  downloadMedia(id: number): Promise<{ download_url: string }> {
    return request.post(`/media/${id}/download`)
  }
}
