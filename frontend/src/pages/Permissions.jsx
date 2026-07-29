import React, { useState, useEffect } from 'react';
import {
  Table, Button, Input, Tag, Space, Drawer, Checkbox, Switch, Modal,
  Form, message, Avatar, Typography, Popconfirm,
} from 'antd';
import {
  SearchOutlined, UserAddOutlined, EditOutlined, UserOutlined, ReloadOutlined,
} from '@ant-design/icons';
import { adminAPI } from '../services/api';

const { Title, Text } = Typography;

function Permissions() {
  const [users, setUsers] = useState([]);
  const [modules, setModules] = useState([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');

  // 编辑抽屉
  const [editing, setEditing] = useState(null);
  const [editModules, setEditModules] = useState([]);
  const [editActive, setEditActive] = useState(true);
  const [editAdmin, setEditAdmin] = useState(false);
  const [saving, setSaving] = useState(false);

  // 添加用户弹窗
  const [addOpen, setAddOpen] = useState(false);
  const [addForm] = Form.useForm();
  const [adding, setAdding] = useState(false);

  const moduleLabel = (key) => modules.find((m) => m.key === key)?.label || key;

  const loadModules = async () => {
    try {
      const res = await adminAPI.listModules();
      setModules(res.data.modules || []);
    } catch (err) {
      console.error(err);
    }
  };

  const loadUsers = async (q = '') => {
    setLoading(true);
    try {
      const res = await adminAPI.listUsers(q);
      setUsers(res.data.users || []);
    } catch (err) {
      message.error(err.response?.data?.detail || '加载用户列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadModules();
    loadUsers();
  }, []);

  const openEdit = (user) => {
    setEditing(user);
    setEditModules(user.permitted_modules || []);
    setEditActive(user.is_active);
    setEditAdmin(user.is_admin);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await adminAPI.updatePermissions(editing.id, {
        permitted_modules: editModules,
        is_active: editActive,
        is_admin: editAdmin,
      });
      message.success('权限已保存');
      setEditing(null);
      loadUsers(search);
    } catch (err) {
      message.error(err.response?.data?.detail || '保存失败');
    } finally {
      setSaving(false);
    }
  };

  const handleAdd = async () => {
    try {
      const values = await addForm.validateFields();
      setAdding(true);
      await adminAPI.addUser({
        name: values.name,
        lark_open_id: values.lark_open_id,
        email: values.email,
        permitted_modules: values.permitted_modules || [],
        is_admin: values.is_admin || false,
      });
      message.success('已添加用户');
      setAddOpen(false);
      addForm.resetFields();
      loadUsers(search);
    } catch (err) {
      if (err?.errorFields) return; // 表单校验错误
      message.error(err.response?.data?.detail || '添加失败');
    } finally {
      setAdding(false);
    }
  };

  const columns = [
    {
      title: '用户',
      dataIndex: 'name',
      render: (name, r) => (
        <Space>
          <Avatar src={r.avatar_url} icon={<UserOutlined />} size="small" />
          <span>{name}</span>
          {r.is_admin && <Tag color="gold">管理员</Tag>}
        </Space>
      ),
    },
    {
      title: 'Email / OpenID',
      dataIndex: 'email',
      render: (email, r) => (
        <div>
          <div>{email || <Text type="secondary">—</Text>}</div>
          <Text type="secondary" style={{ fontSize: 12 }}>{r.lark_open_id}</Text>
        </div>
      ),
    },
    {
      title: '模块权限',
      dataIndex: 'permitted_modules',
      render: (mods) => (
        <Space size={[4, 4]} wrap>
          {(mods || []).length === 0 && <Text type="secondary">无</Text>}
          {(mods || []).map((m) => (
            <Tag key={m} color="blue">{moduleLabel(m)}</Tag>
          ))}
        </Space>
      ),
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      width: 90,
      render: (active) =>
        active ? <Tag color="green">正常</Tag> : <Tag color="red">已停用</Tag>,
    },
    {
      title: '操作',
      width: 110,
      render: (_, r) => (
        <Button type="link" icon={<EditOutlined />} onClick={() => openEdit(r)}>
          编辑权限
        </Button>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <Title level={4} style={{ margin: 0 }}>权限管理</Title>
          <Text type="secondary">管理通过 Lark 登录的用户及其可访问的模块</Text>
        </div>
        <Space>
          <Input
            placeholder="搜索姓名 / 邮箱"
            prefix={<SearchOutlined />}
            allowClear
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onPressEnter={() => loadUsers(search)}
            style={{ width: 220 }}
          />
          <Button onClick={() => loadUsers(search)} icon={<SearchOutlined />}>搜索</Button>
          <Button icon={<ReloadOutlined />} onClick={() => { setSearch(''); loadUsers(''); }} />
          <Button type="primary" icon={<UserAddOutlined />} onClick={() => setAddOpen(true)}>
            添加 Lark 用户
          </Button>
        </Space>
      </div>

      <Table
        rowKey="id"
        columns={columns}
        dataSource={users}
        loading={loading}
        pagination={{ pageSize: 10, showSizeChanger: false }}
      />

      {/* 编辑权限抽屉 */}
      <Drawer
        title={editing ? `编辑权限 · ${editing.name}` : '编辑权限'}
        open={!!editing}
        onClose={() => setEditing(null)}
        width={380}
        footer={
          <div style={{ textAlign: 'right' }}>
            <Space>
              <Button onClick={() => setEditing(null)}>取消</Button>
              <Button type="primary" loading={saving} onClick={handleSave}>保存</Button>
            </Space>
          </div>
        }
      >
        <div style={{ marginBottom: 20 }}>
          <Text strong>可访问模块</Text>
          <div style={{ marginTop: 12 }}>
            <Checkbox.Group
              value={editModules}
              onChange={setEditModules}
              style={{ display: 'flex', flexDirection: 'column', gap: 12 }}
            >
              {modules.map((m) => (
                <Checkbox key={m.key} value={m.key}>{m.label}</Checkbox>
              ))}
            </Checkbox.Group>
          </div>
        </div>

        <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
          <Text strong>账号状态</Text>
          <Switch checked={editActive} onChange={setEditActive}
            checkedChildren="正常" unCheckedChildren="停用" />
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <Text strong>管理员权限</Text>
          <Switch checked={editAdmin} onChange={setEditAdmin}
            checkedChildren="是" unCheckedChildren="否" />
        </div>
      </Drawer>

      {/* 添加用户弹窗 */}
      <Modal
        title="添加 Lark 授权用户"
        open={addOpen}
        onCancel={() => setAddOpen(false)}
        onOk={handleAdd}
        confirmLoading={adding}
        okText="添加"
        cancelText="取消"
      >
        <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
          用于在用户首次登录前预先配置其权限。OpenID 可从 Lark 开放平台获取。
        </Text>
        <Form form={addForm} layout="vertical">
          <Form.Item name="name" label="姓名" rules={[{ required: true, message: '请输入姓名' }]}>
            <Input placeholder="张三" />
          </Form.Item>
          <Form.Item name="lark_open_id" label="Lark OpenID"
            rules={[{ required: true, message: '请输入 Lark OpenID' }]}>
            <Input placeholder="ou_xxxxxxxx" />
          </Form.Item>
          <Form.Item name="email" label="Email">
            <Input placeholder="name@company.com" />
          </Form.Item>
          <Form.Item name="permitted_modules" label="模块权限">
            <Checkbox.Group>
              <Space direction="vertical">
                {modules.map((m) => (
                  <Checkbox key={m.key} value={m.key}>{m.label}</Checkbox>
                ))}
              </Space>
            </Checkbox.Group>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}

export default Permissions;
