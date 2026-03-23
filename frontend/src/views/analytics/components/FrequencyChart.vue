<template>
  <div class="frequency-chart" ref="chartRef"></div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'

interface FrequencyData {
  date: string
  count: number
}

interface Props {
  data: FrequencyData[]
  type: 'daily' | 'weekly' | 'monthly'
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  loading: false
})

const chartRef = ref<HTMLElement>()
let chartInstance: echarts.ECharts | null = null

function initChart() {
  if (!chartRef.value) return
  
  chartInstance = echarts.init(chartRef.value)
  updateChart()
}

function updateChart() {
  if (!chartInstance) return
  
  const xAxisData = props.data.map(item => item.date)
  const seriesData = props.data.map(item => item.count)
  
  const typeLabels = {
    daily: '每日发布',
    weekly: '每周发布',
    monthly: '每月发布'
  }
  
  const option: echarts.EChartsOption = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      },
      formatter: (params: any) => {
        const data = params[0]
        return `${data.axisValue}<br/>${typeLabels[props.type]}: ${data.value} 条`
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '10%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: xAxisData,
      axisLabel: {
        rotate: 45,
        fontSize: 11
      },
      axisTick: {
        alignWithLabel: true
      }
    },
    yAxis: {
      type: 'value',
      name: '发布数量',
      axisLine: {
        show: true
      }
    },
    series: [
      {
        name: typeLabels[props.type],
        type: 'bar',
        data: seriesData,
        barWidth: '60%',
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#409eff' },
            { offset: 1, color: '#79bbff' }
          ]),
          borderRadius: [4, 4, 0, 0]
        },
        emphasis: {
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: '#337ecc' },
              { offset: 1, color: '#409eff' }
            ])
          }
        }
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

watch(() => props.type, () => {
  nextTick(() => {
    updateChart()
  })
})

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
.frequency-chart {
  width: 100%;
  height: 300px;
}
</style>
