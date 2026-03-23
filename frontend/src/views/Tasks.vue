<template>
  <div class="tasks-page page-container">
    <el-table :data="tasks" v-loading="loading" stripe>
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column label="任务类型" width="120">
        <template #default="{ row }">
          {{ getTaskTypeName(row.task_type) }}
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="getTaskStatusType(row.status)">
            {{ getTaskStatusName(row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="进度" width="200">
        <template #default="{ row }">
          <el-progress
            :percentage="Math.round((row.progress / row.total) * 100)"
            :status="row.status === 'completed' ? 'success' : row.status === 'failed' ? 'exception' : ''"
          />
        </template>
      </el-table-column>
      <el-table-column prop="account_name" label="关联账号" width="120" />
      <el-table-column prop="created_at" label="创建时间" width="180" />
      <el-table-column label="操作" width="150">
        <template #default="{ row }">
          <el-button
            v-if="row.status === 'running'"
            size="small"
            type="warning"
            @click="handleCancel(row)"
          >
            取消
          </el-button>
          <el-button
            v-if="row.status === 'failed'"
            size="small"
            type="primary"
            @click="handleRetry(row)"
          >
            重试
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
      @change="fetchTasks"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'

interface Task {
  id: number
  task_type: string
  status: string
  progress: number
  total: number
  account_name: string
  created_at: string
}

const loading = ref(false)
const tasks = ref<Task[]>([])

const pagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0
})

function getTaskTypeName(type: string): string {
  const map: Record<string, string> = {
    sync_tweets: '同步推文',
    download_media: '下载媒体',
    export_data: '导出数据',
    cleanup: '清理任务'
  }
  return map[type] || type
}

function getTaskStatusName(status: string): string {
  const map: Record<string, string> = {
    pending: '等待中',
    running: '运行中',
    completed: '已完成',
    failed: '失败',
    cancelled: '已取消'
  }
  return map[status] || status
}

function getTaskStatusType(status: string): string {
  const map: Record<string, string> = {
    pending: 'info',
    running: 'warning',
    completed: 'success',
    failed: 'danger',
    cancelled: 'info'
  }
  return map[status] || 'info'
}

async function fetchTasks() {
  loading.value = true
  try {
    tasks.value = [
      {
        id: 1,
        task_type: 'sync_tweets',
        status: 'completed',
        progress: 100,
        total: 100,
        account_name: 'user1',
        created_at: '2024-01-15 10:00'
      }
    ]
    pagination.total = 1
  } finally {
    loading.value = false
  }
}

function handleCancel(row: Task) {
  ElMessage.success(`任务 ${row.id} 已取消`)
}

function handleRetry(row: Task) {
  ElMessage.success(`任务 ${row.id} 正在重试`)
}

onMounted(() => {
  fetchTasks()
})
</script>
