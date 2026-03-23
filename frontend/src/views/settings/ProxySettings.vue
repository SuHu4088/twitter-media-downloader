<template>
  <div class="proxy-settings">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>代理配置</span>
          <el-button type="primary" @click="handleAdd">
            <el-icon><Plus /></el-icon>
            添加代理
          </el-button>
        </div>
      </template>

      <el-table :data="proxyList" v-loading="loading" stripe>
        <el-table-column prop="name" label="名称" width="150" />
        <el-table-column prop="type" label="类型" width="100">
          <template #default="{ row }">
            <el-tag size="small">{{ row.type.toUpperCase() }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="host" label="主机" width="180" />
        <el-table-column prop="port" label="端口" width="80" />
        <el-table-column prop="username" label="用户名" width="120">
          <template #default="{ row }">
            {{ row.username || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : row.status === 'inactive' ? 'info' : 'danger'">
              {{ getStatusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="延迟" width="100">
          <template #default="{ row }">
            <span v-if="row.latency">{{ row.latency }}ms</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" fixed="right" width="200">
          <template #default="{ row }">
            <el-button size="small" @click="handleTest(row)" :loading="row.testing">
              测试
            </el-button>
            <el-button size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="editingProxy ? '编辑代理' : '添加代理'"
      width="500px"
      destroy-on-close
    >
      <el-form
        ref="formRef"
        :model="proxyForm"
        :rules="formRules"
        label-width="100px"
      >
        <el-form-item label="名称" prop="name">
          <el-input v-model="proxyForm.name" placeholder="请输入代理名称" />
        </el-form-item>
        <el-form-item label="类型" prop="type">
          <el-select v-model="proxyForm.type" placeholder="请选择代理类型">
            <el-option label="HTTP" value="http" />
            <el-option label="HTTPS" value="https" />
            <el-option label="SOCKS5" value="socks5" />
          </el-select>
        </el-form-item>
        <el-form-item label="主机" prop="host">
          <el-input v-model="proxyForm.host" placeholder="请输入代理主机地址" />
        </el-form-item>
        <el-form-item label="端口" prop="port">
          <el-input-number v-model="proxyForm.port" :min="1" :max="65535" />
        </el-form-item>
        <el-form-item label="用户名">
          <el-input v-model="proxyForm.username" placeholder="可选，如需认证请填写" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input
            v-model="proxyForm.password"
            type="password"
            placeholder="可选，如需认证请填写"
            show-password
          />
        </el-form-item>
        <el-form-item label="设为默认">
          <el-switch v-model="proxyForm.is_default" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">
          确定
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox, FormInstance, FormRules } from 'element-plus'
import { request } from '@/api/request'

interface Proxy {
  id: number
  name: string
  type: 'http' | 'https' | 'socks5'
  host: string
  port: number
  username?: string
  password?: string
  is_default: boolean
  status: 'active' | 'inactive' | 'error'
  latency?: number
  testing?: boolean
}

const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)
const proxyList = ref<Proxy[]>([])
const editingProxy = ref<Proxy | null>(null)
const formRef = ref<FormInstance>()

const proxyForm = reactive({
  name: '',
  type: 'http' as 'http' | 'https' | 'socks5',
  host: '',
  port: 7890,
  username: '',
  password: '',
  is_default: false
})

const formRules: FormRules = {
  name: [{ required: true, message: '请输入代理名称', trigger: 'blur' }],
  type: [{ required: true, message: '请选择代理类型', trigger: 'change' }],
  host: [{ required: true, message: '请输入代理主机地址', trigger: 'blur' }],
  port: [{ required: true, message: '请输入端口号', trigger: 'blur' }]
}

function getStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    active: '正常',
    inactive: '未使用',
    error: '异常'
  }
  return labels[status] || status
}

async function fetchProxyList() {
  loading.value = true
  try {
    const response = await request.get<Proxy[]>('/settings/proxies')
    proxyList.value = response || []
  } catch (error) {
    proxyList.value = [
      {
        id: 1,
        name: '本地代理',
        type: 'http',
        host: '127.0.0.1',
        port: 7890,
        is_default: true,
        status: 'active',
        latency: 15
      }
    ]
  } finally {
    loading.value = false
  }
}

function handleAdd() {
  editingProxy.value = null
  Object.assign(proxyForm, {
    name: '',
    type: 'http',
    host: '',
    port: 7890,
    username: '',
    password: '',
    is_default: false
  })
  dialogVisible.value = true
}

function handleEdit(row: Proxy) {
  editingProxy.value = row
  Object.assign(proxyForm, {
    name: row.name,
    type: row.type,
    host: row.host,
    port: row.port,
    username: row.username || '',
    password: '',
    is_default: row.is_default
  })
  dialogVisible.value = true
}

async function handleSubmit() {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    
    submitting.value = true
    try {
      if (editingProxy.value) {
        await request.put(`/settings/proxies/${editingProxy.value.id}`, proxyForm)
        ElMessage.success('更新成功')
      } else {
        await request.post('/settings/proxies', proxyForm)
        ElMessage.success('添加成功')
      }
      dialogVisible.value = false
      fetchProxyList()
    } catch (error) {
      ElMessage.error('操作失败')
    } finally {
      submitting.value = false
    }
  })
}

async function handleTest(row: Proxy) {
  row.testing = true
  try {
    const result = await request.post<{ success: boolean; latency: number }>(`/settings/proxies/${row.id}/test`)
    row.status = result.success ? 'active' : 'error'
    row.latency = result.latency
    ElMessage.success(result.success ? `连接成功，延迟: ${result.latency}ms` : '连接失败')
  } catch (error) {
    row.status = 'error'
    ElMessage.error('测试失败')
  } finally {
    row.testing = false
  }
}

function handleDelete(row: Proxy) {
  ElMessageBox.confirm(`确定要删除代理 "${row.name}" 吗？`, '删除确认', {
    type: 'warning'
  }).then(async () => {
    try {
      await request.delete(`/settings/proxies/${row.id}`)
      ElMessage.success('删除成功')
      fetchProxyList()
    } catch (error) {
      ElMessage.error('删除失败')
    }
  })
}

onMounted(() => {
  fetchProxyList()
})
</script>

<style scoped lang="scss">
.proxy-settings {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
}
</style>
