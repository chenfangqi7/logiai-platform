<script setup lang="ts">
import { useAuthStore } from '../stores/auth'
const auth = useAuthStore()
</script>

<template>
  <div class="page-heading"><div><p class="eyebrow">SETTINGS</p><h1>系统设置</h1><p class="muted">当前租户与账户信息</p></div></div>
  <div class="panel"><el-descriptions :column="1" border><el-descriptions-item label="租户代码">{{ auth.user?.tenant_code }}</el-descriptions-item><el-descriptions-item label="租户 ID">{{ auth.user?.tenant_id }}</el-descriptions-item><el-descriptions-item label="用户名">{{ auth.user?.username }}</el-descriptions-item><el-descriptions-item label="邮箱">{{ auth.user?.email }}</el-descriptions-item><el-descriptions-item label="角色">{{ auth.user?.role }}</el-descriptions-item></el-descriptions></div>
</template>
