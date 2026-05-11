import React, { useState, useRef, useEffect } from 'react';
import { Input, Button, Card, Space, Typography, Spin, Tag, Table, Select, List, Popconfirm, message, Empty } from 'antd';
import { SendOutlined, RobotOutlined, UserOutlined, PlusOutlined, CodeOutlined, TableOutlined, DeleteOutlined, MessageOutlined, EditOutlined, CheckOutlined } from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';
import { reportAPI } from '../services/api';

const { TextArea } = Input;
const { Title, Text } = Typography;
const { Option } = Select;

function AIReport() {
  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const [currentProject, setCurrentProject] = useState('105');
  const [editingTitle, setEditingTitle] = useState(null);
  const [editTitleValue, setEditTitleValue] = useState('');
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

  // Load sessions on mount
  useEffect(() => {
    loadSessions();
  }, []);

  const loadSessions = async () => {
    setSessionsLoading(true);
    try {
      const res = await reportAPI.listSessions();
      setSessions(res.data || []);
      // Auto-select the most recent session if none selected
      if (!currentSessionId && res.data && res.data.length > 0) {
        await switchToSession(res.data[0].id);
      }
    } catch (err) {
      console.error('Failed to load sessions:', err);
    } finally {
      setSessionsLoading(false);
    }
  };

  const switchToSession = async (sessionId) => {
    try {
      const res = await reportAPI.getSession(sessionId);
      setCurrentSessionId(sessionId);
      setMessages(res.data.messages || []);
      if (res.data.project_id) {
        setCurrentProject(res.data.project_id);
      }
    } catch (err) {
      message.error('加载会话失败');
    }
  };

  const handleNewSession = async () => {
    try {
      const res = await reportAPI.createSession('新对话', currentProject);
      const newSession = res.data;
      setSessions((prev) => [{ ...newSession, message_count: 0 }, ...prev]);
      setCurrentSessionId(newSession.id);
      setMessages([]);
    } catch (err) {
      message.error('创建会话失败');
    }
  };

  const handleDeleteSession = async (sessionId, e) => {
    e?.stopPropagation();
    try {
      await reportAPI.deleteSession(sessionId);
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));
      if (currentSessionId === sessionId) {
        setCurrentSessionId(null);
        setMessages([]);
      }
      message.success('已删除');
    } catch (err) {
      message.error('删除失败');
    }
  };

  const handleRenameSession = async (sessionId) => {
    if (!editTitleValue.trim()) return;
    try {
      await reportAPI.updateSession(sessionId, { title: editTitleValue.trim() });
      setSessions((prev) => prev.map((s) => s.id === sessionId ? { ...s, title: editTitleValue.trim() } : s));
      setEditingTitle(null);
    } catch (err) {
      message.error('重命名失败');
    }
  };

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    // If no session, create one first
    let sessionId = currentSessionId;
    if (!sessionId) {
      try {
        const res = await reportAPI.createSession('新对话', currentProject);
        sessionId = res.data.id;
        setSessions((prev) => [{ ...res.data, message_count: 0 }, ...prev]);
        setCurrentSessionId(sessionId);
      } catch (err) {
        message.error('创建会话失败');
        return;
      }
    }

    const userMessage = { role: 'user', content: input.trim() };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const queryWithProject = `[项目${currentProject}] ${userMessage.content}`;
      
      const response = await reportAPI.chatStream(queryWithProject, sessionId);

      if (!response.ok) {
        throw new Error('Stream request failed');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let parts = [];

      setMessages((prev) => [...prev, { role: 'assistant', content: '', parts: [], loading: true }]);

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

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
              console.warn('Failed to parse SSE data:', dataStr);
            }
          }
        }
      }

      setMessages((prev) => {
        const updated = [...prev];
        if (updated.length > 0) {
          updated[updated.length - 1].loading = false;
        }
        return updated;
      });

      // Refresh sessions list to update title/count
      setTimeout(() => loadSessions(), 500);

    } catch (err) {
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

  const suggestedQueries = [
    '查询今天的活跃用户数',
    '查询今天的充值总金额和充值人数',
    '查询最近7天每天的新增用户数',
    '查询今天提现金额TOP10用户',
  ];

  const renderDataTable = (data) => {
    if (!data || !data.headers || !data.rows || data.rows.length === 0) {
      return <Text type="secondary">无数据</Text>;
    }
    const columns = data.headers.map((header, idx) => ({
      title: header, dataIndex: idx.toString(), key: idx.toString(), ellipsis: true,
    }));
    const dataSource = data.rows.slice(0, 50).map((row, rowIdx) => {
      const record = { key: rowIdx };
      row.forEach((cell, cellIdx) => { record[cellIdx.toString()] = cell; });
      return record;
    });
    return (
      <Table columns={columns} dataSource={dataSource} size="small"
        pagination={data.rows.length > 10 ? { pageSize: 10 } : false}
        scroll={{ x: 'max-content' }} style={{ marginTop: 8 }} />
    );
  };

  const renderAssistantMessage = (msg) => {
    const parts = msg.parts || [];
    if (parts.length === 0 && msg.content) {
      return <ReactMarkdown>{msg.content}</ReactMarkdown>;
    }
    return (
      <div>
        {parts.map((part, idx) => {
          switch (part.type) {
            case 'status':
              return (
                <div key={idx} style={{ marginBottom: 8 }}>
                  <Text type="secondary"><Spin size="small" style={{ marginRight: 8 }} />{part.content}</Text>
                </div>
              );
            case 'sql':
              return (
                <div key={idx} style={{ marginBottom: 12 }}>
                  <div style={{ display: 'flex', alignItems: 'center', marginBottom: 4 }}>
                    <CodeOutlined style={{ marginRight: 6, color: '#722ed1' }} />
                    <Text strong style={{ fontSize: 12, color: '#722ed1' }}>执行的SQL</Text>
                  </div>
                  <pre style={{ background: '#1e1e1e', color: '#d4d4d4', padding: '12px 16px', borderRadius: 8, fontSize: 12, overflow: 'auto', maxHeight: 150, margin: 0 }}>
                    {part.content}
                  </pre>
                </div>
              );
            case 'data':
              return (
                <div key={idx} style={{ marginBottom: 12 }}>
                  <div style={{ display: 'flex', alignItems: 'center', marginBottom: 4 }}>
                    <TableOutlined style={{ marginRight: 6, color: '#13c2c2' }} />
                    <Text strong style={{ fontSize: 12, color: '#13c2c2' }}>查询结果 ({part.content?.total_rows || 0} 行)</Text>
                  </div>
                  {renderDataTable(part.content)}
                </div>
              );
            case 'analysis':
              return (
                <div key={idx} style={{ marginBottom: 8 }}>
                  <div className="markdown-content"><ReactMarkdown>{part.content}</ReactMarkdown></div>
                </div>
              );
            case 'error':
              return (
                <div key={idx} style={{ marginBottom: 8 }}>
                  <Text type="danger">❌ {part.content}</Text>
                </div>
              );
            default:
              return null;
          }
        })}
        {msg.loading && parts[parts.length - 1]?.type !== 'status' && <Spin size="small" />}
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
    <div style={{ height: 'calc(100vh - 160px)', display: 'flex', gap: 0 }}>
      {/* Left sidebar - Session list */}
      <div style={{
        width: 260,
        borderRight: '1px solid #f0f0f0',
        display: 'flex',
        flexDirection: 'column',
        background: '#fafafa',
        borderRadius: '8px 0 0 8px',
        overflow: 'hidden',
      }}>
        <div style={{ padding: '12px 16px', borderBottom: '1px solid #f0f0f0' }}>
          <Button type="primary" icon={<PlusOutlined />} block onClick={handleNewSession}>
            新建对话
          </Button>
        </div>
        <div style={{ flex: 1, overflow: 'auto', padding: '8px' }}>
          {sessionsLoading ? (
            <div style={{ textAlign: 'center', padding: 20 }}><Spin size="small" /></div>
          ) : sessions.length === 0 ? (
            <Empty description="暂无对话" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          ) : (
            sessions.map((session) => (
              <div
                key={session.id}
                onClick={() => switchToSession(session.id)}
                style={{
                  padding: '10px 12px',
                  marginBottom: 4,
                  borderRadius: 8,
                  cursor: 'pointer',
                  background: currentSessionId === session.id ? '#e6f4ff' : 'transparent',
                  border: currentSessionId === session.id ? '1px solid #91caff' : '1px solid transparent',
                  transition: 'all 0.2s',
                }}
                onMouseEnter={(e) => { if (currentSessionId !== session.id) e.currentTarget.style.background = '#f5f5f5'; }}
                onMouseLeave={(e) => { if (currentSessionId !== session.id) e.currentTarget.style.background = 'transparent'; }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  {editingTitle === session.id ? (
                    <Input
                      size="small"
                      value={editTitleValue}
                      onChange={(e) => setEditTitleValue(e.target.value)}
                      onPressEnter={() => handleRenameSession(session.id)}
                      onBlur={() => setEditingTitle(null)}
                      autoFocus
                      style={{ flex: 1, marginRight: 4 }}
                    />
                  ) : (
                    <div style={{ flex: 1, overflow: 'hidden' }}>
                      <Text ellipsis style={{ fontSize: 13, fontWeight: currentSessionId === session.id ? 500 : 400 }}>
                        <MessageOutlined style={{ marginRight: 6, color: '#1890ff', fontSize: 12 }} />
                        {session.title}
                      </Text>
                    </div>
                  )}
                  {currentSessionId === session.id && editingTitle !== session.id && (
                    <Space size={2}>
                      <Button type="text" size="small" icon={<EditOutlined style={{ fontSize: 11 }} />}
                        onClick={(e) => { e.stopPropagation(); setEditingTitle(session.id); setEditTitleValue(session.title); }} />
                      <Popconfirm title="确定删除此对话？" onConfirm={(e) => handleDeleteSession(session.id, e)} okText="删除" cancelText="取消">
                        <Button type="text" size="small" danger icon={<DeleteOutlined style={{ fontSize: 11 }} />}
                          onClick={(e) => e.stopPropagation()} />
                      </Popconfirm>
                    </Space>
                  )}
                </div>
                <div style={{ marginTop: 2 }}>
                  <Text type="secondary" style={{ fontSize: 11 }}>
                    {session.message_count > 0 ? `${Math.floor(session.message_count / 2)} 条问答` : '空对话'}
                    {' · '}
                    {formatTime(session.updated_at || session.created_at)}
                  </Text>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Right - Chat area */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', padding: '0 0 0 16px' }}>
        {/* Header */}
        <div style={{ marginBottom: 12, display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: 4 }}>
          <Space>
            <RobotOutlined style={{ fontSize: 18, color: '#1890ff' }} />
            <Title level={5} style={{ margin: 0 }}>AI 数据报告助手</Title>
            <Tag color="blue" style={{ fontSize: 11 }}>多轮对话 · 记忆保持</Tag>
          </Space>
          <Select value={currentProject} onChange={setCurrentProject} style={{ width: 150 }} size="small">
            {projects.map(p => <Option key={p.id} value={p.id}>{p.name}</Option>)}
          </Select>
        </div>

        {/* Messages */}
        <div style={{ flex: 1, overflow: 'auto', paddingRight: 8 }}>
          {messages.length === 0 && (
            <div style={{ textAlign: 'center', padding: '50px 0' }}>
              <RobotOutlined style={{ fontSize: 56, color: '#d9d9d9', marginBottom: 20 }} />
              <Title level={5} type="secondary">开始新的数据分析对话</Title>
              <Text type="secondary" style={{ display: 'block', marginBottom: 20 }}>
                在同一对话中持续追问，AI 会记住上下文。点击左侧"新建对话"开启新话题。
              </Text>
              <Space wrap style={{ maxWidth: 500 }}>
                {suggestedQueries.map((q, i) => (
                  <Tag key={i} color="blue" style={{ cursor: 'pointer', padding: '4px 10px', fontSize: 12 }}
                    onClick={() => setInput(q)}>
                    {q}
                  </Tag>
                ))}
              </Space>
            </div>
          )}

          {messages.map((msg, index) => (
            <div key={index} style={{ display: 'flex', gap: 10, marginBottom: 14, flexDirection: msg.role === 'user' ? 'row-reverse' : 'row' }}>
              <div style={{
                width: 32, height: 32, borderRadius: '50%', flexShrink: 0,
                background: msg.role === 'user' ? '#1890ff' : '#f0f0f0',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                {msg.role === 'user' ? <UserOutlined style={{ color: 'white', fontSize: 14 }} /> : <RobotOutlined style={{ color: '#1890ff', fontSize: 14 }} />}
              </div>
              <div style={{ maxWidth: msg.role === 'user' ? '70%' : '82%', minWidth: msg.role === 'assistant' ? '55%' : undefined }}>
                {msg.role === 'user' ? (
                  <Card size="small" style={{ background: '#1890ff', border: 'none' }} bodyStyle={{ padding: '10px 14px', color: 'white' }}>
                    <span style={{ fontSize: 13 }}>{msg.content}</span>
                  </Card>
                ) : (
                  <Card size="small" style={{ background: '#f9f9f9', border: '1px solid #f0f0f0' }} bodyStyle={{ padding: '14px' }}>
                    {renderAssistantMessage(msg)}
                  </Card>
                )}
              </div>
            </div>
          ))}

          {loading && messages[messages.length - 1]?.role !== 'assistant' && (
            <div style={{ display: 'flex', gap: 10, marginBottom: 14 }}>
              <div style={{ width: 32, height: 32, borderRadius: '50%', background: '#f0f0f0', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <RobotOutlined style={{ color: '#1890ff', fontSize: 14 }} />
              </div>
              <Card size="small" style={{ background: '#f9f9f9', border: 'none' }}>
                <Spin size="small" /> <Text type="secondary">正在思考...</Text>
              </Card>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div style={{ borderTop: '1px solid #f0f0f0', paddingTop: 12, display: 'flex', gap: 10 }}>
          <TextArea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={`当前项目: ${projects.find(p => p.id === currentProject)?.name} | 输入问题，可持续追问...`}
            autoSize={{ minRows: 1, maxRows: 4 }}
            style={{ flex: 1, borderRadius: 8 }}
            disabled={loading}
          />
          <Button type="primary" icon={<SendOutlined />} onClick={handleSend} loading={loading} style={{ height: 'auto', borderRadius: 8 }}>
            发送
          </Button>
        </div>
      </div>
    </div>
  );
}

export default AIReport;
