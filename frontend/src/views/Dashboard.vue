<template>
  <div class="dashboard-page">
    <el-row :gutter="20">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background-color: #409eff">
              <el-icon size="24"><User /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.accountCount }}</div>
              <div class="stat-label">监控账号</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background-color: #67c23a">
              <el-icon size="24"><Picture /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.mediaCount }}</div>
              <div class="stat-label">媒体文件</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background-color: #e6a23c">
              <el-icon size="24"><List /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.taskCount }}</div>
              <div class="stat-label">运行任务</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background-color: #f56c6c">
              <el-icon size="24"><Coin /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ formatSize(stats.storageSize) }}</div>
              <div class="stat-label">存储占用</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" class="mt-20">
      <el-col :span="16">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>下载趋势</span>
            </div>
          </template>
          <div class="chart-container" ref="chartRef"></div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>最近任务</span>
            </div>
          </template>
          <el-timeline>
            <el-timeline-item
              v-for="task in recentTasks"
              :key="task.id"
              :timestamp="task.created_at"
              placement="top"
            >
              <div class="task-item">
                <span>{{ getTaskTypeName(task.task_type) }}</span>
                <el-tag :type="getTaskStatusType(task.status)" size="small">
                  {{ getTaskStatusName(task.status) }}
                </el-tag>
              </div>
            </el-timeline-item>
          </el-timeline>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import * as echarts from 'echarts'

const chartRef = ref<HTMLElement>()

const stats = ref({
  accountCount: 12,
  mediaCount: 1234,
  taskCount: 5,
  storageSize: 1024 * 1024 * 1024 * 2.5
})

const recentTasks = ref([
  { id: 1, task_type: 'sync_tweets', status: 'completed', created_at: '2024-01-15 10:30' },
  { id: 2, task_type: 'download_media', status: 'running', created_at: '2024-01-15 09:20' },
  { id: 3, task_type: 'sync_tweets', status: 'completed', created_at: '2024-01-14 18:45' }
])

function formatSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB'
  if (bytes < 1024 * 1024 * 1024) return (bytes / 1024 / 1024).toFixed(2) + ' MB'
  return (bytes / 1024 / 1024 / 1024).toFixed(2) + ' GB'
}

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

onMounted(() => {
  if (chartRef.value) {
    const chart = echarts.init(chartRef.value)
    chart.setOption({
      tooltip: { trigger: 'axis' },
      xAxis: {
        type: 'category',
        data: ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
      },
      yAxis: { type: 'value' },
      series: [
        {
          name: '下载数量',
          type: 'line',
          smooth: true,
          data: [120, 200, 150, 80, 70, 110, 130],
          areaStyle: { opacity: 0.3 }
        }
      ]
    })
  }
})
</script>

<style scoped lang="scss">
.dashboard-page {
  .stat-card {
    .stat-content {
      display: flex;
      align-items: center;
    }

    .stat-icon {
      width: 56px;
      height: 56px;
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #fff;
    }

    .stat-info {
      margin-left: 16px;

      .stat-value {
        font-size: 28px;
        font-weight: bold;
        color: #303133;
      }

      .stat-label {
        font-size: 14px;
        color: #909399;
        margin-top: 4px;
      }
    }
  }

  .chart-container {
    height: 300px;
  }

  .task-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
}
</style>
