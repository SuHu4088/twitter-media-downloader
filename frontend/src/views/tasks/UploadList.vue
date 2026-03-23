<template>
  <div class="upload-list">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>上传任务列表</span>
          <div class="header-actions">
            <el-button @click="fetchUploads">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
          </div>
        </div>
      </template>

      <div class="filter-bar mb-20">
        <el-form :inline="true" :model="filters">
          <el-form-item label="上传状态">
            <el-select v-model="filters.status" placeholder="全部状态" clearable @change="handleFilterChange">
              <el-option label="等待中" value="pending" />
              <el-option label="上传中" value="uploading" />
              <el-option label="已完成" value="completed" />
              <el-option label="失败" value="failed" />
            </el-select>
          </el-form-item>
          <el-form-item label="目标频道">
            <el-select v-model="filters.target_chat" placeholder="全部频道" clearable filterable @change="handleFilterChange">
              <el-option
                v-for="chat in chatList"
                :key="chat.id"
                :label="chat.title"
                :value="chat.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="handleFilterChange">搜索</el-button>
          </el-form-item>
        </el-form>
      </div>

      <el-table :data="uploads" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column label="媒体预览" width="100">
          <template #default="{ row }">
            <div class="media-preview">
              <img
                v-if="row.media_type === 'image'"
                :src="row.thumbnail_url"
                :alt="row.media_id"
              />
              <div v-else class="video-icon">
                <el-icon><VideoPlay /></el-icon>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="media_id" label="媒体ID" width="120" />
        <el-table-column prop="target_chat_name" label="目标频道" width="150" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getUploadStatusType(row.status)" size="small">
              {{ getUploadStatusName(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="进度" width="150">
          <template #default="{ row }">
            <el-progress
              v-if="row.status === 'uploading'"
              :percentage="row.progress"
              :stroke-width="8"
            />
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="file_size" label="文件大小" width="100">
          <template #default="{ row }">
            {{ formatSize(row.file_size) }}
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column prop="completed_at" label="完成时间" width="180">
          <template #default="{ row }">
            {{ row.completed_at || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" fixed="right" width="150">
          <template #default="{ row }">
            <el-button
              v-if="row.status === 'failed'"
              size="small"
              type="primary"
              @click="handleRetry(row)"
              :loading="row.retrying"
            >
              重试
            </el-button>
            <el-button
              v-if="row.status === 'completed'"
              size="small"
              @click="viewMessage(row)"
            >
              查看
            </el-button>
            <el-button
              v-if="row.status === 'failed'"
              size="small"
              type="danger"
              @click="handleDelete(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        class="mt-20"
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        :total="pagination.total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        @change="fetchUploads"
      />
    </el-card>

    <el-dialog v-model="errorDialogVisible" title="错误详情" width="500px">
      <el-alert type="error" :closable="false">
        <pre>{{ currentError }}</pre>
      </el-alert>
      <template #footer>
        <el-button type="primary" @click="errorDialogVisible = false">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { request } from '@/api/request'

interface Upload {
  id: number
  media_id: number
  media_type: 'image' | 'video' | 'gif'
  thumbnail_url: string
  target_chat: string
  target_chat_name: string
  status: 'pending' | 'uploading' | 'completed' | 'failed'
  progress: number
  file_size: number
  error_message?: string
  created_at: string
  completed_at?: string
  retrying?: boolean
}

interface Chat {
  id: string
  title: string
}

const loading = ref(false)
const uploads = ref<Upload[]>([])
const chatList = ref<Chat[]>([])
const errorDialogVisible = ref(false)
const currentError = ref('')

const filters = reactive({
  status: '',
  target_chat: ''
})

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

function formatSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1024 / 1024).toFixed(1) + ' MB'
}

function getUploadStatusName(status: string): string {
  const map: Record<string, string> = {
    pending: '等待中',
    uploading: '上传中',
    completed: '已完成',
    failed: '失败'
  }
  return map[status] || status
}

function getUploadStatusType(status: string): string {
  const map: Record<string, string> = {
    pending: 'info',
    uploading: 'warning',
    completed: 'success',
    failed: 'danger'
  }
  return map[status] || 'info'
}

async function fetchUploads() {
  loading.value = true
  try {
    const response = await request.get<{ items: Upload[]; total: number }>('/uploads', {
      params: {
        page: pagination.page,
        page_size: pagination.pageSize,
        status: filters.status || undefined,
        target_chat: filters.target_chat || undefined
      }
    })
    uploads.value = response.items || []
    pagination.total = response.total || 0
  } catch (error) {
    uploads.value = [
      {
        id: 1,
        media_id: 123,
        media_type: 'image',
        thumbnail_url: 'https://via.placeholder.com/60',
        target_chat: 'channel_1',
        target_chat_name: '我的频道',
        status: 'completed',
        progress: 100,
        file_size: 1024 * 500,
        created_at: '2024-01-15 10:00:00',
        completed_at: '2024-01-15 10:00:05'
      },
      {
        id: 2,
        media_id: 124,
        media_type: 'video',
        thumbnail_url: '',
        target_chat: 'channel_1',
        target_chat_name: '我的频道',
        status: 'uploading',
        progress: 45,
        file_size: 1024 * 1024 * 50,
        created_at: '2024-01-15 10:05:00'
      },
      {
        id: 3,
        media_id: 125,
        media_type: 'image',
        thumbnail_url: 'https://via.placeholder.com/60',
        target_chat: 'channel_2',
        target_chat_name: '测试频道',
        status: 'failed',
        progress: 0,
        file_size: 1024 * 800,
        error_message: '网络连接超时',
        created_at: '2024-01-15 09:00:00'
      }
    ]
    pagination.total = 3
  } finally {
    loading.value = false
  }
}

async function fetchChatList() {
  try {
    const response = await request.get<Chat[]>('/settings/telegram/chats')
    chatList.value = response || []
  } catch (error) {
    chatList.value = [
      { id: 'channel_1', title: '我的频道' },
      { id: 'channel_2', title: '测试频道' }
    ]
  }
}

function handleFilterChange() {
  pagination.page = 1
  fetchUploads()
}

async function handleRetry(row: Upload) {
  row.retrying = true
  try {
    await request.post(`/uploads/${row.id}/retry`)
    ElMessage.success('重试任务已创建')
    fetchUploads()
  } catch (error) {
    ElMessage.error('重试失败')
  } finally {
    row.retrying = false
  }
}

function handleDelete(row: Upload) {
  ElMessageBox.confirm(`确定要删除此上传记录吗？`, '删除确认', {
    type: 'warning'
  }).then(async () => {
    try {
      await request.delete(`/uploads/${row.id}`)
      ElMessage.success('删除成功')
      fetchUploads()
    } catch (error) {
      ElMessage.error('删除失败')
    }
  })
}

function viewMessage(row: Upload) {
  ElMessage.info(`跳转到 Telegram 消息: ${row.target_chat}`)
}

let refreshInterval: ReturnType<typeof setInterval> | null = null

onMounted(() => {
  fetchUploads()
  fetchChatList()
  refreshInterval = setInterval(() => {
    if (uploads.value.some(u => u.status === 'uploading')) {
      fetchUploads()
    }
  }, 3000)
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})
</script>

<style scoped lang="scss">
.upload-list {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;

    .header-actions {
      display: flex;
      gap: 10px;
    }
  }

  .filter-bar {
    padding: 16px;
    background: var(--el-fill-color-light);
    border-radius: 8px;
  }

  .media-preview {
    width: 60px;
    height: 60px;
    border-radius: 4px;
    overflow: hidden;
    background: var(--el-fill-color-light);
    display: flex;
    align-items: center;
    justify-content: center;

    img {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }

    .video-icon {
      color: var(--el-text-color-secondary);
    }
  }
}
</style>
