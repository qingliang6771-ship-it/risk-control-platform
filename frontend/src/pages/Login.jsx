import React, { useState } from 'react';
import { Button, Card, Typography, Space, Spin } from 'antd';
import { SafetyOutlined } from '@ant-design/icons';
import { authAPI } from '../services/api';

const { Title, Text } = Typography;

function Login() {
  const [loading, setLoading] = useState(false);

  const handleLarkLogin = async () => {
    setLoading(true);
    try {
      const res = await authAPI.getLarkLoginUrl();
      const loginUrl = res.data.login_url;
      window.location.href = loginUrl;
    } catch (err) {
      console.error('Failed to get login URL:', err);
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    }}>
      <Card style={{ width: 400, textAlign: 'center', borderRadius: 12, boxShadow: '0 20px 60px rgba(0,0,0,0.3)' }}>
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <div>
            <SafetyOutlined style={{ fontSize: 48, color: '#1890ff', marginBottom: 16 }} />
            <Title level={3} style={{ margin: 0 }}>风控数据平台</Title>
            <Text type="secondary">内部风控后台系统</Text>
          </div>

          <Button
            type="primary"
            size="large"
            block
            onClick={handleLarkLogin}
            loading={loading}
            style={{ height: 48, fontSize: 16, borderRadius: 8 }}
          >
            {loading ? '正在跳转...' : '使用飞书登录'}
          </Button>

          <Text type="secondary" style={{ fontSize: 12 }}>
            仅限公司内部员工通过飞书账号登录
          </Text>
        </Space>
      </Card>
    </div>
  );
}

export default Login;
