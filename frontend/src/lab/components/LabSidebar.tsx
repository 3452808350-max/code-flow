import React from 'react'
import { Card, Layout, Menu, Typography } from 'antd'
import type { MenuProps } from 'antd'

const { Sider } = Layout
const { Title, Paragraph } = Typography

export type NavItem = Required<MenuProps>['items'][number]

export function LabSidebar({
  items,
  selectedKey,
  onSelect,
  counts,
}: {
  items: NavItem[]
  selectedKey: string
  onSelect: (key: string) => void
  counts: Record<string, number>
}) {
  return (
    <Sider width={280} className="lab-sider">
      <div className="lab-brand">
        <div className="lab-brand-mark">HL</div>
        <div>
          <Paragraph className="lab-eyebrow">Research Runtime</Paragraph>
          <Title level={3} className="lab-brand-title">
            Harness Lab
          </Title>
        </div>
      </div>
      <Menu
        className="lab-menu"
        theme="dark"
        mode="inline"
        selectedKeys={[selectedKey]}
        items={items}
        onSelect={({ key }) => onSelect(key)}
      />
      <Card className="lab-side-card" size="small" title="Registry Snapshot">
        {Object.entries(counts).map(([label, value]) => (
          <Paragraph key={label} className="lab-side-metric">
            <strong>{label}</strong>: {value}
          </Paragraph>
        ))}
      </Card>
    </Sider>
  )
}
