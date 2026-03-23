<template>
  <div class="media-filter">
    <el-card shadow="never">
      <el-form :model="filterForm" label-position="top">
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="媒体类型">
              <el-select v-model="filterForm.media_type" placeholder="全部类型" clearable @change="handleFilterChange">
                <el-option label="图片" value="image">
                  <el-icon><Picture /></el-icon>
                  <span class="ml-8">图片</span>
                </el-option>
                <el-option label="视频" value="video">
                  <el-icon><VideoPlay /></el-icon>
                  <span class="ml-8">视频</span>
                </el-option>
                <el-option label="GIF" value="gif">
                  <el-icon><PictureFilled /></el-icon>
                  <span class="ml-8">GIF</span>
                </el-option>
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="所属账号">
              <el-select
                v-model="filterForm.account_id"
                placeholder="全部账号"
                clearable
                filterable
                @change="handleFilterChange"
              >
                <el-option
                  v-for="account in accounts"
                  :key="account.id"
                  :label="account.display_name"
                  :value="account.id"
                >
                  <div class="account-option">
                    <el-avatar :size="20" :src="account.avatar_url" />
                    <span class="ml-8">{{ account.display_name }}</span>
                    <span class="username">@{{ account.username }}</span>
                  </div>
                </el-option>
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="日期范围">
              <el-date-picker
                v-model="dateRange"
                type="daterange"
                range-separator="至"
                start-placeholder="开始日期"
                end-placeholder="结束日期"
                value-format="YYYY-MM-DD"
                @change="handleDateChange"
              />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="文件大小">
              <el-slider
                v-model="sizeRange"
                range
                :max="100"
                :format-tooltip="formatSizeTooltip"
                @change="handleFilterChange"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="关键词搜索">
              <el-input
                v-model="filterForm.keyword"
                placeholder="搜索推文内容..."
                clearable
                @keyup.enter="handleFilterChange"
              >
                <template #prefix>
                  <el-icon><Search /></el-icon>
                </template>
              </el-input>
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>

      <div class="filter-actions">
        <el-button type="primary" @click="handleFilterChange">
          <el-icon><Search /></el-icon>
          应用筛选
        </el-button>
        <el-button @click="handleReset">
          <el-icon><RefreshLeft /></el-icon>
          重置
        </el-button>
        <div class="filter-summary" v-if="hasFilters">
          <el-tag v-if="filterForm.media_type" closable @close="clearFilter('media_type')">
            {{ getMediaTypeLabel(filterForm.media_type) }}
          </el-tag>
          <el-tag v-if="filterForm.account_id" closable @close="clearFilter('account_id')">
            {{ getAccountName(filterForm.account_id) }}
          </el-tag>
          <el-tag v-if="dateRange && dateRange.length === 2" closable @close="clearFilter('date')">
            {{ dateRange[0] }} 至 {{ dateRange[1] }}
          </el-tag>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { twitterApi, TwitterAccount } from '@/api/twitter'

interface FilterParams {
  media_type: 'image' | 'video' | 'gif' | ''
  account_id: number | null
  start_date: string
  end_date: string
  keyword: string
  min_size?: number
  max_size?: number
}

const emit = defineEmits<{
  (e: 'filter', params: FilterParams): void
}>()

const accounts = ref<TwitterAccount[]>([])
const dateRange = ref<string[]>([])
const sizeRange = ref([0, 100])

const filterForm = reactive<FilterParams>({
  media_type: '',
  account_id: null,
  start_date: '',
  end_date: '',
  keyword: ''
})

const hasFilters = computed(() => {
  return !!(
    filterForm.media_type ||
    filterForm.account_id ||
    (dateRange.value && dateRange.value.length === 2) ||
    filterForm.keyword
  )
})

function formatSizeTooltip(value: number): string {
  return `${value} MB`
}

function getMediaTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    image: '图片',
    video: '视频',
    gif: 'GIF'
  }
  return labels[type] || type
}

function getAccountName(id: number | null): string {
  if (!id) return ''
  const account = accounts.value.find(a => a.id === id)
  return account?.display_name || ''
}

function handleDateChange(value: string[] | null) {
  if (value && value.length === 2) {
    filterForm.start_date = value[0]
    filterForm.end_date = value[1]
  } else {
    filterForm.start_date = ''
    filterForm.end_date = ''
  }
  handleFilterChange()
}

function handleFilterChange() {
  const params: FilterParams = {
    media_type: filterForm.media_type,
    account_id: filterForm.account_id,
    start_date: filterForm.start_date,
    end_date: filterForm.end_date,
    keyword: filterForm.keyword
  }
  
  if (sizeRange.value[0] > 0) {
    params.min_size = sizeRange.value[0] * 1024 * 1024
  }
  if (sizeRange.value[1] < 100) {
    params.max_size = sizeRange.value[1] * 1024 * 1024
  }
  
  emit('filter', params)
}

function handleReset() {
  filterForm.media_type = ''
  filterForm.account_id = null
  filterForm.start_date = ''
  filterForm.end_date = ''
  filterForm.keyword = ''
  dateRange.value = []
  sizeRange.value = [0, 100]
  handleFilterChange()
}

function clearFilter(field: string) {
  switch (field) {
    case 'media_type':
      filterForm.media_type = ''
      break
    case 'account_id':
      filterForm.account_id = null
      break
    case 'date':
      dateRange.value = []
      filterForm.start_date = ''
      filterForm.end_date = ''
      break
  }
  handleFilterChange()
}

async function fetchAccounts() {
  try {
    const response = await twitterApi.getAccounts({ page_size: 100 })
    accounts.value = response.items
  } catch (error) {
    console.error('获取账号列表失败:', error)
  }
}

onMounted(() => {
  fetchAccounts()
})
</script>

<style scoped lang="scss">
.media-filter {
  .account-option {
    display: flex;
    align-items: center;

    .username {
      margin-left: 8px;
      color: var(--el-text-color-secondary);
      font-size: 12px;
    }
  }

  .filter-actions {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-top: 16px;
    padding-top: 16px;
    border-top: 1px solid var(--el-border-color-lighter);

    .filter-summary {
      display: flex;
      gap: 8px;
      margin-left: auto;
    }
  }

  .ml-8 {
    margin-left: 8px;
  }
}
</style>
