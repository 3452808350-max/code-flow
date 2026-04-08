import React from 'react'
import { Card, Typography } from 'antd'

const { Paragraph } = Typography

export function JsonCard({ title, value }: { title: string; value: unknown }) {
  return (
    <Card size="small" className="lab-nested-card" title={title}>
      <Paragraph className="lab-pre">{JSON.stringify(value, null, 2)}</Paragraph>
    </Card>
  )
}

