<template>
  <div class="media-type-chart" ref="chartRef"></div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'

interface MediaTypeData {
  name: string
  value: number
}

interface Props {
  data: MediaTypeData[]
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  loading: false
})

const chartRef = ref<HTMLElement>()
let chartInstance: echarts.ECharts | null = null

const colorMap: Record<string, string> = {
  '图片': '#409eff',
  '视频': '#67c23a',
  'GIF': '#e6a23c'
}

function initChart() {
  if (!chartRef.value) return
  
  chartInstance = echarts.init(chartRef.value)
  updateChart()
}

function updateChart() {
  if (!chartInstance) return
  
  const total = props.data.reduce((sum, item) => sum + item.value, 0)
  
  const option: echarts.EChartsOption = {
    tooltip: {
      trigger: 'item',
      formatter: (params: any) => {
        const percent = total > 0 ? ((params.value / total) * 100).toFixed(1) : 0
        return `${params.name}<br/>数量: ${params.value}<br/>占比: ${percent}%`
      }
    },
    legend: {
      orient: 'vertical',
      right: '5%',
      top: 'center',
      itemGap: 16,
      formatter: (name: string) => {
        const item = props.data.find(d => d.name === name)
        return `${name}  ${item?.value || 0}`
      }
    },
    series: [
      {
        name: '媒体类型',
        type: 'pie',
        radius: ['45%', '70%'],
        center: ['35%', '50%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 8,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: {
          show: false,
          position: 'center'
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 18,
            fontWeight: 'bold',
            formatter: (params: any) => {
              return `${params.name}\n${params.value}`
            }
          },
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: 'rgba(0, 0, 0, 0.2)'
          }
        },
        labelLine: {
          show: false
        },
        data: props.data.map(item => ({
          name: item.name,
          value: item.value,
          itemStyle: {
            color: colorMap[item.name] || '#909399'
          }
        }))
      }
    ]
  }
  
  chartInstance.setOption(option, true)
}

function handleResize() {
  chartInstance?.resize()
}

watch(() => props.data, () => {
  nextTick(() => {
    updateChart()
  })
}, { deep: true })

onMounted(() => {
  nextTick(() => {
    initChart()
  })
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  chartInstance?.dispose()
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped lang="scss">
.media-type-chart {
  width: 100%;
  height: 300px;
}
</style>
