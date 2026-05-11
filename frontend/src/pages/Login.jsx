import React, { useState } from 'react';
import { Button, Card, Typography, Space, message } from 'antd';
import { SafetyOutlined } from '@ant-design/icons';
import { authAPI } from '../services/api';

const { Title, Text } = Typography;

function Login() {
  const [loading, setLoading] = useState(false);

  const handleLarkLogin = async () => {
    setLoading(true);
    try {
      const res = await authAPI.getLarkLoginUrl();
      window.location.href = res.data.login_url;
    } catch (err) {
      message.error('获取登录链接失败，请稍后重试');
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
      <Card
        style={{
          width: 420,
          borderRadius: 12,
          boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
        }}
        bodyStyle={{ padding: '48px 40px' }}
      >
        <Space direction="vertical" size="large" style={{ width: '100%', textAlign: 'center' }}>
          <SafetyOutlined style={{ fontSize: 48, color: '#1890ff' }} />
          <Title level={2} style={{ margin: 0 }}>风控后台</Title>
          <Text type="secondary">
            内部风控数据平台 · 仅限公司内部人员使用
          </Text>

          <div style={{ marginTop: 32 }}>
            <Button
              type="primary"
              size="large"
              block
              loading={loading}
              onClick={handleLarkLogin}
              style={{
                height: 48,
                fontSize: 16,
                borderRadius: 8,
                background: '#3370ff',
                borderColor: '#3370ff',
              }}
            >
              <img
                src="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cGF0aCBkPSJNMTIgMkw0IDdsMiAxMCA2IDVoMGw2LTUgMi0xMEwxMiAyeiIgZmlsbD0id2hpdGUiLz48L3N2Zz4="
                alt="Lark"
                style={{ width: 20, height: 20, marginRight: 8, verticalAlign: 'middle' }}
              />
              使用 Lark 登录
            </Button>
          </div>

          <Text type="secondary" style={{ fontSize: 12 }}>
            请使用公司 Lark 账号登录，未授权人员无法访问
          </Text>
        </Space>
      </Card>
    </div>
  );
}

export default Login;
