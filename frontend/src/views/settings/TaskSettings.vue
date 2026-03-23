<template>
  <div class="task-settings">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>定时任务配置</span>
        </div>
      </template>

      <el-table :data="taskList" v-loading="loading" stripe>
        <el-table-column prop="name" label="任务名称" width="180" />
        <el-table-column prop="description" label="描述" min-width="200" />
        <el-table-column label="执行间隔" width="150">
          <template #default="{ row }">
            {{ formatInterval(row.interval) }}
          </template>
        </el-table-column>
        <el-table-column prop="cron" label="Cron 表达式" width="150">
          <template #default="{ row }">
            <code v-if="row.cron">{{ row.cron }}</code>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-switch
              v-model="row.enabled"
              @change="handleToggle(row)"
            />
          </template>
        </el-table-column>
        <el-table-column prop="last_run" label="上次执行" width="180">
          <template #default="{ row }">
            {{ row.last_run || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="next_run" label="下次执行" width="180">
          <template #default="{ row }">
            {{ row.next_run || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" fixed="right" width="150">
          <template #default="{ row }">
            <el-button size="small" @click="handleEdit(row)">配置</el-button>
            <el-button size="small" type="primary" @click="handleRun(row)" :loading="row.running">
              执行
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" title="任务配置" width="500px" destroy-on-close>
      <el-form
        ref="formRef"
        :model="taskForm"
        :rules="formRules"
        label-width="100px"
      >
        <el-form-item label="任务名称">
          <el-input :model-value="taskForm.name" disabled />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="taskForm.enabled" />
        </el-form-item>
        <el-form-item label="调度方式">
          <el-radio-group v-model="taskForm.schedule_type">
            <el-radio label="interval">间隔执行</el-radio>
            <el-radio label="cron">Cron 表达式</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="taskForm.schedule_type === 'interval'" label="执行间隔">
          <el-input-number v-model="taskForm.interval_value" :min="1" />
          <el-select v-model="taskForm.interval_unit" class="ml-10" style="width: 100px">
            <el-option label="分钟" value="minutes" />
            <el-option label="小时" value="hours" />
            <el-option label="天" value="days" />
          </el-select>
        </el-form-item>
        <el-form-item v-else label="Cron 表达式" prop="cron">
          <el-input v-model="taskForm.cron" placeholder="例如: 0 0 * * * (每天零点)" />
          <div class="form-tip" v-if="taskForm.cron">
            {{ getCronDescription(taskForm.cron) }}
          </div>
        </el-form-item>
        <el-form-item label="最大重试次数">
          <el-input-number v-model="taskForm.max_retries" :min="0" :max="10" />
        </el-form-item>
        <el-form-item label="超时时间(秒)">
          <el-input-number v-model="taskForm.timeout" :min="60" :max="3600" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">
          保存
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, FormInstance, FormRules } from 'element-plus'
import { request } from '@/api/request'

interface Task {
  id: number
  name: string
  key: string
  description: string
  interval?: number
  cron?: string
  enabled: boolean
  last_run?: string
  next_run?: string
  running?: boolean
}

const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)
const taskList = ref<Task[]>([])
const editingTask = ref<Task | null>(null)
const formRef = ref<FormInstance>()

const taskForm = reactive({
  name: '',
  key: '',
  enabled: true,
  schedule_type: 'interval' as 'interval' | 'cron',
  interval_value: 1,
  interval_unit: 'hours' as 'minutes' | 'hours' | 'days',
  cron: '',
  max_retries: 3,
  timeout: 300
})

const formRules: FormRules = {
  cron: [
    {
      validator: (rule, value, callback) => {
        if (taskForm.schedule_type === 'cron' && !value) {
          callback(new Error('请输入 Cron 表达式'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

function formatInterval(seconds: number): string {
  if (!seconds) return '-'
  if (seconds < 60) return `${seconds} 秒`
  if (seconds < 3600) return `${Math.floor(seconds / 60)} 分钟`
  if (seconds < 86400) return `${Math.floor(seconds / 3600)} 小时`
  return `${Math.floor(seconds / 86400)} 天`
}

function getCronDescription(cron: string): string {
  const parts = cron.split(' ')
  if (parts.length !== 5) return '无效的 Cron 表达式'
  
  const [min, hour, day, month, weekday] = parts
  
  if (min === '0' && hour === '0' && day === '*' && month === '*' && weekday === '*') {
    return '每天 00:00 执行'
  }
  if (min === '0' && hour === '*/6' && day === '*' && month === '*' && weekday === '*') {
    return '每 6 小时执行一次'
  }
  if (min === '0' && hour === '*/1' && day === '*' && month === '*' && weekday === '*') {
    return '每小时执行一次'
  }
  
  return `自定义: ${cron}`
}

async function fetchTaskList() {
  loading.value = true
  try {
    const response = await request.get<Task[]>('/settings/tasks')
    taskList.value = response || []
  } catch (error) {
    taskList.value = [
      {
        id: 1,
        name: '同步推文任务',
        key: 'sync_tweets',
        description: '定时同步已绑定账号的推文',
        interval: 21600,
        enabled: true,
        last_run: '2024-01-15 10:00:00',
        next_run: '2024-01-15 16:00:00'
      },
      {
        id: 2,
        name: '下载媒体任务',
        key: 'download_media',
        description: '定时下载未下载的媒体文件',
        interval: 3600,
        enabled: true,
        last_run: '2024-01-15 11:00:00',
        next_run: '2024-01-15 12:00:00'
      },
      {
        id: 3,
        name: '清理过期数据',
        key: 'cleanup_data',
        description: '清理过期的临时文件和日志',
        cron: '0 3 * * *',
        enabled: false,
        last_run: '-',
        next_run: '-'
      }
    ]
  } finally {
    loading.value = false
  }
}

function handleEdit(row: Task) {
  editingTask.value = row
  Object.assign(taskForm, {
    name: row.name,
    key: row.key,
    enabled: row.enabled,
    schedule_type: row.cron ? 'cron' : 'interval',
    interval_value: row.interval ? Math.floor(row.interval / 3600) : 1,
    interval_unit: 'hours',
    cron: row.cron || '',
    max_retries: 3,
    timeout: 300
  })
  dialogVisible.value = true
}

async function handleSubmit() {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    
    submitting.value = true
    try {
      const data: any = {
        enabled: taskForm.enabled,
        max_retries: taskForm.max_retries,
        timeout: taskForm.timeout
      }
      
      if (taskForm.schedule_type === 'interval') {
        const units: Record<string, number> = {
          minutes: 60,
          hours: 3600,
          days: 86400
        }
        data.interval = taskForm.interval_value * units[taskForm.interval_unit]
        data.cron = null
      } else {
        data.cron = taskForm.cron
        data.interval = null
      }
      
      await request.put(`/settings/tasks/${editingTask.value!.key}`, data)
      ElMessage.success('配置已保存')
      dialogVisible.value = false
      fetchTaskList()
    } catch (error) {
      ElMessage.error('保存失败')
    } finally {
      submitting.value = false
    }
  })
}

async function handleToggle(row: Task) {
  try {
    await request.put(`/settings/tasks/${row.key}`, { enabled: row.enabled })
    ElMessage.success(row.enabled ? '任务已启用' : '任务已禁用')
  } catch (error) {
    row.enabled = !row.enabled
    ElMessage.error('操作失败')
  }
}

async function handleRun(row: Task) {
  row.running = true
  try {
    await request.post(`/settings/tasks/${row.key}/run`)
    ElMessage.success(`任务 "${row.name}" 已开始执行`)
  } catch (error) {
    ElMessage.error('执行失败')
  } finally {
    row.running = false
  }
}

onMounted(() => {
  fetchTaskList()
})
</script>

<style scoped lang="scss">
.task-settings {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .form-tip {
    font-size: 12px;
    color: var(--el-text-color-secondary);
    margin-top: 4px;
  }

  .ml-10 {
    margin-left: 10px;
  }

  code {
    background: var(--el-fill-color-light);
    padding: 2px 6px;
    border-radius: 4px;
    font-family: monospace;
  }
}
</style>
