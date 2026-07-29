import React from 'react';

/**
 * Chargeback 抗辩复核月度统计报告页。
 * 复用 public/chargeback-report.html（内含完整图表 + 上传入口），
 * 以 iframe 全屏嵌入到后台布局中，避免重复实现图表逻辑。
 */
export default function ChargebackReport() {
  return (
    <div style={{ height: 'calc(100vh - 64px - 32px)', margin: -24 }}>
      <iframe
        title="Chargeback 抗辩复核报告"
        src="/chargeback-report.html"
        style={{ width: '100%', height: '100%', border: 'none', borderRadius: 8 }}
      />
    </div>
  );
}
