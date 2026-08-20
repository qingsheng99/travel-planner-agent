<template>
  <div class="login-container">
    <el-card class="login-card">
      <h2 class="title">AI旅行规划助手</h2>
      <p class="subtitle">登录开始规划您的旅程</p>
      
      <el-form :model="loginForm" :rules="rules" ref="formRef" label-width="0">
        <el-form-item prop="email">
          <el-input v-model="loginForm.email" placeholder="邮箱" prefix-icon="Message" size="large" />
        </el-form-item>
        <el-form-item prop="password">
          <el-input v-model="loginForm.password" type="password" placeholder="密码" prefix-icon="Lock" size="large" show-password @keyup.enter="handleLogin" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" size="large" style="width: 100%" :loading="loading" @click="handleLogin">
            登录
          </el-button>
        </el-form-item>
      </el-form>
      
      <div class="footer">
        还没有账号？<router-link to="/register">立即注册</router-link>
      </div>
    </el-card>
  </div>
</template>

<!--
  登录页面 - 用户登录入口
  提供邮箱和密码登录表单，表单校验通过后调用 authStore 进行登录
-->
<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { ElMessage } from 'element-plus'
import type { FormInstance } from 'element-plus'

const router = useRouter()
const authStore = useAuthStore()

// 表单实例引用，用于调用表单校验方法
const formRef = ref<FormInstance>()
// 登录按钮加载状态
const loading = ref(false)

// 登录表单数据模型
const loginForm = reactive({
  email: '',
  password: ''
})

// 表单校验规则：邮箱必填且格式正确，密码必填且不少于6位
const rules = {
  email: [{ required: true, message: '请输入邮箱', trigger: 'blur' }, { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }, { min: 6, message: '密码至少6位', trigger: 'blur' }]
}

/** 处理登录：校验表单、调用登录接口、成功后跳转到首页 */
async function handleLogin() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  
  loading.value = true
  try {
    await authStore.login(loginForm.email, loginForm.password)
    ElMessage.success('登录成功')
    router.push('/')
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
.login-card {
  width: 400px;
  padding: 20px;
}
.title {
  text-align: center;
  color: #333;
  margin-bottom: 8px;
}
.subtitle {
  text-align: center;
  color: #999;
  margin-bottom: 30px;
}
.footer {
  text-align: center;
  color: #666;
}
.footer a {
  color: #667eea;
  text-decoration: none;
}
</style>
