import React, { useState, useEffect } from 'react';
import { Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu, Avatar, Dropdown, message } from 'antd';
import {
  RobotOutlined,
  SafetyOutlined,
  DashboardOutlined,
  LogoutOutlined,
  UserOutlined,
  FileTextOutlined,
} from '@ant-design/icons';
import Login from './pages/Login';
import AuthCallback from './pages/AuthCallback';
import AIReport from './pages/AIReport';
import RiskQuery from './pages/RiskQuery';
import Dashboard from './pages/Dashboard';
import KYCReport from './pages/KYCReport';

import { authAPI } from './services/api';

const { Header, Sider, Content } = Layout;

function ProtectedRoute({ children }) {
  const token = localStorage.getItem('token');
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return children;
}

function AppLayout() {
  const [collapsed, setCollapsed] = useState(false);
  const [user, setUser] = useState(null);
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    const savedUser = localStorage.getItem('user');
    if (savedUser) {
      setUser(JSON.parse(savedUser));
    } else {
      fetchUser();
    }
  }, []);

  const fetchUser = async () => {
    try {
      const res = await authAPI.getMe();
      setUser(res.data);
      localStorage.setItem('user', JSON.stringify(res.data));
    } catch (err) {
      console.error('Failed to fetch user:', err);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    navigate('/login');
    message.success('已退出登录');
  };

  const menuItems = [
    {
      key: '/dashboard',
      icon: <DashboardOutlined />,
      label: '工作台',
    },
    {
      key: '/ai-report',
      icon: <RobotOutlined />,
      label: 'AI 数据报告',
    },
    {
      key: '/risk-query',
      icon: <SafetyOutlined />,
      label: '风控查询',
    },
    {
      key: '/kyc-report',
      icon: <FileTextOutlined />,
      label: 'KYC 报告',
    },
  ];


  const userMenuItems = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: user?.name || '用户',
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
      onClick: handleLogout,
    },
  ];

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        theme="dark"
      >
        <div style={{
          height: 64,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'white',
          fontSize: collapsed ? 16 : 18,
          fontWeight: 'bold',
          borderBottom: '1px solid rgba(255,255,255,0.1)',
        }}>
          {collapsed ? '风控' : '风控后台'}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header style={{
          background: '#fff',
          padding: '0 24px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          boxShadow: '0 1px 4px rgba(0,0,0,0.08)',
        }}>
          <h2 style={{ margin: 0, fontSize: 16, color: '#333' }}>
            风控数据平台
          </h2>
          <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
            <div style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8 }}>
              <Avatar src={user?.avatar_url} icon={<UserOutlined />} />
              <span>{user?.name}</span>
            </div>
          </Dropdown>
        </Header>
        <Content style={{ margin: 16, padding: 24, background: '#fff', borderRadius: 8 }}>
          <Routes>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/ai-report" element={<AIReport />} />
            <Route path="/risk-query" element={<RiskQuery />} />
            <Route path="/kyc-report" element={<KYCReport />} />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />

          </Routes>
        </Content>
      </Layout>
    </Layout>
  );
}

function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/auth/callback" element={<AuthCallback />} />
      <Route
        path="/*"
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}

export default App;
