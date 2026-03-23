<template>
  <div class="telegram-settings">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>Telegram 配置</span>
          <el-tag :type="isConnected ? 'success' : 'info'">
            {{ isConnected ? '已连接' : '未连接' }}
          </el-tag>
        </div>
      </template>

      <el-form
        ref="formRef"
        :model="telegramForm"
        :rules="formRules"
        label-width="120px"
        class="settings-form"
      >
        <el-form-item label="API ID" prop="api_id">
          <el-input
            v-model="telegramForm.api_id"
            placeholder="请输入 Telegram API ID"
            :disabled="isConnected"
          />
        </el-form-item>
        <el-form-item label="API Hash" prop="api_hash">
          <el-input
            v-model="telegramForm.api_hash"
            placeholder="请输入 Telegram API Hash"
            :disabled="isConnected"
            show-password
          />
        </el-form-item>
        <el-form-item label="手机号" prop="phone">
          <el-input
            v-model="telegramForm.phone"
            placeholder="请输入手机号 (含国际区号)"
            :disabled="isConnected"
          >
            <template #prepend>+86</template>
          </el-input>
        </el-form-item>
        <el-form-item label="Session 字符串" v-if="isConnected">
          <el-input
            :model-value="telegramForm.session_string"
            type="textarea"
            :rows="3"
            readonly
          />
          <div class="form-tip">
            Session 已保存，可用于恢复登录状态
          </div>
        </el-form-item>
        <el-form-item>
          <el-button
            v-if="!isConnected"
            type="primary"
            @click="handleConnect"
            :loading="connecting"
          >
            连接 Telegram
          </el-button>
          <el-button v-else type="danger" plain @click="handleDisconnect">
            断开连接
          </el-button>
          <el-button @click="handleTest" :loading="testing" :disabled="!isConnected">
            测试连接
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="mt-20">
      <template #header>
        <span>上传配置</span>
      </template>
      
      <el-form :model="uploadConfig" label-width="120px" class="settings-form">
        <el-form-item label="目标频道/群组">
          <el-select
            v-model="uploadConfig.target_chat"
            placeholder="请选择目标频道或群组"
            filterable
            allow-create
          >
            <el-option
              v-for="chat in chatList"
              :key="chat.id"
              :label="chat.title"
              :value="chat.id"
            />
          </el-select>
          <el-button class="ml-10" @click="fetchChatList" :loading="loadingChats" :disabled="!isConnected">
            刷新列表
          </el-button>
        </el-form-item>
        <el-form-item label="自动上传">
          <el-switch v-model="uploadConfig.auto_upload" />
          <div class="form-tip">
            开启后，新下载的媒体将自动上传到 Telegram
          </div>
        </el-form-item>
        <el-form-item label="上传格式">
          <el-radio-group v-model="uploadConfig.upload_format">
            <el-radio label="album">相册模式</el-radio>
            <el-radio label="single">单张发送</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="添加水印">
          <el-switch v-model="uploadConfig.add_watermark" />
        </el-form-item>
        <el-form-item label="水印文字" v-if="uploadConfig.add_watermark">
          <el-input v-model="uploadConfig.watermark_text" placeholder="请输入水印文字" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="saveUploadConfig">保存配置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-dialog v-model="codeDialogVisible" title="验证码输入" width="400px">
      <el-form :model="codeForm" label-width="100px">
        <el-form-item label="验证码">
          <el-input
            v-model="codeForm.code"
            placeholder="请输入 Telegram 发送的验证码"
            autofocus
          />
        </el-form-item>
        <el-form-item label="两步验证密码" v-if="needPassword">
          <el-input
            v-model="codeForm.password"
            type="password"
            placeholder="如有两步验证请输入密码"
            show-password
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="codeDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitCode" :loading="verifying">
          验证
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, FormInstance, FormRules } from 'element-plus'
import { request } from '@/api/request'

interface Chat {
  id: string
  title: string
  type: 'channel' | 'group' | 'user'
}

const formRef = ref<FormInstance>()
const isConnected = ref(false)
const connecting = ref(false)
const testing = ref(false)
const loadingChats = ref(false)
const verifying = ref(false)
const needPassword = ref(false)
const codeDialogVisible = ref(false)
const chatList = ref<Chat[]>([])

const telegramForm = reactive({
  api_id: '',
  api_hash: '',
  phone: '',
  session_string: ''
})

const uploadConfig = reactive({
  target_chat: '',
  auto_upload: false,
  upload_format: 'album',
  add_watermark: false,
  watermark_text: ''
})

const codeForm = reactive({
  code: '',
  password: ''
})

const formRules: FormRules = {
  api_id: [{ required: true, message: '请输入 API ID', trigger: 'blur' }],
  api_hash: [{ required: true, message: '请输入 API Hash', trigger: 'blur' }],
  phone: [{ required: true, message: '请输入手机号', trigger: 'blur' }]
}

async function fetchStatus() {
  try {
    const response = await request.get<{
      connected: boolean
      phone?: string
      session_string?: string
    }>('/settings/telegram/status')
    isConnected.value = response.connected
    if (response.connected) {
      telegramForm.phone = response.phone || ''
      telegramForm.session_string = response.session_string || ''
    }
  } catch (error) {
    console.error('获取状态失败:', error)
  }
}

async function fetchChatList() {
  loadingChats.value = true
  try {
    const response = await request.get<Chat[]>('/settings/telegram/chats')
    chatList.value = response || []
  } catch (error) {
    ElMessage.error('获取聊天列表失败')
  } finally {
    loadingChats.value = false
  }
}

async function handleConnect() {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    
    connecting.value = true
    try {
      const response = await request.post<{ need_code: boolean; need_password: boolean }>(
        '/settings/telegram/connect',
        telegramForm
      )
      
      if (response.need_code) {
        needPassword.value = response.need_password
        codeDialogVisible.value = true
      } else {
        ElMessage.success('连接成功')
        isConnected.value = true
        fetchChatList()
      }
    } catch (error) {
      ElMessage.error('连接失败')
    } finally {
      connecting.value = false
    }
  })
}

async function submitCode() {
  verifying.value = true
  try {
    await request.post('/settings/telegram/verify', codeForm)
    ElMessage.success('验证成功')
    codeDialogVisible.value = false
    isConnected.value = true
    fetchStatus()
    fetchChatList()
  } catch (error) {
    ElMessage.error('验证失败')
  } finally {
    verifying.value = false
  }
}

async function handleDisconnect() {
  try {
    await request.post('/settings/telegram/disconnect')
    ElMessage.success('已断开连接')
    isConnected.value = false
    telegramForm.session_string = ''
  } catch (error) {
    ElMessage.error('断开连接失败')
  }
}

async function handleTest() {
  testing.value = true
  try {
    await request.post('/settings/telegram/test')
    ElMessage.success('连接正常')
  } catch (error) {
    ElMessage.error('连接异常')
  } finally {
    testing.value = false
  }
}

async function saveUploadConfig() {
  try {
    await request.post('/settings/telegram/upload-config', uploadConfig)
    ElMessage.success('配置已保存')
  } catch (error) {
    ElMessage.error('保存失败')
  }
}

async function fetchUploadConfig() {
  try {
    const response = await request.get<typeof uploadConfig>('/settings/telegram/upload-config')
    Object.assign(uploadConfig, response)
  } catch (error) {
    console.error('获取上传配置失败:', error)
  }
}

onMounted(() => {
  fetchStatus()
  fetchUploadConfig()
})
</script>

<style scoped lang="scss">
.telegram-settings {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .settings-form {
    max-width: 600px;
  }

  .form-tip {
    font-size: 12px;
    color: var(--el-text-color-secondary);
    margin-top: 4px;
  }

  .ml-10 {
    margin-left: 10px;
  }
}
</style>
