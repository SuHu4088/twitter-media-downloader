<template>
  <el-dialog
    v-model="visible"
    :title="media?.media_type === 'video' ? '视频预览' : '图片预览'"
    width="80%"
    top="5vh"
    destroy-on-close
    class="media-detail-dialog"
  >
    <div class="media-detail" v-if="media">
      <div class="preview-section">
        <div class="preview-container" :class="{ 'is-video': media.media_type === 'video' }">
          <img
            v-if="media.media_type === 'image' || media.media_type === 'gif'"
            :src="media.media_url"
            :alt="media.tweet_id"
          />
          <video
            v-else
            :src="media.media_url"
            controls
            autoplay
            class="video-player"
          />
        </div>
      </div>

      <div class="info-section">
        <el-card class="info-card">
          <template #header>
            <div class="card-header">
              <span>推文信息</span>
              <el-button type="primary" link @click="openTweet">
                <el-icon><Link /></el-icon>
                查看原推文
              </el-button>
            </div>
          </template>

          <el-descriptions :column="1" border>
            <el-descriptions-item label="发布者">
              <div class="user-info">
                <el-avatar :size="24" :src="media.account_avatar" />
                <span>{{ media.account_name }}</span>
              </div>
            </el-descriptions-item>
            <el-descriptions-item label="推文ID">{{ media.tweet_id }}</el-descriptions-item>
            <el-descriptions-item label="媒体类型">
              <el-tag size="small">{{ getMediaTypeLabel(media.media_type) }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="文件大小">{{ formatSize(media.file_size) }}</el-descriptions-item>
            <el-descriptions-item v-if="media.width && media.height" label="尺寸">
              {{ media.width }} x {{ media.height }}
            </el-descriptions-item>
            <el-descriptions-item v-if="media.duration" label="时长">
              {{ formatDuration(media.duration) }}
            </el-descriptions-item>
            <el-descriptions-item label="下载时间">
              {{ media.downloaded_at || '未下载' }}
            </el-descriptions-item>
            <el-descriptions-item label="本地路径" v-if="media.local_path">
              <el-tooltip :content="media.local_path" placement="top">
                <span class="path-text">{{ media.local_path }}</span>
              </el-tooltip>
            </el-descriptions-item>
          </el-descriptions>
        </el-card>

        <el-card class="action-card mt-20">
          <template #header>操作</template>
          <div class="action-buttons">
            <el-button type="primary" @click="handleDownload" :loading="downloading">
              <el-icon><Download /></el-icon>
              下载到本地
            </el-button>
            <el-button @click="handleCopyLink">
              <el-icon><Link /></el-icon>
              复制链接
            </el-button>
            <el-button type="danger" plain @click="handleDelete">
              <el-icon><Delete /></el-icon>
              删除
            </el-button>
          </div>
        </el-card>

        <el-card class="tweet-card mt-20" v-if="tweetContent">
          <template #header>推文内容</template>
          <div class="tweet-content">{{ tweetContent }}</div>
        </el-card>
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handlePrev" :disabled="!hasPrev">
          <el-icon><ArrowLeft /></el-icon>
          上一个
        </el-button>
        <span class="page-info">{{ currentIndex + 1 }} / {{ totalCount }}</span>
        <el-button @click="handleNext" :disabled="!hasNext">
          下一个
          <el-icon><ArrowRight /></el-icon>
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { mediaApi, Media } from '@/api/media'

interface Props {
  modelValue: boolean
  media: Media | null
  currentIndex?: number
  totalCount?: number
}

const props = withDefaults(defineProps<Props>(), {
  currentIndex: 0,
  totalCount: 0
})

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'prev'): void
  (e: 'next'): void
  (e: 'delete', mediaId: number): void
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const downloading = ref(false)
const tweetContent = ref('')

const hasPrev = computed(() => props.currentIndex > 0)
const hasNext = computed(() => props.currentIndex < props.totalCount - 1)

function formatSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1024 / 1024).toFixed(1) + ' MB'
}

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

function getMediaTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    image: '图片',
    video: '视频',
    gif: 'GIF'
  }
  return labels[type] || type
}

function openTweet() {
  if (props.media) {
    window.open(`https://twitter.com/i/status/${props.media.tweet_id}`, '_blank')
  }
}

async function handleDownload() {
  if (!props.media) return
  
  downloading.value = true
  try {
    const result = await mediaApi.downloadMedia(props.media.id)
    const link = document.createElement('a')
    link.href = result.download_url
    link.download = `${props.media.tweet_id}_${props.media.id}`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    ElMessage.success('下载成功')
  } catch (error) {
    ElMessage.error('下载失败')
  } finally {
    downloading.value = false
  }
}

async function handleCopyLink() {
  if (!props.media) return
  
  try {
    await navigator.clipboard.writeText(props.media.media_url)
    ElMessage.success('链接已复制')
  } catch (error) {
    ElMessage.error('复制失败')
  }
}

function handleDelete() {
  if (!props.media) return
  
  ElMessageBox.confirm('确定要删除这个媒体文件吗？', '删除确认', {
    type: 'warning'
  }).then(async () => {
    try {
      await mediaApi.deleteMedia(props.media!.id)
      ElMessage.success('删除成功')
      emit('delete', props.media!.id)
      visible.value = false
    } catch (error) {
      ElMessage.error('删除失败')
    }
  })
}

function handlePrev() {
  emit('prev')
}

function handleNext() {
  emit('next')
}

watch(() => props.media, async (newMedia) => {
  if (newMedia) {
    tweetContent.value = ''
  }
})
</script>

<style scoped lang="scss">
.media-detail-dialog {
  :deep(.el-dialog__body) {
    padding: 0;
  }
}

.media-detail {
  display: flex;
  height: 70vh;

  .preview-section {
    flex: 1;
    background: #000;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;

    .preview-container {
      max-width: 100%;
      max-height: 100%;

      img,
      video {
        max-width: 100%;
        max-height: 100%;
        object-fit: contain;
      }

      &.is-video {
        width: 100%;
        height: 100%;

        .video-player {
          width: 100%;
          height: 100%;
        }
      }
    }
  }

  .info-section {
    width: 350px;
    padding: 20px;
    overflow-y: auto;
    background: var(--el-bg-color-page);

    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .user-info {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .path-text {
      max-width: 200px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      display: inline-block;
    }

    .action-buttons {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
    }

    .tweet-content {
      white-space: pre-wrap;
      word-break: break-word;
      line-height: 1.6;
    }
  }
}

.dialog-footer {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 20px;

  .page-info {
    color: var(--el-text-color-secondary);
    font-size: 14px;
  }
}
</style>
