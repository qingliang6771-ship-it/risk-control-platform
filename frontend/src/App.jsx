import React, { useState, useEffect } from 'react';
import { Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu, Avatar, Dropdown, message, Spin, Result, Button } from 'antd';
import {
  RobotOutlined,
  SafetyOutlined,
  DashboardOutlined,
  LogoutOutlined,
  UserOutlined,
  FileTextOutlined,
  TeamOutlined,
} from '@ant-design/icons';
import Login from './pages/Login';
import AuthCallback from './pages/AuthCallback';
import AIReport from './pages/AIReport';
import RiskQuery from './pages/RiskQuery';
import Dashboard from './pages/Dashboard';
import KYCReport from './pages/KYCReport';
import Permissions from './pages/Permissions';

import { authAPI } from './services/api';

const { Header, Sider, Content } = Layout;

// 模块定义：key 与后端 permitted_modules / 路由一一对应
const MODULES = [
  { key: 'dashboard', path: '/dashboard', icon: <DashboardOutlined />, label: '工作台', element: <Dashboard />, adminOnly: false },
  { key: 'ai-report', path: '/ai-report', icon: <RobotOutlined />, label: 'AI 数据报告', element: <AIReport />, adminOnly: false },
  { key: 'risk-query', path: '/risk-query', icon: <SafetyOutlined />, label: '风控查询', element: <RiskQuery />, adminOnly: false },
  { key: 'kyc-report', path: '/kyc-report', icon: <FileTextOutlined />, label: 'KYC 报告', element: <KYCReport />, adminOnly: false },
  { key: 'permissions', path: '/permissions', icon: <TeamOutlined />, label: '权限管理', element: <Permissions />, adminOnly: true },
];

function ProtectedRoute({ children }) {
  const token = localStorage.getItem('token');
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return children;
}

function Forbidden() {
  const navigate = useNavigate();
  return (
    <Result
      status="403"
      title="403"
      subTitle="抱歉，你没有访问该模块的权限，请联系管理员开通。"
      extra={<Button type="primary" onClick={() => navigate('/')}>返回首页</Button>}
    />
  );
}

function AppLayout() {
  const [collapsed, setCollapsed] = useState(false);
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    // 始终从后端拉取最新权限，避免本地缓存导致权限过期
    fetchUser();
  }, []);

  const fetchUser = async () => {
    try {
      const res = await authAPI.getMe();
      setUser(res.data);
      localStorage.setItem('user', JSON.stringify(res.data));
    } catch (err) {
      console.error('Failed to fetch user:', err);
      // token 失效时 api 拦截器会跳登录页
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    navigate('/login');
    message.success('已退出登录');
  };

  if (loading) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Spin size="large" tip="加载中..." />
      </div>
    );
  }

  const permitted = user?.permitted_modules || [];
  const isAdmin = user?.is_admin;

  // 允许访问的模块（管理员可见全部）
  const allowedModules = MODULES.filter(
    (m) => isAdmin || permitted.includes(m.key)
  );

  const menuItems = allowedModules.map((m) => ({
    key: m.path,
    icon: m.icon,
    label: m.label,
  }));

  const canAccess = (moduleKey) =>
    isAdmin || permitted.includes(moduleKey);

  // 默认落地页：第一个有权限的模块
  const defaultPath = allowedModules[0]?.path || '/forbidden';

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
      <Sider collapsible collapsed={collapsed} onCollapse={setCollapsed} theme="dark">
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
          <h2 style={{ margin: 0, fontSize: 16, color: '#333' }}>风控数据平台</h2>
          <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
            <div style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8 }}>
              <Avatar src={user?.avatar_url} icon={<UserOutlined />} />
              <span>{user?.name}</span>
            </div>
          </Dropdown>
        </Header>
        <Content style={{ margin: 16, padding: 24, background: '#fff', borderRadius: 8 }}>
          <Routes>
            {MODULES.map((m) => (
              <Route
                key={m.key}
                path={m.path}
                element={canAccess(m.key) ? m.element : <Forbidden />}
              />
            ))}
            <Route path="/forbidden" element={<Forbidden />} />
            <Route path="*" element={<Navigate to={defaultPath} replace />} />
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
