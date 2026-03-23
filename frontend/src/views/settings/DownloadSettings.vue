<template>
  <div class="download-settings">
    <el-card>
      <template #header>
        <span>下载路径配置</span>
      </template>

      <el-form
        ref="formRef"
        :model="downloadForm"
        :rules="formRules"
        label-width="120px"
        class="settings-form"
      >
        <el-form-item label="下载路径" prop="download_path">
          <el-input v-model="downloadForm.download_path" placeholder="请输入下载路径">
            <template #append>
              <el-button @click="selectFolder">选择文件夹</el-button>
            </template>
          </el-input>
          <div class="form-tip">
            媒体文件将下载到此目录
          </div>
        </el-form-item>
        <el-form-item label="临时路径" prop="temp_path">
          <el-input v-model="downloadForm.temp_path" placeholder="请输入临时文件路径">
            <template #append>
              <el-button @click="selectTempFolder">选择文件夹</el-button>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item label="文件命名规则">
          <el-select v-model="downloadForm.naming_pattern" placeholder="请选择命名规则">
            <el-option label="{username}/{date}/{tweet_id}" value="username_date_tweet" />
            <el-option label="{username}/{tweet_id}" value="username_tweet" />
            <el-option label="{date}/{username}_{tweet_id}" value="date_username_tweet" />
            <el-option label="{tweet_id}" value="tweet" />
          </el-select>
          <div class="form-tip">
            示例: user1/2024-01-15/123456.jpg
          </div>
        </el-form-item>
        <el-form-item label="并发下载数">
          <el-input-number v-model="downloadForm.concurrent_downloads" :min="1" :max="10" />
        </el-form-item>
        <el-form-item label="下载超时(秒)">
          <el-input-number v-model="downloadForm.timeout" :min="30" :max="600" />
        </el-form-item>
        <el-form-item label="自动重试">
          <el-switch v-model="downloadForm.auto_retry" />
        </el-form-item>
        <el-form-item label="重试次数" v-if="downloadForm.auto_retry">
          <el-input-number v-model="downloadForm.retry_count" :min="1" :max="5" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSave" :loading="saving">保存设置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="mt-20">
      <template #header>
        <span>存储统计</span>
      </template>

      <el-row :gutter="20">
        <el-col :xs="24" :sm="12" :md="6">
          <div class="stat-item">
            <div class="stat-label">总存储空间</div>
            <div class="stat-value">{{ formatSize(storageStats.total) }}</div>
          </div>
        </el-col>
        <el-col :xs="24" :sm="12" :md="6">
          <div class="stat-item">
            <div class="stat-label">已使用</div>
            <div class="stat-value">{{ formatSize(storageStats.used) }}</div>
          </div>
        </el-col>
        <el-col :xs="24" :sm="12" :md="6">
          <div class="stat-item">
            <div class="stat-label">可用空间</div>
            <div class="stat-value">{{ formatSize(storageStats.available) }}</div>
          </div>
        </el-col>
        <el-col :xs="24" :sm="12" :md="6">
          <div class="stat-item">
            <div class="stat-label">使用率</div>
            <div class="stat-value">
              <el-progress
                type="circle"
                :percentage="storageStats.usage_percent"
                :width="60"
                :status="storageStats.usage_percent > 80 ? 'exception' : ''"
              />
            </div>
          </div>
        </el-col>
      </el-row>

      <el-divider />

      <el-row :gutter="20">
        <el-col :span="24">
          <div class="storage-detail">
            <div class="detail-header">
              <span>存储分布</span>
              <el-button size="small" @click="fetchStorageStats">刷新</el-button>
            </div>
            <div class="detail-bars">
              <div class="bar-item" v-for="item in storageDistribution" :key="item.type">
                <div class="bar-label">
                  <span>{{ item.label }}</span>
                  <span>{{ formatSize(item.size) }}</span>
                </div>
                <el-progress
                  :percentage="item.percent"
                  :stroke-width="12"
                  :show-text="false"
                  :color="item.color"
                />
              </div>
            </div>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <el-card class="mt-20">
      <template #header>
        <div class="card-header">
          <span>存储管理</span>
        </div>
      </template>

      <el-space wrap>
        <el-button @click="handleCleanup('temp')">
          <el-icon><Delete /></el-icon>
          清理临时文件
        </el-button>
        <el-button @click="handleCleanup('cache')">
          <el-icon><Delete /></el-icon>
          清理缓存
        </el-button>
        <el-button type="danger" plain @click="handleCleanup('all')">
          <el-icon><Warning /></el-icon>
          清理所有
        </el-button>
      </el-space>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox, FormInstance, FormRules } from 'element-plus'
import { request } from '@/api/request'

interface StorageStats {
  total: number
  used: number
  available: number
  usage_percent: number
}

interface StorageItem {
  type: string
  label: string
  size: number
  percent: number
  color: string
}

const formRef = ref<FormInstance>()
const saving = ref(false)

const downloadForm = reactive({
  download_path: '/data/downloads',
  temp_path: '/data/temp',
  naming_pattern: 'username_date_tweet',
  concurrent_downloads: 3,
  timeout: 120,
  auto_retry: true,
  retry_count: 3
})

const formRules: FormRules = {
  download_path: [{ required: true, message: '请输入下载路径', trigger: 'blur' }],
  temp_path: [{ required: true, message: '请输入临时路径', trigger: 'blur' }]
}

const storageStats = ref<StorageStats>({
  total: 500 * 1024 * 1024 * 1024,
  used: 150 * 1024 * 1024 * 1024,
  available: 350 * 1024 * 1024 * 1024,
  usage_percent: 30
})

const storageDistribution = ref<StorageItem[]>([
  { type: 'image', label: '图片', size: 80 * 1024 * 1024 * 1024, percent: 53, color: '#409eff' },
  { type: 'video', label: '视频', size: 50 * 1024 * 1024 * 1024, percent: 33, color: '#67c23a' },
  { type: 'gif', label: 'GIF', size: 15 * 1024 * 1024 * 1024, percent: 10, color: '#e6a23c' },
  { type: 'other', label: '其他', size: 5 * 1024 * 1024 * 1024, percent: 4, color: '#909399' }
])

function formatSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  if (bytes < 1024 * 1024 * 1024) return (bytes / 1024 / 1024).toFixed(1) + ' MB'
  return (bytes / 1024 / 1024 / 1024).toFixed(1) + ' GB'
}

function selectFolder() {
  ElMessage.info('请在实际应用中使用 Electron API 选择文件夹')
}

function selectTempFolder() {
  ElMessage.info('请在实际应用中使用 Electron API 选择文件夹')
}

async function fetchSettings() {
  try {
    const response = await request.get<typeof downloadForm>('/settings/download')
    Object.assign(downloadForm, response)
  } catch (error) {
    console.error('获取设置失败:', error)
  }
}

async function fetchStorageStats() {
  try {
    const response = await request.get<StorageStats>('/settings/storage/stats')
    storageStats.value = response
  } catch (error) {
    console.error('获取存储统计失败:', error)
  }
}

async function handleSave() {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    
    saving.value = true
    try {
      await request.post('/settings/download', downloadForm)
      ElMessage.success('设置已保存')
    } catch (error) {
      ElMessage.error('保存失败')
    } finally {
      saving.value = false
    }
  })
}

function handleCleanup(type: string) {
  const messages: Record<string, string> = {
    temp: '确定要清理临时文件吗？',
    cache: '确定要清理缓存吗？',
    all: '确定要清理所有文件吗？此操作不可恢复！'
  }
  
  ElMessageBox.confirm(messages[type], '清理确认', {
    type: type === 'all' ? 'warning' : 'info',
    confirmButtonText: '确定',
    cancelButtonText: '取消'
  }).then(async () => {
    try {
      await request.post('/settings/storage/cleanup', { type })
      ElMessage.success('清理完成')
      fetchStorageStats()
    } catch (error) {
      ElMessage.error('清理失败')
    }
  })
}

onMounted(() => {
  fetchSettings()
  fetchStorageStats()
})
</script>

<style scoped lang="scss">
.download-settings {
  .settings-form {
    max-width: 600px;
  }

  .form-tip {
    font-size: 12px;
    color: var(--el-text-color-secondary);
    margin-top: 4px;
  }

  .stat-item {
    text-align: center;
    padding: 20px;
    background: var(--el-fill-color-light);
    border-radius: 8px;

    .stat-label {
      font-size: 14px;
      color: var(--el-text-color-secondary);
      margin-bottom: 8px;
    }

    .stat-value {
      font-size: 24px;
      font-weight: 600;
    }
  }

  .storage-detail {
    .detail-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
    }

    .detail-bars {
      .bar-item {
        margin-bottom: 16px;

        .bar-label {
          display: flex;
          justify-content: space-between;
          margin-bottom: 8px;
          font-size: 14px;
        }
      }
    }
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
}
</style>
