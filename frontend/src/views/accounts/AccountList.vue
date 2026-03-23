<template>
  <div class="account-list">
    <div class="list-header mb-20">
      <el-input
        v-model="searchKeyword"
        placeholder="搜索账号"
        clearable
        class="search-input"
        @keyup.enter="handleSearch"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
      <el-select v-model="statusFilter" placeholder="状态筛选" clearable class="status-select" @change="fetchAccounts">
        <el-option label="全部" value="" />
        <el-option label="活跃" value="active" />
        <el-option label="暂停" value="inactive" />
      </el-select>
    </div>

    <div v-loading="loading" class="account-cards">
      <el-row :gutter="20">
        <el-col v-for="account in accounts" :key="account.id" :xs="24" :sm="12" :md="8" :lg="6">
          <el-card class="account-card" shadow="hover" @click="handleCardClick(account)">
            <div class="card-content">
              <div class="avatar-section">
                <el-avatar :size="64" :src="account.avatar_url">
                  <el-icon :size="32"><User /></el-icon>
                </el-avatar>
                <el-tag
                  :type="account.is_active ? 'success' : 'info'"
                  size="small"
                  class="status-tag"
                >
                  {{ account.is_active ? '活跃' : '暂停' }}
                </el-tag>
              </div>
              <div class="info-section">
                <div class="display-name">{{ account.display_name }}</div>
                <div class="username">@{{ account.username }}</div>
                <div class="stats">
                  <span><el-icon><User /></el-icon> {{ formatNumber(account.followers_count) }}</span>
                  <span><el-icon><Document /></el-icon> {{ formatNumber(account.tweets_count) }}</span>
                </div>
              </div>
            </div>
            <div class="card-actions" @click.stop>
              <el-button-group>
                <el-button size="small" @click="handleSync(account)">
                  <el-icon><Refresh /></el-icon>
                </el-button>
                <el-button size="small" @click="handleToggle(account)">
                  <el-icon>
                    <VideoPause v-if="account.is_active" />
                    <VideoPlay v-else />
                  </el-icon>
                </el-button>
                <el-button size="small" type="danger" @click="handleDelete(account)">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </el-button-group>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <el-empty v-if="!loading && accounts.length === 0" description="暂无账号数据" />
    </div>

    <el-pagination
      v-if="pagination.total > 0"
      class="mt-20"
      v-model:current-page="pagination.page"
      v-model:page-size="pagination.pageSize"
      :total="pagination.total"
      :page-sizes="[8, 16, 32]"
      layout="total, sizes, prev, pager, next"
      @change="fetchAccounts"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { twitterApi, TwitterAccount, AccountListParams } from '@/api/twitter'

const emit = defineEmits<{
  (e: 'select', account: TwitterAccount): void
}>()

const loading = ref(false)
const accounts = ref<TwitterAccount[]>([])
const searchKeyword = ref('')
const statusFilter = ref('')

const pagination = reactive({
  page: 1,
  pageSize: 8,
  total: 0
})

async function fetchAccounts() {
  loading.value = true
  try {
    const params: AccountListParams = {
      page: pagination.page,
      page_size: pagination.pageSize,
      keyword: searchKeyword.value || undefined,
      is_active: statusFilter.value === 'active' ? true : statusFilter.value === 'inactive' ? false : undefined
    }
    const response = await twitterApi.getAccounts(params)
    accounts.value = response.items
    pagination.total = response.total
  } catch (error) {
    console.error('获取账号列表失败:', error)
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  pagination.page = 1
  fetchAccounts()
}

function handleCardClick(account: TwitterAccount) {
  emit('select', account)
}

async function handleSync(account: TwitterAccount) {
  try {
    await twitterApi.syncAccount(account.id)
    ElMessage.success(`正在同步账号: ${account.username}`)
  } catch (error) {
    ElMessage.error('同步失败')
  }
}

async function handleToggle(account: TwitterAccount) {
  try {
    await twitterApi.toggleAccountActive(account.id)
    account.is_active = !account.is_active
    ElMessage.success(`${account.username} 已${account.is_active ? '启用' : '暂停'}`)
  } catch (error) {
    ElMessage.error('操作失败')
  }
}

function handleDelete(account: TwitterAccount) {
  ElMessageBox.confirm(`确定要删除账号 @${account.username} 吗？删除后相关数据将无法恢复。`, '删除确认', {
    type: 'warning',
    confirmButtonText: '确定删除',
    cancelButtonText: '取消'
  }).then(async () => {
    try {
      await twitterApi.deleteAccount(account.id)
      ElMessage.success('删除成功')
      fetchAccounts()
    } catch (error) {
      ElMessage.error('删除失败')
    }
  })
}

function formatNumber(num: number): string {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1) + 'M'
  }
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'K'
  }
  return num.toString()
}

onMounted(() => {
  fetchAccounts()
})

defineExpose({
  refresh: fetchAccounts
})
</script>

<style scoped lang="scss">
.account-list {
  .list-header {
    display: flex;
    gap: 16px;
    flex-wrap: wrap;

    .search-input {
      width: 250px;
    }

    .status-select {
      width: 150px;
    }
  }

  .account-cards {
    min-height: 300px;
  }

  .account-card {
    margin-bottom: 20px;
    cursor: pointer;
    transition: all 0.3s;

    &:hover {
      .card-actions {
        opacity: 1;
      }
    }

    .card-content {
      text-align: center;

      .avatar-section {
        position: relative;
        display: inline-block;
        margin-bottom: 12px;

        .status-tag {
          position: absolute;
          bottom: -4px;
          right: -4px;
        }
      }

      .info-section {
        .display-name {
          font-weight: 600;
          font-size: 16px;
          margin-bottom: 4px;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .username {
          color: var(--el-text-color-secondary);
          font-size: 14px;
          margin-bottom: 8px;
        }

        .stats {
          display: flex;
          justify-content: center;
          gap: 16px;
          font-size: 12px;
          color: var(--el-text-color-regular);

          span {
            display: flex;
            align-items: center;
            gap: 4px;
          }
        }
      }
    }

    .card-actions {
      text-align: center;
      padding-top: 12px;
      border-top: 1px solid var(--el-border-color-lighter);
      opacity: 0;
      transition: opacity 0.3s;
    }
  }
}
</style>
