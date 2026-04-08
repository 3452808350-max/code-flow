import React from 'react'
import { Tag } from 'antd'

const COLOR_MAP: Record<string, string> = {
  configured: 'default',
  running: 'processing',
  awaiting_approval: 'warning',
  awaiting_escalation: 'warning',
  evaluating: 'processing',
  publish_ready: 'success',
  rolled_back: 'default',
  rejected: 'error',
  idle: 'success',
  leased: 'processing',
  executing: 'processing',
  draining: 'warning',
  offline: 'default',
  unhealthy: 'error',
  completed: 'success',
  failed: 'error',
  published: 'success',
  candidate: 'processing',
  archived: 'default',
}

export function StatusPill({ value }: { value: string }) {
  return <Tag color={COLOR_MAP[value] || 'default'}>{value}</Tag>
}
