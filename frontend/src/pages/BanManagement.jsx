import React, { useState, useEffect, useCallback } from 'react';
import {
  Table, Button, Space, Select, Input, Drawer, Form, InputNumber, Switch,
  Tag, message, Modal, Upload, Typography, Row, Col, Divider, Alert, List,
  Card, Statistic, Popconfirm, DatePicker,
} from 'antd';
import {
  PlusOutlined, UploadOutlined, InboxOutlined, ReloadOutlined,
  DollarOutlined, DownloadOutlined, DeleteOutlined, ExportOutlined,
  CheckCircleTwoTone, CloseCircleTwoTone, TeamOutlined,
  CalendarOutlined, ScheduleOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { banAPI } from '../services/api';

const { TextArea } = Input;
const { Text, Link } = Typography;
const { Dragger } = Upload;
const { RangePicker } = DatePicker;


// 封禁类型 -> 展示颜色
const LEVEL_COLOR = {
  compliance: 'volcano',
  payment: 'orange',
  kyc: 'geekblue',
  project_freeze: 'purple',
  persuade_quit: 'gold',
};

export default function BanManagement() {
  // 当前用户（判断是否管理员，用于删除按钮显隐）
  const user = JSON.parse(localStorage.getItem('user') || '{}');
  const isAdmin = !!user.is_admin;

  const [loading, setLoading] = useState(false);
  const [data, setData] = useState([]);
  const [pagination, setPagination] = useState({ current: 1, pageSize: 20, total: 0 });

  // 统计看板
  const [stats, setStats] = useState(null);

  // 选项
  const [banLevels, setBanLevels] = useState([]);

  // 筛选
  const [filters, setFilters] = useState({
    bundle_id: '', app_user_id: '', ban_level: undefined, cleared: undefined,
    start_date: undefined, end_date: undefined,
  });
  // 时间范围（dayjs 对象数组，用于 RangePicker 受控）
  const [dateRange, setDateRange] = useState(null);
  const [exporting, setExporting] = useState(false);


  // 手动录入抽屉
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [fundLoading, setFundLoading] = useState(false);
  const [form] = Form.useForm();

  // 批量上传弹窗
  const [uploadOpen, setUploadOpen] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);

  // 加载下拉选项
  useEffect(() => {
    banAPI.getOptions()
      .then((res) => setBanLevels(res.data.ban_levels || []))
      .catch(() => message.error('加载选项失败'));
  }, []);

  // 把筛选条件转为查询参数（列表/统计/导出共用）
  const buildParams = (curFilters) => {
    const params = {};
    if (curFilters.bundle_id) params.bundle_id = curFilters.bundle_id;
    if (curFilters.app_user_id) params.app_user_id = curFilters.app_user_id;
    if (curFilters.ban_level) params.ban_level = curFilters.ban_level;
    if (curFilters.cleared !== undefined) params.cleared = curFilters.cleared;
    if (curFilters.start_date) params.start_date = curFilters.start_date;
    if (curFilters.end_date) params.end_date = curFilters.end_date;
    return params;
  };

  const fetchStats = useCallback(async (curFilters = filters) => {
    try {
      const res = await banAPI.getStats(buildParams(curFilters));
      setStats(res.data);
    } catch {
      // 看板加载失败不阻塞主流程
    }
  }, [filters]);

  const fetchData = useCallback(async (page = 1, pageSize = 20, curFilters = filters) => {
    setLoading(true);
    try {
      const params = { page, page_size: pageSize, ...buildParams(curFilters) };
      const res = await banAPI.list(params);
      setData(res.data.items || []);
      setPagination({ current: res.data.page, pageSize: res.data.page_size, total: res.data.total });
    } catch (err) {
      message.error(err.response?.data?.detail || '加载封禁列表失败');
    } finally {
      setLoading(false);
    }
  }, [filters]);


  useEffect(() => { fetchData(1, 20); fetchStats(); }, []); // eslint-disable-line

  const refreshAll = () => { fetchData(pagination.current, pagination.pageSize, filters); fetchStats(); };

  const handleSearch = () => { fetchData(1, pagination.pageSize, filters); fetchStats(filters); };
  const handleReset = () => {
    const empty = {
      bundle_id: '', app_user_id: '', ban_level: undefined, cleared: undefined,
      start_date: undefined, end_date: undefined,
    };
    setFilters(empty);
    setDateRange(null);
    fetchData(1, pagination.pageSize, empty);
    fetchStats(empty);
  };

  // 时间范围变化
  const handleRangeChange = (range) => {
    setDateRange(range);
    setFilters((f) => ({
      ...f,
      start_date: range?.[0] ? range[0].format('YYYY-MM-DD') : undefined,
      end_date: range?.[1] ? range[1].format('YYYY-MM-DD') : undefined,
    }));
  };

  // ---- 导出 CSV（按当前筛选）----
  const handleExport = async () => {
    setExporting(true);
    try {
      const res = await banAPI.exportCsv(buildParams(filters));
      const url = window.URL.createObjectURL(new Blob([res.data], { type: 'text/csv' }));
      const a = document.createElement('a');
      a.href = url;
      a.download = `ban_records_${dayjs().format('YYYYMMDD_HHmmss')}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      message.success('已开始下载导出文件');
    } catch (err) {
      message.error(err.response?.data?.detail || '导出失败');
    } finally {
      setExporting(false);
    }
  };


  // ---- 手动录入 ----
  const openDrawer = () => {
    form.resetFields();
    form.setFieldsValue({
      ban_level: 'compliance', cleared: false, balance_refunded: false,
      total_recharge: 0, total_withdraw: 0, total_risk_amount: 0, current_balance: 0,
    });
    setDrawerOpen(true);
  };

  const handleFetchFund = async () => {
    const appId = form.getFieldValue('app_user_id');
    const pcId = form.getFieldValue('payment_center_user_id');
    if (!appId && !pcId) {
      message.warning('请先填写业务用户ID或支付中心用户ID');
      return;
    }
    setFundLoading(true);
    try {
      const res = await banAPI.fetchFundInfo({ app_user_id: appId, payment_center_user_id: pcId });
      const d = res.data.data || {};
      form.setFieldsValue({
        total_recharge: d.total_recharge ?? 0,
        total_withdraw: d.total_withdraw ?? 0,
        total_risk_amount: d.total_risk_amount ?? 0,
        current_balance: d.current_balance ?? 0,
      });
      message.info(res.data.message || '已回填资金信息');
    } catch (err) {
      message.error(err.response?.data?.detail || '获取资金信息失败');
    } finally {
      setFundLoading(false);
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setSubmitting(true);
      await banAPI.create(values);
      message.success('封禁记录已录入');
      setDrawerOpen(false);
      fetchData(1, pagination.pageSize, filters);
      fetchStats();
    } catch (err) {
      if (err?.errorFields) return;
      message.error(err.response?.data?.detail || '录入失败');
    } finally {
      setSubmitting(false);
    }
  };

  // ---- 删除（管理员）----
  const handleDelete = async (id) => {
    try {
      await banAPI.remove(id);
      message.success('已删除');
      refreshAll();
    } catch (err) {
      message.error(err.response?.data?.detail || '删除失败');
    }
  };

  // ---- 批量上传 ----
  const openUpload = () => { setUploadResult(null); setUploadOpen(true); };

  const handleDownloadTemplate = async () => {
    try {
      const res = await banAPI.downloadTemplate();
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement('a');
      a.href = url;
      a.download = 'ban_import_template.csv';
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch {
      message.error('下载模板失败');
    }
  };

  const beforeUpload = async (file) => {
    setUploading(true);
    setUploadResult(null);
    try {
      const res = await banAPI.batchUpload(file);
      setUploadResult(res.data);
      if (res.data.success > 0) {
        message.success(`成功导入 ${res.data.success} 条`);
        refreshAll();
      }
      if (res.data.failed > 0) {
        message.warning(`有 ${res.data.failed} 条导入失败，请查看详情`);
      }
    } catch (err) {
      message.error(err.response?.data?.detail || '批量上传失败');
    } finally {
      setUploading(false);
    }
    return Upload.LIST_IGNORE;
  };

  const columns = [
    {
      title: '是否已清退完成', dataIndex: 'cleared', width: 130, fixed: 'left',
      render: (v) => (v
        ? <Tag icon={<CheckCircleTwoTone twoToneColor="#52c41a" />} color="success">已清退</Tag>
        : <Tag icon={<CloseCircleTwoTone twoToneColor="#ff4d4f" />} color="error">未清退</Tag>),
    },
    { title: 'BundleID', dataIndex: 'bundle_id', width: 150, ellipsis: true, render: (v) => v || '-' },
    { title: '业务用户ID', dataIndex: 'app_user_id', width: 130 },
    { title: '支付中心用户ID', dataIndex: 'payment_center_user_id', width: 140 },
    {
      title: '封禁类型', dataIndex: 'ban_level', width: 110,
      render: (v, r) => <Tag color={LEVEL_COLOR[v] || 'default'}>{r.ban_level_label}</Tag>,
    },
    { title: '封禁原因', dataIndex: 'ban_reason', width: 200, ellipsis: true },
    { title: '累计充值', dataIndex: 'total_recharge', width: 100, align: 'right' },
    { title: '累计提现', dataIndex: 'total_withdraw', width: 100, align: 'right' },
    { title: '累计风险金额', dataIndex: 'total_risk_amount', width: 110, align: 'right' },
    { title: '当前余额', dataIndex: 'current_balance', width: 100, align: 'right' },
    {
      title: '已退余额', dataIndex: 'balance_refunded', width: 90,
      render: (v) => (v ? <Tag color="green">是</Tag> : <Tag>否</Tag>),
    },
    { title: '操作人', dataIndex: 'operator_name', width: 100, render: (v) => v || '-' },
    {
      title: '封禁时间', dataIndex: 'created_at', width: 170,
      render: (v) => (v ? new Date(v).toLocaleString('zh-CN') : '-'),
    },
  ];

  if (isAdmin) {
    columns.push({
      title: '操作', key: 'action', width: 90, fixed: 'right',
      render: (_, r) => (
        <Popconfirm title="确认删除这条记录？" okText="删除" cancelText="取消"
          okButtonProps={{ danger: true }} onConfirm={() => handleDelete(r.id)}>
          <Button danger size="small" icon={<DeleteOutlined />}>删除</Button>
        </Popconfirm>
      ),
    });
  }

  return (
    <div>
      {/* 统计看板 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={12} sm={8} md={4}>
          <Card size="small"><Statistic title="封禁总人数" value={stats?.total ?? 0} prefix={<TeamOutlined />} /></Card>
        </Col>
        <Col xs={12} sm={8} md={4}>
          <Card size="small"><Statistic title="已清退" value={stats?.cleared ?? 0} valueStyle={{ color: '#52c41a' }} /></Card>
        </Col>
        <Col xs={12} sm={8} md={4}>
          <Card size="small"><Statistic title="未清退" value={stats?.not_cleared ?? 0} valueStyle={{ color: '#ff4d4f' }} /></Card>
        </Col>
        <Col xs={12} sm={8} md={4}>
          <Card size="small"><Statistic title="本周新增" value={stats?.this_week ?? 0} prefix={<ScheduleOutlined />} /></Card>
        </Col>
        <Col xs={12} sm={8} md={4}>
          <Card size="small"><Statistic title="本月新增" value={stats?.this_month ?? 0} prefix={<CalendarOutlined />} /></Card>
        </Col>
      </Row>

      {/* 各类型分布 */}
      <Card size="small" title="各封禁类型人数" style={{ marginBottom: 16 }}>
        <Space size={[24, 8]} wrap>
          {(stats?.by_level || []).map((it) => (
            <Statistic
              key={it.key}
              title={<Tag color={LEVEL_COLOR[it.key] || 'default'}>{it.label}</Tag>}
              value={it.count}
            />
          ))}
          {(!stats || stats.by_level?.length === 0) && <Text type="secondary">暂无数据</Text>}
        </Space>
      </Card>

      {/* 顶部：筛选 + 操作按钮 */}
      <Row justify="space-between" align="middle" style={{ marginBottom: 16 }} gutter={[8, 8]}>
        <Col>
          <Space wrap>
            <Input
              placeholder="BundleID"
              allowClear
              style={{ width: 170 }}
              value={filters.bundle_id}
              onChange={(e) => setFilters((f) => ({ ...f, bundle_id: e.target.value }))}
              onPressEnter={handleSearch}
            />
            <Input
              placeholder="业务用户ID"
              allowClear
              style={{ width: 150 }}
              value={filters.app_user_id}
              onChange={(e) => setFilters((f) => ({ ...f, app_user_id: e.target.value }))}
              onPressEnter={handleSearch}
            />
            <Select
              placeholder="封禁类型"
              allowClear
              style={{ width: 140 }}
              value={filters.ban_level}
              onChange={(v) => setFilters((f) => ({ ...f, ban_level: v }))}
              options={banLevels.map((l) => ({ value: l.key, label: l.label }))}
            />
            <Select
              placeholder="清退状态"
              allowClear
              style={{ width: 130 }}
              value={filters.cleared}
              onChange={(v) => setFilters((f) => ({ ...f, cleared: v }))}
              options={[
                { value: true, label: '已清退' },
                { value: false, label: '未清退' },
              ]}
            />
            <RangePicker
              value={dateRange}
              onChange={handleRangeChange}
              allowClear
              placeholder={['封禁起始日', '封禁结束日']}
              style={{ width: 260 }}
            />
            <Button type="primary" onClick={handleSearch}>查询</Button>
            <Button icon={<ReloadOutlined />} onClick={handleReset}>重置</Button>
          </Space>
        </Col>
        <Col>
          <Space>
            <Button icon={<ExportOutlined />} loading={exporting} onClick={handleExport}>
              导出数据
            </Button>
            <Button icon={<PlusOutlined />} type="primary" onClick={openDrawer}>手动录入</Button>
            <Button icon={<UploadOutlined />} onClick={openUpload}>批量上传</Button>
          </Space>
        </Col>

      </Row>

      {/* 数据表格 */}
      <Table
        rowKey="id"
        loading={loading}
        columns={columns}
        dataSource={data}
        scroll={{ x: 1800 }}
        size="middle"
        pagination={{
          ...pagination,
          showSizeChanger: true,
          showTotal: (t) => `共 ${t} 条`,
          onChange: (page, pageSize) => fetchData(page, pageSize, filters),
        }}
      />

      {/* 手动录入抽屉 */}
      <Drawer
        title="手动录入封禁记录"
        width={520}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        extra={
          <Space>
            <Button onClick={() => setDrawerOpen(false)}>取消</Button>
            <Button type="primary" loading={submitting} onClick={handleSubmit}>提交</Button>
          </Space>
        }
      >
        <Form form={form} layout="vertical">
          <Form.Item label="是否已清退完成" name="cleared" valuePropName="checked">
            <Switch checkedChildren="已清退" unCheckedChildren="未清退" />
          </Form.Item>

          <Form.Item label="BundleID" name="bundle_id">
            <Input placeholder="请输入 BundleID（如 com.company.app1）" />
          </Form.Item>

          <Form.Item
            label="业务用户ID (app_user_id)"
            name="app_user_id"
            rules={[{ required: true, message: '请输入业务用户ID' }]}
          >
            <Input placeholder="请输入业务用户ID" />
          </Form.Item>

          <Form.Item
            label="支付中心用户ID (payment_center_user_id)"
            name="payment_center_user_id"
            rules={[{ required: true, message: '请输入支付中心用户ID' }]}
          >
            <Input placeholder="请输入支付中心用户ID" />
          </Form.Item>

          <Form.Item>
            <Button icon={<DollarOutlined />} loading={fundLoading} onClick={handleFetchFund} block>
              获取资金信息（自动回填）
            </Button>
            <Text type="secondary" style={{ fontSize: 12 }}>
              填写用户ID后，可点击自动拉取并回填下方资金数据（当前为占位接口）。
            </Text>
          </Form.Item>

          <Form.Item
            label="封禁类型"
            name="ban_level"
            rules={[{ required: true, message: '请选择封禁类型' }]}
          >
            <Select options={banLevels.map((l) => ({ value: l.key, label: l.label }))} />
          </Form.Item>

          <Form.Item
            label="封禁原因"
            name="ban_reason"
            rules={[{ required: true, message: '请输入封禁原因' }]}
          >
            <TextArea rows={3} placeholder="请描述封禁原因" />
          </Form.Item>

          <Divider orientation="left" plain>资金数据</Divider>
          <Row gutter={12}>
            <Col span={12}>
              <Form.Item label="累计充值" name="total_recharge">
                <InputNumber style={{ width: '100%' }} min={0} precision={2} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="累计提现" name="total_withdraw">
                <InputNumber style={{ width: '100%' }} min={0} precision={2} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="累计风险金额" name="total_risk_amount">
                <InputNumber style={{ width: '100%' }} min={0} precision={2} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="当前余额" name="current_balance">
                <InputNumber style={{ width: '100%' }} min={0} precision={2} />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item label="是否已经退余额" name="balance_refunded" valuePropName="checked">
            <Switch checkedChildren="是" unCheckedChildren="否" />
          </Form.Item>
        </Form>
      </Drawer>

      {/* 批量上传弹窗 */}
      <Modal
        title="批量上传封禁记录"
        open={uploadOpen}
        onCancel={() => setUploadOpen(false)}
        footer={<Button onClick={() => setUploadOpen(false)}>关闭</Button>}
        width={560}
      >
        <div style={{ marginBottom: 12 }}>
          <Link onClick={handleDownloadTemplate}>
            <DownloadOutlined /> 下载 Excel/CSV 模板
          </Link>
          <Text type="secondary" style={{ marginLeft: 8, fontSize: 12 }}>
            支持 .xlsx 和 .csv，请按模板列填写
          </Text>
        </div>

        <Dragger
          multiple={false}
          showUploadList={false}
          accept=".xlsx,.xls,.csv"
          beforeUpload={beforeUpload}
          disabled={uploading}
        >
          <p className="ant-upload-drag-icon"><InboxOutlined /></p>
          <p className="ant-upload-text">
            {uploading ? '正在上传解析…' : '点击或拖拽文件到此区域上传'}
          </p>
          <p className="ant-upload-hint">仅支持单个 .xlsx / .csv 文件</p>
        </Dragger>

        {uploadResult && (
          <div style={{ marginTop: 16 }}>
            <Alert
              type={uploadResult.failed > 0 ? 'warning' : 'success'}
              showIcon
              message={`共 ${uploadResult.total} 行：成功 ${uploadResult.success} 条，失败 ${uploadResult.failed} 条`}
            />
            {uploadResult.errors?.length > 0 && (
              <List
                size="small"
                style={{ marginTop: 12, maxHeight: 200, overflow: 'auto' }}
                header={<Text strong>失败明细</Text>}
                bordered
                dataSource={uploadResult.errors}
                renderItem={(item) => (
                  <List.Item>
                    <Text type="danger">第 {item.row} 行：</Text>
                    <Text>{(item.reasons || []).join('；')}</Text>
                  </List.Item>
                )}
              />
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}
