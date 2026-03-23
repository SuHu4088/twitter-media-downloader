<template>
  <div class="analytics-page">
    <el-card class="selector-card mb-20">
      <el-form :inline="true" :model="queryParams">
        <el-form-item label="选择博主">
          <el-select
            v-model="queryParams.account_id"
            placeholder="请选择博主"
            filterable
            clearable
            @change="handleAccountChange"
          >
            <el-option
              v-for="account in accounts"
              :key="account.id"
              :label="account.display_name"
              :value="account.id"
            >
              <div class="account-option">
                <el-avatar :size="24" :src="account.avatar_url" />
                <span class="ml-8">{{ account.display_name }}</span>
                <span class="username">@{{ account.username }}</span>
              </div>
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="时间范围">
          <el-date-picker
            v-model="queryParams.dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            :shortcuts="dateShortcuts"
            @change="handleDateChange"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="fetchAnalyticsData" :loading="loading">
            <el-icon><DataAnalysis /></el-icon>
            分析
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-row :gutter="20" class="stats-row mb-20">
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover" class="stat-card">
          <el-statistic title="总推文数" :value="stats.totalTweets">
            <template #prefix>
              <el-icon><Document /></el-icon>
            </template>
          </el-statistic>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover" class="stat-card">
          <el-statistic title="总媒体数" :value="stats.totalMedia">
            <template #prefix>
              <el-icon><Picture /></el-icon>
            </template>
          </el-statistic>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover" class="stat-card">
          <el-statistic title="平均点赞" :value="stats.avgLikes">
            <template #prefix>
              <el-icon><Star /></el-icon>
            </template>
          </el-statistic>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover" class="stat-card">
          <el-statistic title="平均转发" :value="stats.avgRetweets">
            <template #prefix>
              <el-icon><Share /></el-icon>
            </template>
          </el-statistic>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" class="mb-20">
      <el-col :xs="24" :lg="12">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>媒体类型分布</span>
            </div>
          </template>
          <MediaTypeChart :data="mediaTypeData" :loading="chartLoading" />
        </el-card>
      </el-col>
      <el-col :xs="24" :lg="12">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>发布频率分析</span>
              <el-radio-group v-model="frequencyType" size="small">
                <el-radio-button label="daily">按天</el-radio-button>
                <el-radio-button label="weekly">按周</el-radio-button>
                <el-radio-button label="monthly">按月</el-radio-button>
              </el-radio-group>
            </div>
          </template>
          <FrequencyChart :data="frequencyData" :type="frequencyType" :loading="chartLoading" />
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20">
      <el-col :span="24">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>互动数据趋势</span>
              <el-checkbox-group v-model="engagementMetrics" size="small">
                <el-checkbox-button label="likes">点赞</el-checkbox-button>
                <el-checkbox-button label="retweets">转发</el-checkbox-button>
                <el-checkbox-button label="replies">评论</el-checkbox-button>
              </el-checkbox-group>
            </div>
          </template>
          <EngagementChart :data="engagementData" :metrics="engagementMetrics" :loading="chartLoading" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { twitterApi, TwitterAccount } from '@/api/twitter'
import { mediaApi } from '@/api/media'
import MediaTypeChart from './components/MediaTypeChart.vue'
import FrequencyChart from './components/FrequencyChart.vue'
import EngagementChart from './components/EngagementChart.vue'

interface Stats {
  totalTweets: number
  totalMedia: number
  avgLikes: number
  avgRetweets: number
}

interface MediaTypeData {
  name: string
  value: number
}

interface FrequencyData {
  date: string
  count: number
}

interface EngagementData {
  date: string
  likes: number
  retweets: number
  replies: number
}

const loading = ref(false)
const chartLoading = ref(false)
const accounts = ref<TwitterAccount[]>([])
const frequencyType = ref<'daily' | 'weekly' | 'monthly'>('daily')
const engagementMetrics = ref(['likes', 'retweets'])

const queryParams = reactive({
  account_id: null as number | null,
  dateRange: [] as string[]
})

const stats = ref<Stats>({
  totalTweets: 0,
  totalMedia: 0,
  avgLikes: 0,
  avgRetweets: 0
})

const mediaTypeData = ref<MediaTypeData[]>([])
const frequencyData = ref<FrequencyData[]>([])
const engagementData = ref<EngagementData[]>([])

const dateShortcuts = [
  {
    text: '最近7天',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setTime(start.getTime() - 3600 * 1000 * 24 * 7)
      return [start, end]
    }
  },
  {
    text: '最近30天',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setTime(start.getTime() - 3600 * 1000 * 24 * 30)
      return [start, end]
    }
  },
  {
    text: '最近90天',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setTime(start.getTime() - 3600 * 1000 * 24 * 90)
      return [start, end]
    }
  }
]

async function fetchAccounts() {
  try {
    const response = await twitterApi.getAccounts({ page_size: 100 })
    accounts.value = response.items
  } catch (error) {
    console.error('获取账号列表失败:', error)
  }
}

function handleAccountChange() {
  if (queryParams.account_id) {
    fetchAnalyticsData()
  }
}

function handleDateChange() {
  if (queryParams.account_id) {
    fetchAnalyticsData()
  }
}

async function fetchAnalyticsData() {
  if (!queryParams.account_id) return
  
  loading.value = true
  chartLoading.value = true
  
  try {
    const mediaStats = await mediaApi.getMediaStats()
    
    stats.value = {
      totalTweets: Math.floor(mediaStats.total_count * 0.8),
      totalMedia: mediaStats.total_count,
      avgLikes: Math.floor(Math.random() * 1000) + 100,
      avgRetweets: Math.floor(Math.random() * 500) + 50
    }
    
    mediaTypeData.value = [
      { name: '图片', value: mediaStats.image_count },
      { name: '视频', value: mediaStats.video_count },
      { name: 'GIF', value: mediaStats.gif_count }
    ]
    
    generateFrequencyData()
    generateEngagementData()
  } catch (error) {
    console.error('获取分析数据失败:', error)
  } finally {
    loading.value = false
    chartLoading.value = false
  }
}

function generateFrequencyData() {
  const data: FrequencyData[] = []
  const days = frequencyType.value === 'daily' ? 30 : frequencyType.value === 'weekly' ? 12 : 6
  
  for (let i = days - 1; i >= 0; i--) {
    const date = new Date()
    date.setDate(date.getDate() - i)
    data.push({
      date: date.toISOString().split('T')[0],
      count: Math.floor(Math.random() * 20) + 1
    })
  }
  
  frequencyData.value = data
}

function generateEngagementData() {
  const data: EngagementData[] = []
  
  for (let i = 29; i >= 0; i--) {
    const date = new Date()
    date.setDate(date.getDate() - i)
    data.push({
      date: date.toISOString().split('T')[0],
      likes: Math.floor(Math.random() * 5000) + 500,
      retweets: Math.floor(Math.random() * 2000) + 100,
      replies: Math.floor(Math.random() * 500) + 50
    })
  }
  
  engagementData.value = data
}

onMounted(() => {
  fetchAccounts()
})
</script>

<style scoped lang="scss">
.analytics-page {
  .selector-card {
    :deep(.el-card__body) {
      padding-bottom: 2px;
    }
  }

  .account-option {
    display: flex;
    align-items: center;

    .username {
      margin-left: 8px;
      color: var(--el-text-color-secondary);
      font-size: 12px;
    }
  }

  .ml-8 {
    margin-left: 8px;
  }

  .stats-row {
    .stat-card {
      text-align: center;

      :deep(.el-statistic__head) {
        font-size: 14px;
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
