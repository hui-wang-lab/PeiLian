(function() {
  const params = new URLSearchParams(window.location.search);
  const sessionId = params.get('session');
  if (!sessionId) {
    alert('缺少会话 ID');
    window.location.href = '/';
    return;
  }

  const CATEGORY_LABELS = {
    family_structure: '家庭结构',
    occupation: '职业行业',
    income: '收入水平',
    existing_coverage: '已有保障',
    future_planning: '未来规划',
    health_status: '健康情况'
  };

  async function loadReport() {
    try {
      const resp = await fetch('/api/sessions/' + sessionId + '/report');
      if (!resp.ok) {
        const err = await resp.json();
        alert('加载报告失败：' + (err.detail || resp.statusText));
        return;
      }
      const report = await resp.json();
      renderReport(report);
    } catch (e) {
      alert('网络错误：' + e.message);
    }
  }

  function renderReport(report) {
    document.getElementById('report-loading').style.display = 'none';
    document.getElementById('report-content').style.display = '';

    renderRadarChart(report);
    renderDialogue(report);
    renderCompliance(report);
    renderCustomerReport(report);
  }

  function renderRadarChart(report) {
    var scores = report.judge_result.agent_report.scores;
    var dimMap = {};
    scores.forEach(function(s) { dimMap[s.dimension] = s; });

    var indicator = [
      { name: '专业度', max: 5 },
      { name: '共情度', max: 5 },
      { name: '逻辑结构', max: 5 },
      { name: '异议处理', max: 5 },
      { name: '合规分', max: 5 }
    ];

    var values = [
      (dimMap.professionalism || {}).score || 0,
      (dimMap.empathy || {}).score || 0,
      (dimMap.structure || {}).score || 0,
      (dimMap.objection_handling || {}).score || 0,
      report.compliance_score
    ];

    var chart = echarts.init(document.getElementById('radar-chart'));
    chart.setOption({
      tooltip: { trigger: 'item' },
      color: ['#6366f1'],
      radar: {
        indicator: indicator,
        shape: 'polygon',
        splitNumber: 5,
        axisName: { color: '#475569', fontSize: 13, fontWeight: 600 },
        splitLine: { lineStyle: { color: '#e2e8f0' } },
        splitArea: {
          areaStyle: {
            color: ['rgba(99,102,241,0.02)', 'rgba(99,102,241,0.04)']
          }
        },
        axisLine: { lineStyle: { color: '#e2e8f0' } }
      },
      series: [{
        type: 'radar',
        data: [{
          value: values,
          name: '本次评分',
          symbol: 'circle',
          symbolSize: 6,
          areaStyle: {
            color: {
              type: 'radial', x: 0.5, y: 0.5, r: 0.75,
              colorStops: [
                { offset: 0, color: 'rgba(168,85,247,0.30)' },
                { offset: 1, color: 'rgba(99,102,241,0.10)' }
              ]
            }
          },
          lineStyle: { color: '#6366f1', width: 2 },
          itemStyle: { color: '#6366f1', borderColor: '#fff', borderWidth: 2 }
        }]
      }]
    });
    window.addEventListener('resize', function() { chart.resize(); });
  }

  function renderDialogue(report) {
    var container = document.getElementById('dialogue-annotated');
    var annotations = {};
    report.annotations.forEach(function(a) { annotations[a.turn_index] = a; });

    var html = '';
    report.messages.forEach(function(msg) {
      if (msg.role === 'system') return;
      var ann = annotations[msg.turn_index];
      var tags = '';
      if (ann) {
        ann.categories.forEach(function(c) {
          var label = CATEGORY_LABELS[c] || c;
          tags += '<span class="tag tag-kyc">' + label + ' ✓</span>';
        });
        ann.compliance_hits.forEach(function(h) {
          tags += '<span class="tag tag-compliance">⚠ ' + h.rule_label + '</span>';
        });
      }
      var roleLabel = msg.role === 'user' ? '代理人' : '客户';
      html += '<div class="turn-block">' +
        '<div class="turn-header">' + roleLabel + (ann ? '（第 ' + ann.agent_turn_number + ' 轮）' : '') + '</div>' +
        '<div class="turn-content ' + msg.role + '">' + escapeHtml(msg.content) + '</div>' +
        (tags ? '<div class="tags">' + tags + '</div>' : '') +
        '</div>';
    });
    container.innerHTML = html || '<p>暂无对话记录</p>';
  }

  function renderCompliance(report) {
    var container = document.getElementById('compliance-section');
    var hits = report.judge_result.evaluation_report.compliance_hits;
    if (!hits || hits.length === 0) {
      container.innerHTML = '<p class="no-issues">未发现违规</p>';
      return;
    }
    var html = hits.map(function(h) {
      return '<div class="hit-item">' +
        '<div class="rule-label">⚠ 第 ' + h.agent_turn_number + ' 轮 [代理人] — ' + h.rule_label + '</div>' +
        '<div>原话：' + escapeHtml(h.excerpt) + '</div>' +
        '<div>命中关键词：「' + escapeHtml(h.matched_keyword) + '」</div>' +
        '</div>';
    }).join('');
    container.innerHTML = html;
  }

  function renderCustomerReport(report) {
    var container = document.getElementById('customer-report');
    var cr = report.judge_result.customer_report;
    var html = '';
    var hasIssues = (cr.premature_disclosure_issues && cr.premature_disclosure_issues.length > 0) ||
                    (cr.inconsistency_issues && cr.inconsistency_issues.length > 0);
    if (!hasIssues) {
      html = '<p class="no-issues">未发现客户行为异常</p>';
    } else {
      if (cr.premature_disclosure_issues && cr.premature_disclosure_issues.length > 0) {
        html += '<h3 style="margin-bottom:8px;">越界泄露（' + cr.premature_disclosure_issues.length + ' 处）</h3>';
        cr.premature_disclosure_issues.forEach(function(i) {
          html += '<div class="issue-item">' +
            '<div>第 ' + i.agent_turn_number + ' 轮 [' + escapeHtml(i.protected_field) + ']</div>' +
            '<div>原话：' + escapeHtml(i.excerpt) + '</div>' +
            '<div>理由：' + escapeHtml(i.reasoning) + '</div>' +
            '</div>';
        });
      }
      if (cr.inconsistency_issues && cr.inconsistency_issues.length > 0) {
        html += '<h3 style="margin:12px 0 8px;">一致性问题（' + cr.inconsistency_issues.length + ' 处）</h3>';
        cr.inconsistency_issues.forEach(function(i) {
          html += '<div class="issue-item">' +
            '<div>第 ' + i.agent_turn_number + ' 轮 [' + escapeHtml(i.protected_field) + ']</div>' +
            '<div>原话：' + escapeHtml(i.excerpt) + '</div>' +
            '<div>理由：' + escapeHtml(i.reasoning) + '</div>' +
            '</div>';
        });
      }
    }
    html += '<p style="margin-top:12px;color:#666;font-size:13px;">综合评语：' + escapeHtml(cr.overall_comment) + '</p>';
    container.innerHTML = html;
  }

  function escapeHtml(text) {
    var div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  loadReport();
})();
