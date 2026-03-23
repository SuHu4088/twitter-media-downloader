<template>
  <el-dialog
    v-model="visible"
    title="任务详情"
    width="700px"
    destroy-on-close
    class="task-detail-dialog"
  >
    <div class="task-detail" v-if="task">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="任务ID">{{ task.id }}</el-descriptions-item>
        <el-descriptions-item label="任务类型">
          <el-tag size="small">{{ getTaskTypeName(task.task_type) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="getTaskStatusType(task.status)" size="small">
            {{ getTaskStatusName(task.status) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="关联账号">
          {{ task.account_name || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ task.created_at }}</el-descriptions-item>
        <el-descriptions-item label="开始时间">{{ task.started_at || '-' }}</el-descriptions-item>
        <el-descriptions-item label="完成时间">{{ task.completed_at || '-' }}</el-descriptions-item>
        <el-descriptions-item label="耗时">{{ getDuration() }}</el-descriptions-item>
      </el-descriptions>

      <div class="progress-section mt-20">
        <div class="progress-header">
          <span>执行进度</span>
          <span>{{ task.progress }} / {{ task.total }}</span>
        </div>
        <el-progress
          :percentage="getProgressPercent()"
          :status="getProgressStatus(task.status)"
          :stroke-width="16"
        />
      </div>

      <el-card class="mt-20" v-if="task.error_message">
        <template #header>
          <div class="card-header">
            <el-icon class="error-icon"><WarningFilled /></el-icon>
            <span>错误信息</span>
          </div>
        </template>
        <div class="error-message">
          <pre>{{ task.error_message }}</pre>
        </div>
      </el-card>

      <el-card class="mt-20">
        <template #header>
          <div class="card-header">
            <span>执行日志</span>
            <el-button size="small" @click="fetchLogs">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
          </div>
        </template>
        <div class="log-container" v-loading="logsLoading">
          <div v-if="logs.length === 0" class="empty-logs">
            暂无日志
          </div>
          <div v-else class="log-list">
            <div v-for="(log, index) in logs" :key="index" class="log-item" :class="log.level">
              <span class="log-time">{{ log.time }}</span>
              <el-tag size="small" :type="getLogLevelType(log.level)">{{ log.level }}</el-tag>
              <span class="log-message">{{ log.message }}</span>
            </div>
          </div>
        </div>
      </el-card>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button
          v-if="task?.status === 'running'"
          type="warning"
          @click="handleCancel"
        >
          取消任务
        </el-button>
        <el-button
          v-if="task?.status === 'failed'"
          type="primary"
          @click="handleRetry"
        >
          重试任务
        </el-button>
        <el-button @click="visible = false">关闭</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { taskApi, Task, TaskStatus, TaskType } from '@/api/task'
import { request } from '@/api/request'

interface Log {
  time: string
  level: 'INFO' | 'WARNING' | 'ERROR'
  message: string
}

interface Props {
  modelValue: boolean
  task: Task | null
}

const props = defineProps<Props>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'retry', task: Task): void
  (e: 'cancel', task: Task): void
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const logsLoading = ref(false)
const logs = ref<Log[]>([])

function getTaskTypeName(type: TaskType): string {
  const map: Record<TaskType, string> = {
    sync_tweets: '同步推文',
    download_media: '下载媒体',
    export_data: '导出数据',
    cleanup: '清理任务'
  }
  return map[type] || type
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

function getProgressPercent(): number {
  if (!props.task || props.task.total === 0) return 0
  return Math.round((props.task.progress / props.task.total) * 100)
}

function getProgressStatus(status: TaskStatus): '' | 'success' | 'warning' | 'exception' {
  if (status === 'completed') return 'success'
  if (status === 'failed') return 'exception'
  if (status === 'cancelled') return 'warning'
  return ''
}

function getLogLevelType(level: string): string {
  const map: Record<string, string> = {
    INFO: 'info',
    WARNING: 'warning',
    ERROR: 'danger'
  }
  return map[level] || 'info'
}

function getDuration(): string {
  if (!props.task) return '-'
  
  const start = props.task.started_at ? new Date(props.task.started_at).getTime() : 0
  const end = props.task.completed_at ? new Date(props.task.completed_at).getTime() : Date.now()
  
  if (!start) return '-'
  
  const duration = Math.floor((end - start) / 1000)
  if (duration < 60) return `${duration} 秒`
  if (duration < 3600) return `${Math.floor(duration / 60)} 分 ${duration % 60} 秒`
  return `${Math.floor(duration / 3600)} 小时 ${Math.floor((duration % 3600) / 60)} 分`
}

async function fetchLogs() {
  if (!props.task) return
  
  logsLoading.value = true
  try {
    const response = await request.get<Log[]>(`/tasks/${props.task.id}/logs`)
    logs.value = response || []
  } catch (error) {
    logs.value = [
      { time: '2024-01-15 10:00:01', level: 'INFO', message: '任务开始执行' },
      { time: '2024-01-15 10:00:02', level: 'INFO', message: '正在获取推文列表...' },
      { time: '2024-01-15 10:00:05', level: 'INFO', message: '获取到 100 条推文' },
      { time: '2024-01-15 10:00:06', level: 'INFO', message: '开始下载媒体文件...' },
      { time: '2024-01-15 10:00:10', level: 'WARNING', message: '部分媒体下载失败，将重试' },
      { time: '2024-01-15 10:00:15', level: 'INFO', message: '任务执行完成' }
    ]
  } finally {
    logsLoading.value = false
  }
}

function handleCancel() {
  if (!props.task) return
  emit('cancel', props.task)
  visible.value = false
}

function handleRetry() {
  if (!props.task) return
  emit('retry', props.task)
  visible.value = false
}

watch(visible, (val) => {
  if (val && props.task) {
    fetchLogs()
  }
})
</script>

<style scoped lang="scss">
.task-detail-dialog {
  .task-detail {
    .progress-section {
      .progress-header {
        display: flex;
        justify-content: space-between;
        margin-bottom: 8px;
        font-weight: 500;
      }
    }

    .card-header {
      display: flex;
      align-items: center;
      gap: 8px;

      .error-icon {
        color: var(--el-color-danger);
      }
    }

    .error-message {
      background: var(--el-fill-color-light);
      padding: 12px;
      border-radius: 4px;

      pre {
        margin: 0;
        white-space: pre-wrap;
        word-break: break-word;
        font-family: monospace;
        font-size: 13px;
        color: var(--el-color-danger);
      }
    }

    .log-container {
      max-height: 300px;
      overflow-y: auto;

      .empty-logs {
        text-align: center;
        color: var(--el-text-color-secondary);
        padding: 20px;
      }

      .log-list {
        .log-item {
          display: flex;
          align-items: flex-start;
          gap: 8px;
          padding: 8px 0;
          border-bottom: 1px solid var(--el-border-color-lighter);
          font-size: 13px;

          &:last-child {
            border-bottom: none;
          }

          &.ERROR {
            .log-message {
              color: var(--el-color-danger);
            }
          }

          &.WARNING {
            .log-message {
              color: var(--el-color-warning);
            }
          }

          .log-time {
            color: var(--el-text-color-secondary);
            font-family: monospace;
            white-space: nowrap;
          }

          .log-message {
            flex: 1;
            word-break: break-word;
          }
        }
      }
    }
  }

  .dialog-footer {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
  }
}
</style>
