<template>
  <div class="media-grid" ref="gridContainer">
    <div v-loading="loading" class="grid-container" :style="gridStyle">
      <div
        v-for="(item, index) in mediaList"
        :key="item.id"
        class="media-item"
        :style="getItemStyle(item, index)"
        @click="handleItemClick(item)"
      >
        <div class="media-preview">
          <img
            v-if="item.media_type === 'image'"
            :src="getThumbnailUrl(item)"
            :alt="item.tweet_id"
            loading="lazy"
            @error="handleImageError"
          />
          <div v-else-if="item.media_type === 'gif'" class="gif-preview">
            <img :src="item.media_url" :alt="item.tweet_id" loading="lazy" @error="handleImageError" />
            <span class="gif-badge">GIF</span>
          </div>
          <div v-else class="video-preview">
            <el-icon :size="48"><VideoPlay /></el-icon>
            <span v-if="item.duration" class="duration">{{ formatDuration(item.duration) }}</span>
          </div>
          <div class="media-overlay">
            <el-icon :size="24"><ZoomIn /></el-icon>
          </div>
        </div>
        <div class="media-info">
          <div class="media-meta">
            <el-avatar :size="20" :src="item.account_avatar" />
            <span class="account-name">{{ item.account_name }}</span>
          </div>
          <div class="media-size">{{ formatSize(item.file_size) }}</div>
        </div>
        <div class="media-checkbox" @click.stop>
          <el-checkbox v-model="selectedItems" :value="item.id" />
        </div>
      </div>
    </div>

    <el-empty v-if="!loading && mediaList.length === 0" description="暂无媒体数据" />

    <div v-if="selectedItems.length > 0" class="batch-actions">
      <el-button type="danger" @click="handleBatchDelete">
        删除选中 ({{ selectedItems.length }})
      </el-button>
      <el-button @click="selectedItems = []">取消选择</el-button>
    </div>

    <el-pagination
      v-if="pagination.total > 0"
      class="mt-20"
      v-model:current-page="pagination.page"
      v-model:page-size="pagination.pageSize"
      :total="pagination.total"
      :page-sizes="[20, 40, 60, 100]"
      layout="total, sizes, prev, pager, next"
      @change="handlePageChange"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { mediaApi, Media, MediaListParams } from '@/api/media'

interface Props {
  filters?: {
    media_type?: 'image' | 'video' | 'gif' | ''
    account_id?: number | null
    start_date?: string
    end_date?: string
  }
}

const props = withDefaults(defineProps<Props>(), {
  filters: () => ({})
})

const emit = defineEmits<{
  (e: 'select', media: Media): void
  (e: 'update'): void
}>()

const loading = ref(false)
const mediaList = ref<Media[]>([])
const selectedItems = ref<number[]>([])
const gridContainer = ref<HTMLElement>()

const pagination = ref({
  page: 1,
  pageSize: 40,
  total: 0
})

const gridStyle = computed(() => ({
  columnCount: Math.max(2, Math.floor((window.innerWidth - 300) / 250))
}))

function getItemStyle(item: Media, index: number) {
  const aspectRatio = item.height && item.width ? item.height / item.width : 0.75
  return {
    breakInside: 'avoid',
    marginBottom: '16px'
  }
}

function getThumbnailUrl(item: Media): string {
  if (item.local_path) {
    return `/api/media/file/${item.id}`
  }
  return item.media_url
}

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

function handleImageError(event: Event) {
  const target = event.target as HTMLImageElement
  target.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="200" height="200"%3E%3Crect fill="%23f5f7fa" width="200" height="200"/%3E%3Ctext fill="%23909399" x="50%25" y="50%25" text-anchor="middle" dy=".3em"%3E加载失败%3C/text%3E%3C/svg%3E'
}

function handleItemClick(item: Media) {
  emit('select', item)
}

async function fetchMedia() {
  loading.value = true
  try {
    const params: MediaListParams = {
      page: pagination.value.page,
      page_size: pagination.value.pageSize,
      media_type: props.filters.media_type || undefined,
      account_id: props.filters.account_id || undefined,
      start_date: props.filters.start_date || undefined,
      end_date: props.filters.end_date || undefined
    }
    const response = await mediaApi.getMediaList(params)
    mediaList.value = response.items
    pagination.value.total = response.total
  } catch (error) {
    console.error('获取媒体列表失败:', error)
  } finally {
    loading.value = false
  }
}

function handlePageChange() {
  fetchMedia()
}

async function handleBatchDelete() {
  try {
    await ElMessageBox.confirm(`确定要删除选中的 ${selectedItems.value.length} 个媒体吗？`, '批量删除', {
      type: 'warning'
    })
    await mediaApi.batchDeleteMedia(selectedItems.value)
    ElMessage.success('删除成功')
    selectedItems.value = []
    fetchMedia()
    emit('update')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

function handleScroll() {
  const container = gridContainer.value
  if (!container) return
  
  const { scrollTop, scrollHeight, clientHeight } = document.documentElement
  if (scrollTop + clientHeight >= scrollHeight - 100) {
    if (!loading.value && pagination.value.page * pagination.value.pageSize < pagination.value.total) {
      pagination.value.page++
      fetchMedia()
    }
  }
}

onMounted(() => {
  fetchMedia()
})

onUnmounted(() => {
  window.removeEventListener('scroll', handleScroll)
})

defineExpose({
  refresh: fetchMedia
})

watch(() => props.filters, () => {
  pagination.value.page = 1
  fetchMedia()
}, { deep: true })
</script>

<script lang="ts">
import { watch } from 'vue'
export default {
  name: 'MediaGrid'
}
</script>

<style scoped lang="scss">
.media-grid {
  .grid-container {
    column-gap: 16px;
  }

  .media-item {
    background: #fff;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
    cursor: pointer;
    position: relative;
    transition: transform 0.3s, box-shadow 0.3s;

    &:hover {
      transform: translateY(-4px);
      box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);

      .media-overlay {
        opacity: 1;
      }

      .media-checkbox {
        opacity: 1;
      }
    }

    .media-preview {
      position: relative;
      background: #f5f7fa;
      min-height: 150px;
      display: flex;
      align-items: center;
      justify-content: center;

      img {
        width: 100%;
        display: block;
      }

      .gif-preview,
      .video-preview {
        width: 100%;
        display: flex;
        align-items: center;
        justify-content: center;
        position: relative;

        img {
          width: 100%;
        }
      }

      .gif-badge,
      .duration {
        position: absolute;
        bottom: 8px;
        right: 8px;
        background: rgba(0, 0, 0, 0.7);
        color: #fff;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 12px;
      }

      .video-preview {
        min-height: 200px;
        color: #909399;
      }

      .media-overlay {
        position: absolute;
        inset: 0;
        background: rgba(0, 0, 0, 0.3);
        display: flex;
        align-items: center;
        justify-content: center;
        color: #fff;
        opacity: 0;
        transition: opacity 0.3s;
      }
    }

    .media-info {
      padding: 12px;

      .media-meta {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 4px;

        .account-name {
          font-size: 14px;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
      }

      .media-size {
        font-size: 12px;
        color: var(--el-text-color-secondary);
      }
    }

    .media-checkbox {
      position: absolute;
      top: 8px;
      left: 8px;
      opacity: 0;
      transition: opacity 0.3s;
      background: rgba(255, 255, 255, 0.9);
      border-radius: 4px;
      padding: 4px;
    }
  }

  .batch-actions {
    position: fixed;
    bottom: 80px;
    left: 50%;
    transform: translateX(-50%);
    background: #fff;
    padding: 12px 24px;
    border-radius: 8px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
    display: flex;
    gap: 12px;
    z-index: 100;
  }
}
</style>
