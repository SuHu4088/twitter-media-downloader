import { request } from './request'

export interface TwitterAccount {
  id: number
  username: string
  display_name: string
  avatar_url: string
  description: string
  followers_count: number
  following_count: number
  tweets_count: number
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface OAuthUrlResponse {
  oauth_url: string
  oauth_token: string
}

export interface OAuthCallbackParams {
  oauth_token: string
  oauth_verifier: string
}

export interface AccountListParams {
  page?: number
  page_size?: number
  is_active?: boolean
  keyword?: string
}

export interface AccountListResponse {
  items: TwitterAccount[]
  total: number
  page: number
  page_size: number
}

export const twitterApi = {
  getOAuthUrl(): Promise<OAuthUrlResponse> {
    return request.get('/twitter/oauth/url')
  },

  oauthCallback(params: OAuthCallbackParams): Promise<TwitterAccount> {
    return request.post('/twitter/oauth/callback', params)
  },

  getAccounts(params: AccountListParams): Promise<AccountListResponse> {
    return request.get('/twitter/accounts', { params })
  },

  getAccount(id: number): Promise<TwitterAccount> {
    return request.get(`/twitter/accounts/${id}`)
  },

  updateAccount(id: number, data: Partial<TwitterAccount>): Promise<TwitterAccount> {
    return request.put(`/twitter/accounts/${id}`, data)
  },

  deleteAccount(id: number): Promise<void> {
    return request.delete(`/twitter/accounts/${id}`)
  },

  toggleAccountActive(id: number): Promise<TwitterAccount> {
    return request.post(`/twitter/accounts/${id}/toggle`)
  },

  syncAccount(id: number): Promise<void> {
    return request.post(`/twitter/accounts/${id}/sync`)
  }
}
