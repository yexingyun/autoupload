<template>
  <el-dialog
    :model-value="visible"
    title="发布进度"
    width="540px"
    :close-on-click-modal="false"
    :close-on-press-escape="false"
    :show-close="phase === 'done'"
    @close="handleClose"
  >
    <!-- 顶部进度条 -->
    <div class="progress-header" v-if="accountItems.length > 0">
      <el-progress
        :percentage="overallPercentage"
        :status="overallPercentage === 100 ? (failCount > 0 ? 'exception' : 'success') : ''"
        :stroke-width="12"
      />
      <p class="progress-summary">
        <template v-if="phase === 'publishing'">
          正在发布... ({{ completeCount }}/{{ accountItems.length }})
        </template>
        <template v-else-if="phase === 'done'">
          发布完成：{{ successCount }} 个成功，{{ failCount }} 个失败
        </template>
      </p>
    </div>

    <!-- 空状态 -->
    <el-empty v-if="accountItems.length === 0" description="暂无账号数据" />

    <!-- 账号时间线 -->
    <div class="account-timeline" ref="timelineRef" v-if="accountItems.length > 0">
      <div
        v-for="(item, index) in accountItems"
        :key="item.accountId"
        :class="['timeline-item', item.status]"
      >
        <!-- 左侧：竖线 + 状态点 -->
        <div class="timeline-connector">
          <div class="timeline-dot" :class="item.status">
            <el-icon v-if="item.status === 'completed'"><CircleCheckFilled /></el-icon>
            <el-icon v-else-if="item.status === 'error'"><CircleCloseFilled /></el-icon>
            <el-icon v-else-if="item.status === 'publishing'" class="is-loading"><Loading /></el-icon>
            <el-icon v-else><Minus /></el-icon>
          </div>
          <div v-if="index < accountItems.length - 1" class="connector-line" />
        </div>
        <!-- 右侧：内容 -->
        <div class="timeline-content">
          <div class="content-header">
            <span class="account-name">{{ item.accountName }}</span>
            <el-tag :type="statusTagType(item.status)" size="small" effect="plain">
              {{ statusText(item.status) }}
            </el-tag>
          </div>
          <!-- 错误详情 -->
          <transition name="el-zoom-in-top">
            <div v-if="item.status === 'error'" class="error-detail">
              <div class="error-message">
                <el-icon><WarningFilled /></el-icon>
                <span>{{ item.errorMessage }}</span>
              </div>
              <div v-if="item.suggestion" class="error-suggestion">
                <el-icon><InfoFilled /></el-icon>
                <span>{{ item.suggestion }}</span>
              </div>
              <div class="error-actions">
                <el-button
                  size="small"
                  type="primary"
                  plain
                  @click="retryAccount(item.accountId)"
                  :loading="item._retrying"
                >
                  <el-icon><Refresh /></el-icon> 重新发布
                </el-button>
                <el-button
                  v-if="item.errorType === 'cookie'"
                  size="small"
                  type="warning"
                  plain
                  @click="openLogin(item)"
                  :disabled="item._logining"
                >
                  <el-icon><Refresh /></el-icon> 重新登录并发布
                </el-button>
              </div>
              <!-- 登录中状态 -->
              <div v-if="item._logining" class="login-inline-status">
                <template v-if="item._loginStatus === 'connecting'">
                  <el-icon class="is-loading"><Loading /></el-icon>
                  <span>正在获取二维码...</span>
                </template>
                <template v-else-if="item._loginStatus === 'qr_ready'">
                  <div class="qr-platform-label">
                    正在登录：<el-tag :type="platformTagType(getPlatformName(item.accountType))" size="small" effect="plain">{{ getPlatformName(item.accountType) }}</el-tag>
                  </div>
                  <div class="qr-image-wrapper">
                    <img :src="item._qrCodeData" class="qr-image" alt="登录二维码" />
                  </div>
                  <p class="qr-tip">请使用 <strong>{{ getPlatformName(item.accountType) }}</strong> APP 扫描二维码登录</p>
                </template>
                <template v-else-if="item._loginStatus === 'success'">
                  <el-icon class="login-success-icon"><CircleCheckFilled /></el-icon>
                  <span>登录成功，正在重新发布...</span>
                </template>
                <template v-else-if="item._loginStatus === 'failed'">
                  <el-icon class="login-fail-icon"><CircleCloseFilled /></el-icon>
                  <span>{{ item._loginError || '登录失败' }}</span>
                  <el-button size="small" type="warning" plain @click="openLogin(item)">
                    重试登录
                  </el-button>
                </template>
              </div>
            </div>
          </transition>
        </div>
      </div>
    </div>

    <template #footer>
      <span class="dialog-footer">
        <el-button @click="handleClose" :disabled="phase === 'publishing'">
          {{ phase === 'done' ? '关闭' : '取消' }}
        </el-button>
        <el-button
          v-if="phase === 'done' && failCount > 0"
          type="primary"
          @click="retryAllFailed"
        >
          <el-icon><Refresh /></el-icon> 全部重试
        </el-button>
      </span>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch, nextTick, onBeforeUnmount } from 'vue'
import {
  CircleCheckFilled, CircleCloseFilled,
  Loading, Minus, WarningFilled, InfoFilled, Refresh
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5409'

// 创建一个不带响应拦截器的 axios 实例，避免自动弹出错误提示
const apiClient = axios.create({
  baseURL: apiBaseUrl,
  headers: { 'Content-Type': 'application/json' }
})
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

const props = defineProps({
  visible: Boolean,
  tab: { type: Object, default: null },
  accounts: { type: Array, default: () => [] }
})

const emit = defineEmits(['update:visible', 'done', 'relogin-done'])

// 跟踪所有活跃的 SSE 连接，用于组件卸载时清理
const _activeSSEConnections = new Set()

onBeforeUnmount(() => {
  _activeSSEConnections.forEach(es => {
    try { es.close() } catch (_) {}
  })
  _activeSSEConnections.clear()
})

// ============ 发布进度状态 ============
const timelineRef = ref(null)
const phase = ref('idle') // 'idle' | 'publishing' | 'done'
const accountItems = ref([])
const _cancelled = ref(false)

// 计算属性
const completeCount = computed(() =>
  accountItems.value.filter(i => i.status === 'completed' || i.status === 'error').length
)
const successCount = computed(() =>
  accountItems.value.filter(i => i.status === 'completed').length
)
const failCount = computed(() =>
  accountItems.value.filter(i => i.status === 'error').length
)
const overallPercentage = computed(() => {
  if (accountItems.value.length === 0) return 0
  return Math.round((completeCount.value / accountItems.value.length) * 100)
})

// 状态映射
const statusTextMap = {
  waiting: '等待中',
  publishing: '发布中...',
  completed: '发布完成',
  error: '发布异常'
}
const statusTagTypeMap = {
  waiting: 'info',
  publishing: 'primary',
  completed: 'success',
  error: 'danger'
}

function statusText(status) {
  return statusTextMap[status] || status
}

function statusTagType(status) {
  return statusTagTypeMap[status] || 'info'
}

// 平台编号到中文名的映射（1=小红书, 2=视频号, 3=抖音, 4=快手）
const typeToPlatform = {
  1: '小红书',
  2: '视频号',
  3: '抖音',
  4: '快手'
}

function getPlatformName(type) {
  return typeToPlatform[type] || '未知'
}

// 平台标签样式
function platformTagType(platform) {
  const typeMap = {
    '快手': 'success',
    '抖音': 'danger',
    '视频号': 'warning',
    '小红书': 'info'
  }
  return typeMap[platform] || 'info'
}

// 初始化项目列表
function initItems() {
  accountItems.value = (props.accounts || []).map(a => ({
    accountId: a.id,
    accountName: a.name,
    accountType: a.type,
    platform: a.platform,
    filePath: a.filePath,
    status: 'waiting',
    errorMessage: null,
    errorType: null,
    suggestion: null,
    _retrying: false,
    // 登录相关
    _logining: false,
    _loginStatus: '',   // 'connecting' | 'qr_ready' | 'success' | 'failed' | ''
    _qrCodeData: '',
    _loginError: ''
  }))
}

// 错误分类
function classifyError(error) {
  const msg = String(error?.response?.data?.msg || error?.message || '').toLowerCase()
  if (/cookie|登录|过期|未登录|token/.test(msg)) {
    return {
      errorType: 'cookie',
      suggestion: '请尝试重新登录后发布'
    }
  }
  if (!error.response || error.code === 'ECONNABORTED' || error.message === 'Network Error') {
    return {
      errorType: 'network',
      suggestion: '请检查网络连接后重试'
    }
  }
  return { errorType: 'server', suggestion: null }
}

function getErrorMessage(error) {
  return error?.response?.data?.msg || error?.message || '未知错误'
}

// ============ SSE 登录 ============
function closeSSEConnection(eventSource) {
  if (eventSource) {
    eventSource.close()
    _activeSSEConnections.delete(eventSource)
  }
}

function openLogin(item) {
  if (item._logining) return

  const account = props.accounts.find(a => a.id === item.accountId)
  if (!account) {
    ElMessage.error('账号信息缺失')
    return
  }

  // 重置登录状态
  item._logining = true
  item._loginStatus = 'connecting'
  item._qrCodeData = ''
  item._loginError = ''

  // 直接从账号的 type 字段获取平台编号（1=小红书, 2=视频号, 3=抖音, 4=快手）
  const platformType = account.type ? String(account.type) : '3'
  const url = `${apiBaseUrl}/login?type=${platformType}&id=${encodeURIComponent(account.name)}`

  const eventSource = new EventSource(url)
  _activeSSEConnections.add(eventSource)

  eventSource.onmessage = async (event) => {
    const data = event.data

    // 登录成功
    if (data === '200') {
      item._loginStatus = 'success'
      closeSSEConnection(eventSource)

      // 等待后端完成数据库写入和 cookie 文件落盘
      await new Promise(r => setTimeout(r, 4000))

      let newFilePath = null

      // 刷新账号列表，获取新的 cookie filePath
      try {
        const response = await apiClient.get('/getValidAccounts')
        if (response.data?.code === 200) {
          const rows = response.data.data || []
          // 查找 type 和 name 都匹配且状态正常的行
          const newRow = rows.find(r =>
            r[1] === account.type && r[3] === account.name && r[4] === 1
          )
          if (newRow) {
            newFilePath = newRow[2]
            item.filePath = newFilePath
            console.log(`已获取新凭证: type=${newRow[1]} name=${newRow[3]} status=${newRow[4]} filePath=${newFilePath}`)
          } else {
            console.warn('登录后未找到新的有效账号记录', {
              expectedType: account.type,
              expectedName: account.name,
              validRows: rows.filter(r => r[4] === 1)
                .map(r => ({ type: r[1], name: r[3], filePath: r[2], status: r[4] }))
            })
          }
        }
      } catch (e) {
        console.error('刷新账号信息失败:', e)
      }

      if (!newFilePath) {
        // 没找到新记录，无法安全重试，提示用户去账号管理页
        item._logining = false
        item._loginStatus = ''
        item.status = 'error'
        item.errorMessage = '重新登录成功，但未能获取新凭证。请前往账号管理页重新添加该账号后重试'
        item.errorType = 'login_orphan'
        item.suggestion = '请前往账号管理页 → 删除此账号 → 重新添加'
        checkAllDone()
        return
      }

      // 通知父组件刷新账号 Store
      emit('relogin-done', { accountId: item.accountId })

      // 关闭登录状态，自动重新发布
      item._logining = false
      item._loginStatus = ''
      await retryAccount(item.accountId)
      return
    }

    // 登录失败
    if (data === '500') {
      item._loginStatus = 'failed'
      item._loginError = '登录失败，请稍后重试'
      closeSSEConnection(eventSource)
      return
    }

    // 二维码图片（较长的字符串即为图片数据）
    if (data.length > 50 && item._loginStatus === 'connecting') {
      let imgSrc = data
      if (!imgSrc.startsWith('data:image')) {
        imgSrc = `data:image/png;base64,${data}`
      }
      item._qrCodeData = imgSrc
      item._loginStatus = 'qr_ready'
    }
  }

  eventSource.onerror = () => {
    item._loginStatus = 'failed'
    item._loginError = '连接登录服务失败，请检查网络后重试'
    closeSSEConnection(eventSource)
  }
}

// ============ 发布逻辑 ============

// 发布单个账号
async function publishSingleAccount(item) {
  const tab = props.tab
  if (!tab) throw new Error('发布数据缺失')

  const publishData = {
    // 优先使用账号自身的平台类型，确保重试时使用正确平台
    type: item.accountType || tab.selectedPlatform,
    title: tab.title,
    desc: tab.desc || '',
    tags: tab.selectedTopics || [],
    fileList: (tab.fileList || []).map(f => f.path),
    accountList: [item.filePath],
    enableTimer: tab.scheduleEnabled ? 1 : 0,
    videosPerDay: tab.scheduleEnabled ? tab.videosPerDay || 1 : 1,
    dailyTimes: tab.scheduleEnabled ? tab.dailyTimes || ['10:00'] : ['10:00'],
    startDays: tab.scheduleEnabled ? tab.startDays || 0 : 0,
    category: tab.isOriginal ? 1 : 0,
    productLink: tab.productLink?.trim() || '',
    productTitle: tab.productTitle?.trim() || '',
    isDraft: tab.isDraft || false
  }

  const endpoint = tab.publishType === 'note' ? '/postNote' : '/postVideo'
  const response = await apiClient.post(endpoint, publishData)

  if (response.data?.code === 200) return
  throw new Error(response.data?.msg || '发布失败')
}

// 滚动到底部
function scrollToBottom() {
  nextTick(() => {
    const el = timelineRef.value
    if (el) {
      el.scrollTop = el.scrollHeight
    }
  })
}

// 串行发布所有账号
async function publishSequentially(startIndex = 0) {
  _cancelled.value = false
  phase.value = 'publishing'

  for (let i = startIndex; i < accountItems.value.length; i++) {
    if (_cancelled.value) break

    const item = accountItems.value[i]
    if (item.status === 'completed') continue
    if (item.status !== 'waiting') continue

    item.status = 'publishing'
    scrollToBottom()

    try {
      await publishSingleAccount(item)
      item.status = 'completed'
    } catch (error) {
      console.error(`发布失败 [账号=${item.accountName}]:`, error?.response?.data?.msg || error?.message || error)
      const { errorType, suggestion } = classifyError(error)
      item.status = 'error'
      item.errorMessage = getErrorMessage(error)
      item.errorType = errorType
      item.suggestion = suggestion
    }
    scrollToBottom()
  }

  phase.value = 'done'
  emitDone()
}

// 重试单个账号
async function retryAccount(accountId) {
  const index = accountItems.value.findIndex(i => i.accountId === accountId)
  if (index === -1) return

  const item = accountItems.value[index]
  if (item._retrying) return

  item._retrying = true
  item.status = 'publishing'
  item.errorMessage = null
  item.errorType = null
  item.suggestion = null

  try {
    console.log(`重试发布 [账号=${item.accountName}] filePath=${item.filePath}`)
    await publishSingleAccount(item)
    item.status = 'completed'
  } catch (error) {
    console.error(`重试发布失败 [账号=${item.accountName}]:`, error?.response?.data?.msg || error?.message || error)
    const { errorType, suggestion } = classifyError(error)
    item.status = 'error'
    item.errorMessage = getErrorMessage(error)
    item.errorType = errorType
    item.suggestion = suggestion
  } finally {
    item._retrying = false
  }

  // 检查是否全部完成
  checkAllDone()
}

// 全部重试
async function retryAllFailed() {
  accountItems.value.forEach(i => {
    if (i.status === 'error') {
      i.status = 'waiting'
      i.errorMessage = null
      i.errorType = null
      i.suggestion = null
      i._retrying = false
      i._logining = false
      i._loginStatus = ''
      i._qrCodeData = ''
      i._loginError = ''
    }
  })

  const firstWaiting = accountItems.value.findIndex(i => i.status === 'waiting')
  if (firstWaiting === -1) return

  await publishSequentially(firstWaiting)
}

function checkAllDone() {
  const allDone = accountItems.value.every(i => i.status === 'completed' || i.status === 'error')
  if (allDone) {
    phase.value = 'done'
    emitDone()
  }
}

function emitDone() {
  emit('done', {
    successCount: successCount.value,
    failCount: failCount.value,
    results: accountItems.value.map(i => ({
      accountId: i.accountId,
      status: i.status,
      errorMessage: i.errorMessage
    }))
  })
}

// 关闭
function handleClose() {
  if (phase.value === 'publishing') return
  emit('update:visible', false)
}

// 监听 visible 变化自动开始
watch(() => props.visible, async (val) => {
  if (val && props.accounts.length > 0 && props.tab) {
    _cancelled.value = false
    initItems()
    phase.value = 'publishing'
    await nextTick()
    await publishSequentially(0)
  }
})
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.progress-header {
  padding-bottom: 16px;
  border-bottom: 1px solid $border-lighter;
  margin-bottom: 8px;

  .progress-summary {
    margin: 8px 0 0;
    font-size: $font-size-small;
    color: $text-secondary;
    text-align: center;
  }
}

.account-timeline {
  max-height: 400px;
  overflow-y: auto;
  padding: 4px 0;

  .timeline-item {
    display: flex;
    gap: 12px;

    .timeline-connector {
      display: flex;
      flex-direction: column;
      align-items: center;
      width: 24px;
      flex-shrink: 0;

      .timeline-dot {
        width: 24px;
        height: 24px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 16px;
        background: $bg-color;
        flex-shrink: 0;

        &.completed { color: $success-color; }
        &.error { color: $danger-color; }
        &.publishing { color: $primary-color; }
        &.waiting { color: $info-color; background: $border-extra-light; }

        .is-loading {
          animation: rotating 1.5s linear infinite;
        }
      }

      .connector-line {
        width: 2px;
        flex: 1;
        background: $border-lighter;
        min-height: 16px;
      }
    }

    .timeline-content {
      flex: 1;
      min-width: 0;
      padding-bottom: 20px;

      .content-header {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 4px;

        .account-name {
          font-size: $font-size-base;
          color: $text-primary;
          font-weight: 500;
        }
      }

      .error-detail {
        margin-top: 8px;
        padding: 10px 12px;
        background: #fef0f0;
        border-radius: $border-radius-base;
        border: 1px solid #fde2e2;

        .error-message,
        .error-suggestion {
          display: flex;
          align-items: flex-start;
          gap: 6px;
          font-size: $font-size-small;
          margin-bottom: 6px;

          .el-icon {
            flex-shrink: 0;
            margin-top: 2px;
          }
        }

        .error-message {
          color: $danger-color;
          .el-icon { color: $danger-color; }
        }

        .error-suggestion {
          color: $warning-color;
          .el-icon { color: $warning-color; }
        }

        .error-actions {
          display: flex;
          gap: 8px;
          margin-top: 8px;
          flex-wrap: wrap;
        }

        .login-inline-status {
          margin-top: 12px;
          padding: 12px;
          background: #f0f9ff;
          border-radius: $border-radius-base;
          border: 1px solid #dee8f5;
          text-align: center;
          font-size: $font-size-small;
          color: $text-regular;

          .qr-platform-label {
            margin-bottom: 8px;
            font-size: $font-size-small;
            color: $text-regular;
          }

          .qr-image-wrapper {
            margin: 0 auto 8px;
            width: 160px;
            height: 160px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: #fff;
            border: 1px solid $border-lighter;
            border-radius: $border-radius-base;
            padding: 4px;

            .qr-image {
              width: 100%;
              height: 100%;
              object-fit: contain;
            }
          }

          .qr-tip {
            margin: 0 0 4px;
            color: $text-secondary;
          }

          .login-success-icon {
            color: $success-color;
            font-size: 20px;
            vertical-align: middle;
            margin-right: 4px;
          }

          .login-fail-icon {
            color: $danger-color;
            font-size: 20px;
            vertical-align: middle;
            margin-right: 4px;
          }

          .el-icon.is-loading {
            animation: rotating 1.5s linear infinite;
            font-size: 20px;
            vertical-align: middle;
            margin-right: 4px;
          }
        }
      }
    }
  }
}

@keyframes rotating {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
