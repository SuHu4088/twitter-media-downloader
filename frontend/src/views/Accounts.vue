<template>
  <div class="accounts-page page-container">
    <div class="page-header mb-20">
      <el-button type="primary" @click="handleAddAccount">
        <el-icon><Plus /></el-icon>添加账号
      </el-button>
    </div>

    <el-table :data="accounts" v-loading="loading" stripe>
      <el-table-column prop="username" label="用户名" width="150" />
      <el-table-column prop="display_name" label="显示名称" width="150" />
      <el-table-column label="头像" width="80">
        <template #default="{ row }">
          <el-avatar :size="40" :src="row.avatar_url" />
        </template>
      </el-table-column>
      <el-table-column prop="followers_count" label="粉丝数" width="100" />
      <el-table-column prop="tweets_count" label="推文数" width="100" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'info'">
            {{ row.is_active ? '活跃' : '暂停' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="添加时间" width="180" />
      <el-table-column label="操作" fixed="right" width="200">
        <template #default="{ row }">
          <el-button size="small" @click="handleSync(row)">同步</el-button>
          <el-button size="small" @click="handleToggle(row)">
            {{ row.is_active ? '暂停' : '启用' }}
          </el-button>
          <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
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
      @change="fetchAccounts"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

interface Account {
  id: number
  username: string
  display_name: string
  avatar_url: string
  followers_count: number
  tweets_count: number
  is_active: boolean
  created_at: string
}

const loading = ref(false)
const accounts = ref<Account[]>([])

const pagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0
})

async function fetchAccounts() {
  loading.value = true
  try {
    accounts.value = [
      {
        id: 1,
        username: 'example_user',
        display_name: 'Example User',
        avatar_url: '',
        followers_count: 1000,
        tweets_count: 500,
        is_active: true,
        created_at: '2024-01-10 10:00'
      }
    ]
    pagination.total = 1
  } finally {
    loading.value = false
  }
}

function handleAddAccount() {
  ElMessage.info('请使用OAuth授权添加账号')
}

function handleSync(row: Account) {
  ElMessage.success(`正在同步账号: ${row.username}`)
}

function handleToggle(row: Account) {
  row.is_active = !row.is_active
  ElMessage.success(`${row.username} 已${row.is_active ? '启用' : '暂停'}`)
}

function handleDelete(row: Account) {
  ElMessageBox.confirm(`确定要删除账号 ${row.username} 吗？`, '提示', {
    type: 'warning'
  }).then(() => {
    ElMessage.success('删除成功')
    fetchAccounts()
  })
}

onMounted(() => {
  fetchAccounts()
})
</script>

<style scoped lang="scss">
.accounts-page {
  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
}
</style>
