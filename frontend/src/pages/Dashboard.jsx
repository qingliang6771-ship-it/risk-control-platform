import React from 'react';
import { Card, Row, Col, Statistic, Typography, Space } from 'antd';
import { SafetyOutlined, RobotOutlined, UserOutlined, AlertOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';

const { Title, Text } = Typography;

function Dashboard() {
  const navigate = useNavigate();

  return (
    <div>
      <Title level={4} style={{ marginBottom: 24 }}>工作台</Title>

      <Row gutter={[16, 16]}>
        <Col span={6}>
          <Card>
            <Statistic title="今日查询次数" value={0} prefix={<SafetyOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="AI报告生成" value={0} prefix={<RobotOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="高风险用户" value={0} prefix={<AlertOutlined />} valueStyle={{ color: '#cf1322' }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="活跃用户" value={0} prefix={<UserOutlined />} />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
        <Col span={12}>
          <Card
            hoverable
            onClick={() => navigate('/ai-report')}
            style={{ cursor: 'pointer' }}
          >
            <Space direction="vertical">
              <RobotOutlined style={{ fontSize: 32, color: '#1890ff' }} />
              <Title level={5}>AI 数据报告</Title>
              <Text type="secondary">
                通过自然语言查询数数平台数据，AI自动生成分析报告
              </Text>
            </Space>
          </Card>
        </Col>
        <Col span={12}>
          <Card
            hoverable
            onClick={() => navigate('/risk-query')}
            style={{ cursor: 'pointer' }}
          >
            <Space direction="vertical">
              <SafetyOutlined style={{ fontSize: 32, color: '#52c41a' }} />
              <Title level={5}>风控查询</Title>
              <Text type="secondary">
                查询特定用户的风控分、欺诈检测、信用评估等模型结果
              </Text>
            </Space>
          </Card>
        </Col>
      </Row>
    </div>
  );
}

export default Dashboard;
