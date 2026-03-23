<template>
  <div class="task-list">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>下载任务列表</span>
          <div class="header-actions">
            <el-button type="primary" @click="handleCreateTask">
              <el-icon><Plus /></el-icon>
              新建任务
            </el-button>
            <el-button @click="fetchTasks">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
          </div>
        </div>
      </template>

      <div class="filter-bar mb-20">
        <el-form :inline="true" :model="filters">
          <el-form-item label="任务状态">
            <el-select v-model="filters.status" placeholder="全部状态" clearable @change="handleFilterChange">
              <el-option label="等待中" value="pending" />
              <el-option label="运行中" value="running" />
              <el-option label="已完成" value="completed" />
              <el-option label="失败" value="failed" />
              <el-option label="已取消" value="cancelled" />
            </el-select>
          </el-form-item>
          <el-form-item label="任务类型">
            <el-select v-model="filters.task_type" placeholder="全部类型" clearable @change="handleFilterChange">
              <el-option label="同步推文" value="sync_tweets" />
              <el-option label="下载媒体" value="download_media" />
              <el-option label="导出数据" value="export_data" />
              <el-option label="清理任务" value="cleanup" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="handleFilterChange">搜索</el-button>
          </el-form-item>
        </el-form>
      </div>

      <el-table :data="tasks" v-loading="loading" stripe @row-click="handleRowClick">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column label="任务类型" width="120">
          <template #default="{ row }">
            <el-tag size="small" :type="getTaskTypeTag(row.task_type)">
              {{ getTaskTypeName(row.task_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getTaskStatusType(row.status)" size="small">
              {{ getTaskStatusName(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="进度" width="200">
          <template #default="{ row }">
            <div class="progress-cell">
              <el-progress
                :percentage="getProgressPercent(row)"
                :status="getProgressStatus(row.status)"
                :stroke-width="8"
              />
              <span class="progress-text">{{ row.progress }}/{{ row.total }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="account_name" label="关联账号" width="120">
          <template #default="{ row }">
            {{ row.account_name || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column prop="completed_at" label="完成时间" width="180">
          <template #default="{ row }">
            {{ row.completed_at || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" fixed="right" width="180">
          <template #default="{ row }">
            <el-button
              v-if="row.status === 'running'"
              size="small"
              type="warning"
              @click.stop="handleCancel(row)"
            >
              取消
            </el-button>
            <el-button
              v-if="row.status === 'failed'"
              size="small"
              type="primary"
              @click.stop="handleRetry(row)"
            >
              重试
            </el-button>
            <el-button
              v-if="row.status === 'pending'"
              size="small"
              type="danger"
              @click.stop="handleDelete(row)"
            >
              删除
            </el-button>
            <el-button
              size="small"
              @click.stop="handleViewDetail(row)"
            >
              详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        class="mt-20"
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        :total="pagination.total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        @change="fetchTasks"
      />
    </el-card>

    <el-dialog v-model="createDialogVisible" title="新建下载任务" width="500px" destroy-on-close>
      <el-form ref="createFormRef" :model="createForm" :rules="createRules" label-width="100px">
        <el-form-item label="任务类型" prop="task_type">
          <el-select v-model="createForm.task_type" placeholder="请选择任务类型">
            <el-option label="同步推文" value="sync_tweets" />
            <el-option label="下载媒体" value="download_media" />
            <el-option label="导出数据" value="export_data" />
          </el-select>
        </el-form-item>
        <el-form-item label="关联账号" v-if="createForm.task_type !== 'cleanup'">
          <el-select v-model="createForm.account_id" placeholder="请选择账号" clearable filterable>
            <el-option
              v-for="account in accounts"
              :key="account.id"
              :label="account.display_name"
              :value="account.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="媒体类型" v-if="createForm.task_type === 'download_media'">
          <el-select v-model="createForm.media_type" placeholder="全部类型" clearable>
            <el-option label="图片" value="image" />
            <el-option label="视频" value="video" />
            <el-option label="GIF" value="gif" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmitCreate" :loading="creating">创建</el-button>
      </template>
    </el-dialog>

    <TaskDetail
      v-model="detailDialogVisible"
      :task="selectedTask"
      @retry="handleRetry"
      @cancel="handleCancel"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox, FormInstance, FormRules } from 'element-plus'
import { taskApi, Task, TaskStatus, TaskType, TaskListParams } from '@/api/task'
import { twitterApi, TwitterAccount } from '@/api/twitter'
import TaskDetail from './TaskDetail.vue'

const loading = ref(false)
const creating = ref(false)
const createDialogVisible = ref(false)
const detailDialogVisible = ref(false)
const tasks = ref<Task[]>([])
const accounts = ref<TwitterAccount[]>([])
const selectedTask = ref<Task | null>(null)
const createFormRef = ref<FormInstance>()

const filters = reactive({
  status: '' as TaskStatus | '',
  task_type: '' as TaskType | ''
})

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

const createForm = reactive({
  task_type: 'download_media' as TaskType,
  account_id: null as number | null,
  media_type: ''
})

const createRules: FormRules = {
  task_type: [{ required: true, message: '请选择任务类型', trigger: 'change' }]
}

function getTaskTypeName(type: TaskType): string {
  const map: Record<TaskType, string> = {
    sync_tweets: '同步推文',
    download_media: '下载媒体',
    export_data: '导出数据',
    cleanup: '清理任务'
  }
  return map[type] || type
}

function getTaskTypeTag(type: TaskType): string {
  const map: Record<TaskType, string> = {
    sync_tweets: 'primary',
    download_media: 'success',
    export_data: 'warning',
    cleanup: 'info'
  }
  return map[type] || ''
}

function getTaskStatusName(status: TaskStatus): string {
  const map: Record<TaskStatus, string> = {
    pending: '等待中',
    running: '运行中',
    completed: '已完成',
    failed: '失败',
    cancelled: '已取消'
  }
  return map[status] || status
}

function getTaskStatusType(status: TaskStatus): string {
  const map: Record<TaskStatus, string> = {
    pending: 'info',
    running: 'warning',
    completed: 'success',
    failed: 'danger',
    cancelled: 'info'
  }
  return map[status] || 'info'
}

function getProgressPercent(task: Task): number {
  if (task.total === 0) return 0
  return Math.round((task.progress / task.total) * 100)
}

function getProgressStatus(status: TaskStatus): '' | 'success' | 'warning' | 'exception' {
  if (status === 'completed') return 'success'
  if (status === 'failed') return 'exception'
  if (status === 'cancelled') return 'warning'
  return ''
}

async function fetchTasks() {
  loading.value = true
  try {
    const params: TaskListParams = {
      page: pagination.page,
      page_size: pagination.pageSize,
      status: filters.status || undefined,
      task_type: filters.task_type || undefined
    }
    const response = await taskApi.getTasks(params)
    tasks.value = response.items
    pagination.total = response.total
  } catch (error) {
    console.error('获取任务列表失败:', error)
  } finally {
    loading.value = false
  }
}

async function fetchAccounts() {
  try {
    const response = await twitterApi.getAccounts({ page_size: 100 })
    accounts.value = response.items
  } catch (error) {
    console.error('获取账号列表失败:', error)
  }
}

function handleFilterChange() {
  pagination.page = 1
  fetchTasks()
}

function handleRowClick(row: Task) {
  handleViewDetail(row)
}

function handleViewDetail(row: Task) {
  selectedTask.value = row
  detailDialogVisible.value = true
}

function handleCreateTask() {
  Object.assign(createForm, {
    task_type: 'download_media',
    account_id: null,
    media_type: ''
  })
  createDialogVisible.value = true
}

async function handleSubmitCreate() {
  if (!createFormRef.value) return
  
  await createFormRef.value.validate(async (valid) => {
    if (!valid) return
    
    creating.value = true
    try {
      if (createForm.task_type === 'sync_tweets') {
        await taskApi.createSyncTask(createForm.account_id!)
      } else if (createForm.task_type === 'download_media') {
        await taskApi.createDownloadTask({
          account_id: createForm.account_id || undefined,
          media_type: createForm.media_type || undefined
        })
      }
      ElMessage.success('任务创建成功')
      createDialogVisible.value = false
      fetchTasks()
    } catch (error) {
      ElMessage.error('创建失败')
    } finally {
      creating.value = false
    }
  })
}

async function handleCancel(row: Task) {
  try {
    await taskApi.cancelTask(row.id)
    ElMessage.success('任务已取消')
    fetchTasks()
  } catch (error) {
    ElMessage.error('取消失败')
  }
}

async function handleRetry(row: Task) {
  try {
    await taskApi.retryTask(row.id)
    ElMessage.success('任务已重新开始')
    fetchTasks()
  } catch (error) {
    ElMessage.error('重试失败')
  }
}

function handleDelete(row: Task) {
  ElMessageBox.confirm(`确定要删除任务 #${row.id} 吗？`, '删除确认', {
    type: 'warning'
  }).then(async () => {
    try {
      await request.delete(`/tasks/${row.id}`)
      ElMessage.success('删除成功')
      fetchTasks()
    } catch (error) {
      ElMessage.error('删除失败')
    }
  })
}

import { request } from '@/api/request'

let refreshInterval: ReturnType<typeof setInterval> | null = null

onMounted(() => {
  fetchTasks()
  fetchAccounts()
  refreshInterval = setInterval(() => {
    if (tasks.value.some(t => t.status === 'running')) {
      fetchTasks()
    }
  }, 5000)
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})
</script>

<style scoped lang="scss">
.task-list {
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

  .progress-cell {
    .progress-text {
      font-size: 12px;
      color: var(--el-text-color-secondary);
      margin-top: 4px;
      display: block;
    }
  }
}
</style>
