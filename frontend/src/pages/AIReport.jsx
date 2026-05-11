import React, { useState, useRef, useEffect } from 'react';
import { Input, Button, Card, Space, Typography, Spin, Tag, Table, Select, Drawer, List, Popconfirm, message, Badge } from 'antd';
import { SendOutlined, RobotOutlined, UserOutlined, ClearOutlined, CodeOutlined, TableOutlined, HistoryOutlined, DeleteOutlined, MessageOutlined } from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';
import { reportAPI } from '../services/api';

const { TextArea } = Input;
const { Title, Text } = Typography;
const { Option } = Select;

function AIReport() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [currentProject, setCurrentProject] = useState('105');
  const [historyDrawerOpen, setHistoryDrawerOpen] = useState(false);
  const [historyList, setHistoryList] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const projects = [
    { id: '102', name: '黄老师 (102)' },
    { id: '105', name: '丁老师 (105)' },
    { id: '116', name: '魏老师 (116)' },
    { id: '128', name: '支付中心 (128)' },
  ];

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Load history on mount
  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    setHistoryLoading(true);
    try {
      const res = await reportAPI.getHistory(50);
      setHistoryList(res.data || []);
    } catch (err) {
      console.error('Failed to load history:', err);
    } finally {
      setHistoryLoading(false);
    }
  };

  const handleDeleteHistory = async (logId) => {
    try {
      await reportAPI.deleteHistory(logId);
      setHistoryList((prev) => prev.filter((item) => item.id !== logId));
      message.success('已删除');
    } catch (err) {
      message.error('删除失败');
    }
  };

  const handleLoadHistoryItem = (item) => {
    // Reconstruct messages from history item
    const msgs = [];
    msgs.push({ role: 'user', content: item.query });

    if (item.result) {
      const parts = [];
      if (item.result.sql) parts.push({ type: 'sql', content: item.result.sql });
      if (item.result.data) parts.push({ type: 'data', content: item.result.data });
      if (item.result.analysis) parts.push({ type: 'analysis', content: item.result.analysis });
      if (item.error) parts.push({ type: 'error', content: item.error });
      msgs.push({ role: 'assistant', content: item.result.analysis || '', parts, loading: false });
    }

    setMessages(msgs);
    setHistoryDrawerOpen(false);
  };

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMessage = { role: 'user', content: input.trim() };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      // 在查询中附加项目信息
      const queryWithProject = `[项目${currentProject}] ${userMessage.content}`;
      
      const response = await reportAPI.chatStream(
        queryWithProject,
        messages.filter(m => m.role === 'user' || m.role === 'assistant').map((m) => ({ role: m.role, content: typeof m.content === 'string' ? m.content : '(数据结果)' }))
      );

      if (!response.ok) {
        throw new Error('Stream request failed');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let parts = []; // 收集各部分内容

      // 添加一个占位消息
      setMessages((prev) => [...prev, { role: 'assistant', content: '', parts: [], loading: true }]);

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // 保留未完成的行

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.slice(6).trim();
            if (!dataStr || dataStr === '[DONE]') continue;
            
            try {
              const data = JSON.parse(dataStr);
              
              if (data.type === 'status') {
                parts = [...parts, { type: 'status', content: data.content }];
              } else if (data.type === 'sql') {
                parts = [...parts, { type: 'sql', content: data.content }];
              } else if (data.type === 'data') {
                parts = [...parts, { type: 'data', content: data.content }];
              } else if (data.type === 'analysis') {
                parts = [...parts, { type: 'analysis', content: data.content }];
              } else if (data.type === 'error') {
                parts = [...parts, { type: 'error', content: data.content }];
              }
              
              // 更新消息
              setMessages((prev) => {
                const updated = [...prev];
                updated[updated.length - 1] = {
                  role: 'assistant',
                  content: data.type === 'analysis' ? data.content : '',
                  parts: [...parts],
                  loading: data.type !== 'done',
                };
                return updated;
              });
            } catch (e) {
              // 非 JSON 数据，忽略
              console.warn('Failed to parse SSE data:', dataStr);
            }
          }
        }
      }

      // 标记完成
      setMessages((prev) => {
        const updated = [...prev];
        if (updated.length > 0) {
          updated[updated.length - 1].loading = false;
        }
        return updated;
      });

      // Refresh history after successful query
      setTimeout(() => loadHistory(), 1000);

    } catch (err) {
      // Fallback to non-streaming
      try {
        const queryWithProject = `[项目${currentProject}] ${userMessage.content}`;
        const res = await reportAPI.generateReport(queryWithProject);
        const result = res.data;
        const parts = [];
        if (result.sql) parts.push({ type: 'sql', content: result.sql });
        if (result.data) parts.push({ type: 'data', content: result.data });
        if (result.analysis) parts.push({ type: 'analysis', content: result.analysis });
        if (result.error) parts.push({ type: 'error', content: result.error });
        
        setMessages((prev) => [
          ...prev,
          { role: 'assistant', content: result.analysis || '', parts, loading: false },
        ]);
      } catch (fallbackErr) {
        setMessages((prev) => [
          ...prev,
          { role: 'assistant', content: '抱歉，请求失败，请稍后重试。', parts: [{ type: 'error', content: '请求失败' }], loading: false },
        ]);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleClear = () => {
    setMessages([]);
  };

  const suggestedQueries = [
    '查询今天的活跃用户数',
    '查询今天的充值总金额和充值人数',
    '查询最近7天每天的新增用户数',
    '查询今天提现金额TOP10用户',
  ];

  // 渲染数据表格
  const renderDataTable = (data) => {
    if (!data || !data.headers || !data.rows || data.rows.length === 0) {
      return <Text type="secondary">无数据</Text>;
    }

    const columns = data.headers.map((header, idx) => ({
      title: header,
      dataIndex: idx.toString(),
      key: idx.toString(),
      ellipsis: true,
    }));

    const dataSource = data.rows.slice(0, 50).map((row, rowIdx) => {
      const record = { key: rowIdx };
      row.forEach((cell, cellIdx) => {
        record[cellIdx.toString()] = cell;
      });
      return record;
    });

    return (
      <Table
        columns={columns}
        dataSource={dataSource}
        size="small"
        pagination={data.rows.length > 10 ? { pageSize: 10 } : false}
        scroll={{ x: 'max-content' }}
        style={{ marginTop: 8 }}
      />
    );
  };

  // 渲染助手消息的各部分
  const renderAssistantMessage = (msg) => {
    const parts = msg.parts || [];
    
    if (parts.length === 0 && msg.content) {
      return <ReactMarkdown>{msg.content}</ReactMarkdown>;
    }

    return (
      <div className="assistant-message-parts">
        {parts.map((part, idx) => {
          switch (part.type) {
            case 'status':
              return (
                <div key={idx} style={{ marginBottom: 8 }}>
                  <Text type="secondary">
                    <Spin size="small" style={{ marginRight: 8 }} />
                    {part.content}
                  </Text>
                </div>
              );
            case 'sql':
              return (
                <div key={idx} style={{ marginBottom: 12 }}>
                  <div style={{ display: 'flex', alignItems: 'center', marginBottom: 4 }}>
                    <CodeOutlined style={{ marginRight: 6, color: '#722ed1' }} />
                    <Text strong style={{ fontSize: 12, color: '#722ed1' }}>执行的SQL</Text>
                  </div>
                  <pre style={{
                    background: '#1e1e1e',
                    color: '#d4d4d4',
                    padding: '12px 16px',
                    borderRadius: 8,
                    fontSize: 12,
                    overflow: 'auto',
                    maxHeight: 150,
                    margin: 0,
                  }}>
                    {part.content}
                  </pre>
                </div>
              );
            case 'data':
              return (
                <div key={idx} style={{ marginBottom: 12 }}>
                  <div style={{ display: 'flex', alignItems: 'center', marginBottom: 4 }}>
                    <TableOutlined style={{ marginRight: 6, color: '#13c2c2' }} />
                    <Text strong style={{ fontSize: 12, color: '#13c2c2' }}>
                      查询结果 ({part.content?.total_rows || 0} 行)
                    </Text>
                  </div>
                  {renderDataTable(part.content)}
                </div>
              );
            case 'analysis':
              return (
                <div key={idx} style={{ marginBottom: 8 }}>
                  <div className="markdown-content">
                    <ReactMarkdown>{part.content}</ReactMarkdown>
                  </div>
                </div>
              );
            case 'error':
              return (
                <div key={idx} style={{ marginBottom: 8, color: '#ff4d4f' }}>
                  <Text type="danger">❌ {part.content}</Text>
                </div>
              );
            default:
              return null;
          }
        })}
        {msg.loading && parts[parts.length - 1]?.type !== 'status' && (
          <Spin size="small" />
        )}
      </div>
    );
  };

  const formatTime = (isoStr) => {
    if (!isoStr) return '';
    const d = new Date(isoStr);
    const now = new Date();
    const diffMs = now - d;
    const diffMin = Math.floor(diffMs / 60000);
    if (diffMin < 1) return '刚刚';
    if (diffMin < 60) return `${diffMin}分钟前`;
    const diffHour = Math.floor(diffMin / 60);
    if (diffHour < 24) return `${diffHour}小时前`;
    const diffDay = Math.floor(diffHour / 24);
    if (diffDay < 7) return `${diffDay}天前`;
    return d.toLocaleDateString('zh-CN');
  };

  return (
    <div style={{ height: 'calc(100vh - 160px)', display: 'flex', flexDirection: 'column' }}>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Space>
          <RobotOutlined style={{ fontSize: 20, color: '#1890ff' }} />
          <Title level={4} style={{ margin: 0 }}>AI 数据报告助手</Title>
          <Tag color="blue">接入数数API + AI分析</Tag>
        </Space>
        <Space>
          <Select
            value={currentProject}
            onChange={setCurrentProject}
            style={{ width: 160 }}
          >
            {projects.map(p => (
              <Option key={p.id} value={p.id}>{p.name}</Option>
            ))}
          </Select>
          <Badge count={historyList.length} size="small" offset={[-5, 5]}>
            <Button icon={<HistoryOutlined />} onClick={() => { setHistoryDrawerOpen(true); loadHistory(); }}>
              历史记录
            </Button>
          </Badge>
          <Button icon={<ClearOutlined />} onClick={handleClear}>
            清空对话
          </Button>
        </Space>
      </div>

      {/* Messages area */}
      <div style={{
        flex: 1,
        overflow: 'auto',
        padding: '16px 0',
        display: 'flex',
        flexDirection: 'column',
      }}>
        {messages.length === 0 && (
          <div style={{ textAlign: 'center', padding: '60px 0' }}>
            <RobotOutlined style={{ fontSize: 64, color: '#d9d9d9', marginBottom: 24 }} />
            <Title level={4} type="secondary">你好！我是风控数据分析助手</Title>
            <Text type="secondary" style={{ display: 'block', marginBottom: 24 }}>
              我可以帮你查询数数平台数据、分析用户行为、生成风控报告。请先选择项目再提问。
            </Text>
            <Space wrap style={{ maxWidth: 600 }}>
              {suggestedQueries.map((q, i) => (
                <Tag
                  key={i}
                  color="blue"
                  style={{ cursor: 'pointer', padding: '4px 12px', fontSize: 13 }}
                  onClick={() => setInput(q)}
                >
                  {q}
                </Tag>
              ))}
            </Space>
          </div>
        )}

        {messages.map((msg, index) => (
          <div
            key={index}
            style={{
              display: 'flex',
              gap: 12,
              marginBottom: 16,
              flexDirection: msg.role === 'user' ? 'row-reverse' : 'row',
            }}
          >
            <div style={{
              width: 36,
              height: 36,
              borderRadius: '50%',
              background: msg.role === 'user' ? '#1890ff' : '#f0f0f0',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
            }}>
              {msg.role === 'user' ? (
                <UserOutlined style={{ color: 'white' }} />
              ) : (
                <RobotOutlined style={{ color: '#1890ff' }} />
              )}
            </div>
            <div style={{
              maxWidth: msg.role === 'user' ? '75%' : '85%',
              minWidth: msg.role === 'assistant' ? '60%' : undefined,
            }}>
              {msg.role === 'user' ? (
                <Card
                  size="small"
                  style={{ background: '#1890ff', border: 'none' }}
                  bodyStyle={{ padding: '12px 16px', color: 'white' }}
                >
                  <span>{msg.content}</span>
                </Card>
              ) : (
                <Card
                  size="small"
                  style={{ background: '#f9f9f9', border: '1px solid #f0f0f0' }}
                  bodyStyle={{ padding: '16px' }}
                >
                  {renderAssistantMessage(msg)}
                </Card>
              )}
            </div>
          </div>
        ))}

        {loading && messages[messages.length - 1]?.role !== 'assistant' && (
          <div style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
            <div style={{
              width: 36, height: 36, borderRadius: '50%',
              background: '#f0f0f0', display: 'flex',
              alignItems: 'center', justifyContent: 'center',
            }}>
              <RobotOutlined style={{ color: '#1890ff' }} />
            </div>
            <Card size="small" style={{ background: '#f9f9f9', border: 'none' }}>
              <Spin size="small" /> <Text type="secondary">正在思考...</Text>
            </Card>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div style={{
        borderTop: '1px solid #f0f0f0',
        paddingTop: 16,
        display: 'flex',
        gap: 12,
      }}>
        <TextArea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={`当前项目: ${projects.find(p => p.id === currentProject)?.name} | 输入问题，如：查询今天的充值总金额...`}
          autoSize={{ minRows: 1, maxRows: 4 }}
          style={{ flex: 1, borderRadius: 8 }}
          disabled={loading}
        />
        <Button
          type="primary"
          icon={<SendOutlined />}
          onClick={handleSend}
          loading={loading}
          style={{ height: 'auto', borderRadius: 8 }}
        >
          发送
        </Button>
      </div>

      {/* History Drawer */}
      <Drawer
        title={
          <Space>
            <HistoryOutlined />
            <span>查询历史记录</span>
          </Space>
        }
        placement="right"
        width={420}
        open={historyDrawerOpen}
        onClose={() => setHistoryDrawerOpen(false)}
      >
        {historyLoading ? (
          <div style={{ textAlign: 'center', padding: 40 }}><Spin /></div>
        ) : historyList.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <Text type="secondary">暂无历史记录</Text>
          </div>
        ) : (
          <List
            dataSource={historyList}
            renderItem={(item) => (
              <List.Item
                style={{ cursor: 'pointer', padding: '12px 8px', borderRadius: 8 }}
                actions={[
                  <Popconfirm
                    key="delete"
                    title="确定删除？"
                    onConfirm={(e) => { e.stopPropagation(); handleDeleteHistory(item.id); }}
                    okText="删除"
                    cancelText="取消"
                  >
                    <Button type="text" size="small" danger icon={<DeleteOutlined />} onClick={(e) => e.stopPropagation()} />
                  </Popconfirm>
                ]}
                onClick={() => handleLoadHistoryItem(item)}
              >
                <List.Item.Meta
                  avatar={<MessageOutlined style={{ fontSize: 18, color: '#1890ff', marginTop: 4 }} />}
                  title={
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Text ellipsis style={{ maxWidth: 240, fontSize: 13 }}>{item.query}</Text>
                      <Tag color={item.status === 'success' ? 'green' : 'red'} style={{ fontSize: 11 }}>
                        {item.status === 'success' ? '成功' : '失败'}
                      </Tag>
                    </div>
                  }
                  description={
                    <Space size={12}>
                      <Text type="secondary" style={{ fontSize: 11 }}>{formatTime(item.created_at)}</Text>
                      {item.duration_ms && (
                        <Text type="secondary" style={{ fontSize: 11 }}>耗时 {(item.duration_ms / 1000).toFixed(1)}s</Text>
                      )}
                    </Space>
                  }
                />
              </List.Item>
            )}
          />
        )}
      </Drawer>
    </div>
  );
}

export default AIReport;
