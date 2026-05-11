import React, { useState } from 'react';
import { Input, Button, Card, Row, Col, Statistic, Tag, Descriptions, Spin, message, Space, Typography, Tabs } from 'antd';
import { SearchOutlined, SafetyOutlined, WarningOutlined, CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons';
import { riskAPI } from '../services/api';

const { Title, Text } = Typography;

function RiskQuery() {
  const [userId, setUserId] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const handleQuery = async () => {
    if (!userId.trim()) {
      message.warning('请输入用户ID');
      return;
    }
    setLoading(true);
    setResult(null);
    try {
      const res = await riskAPI.getAllModels(userId.trim());
      setResult(res.data.data);
    } catch (err) {
      message.error('查询失败: ' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  const getRiskLevel = (score) => {
    if (score === undefined || score === null) return { color: 'default', text: '未知' };
    if (score >= 80) return { color: 'red', text: '高风险' };
    if (score >= 60) return { color: 'orange', text: '中风险' };
    if (score >= 40) return { color: 'gold', text: '低风险' };
    return { color: 'green', text: '安全' };
  };

  const renderModelCard = (title, data, icon) => {
    if (!data || data.error) {
      return (
        <Card size="small" title={title} style={{ height: '100%' }}>
          <Text type="secondary">{data?.error || '暂无数据'}</Text>
        </Card>
      );
    }

    const score = data.score ?? data.risk_score ?? data.confidence ?? null;
    const level = getRiskLevel(score);

    return (
      <Card
        size="small"
        title={
          <Space>
            {icon}
            <span>{title}</span>
          </Space>
        }
        extra={score !== null && <Tag color={level.color}>{level.text}</Tag>}
        style={{ height: '100%' }}
      >
        {score !== null && (
          <Statistic
            value={score}
            suffix="/ 100"
            valueStyle={{ color: level.color === 'red' ? '#cf1322' : level.color === 'green' ? '#3f8600' : '#d48806' }}
          />
        )}
        <Descriptions column={1} size="small" style={{ marginTop: 12 }}>
          {Object.entries(data).filter(([k]) => !['score', 'risk_score', 'confidence', 'user_id'].includes(k)).slice(0, 5).map(([key, value]) => (
            <Descriptions.Item key={key} label={key}>
              {typeof value === 'object' ? JSON.stringify(value) : String(value)}
            </Descriptions.Item>
          ))}
        </Descriptions>
      </Card>
    );
  };

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <Title level={4} style={{ marginBottom: 16 }}>
          <SafetyOutlined style={{ marginRight: 8 }} />
          用户风控查询
        </Title>
        <Space.Compact style={{ width: '100%', maxWidth: 500 }}>
          <Input
            size="large"
            placeholder="输入用户ID进行风控查询"
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
            onPressEnter={handleQuery}
            prefix={<SearchOutlined />}
          />
          <Button
            type="primary"
            size="large"
            onClick={handleQuery}
            loading={loading}
          >
            查询
          </Button>
        </Space.Compact>
      </div>

      {loading && (
        <div style={{ textAlign: 'center', padding: 60 }}>
          <Spin size="large" tip="正在查询风控模型..." />
        </div>
      )}

      {result && !loading && (
        <div>
          {/* Summary */}
          <Card style={{ marginBottom: 16 }}>
            <Row gutter={16}>
              <Col span={6}>
                <Statistic
                  title="用户ID"
                  value={result.user_id}
                  valueStyle={{ fontSize: 16 }}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="综合风控分"
                  value={result.risk_score?.score ?? result.risk_score?.risk_score ?? '--'}
                  suffix="/ 100"
                  valueStyle={{
                    color: getRiskLevel(result.risk_score?.score ?? result.risk_score?.risk_score).color === 'red' ? '#cf1322' : '#3f8600'
                  }}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="模型数量"
                  value={5}
                  suffix="个"
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="查询状态"
                  value="完成"
                  prefix={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
                  valueStyle={{ color: '#52c41a' }}
                />
              </Col>
            </Row>
          </Card>

          {/* Model Results */}
          <Row gutter={[16, 16]}>
            <Col span={8}>
              {renderModelCard('综合风控评分', result.risk_score, <SafetyOutlined style={{ color: '#1890ff' }} />)}
            </Col>
            <Col span={8}>
              {renderModelCard('欺诈检测', result.fraud_detection, <WarningOutlined style={{ color: '#fa8c16' }} />)}
            </Col>
            <Col span={8}>
              {renderModelCard('信用评估', result.credit_assessment, <CheckCircleOutlined style={{ color: '#52c41a' }} />)}
            </Col>
            <Col span={8}>
              {renderModelCard('行为分析', result.behavior_analysis, <SearchOutlined style={{ color: '#722ed1' }} />)}
            </Col>
            <Col span={8}>
              {renderModelCard('设备指纹', result.device_fingerprint, <CloseCircleOutlined style={{ color: '#eb2f96' }} />)}
            </Col>
          </Row>
        </div>
      )}

      {!result && !loading && (
        <Card style={{ textAlign: 'center', padding: '40px 0' }}>
          <SafetyOutlined style={{ fontSize: 48, color: '#d9d9d9', marginBottom: 16 }} />
          <Title level={5} type="secondary">输入用户ID查询风控信息</Title>
          <Text type="secondary">
            支持查询：综合风控分、欺诈检测、信用评估、行为分析、设备指纹
          </Text>
        </Card>
      )}
    </div>
  );
}

export default RiskQuery;
