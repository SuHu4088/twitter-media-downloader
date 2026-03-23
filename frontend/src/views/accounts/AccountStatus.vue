<template>
  <div class="account-status">
    <el-card v-if="account" class="status-card">
      <template #header>
        <div class="card-header">
          <div class="account-info">
            <el-avatar :size="40" :src="account.avatar_url" />
            <div class="info-text">
              <div class="display-name">{{ account.display_name }}</div>
              <div class="username">@{{ account.username }}</div>
            </div>
          </div>
          <el-tag :type="account.is_active ? 'success' : 'info'">
            {{ account.is_active ? '活跃' : '暂停' }}
          </el-tag>
        </div>
      </template>

      <el-descriptions :column="2" border class="status-descriptions">
        <el-descriptions-item label="同步状态">
          <div class="status-item">
            <el-icon :class="syncStatus.class" :size="18">
              <component :is="syncStatus.icon" />
            </el-icon>
            <span>{{ syncStatus.text }}</span>
          </div>
        </el-descriptions-item>
        <el-descriptions-item label="令牌状态">
          <div class="status-item">
            <el-icon :class="tokenStatus.class" :size="18">
              <component :is="tokenStatus.icon" />
            </el-icon>
            <span>{{ tokenStatus.text }}</span>
          </div>
        </el-descriptions-item>
        <el-descriptions-item label="最后同步时间">
          <span v-if="lastSyncTime">{{ lastSyncTime }}</span>
          <span v-else class="text-secondary">暂无同步记录</span>
        </el-descriptions-item>
        <el-descriptions-item label="下次同步时间">
          <span v-if="nextSyncTime">{{ nextSyncTime }}</span>
          <span v-else class="text-secondary">未计划</span>
        </el-descriptions-item>
        <el-descriptions-item label="已同步推文">
          <el-statistic :value="syncStats.tweets_count" />
        </el-descriptions-item>
        <el-descriptions-item label="已下载媒体">
          <el-statistic :value="syncStats.media_count" />
        </el-descriptions-item>
      </el-descriptions>

      <div class="sync-progress mt-20" v-if="isSyncing">
        <div class="progress-header">
          <span>同步进度</span>
          <span>{{ syncProgress.current }}/{{ syncProgress.total }}</span>
        </div>
        <el-progress
          :percentage="syncProgress.percentage"
          :status="syncProgress.status"
          :stroke-width="10"
        />
      </div>

      <div class="action-buttons mt-20">
        <el-button type="primary" @click="handleSync" :loading="isSyncing" :disabled="!account.is_active">
          <el-icon><Refresh /></el-icon>
          {{ isSyncing ? '同步中...' : '立即同步' }}
        </el-button>
        <el-button @click="handleToggle">
          <el-icon>
            <VideoPause v-if="account.is_active" />
            <VideoPlay v-else />
          </el-icon>
          {{ account.is_active ? '暂停监控' : '恢复监控' }}
        </el-button>
        <el-button type="danger" plain @click="handleUnbind">
          <el-icon><Delete /></el-icon>
          解除绑定
        </el-button>
      </div>
    </el-card>

    <el-card v-else class="status-card">
      <el-empty description="请选择一个账号查看状态" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { twitterApi, TwitterAccount } from '@/api/twitter'

interface SyncProgress {
  current: number
  total: number
  percentage: number
  status: '' | 'success' | 'warning' | 'exception'
}

interface SyncStats {
  tweets_count: number
  media_count: number
}

const props = defineProps<{
  account?: TwitterAccount | null
}>()

const emit = defineEmits<{
  (e: 'update', account: TwitterAccount): void
  (e: 'unbind', accountId: number): void
}>()

const isSyncing = ref(false)
const lastSyncTime = ref<string>('')
const nextSyncTime = ref<string>('')
const tokenValid = ref<boolean>(true)
const tokenExpireTime = ref<string>('')

const syncProgress = ref<SyncProgress>({
  current: 0,
  total: 100,
  percentage: 0,
  status: ''
})

const syncStats = ref<SyncStats>({
  tweets_count: 0,
  media_count: 0
})

const syncStatus = computed(() => {
  if (isSyncing.value) {
    return { text: '同步中', icon: 'Loading', class: 'is-loading text-primary' }
  }
  if (!props.account?.is_active) {
    return { text: '已暂停', icon: 'VideoPause', class: 'text-warning' }
  }
  return { text: '正常', icon: 'CircleCheck', class: 'text-success' }
})

const tokenStatus = computed(() => {
  if (tokenValid.value) {
    return { text: '有效', icon: 'CircleCheck', class: 'text-success' }
  }
  return { text: '已过期', icon: 'CircleClose', class: 'text-danger' }
})

let syncCheckInterval: ReturnType<typeof setInterval> | null = null

async function fetchAccountStatus() {
  if (!props.account) return
  
  try {
    const data = await twitterApi.getAccount(props.account.id)
    lastSyncTime.value = data.updated_at
    emit('update', data)
  } catch (error) {
    console.error('获取账号状态失败:', error)
  }
}

async function handleSync() {
  if (!props.account) return
  
  isSyncing.value = true
  syncProgress.value = { current: 0, total: 100, percentage: 0, status: '' }
  
  try {
    await twitterApi.syncAccount(props.account.id)
    simulateSyncProgress()
  } catch (error) {
    ElMessage.error('同步启动失败')
    isSyncing.value = false
  }
}

function simulateSyncProgress() {
  const interval = setInterval(() => {
    if (syncProgress.value.current < syncProgress.value.total) {
      syncProgress.value.current += Math.floor(Math.random() * 10) + 1
      if (syncProgress.value.current > syncProgress.value.total) {
        syncProgress.value.current = syncProgress.value.total
      }
      syncProgress.value.percentage = Math.round(
        (syncProgress.value.current / syncProgress.value.total) * 100
      )
    } else {
      syncProgress.value.status = 'success'
      clearInterval(interval)
      setTimeout(() => {
        isSyncing.value = false
        ElMessage.success('同步完成')
        fetchAccountStatus()
      }, 500)
    }
  }, 500)
}

async function handleToggle() {
  if (!props.account) return
  
  try {
    const data = await twitterApi.toggleAccountActive(props.account.id)
    emit('update', data)
    ElMessage.success(data.is_active ? '已恢复监控' : '已暂停监控')
  } catch (error) {
    ElMessage.error('操作失败')
  }
}

function handleUnbind() {
  if (!props.account) return
  
  ElMessageBox.confirm(
    `确定要解除绑定 @${props.account.username} 吗？解除后相关数据将保留，但不再同步新内容。`,
    '解除绑定',
    {
      type: 'warning',
      confirmButtonText: '确定解除',
      cancelButtonText: '取消'
    }
  ).then(() => {
    emit('unbind', props.account!.id)
  })
}

watch(() => props.account, (newAccount) => {
  if (newAccount) {
    fetchAccountStatus()
  }
}, { immediate: true })

onMounted(() => {
  syncCheckInterval = setInterval(() => {
    if (props.account && !isSyncing.value) {
      fetchAccountStatus()
    }
  }, 30000)
})

onUnmounted(() => {
  if (syncCheckInterval) {
    clearInterval(syncCheckInterval)
  }
})
</script>

<style scoped lang="scss">
.account-status {
  .status-card {
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;

      .account-info {
        display: flex;
        align-items: center;
        gap: 12px;

        .info-text {
          .display-name {
            font-weight: 600;
          }

          .username {
            font-size: 12px;
            color: var(--el-text-color-secondary);
          }
        }
      }
    }

    .status-descriptions {
      .status-item {
        display: flex;
        align-items: center;
        gap: 8px;

        .text-success {
          color: var(--el-color-success);
        }

        .text-warning {
          color: var(--el-color-warning);
        }

        .text-danger {
          color: var(--el-color-danger);
        }

        .text-primary {
          color: var(--el-color-primary);
        }
      }
    }

    .sync-progress {
      .progress-header {
        display: flex;
        justify-content: space-between;
        margin-bottom: 8px;
        font-size: 14px;
      }
    }

    .action-buttons {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
    }
  }

  .text-secondary {
    color: var(--el-text-color-secondary);
  }
}
</style>
