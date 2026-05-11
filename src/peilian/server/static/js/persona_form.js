(function () {
  const tagBuckets = {};
  const concerns = [];

  const concernPresets = {
    price_sensitive: {
      title: '担心预算',
      key: 'price_sensitive',
      label: '担心保费影响家庭预算',
      keywords: ['保费', '预算', '贵', '多少钱'],
    },
    trust_issue: {
      title: '信任不足',
      key: 'trust_issue',
      label: '担心被过度推销或误导',
      keywords: ['靠谱', '信任', '骗人', '推销'],
    },
    health_disclosure: {
      title: '健康告知',
      key: 'health_disclosure',
      label: '不想讲太细的健康情况',
      keywords: ['健康', '体检', '病史', '告知'],
    },
    compare_products: {
      title: '想多比较',
      key: 'compare_products',
      label: '想和其他产品或渠道再比较',
      keywords: ['比较', '别家', '再看看', '朋友'],
    },
    family_decision: {
      title: '家人决策',
      key: 'family_decision',
      label: '需要和家人商量后再决定',
      keywords: ['家人', '爱人', '商量', '决定'],
    },
  };

  const personaPresets = {
    price_sensitive: {
      idPrefix: 'price_sensitive_customer',
      name: '林先生',
      age: 38,
      occupation: '小企业主',
      income_level: '中等',
      family: '已婚，一个 6 岁孩子',
      initial_mood: '礼貌但略微戒备',
      existing_coverage: ['社保', '百万医疗险'],
      pain_points: ['担心家庭现金流', '对保险条款不熟悉'],
      persistence: 0.7,
      expressiveness: 0.5,
      concerns: ['price_sensitive', 'health_disclosure'],
      style: 'mild',
    },
    trust_issue: {
      idPrefix: 'trust_issue_customer',
      name: '周女士',
      age: 42,
      occupation: '门店老板',
      income_level: '中高收入',
      family: '已婚，父母需要赡养',
      initial_mood: '客气但防备心强',
      existing_coverage: ['社保'],
      pain_points: ['以前听过亲友理赔纠纷', '不喜欢被催单'],
      persistence: 0.8,
      expressiveness: 0.4,
      concerns: ['trust_issue', 'compare_products'],
      style: 'mild',
    },
    busy_direct: {
      idPrefix: 'busy_direct_customer',
      name: '陈先生',
      age: 35,
      occupation: '互联网产品经理',
      income_level: '中高收入',
      family: '已婚，一个 2 岁孩子',
      initial_mood: '赶时间，希望对方直接说重点',
      existing_coverage: ['公司团险', '社保'],
      pain_points: ['时间紧', '希望方案清楚简单'],
      persistence: 0.5,
      expressiveness: 0.7,
      concerns: ['compare_products', 'family_decision'],
      style: 'mild',
    },
    high_net_worth: {
      idPrefix: 'high_net_worth_customer',
      name: '顾先生',
      age: 48,
      occupation: '企业合伙人',
      income_level: '高净值',
      family: '已婚，两个孩子',
      initial_mood: '理性克制，对专业度要求高',
      existing_coverage: ['高端医疗', '定期寿险'],
      pain_points: ['关注资产传承', '不想买重复保障'],
      persistence: 0.9,
      expressiveness: 0.4,
      concerns: ['compare_products', 'trust_issue'],
      style: 'heavy',
    },
  };

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text == null ? '' : String(text);
    return div.innerHTML;
  }

  function setValue(id, value) {
    const el = document.getElementById(id);
    if (el) el.value = value;
  }

  function makeSlug(prefix) {
    const suffix = Date.now().toString(36).slice(-6);
    return (prefix || 'custom_customer') + '_' + suffix;
  }

  function uniqueConcernKey(base, index) {
    const normalized = base || 'custom_concern';
    const taken = new Set(concerns.map((c, i) => (i === index ? '' : c.key)));
    if (!taken.has(normalized)) return normalized;
    let n = 2;
    while (taken.has(normalized + '_' + n)) n += 1;
    return normalized + '_' + n;
  }

  function showBanner(kind, text) {
    const b = document.getElementById('form-banner');
    b.className = 'form-banner show ' + kind;
    b.textContent = text;
    if (kind === 'success') {
      setTimeout(() => { b.classList.remove('show'); }, 3000);
    }
  }

  function setTags(target, values) {
    tagBuckets[target] = Array.from(new Set((values || []).filter(Boolean)));
    const row = document.querySelector(`.tag-input-row[data-tag-target="${target}"]`);
    if (row) renderTagRow(row);
  }

  function renderTagRow(row) {
    const target = row.dataset.tagTarget;
    if (!target) return;
    tagBuckets[target] = tagBuckets[target] || [];
    const input = row.querySelector('input');
    row.querySelectorAll('.tag-chip').forEach(n => n.remove());
    tagBuckets[target].forEach((t, idx) => {
      const chip = document.createElement('span');
      chip.className = 'tag-chip';
      chip.innerHTML = `${escapeHtml(t)}<button type="button" class="remove" data-idx="${idx}" aria-label="移除">×</button>`;
      row.insertBefore(chip, input);
    });
    row.querySelectorAll('.remove').forEach(btn => {
      btn.addEventListener('click', () => {
        tagBuckets[target].splice(Number(btn.dataset.idx), 1);
        renderTagRow(row);
      });
    });
  }

  function addTags(value, list) {
    value.split(/[,，]/).map(s => s.trim()).filter(Boolean).forEach(p => {
      if (!list.includes(p)) list.push(p);
    });
  }

  function setupTagRow(row) {
    const target = row.dataset.tagTarget;
    if (!target) return;
    tagBuckets[target] = tagBuckets[target] || [];
    const input = row.querySelector('input');

    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ',' || e.key === '，') {
        e.preventDefault();
        addTags(input.value.trim(), tagBuckets[target]);
        input.value = '';
        renderTagRow(row);
      } else if (e.key === 'Backspace' && input.value === '' && tagBuckets[target].length) {
        tagBuckets[target].pop();
        renderTagRow(row);
      }
    });
    input.addEventListener('blur', () => {
      addTags(input.value.trim(), tagBuckets[target]);
      input.value = '';
      renderTagRow(row);
    });
    renderTagRow(row);
  }

  function makeConcern(type) {
    const preset = concernPresets[type] || concernPresets.price_sensitive;
    const index = concerns.length;
    return {
      type,
      key: uniqueConcernKey(preset.key, index),
      label: preset.label,
      keywords: preset.keywords.slice(),
      initial_stage: 'untouched',
    };
  }

  function renderConcerns() {
    const list = document.getElementById('concerns-list');
    list.innerHTML = concerns.map((c, idx) => `
      <div class="concern-row" data-idx="${idx}">
        <div class="concern-header">
          <span>顾虑 #${idx + 1}</span>
          <button type="button" class="remove-concern" data-idx="${idx}">移除</button>
        </div>
        <div class="form-row">
          <div class="form-field">
            <label class="field-label">顾虑类型</label>
            <select data-field="type" data-idx="${idx}">
              ${Object.entries(concernPresets).map(([key, p]) => `
                <option value="${key}" ${c.type === key ? 'selected' : ''}>${escapeHtml(p.title)}</option>
              `).join('')}
            </select>
          </div>
          <div class="form-field">
            <label class="field-label">具体担心<span class="required">*</span></label>
            <input type="text" data-field="label" data-idx="${idx}" value="${escapeHtml(c.label)}" placeholder="如 担心保费太贵影响房贷">
          </div>
        </div>
        <div class="form-field">
          <label class="field-label">触发词</label>
          <div class="tag-input-row concern-tag-row" data-concern-idx="${idx}">
            <input type="text" placeholder="输入后回车或逗号分隔">
          </div>
          <div class="field-hint">代理人提到这些词时，客户才更容易把这条顾虑露出来。</div>
        </div>
      </div>
    `).join('');

    list.querySelectorAll('[data-field]').forEach(el => {
      el.addEventListener('input', () => updateConcernField(el));
      el.addEventListener('change', () => updateConcernField(el));
    });

    list.querySelectorAll('.remove-concern').forEach(btn => {
      btn.addEventListener('click', () => {
        concerns.splice(Number(btn.dataset.idx), 1);
        if (!concerns.length) concerns.push(makeConcern('price_sensitive'));
        renderConcerns();
      });
    });

    list.querySelectorAll('.concern-tag-row').forEach(setupConcernTagRow);
  }

  function updateConcernField(el) {
    const idx = Number(el.dataset.idx);
    const field = el.dataset.field;
    if (field === 'type') {
      const preset = concernPresets[el.value];
      concerns[idx].type = el.value;
      concerns[idx].key = uniqueConcernKey(preset.key, idx);
      concerns[idx].label = preset.label;
      concerns[idx].keywords = preset.keywords.slice();
      renderConcerns();
      return;
    }
    concerns[idx][field] = el.value;
  }

  function setupConcernTagRow(row) {
    const concernIdx = Number(row.dataset.concernIdx);
    const input = row.querySelector('input');

    function rerender() {
      row.querySelectorAll('.tag-chip').forEach(n => n.remove());
      (concerns[concernIdx].keywords || []).forEach((t, ki) => {
        const chip = document.createElement('span');
        chip.className = 'tag-chip';
        chip.innerHTML = `${escapeHtml(t)}<button type="button" class="remove" data-ki="${ki}" aria-label="移除">×</button>`;
        row.insertBefore(chip, input);
      });
      row.querySelectorAll('.remove').forEach(b => {
        b.addEventListener('click', () => {
          concerns[concernIdx].keywords.splice(Number(b.dataset.ki), 1);
          rerender();
        });
      });
    }

    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ',' || e.key === '，') {
        e.preventDefault();
        addTags(input.value.trim(), concerns[concernIdx].keywords);
        input.value = '';
        rerender();
      } else if (e.key === 'Backspace' && input.value === '' && concerns[concernIdx].keywords.length) {
        concerns[concernIdx].keywords.pop();
        rerender();
      }
    });
    input.addEventListener('blur', () => {
      addTags(input.value.trim(), concerns[concernIdx].keywords);
      input.value = '';
      rerender();
    });
    rerender();
  }

  function updateRangePreview() {
    const p = Number(document.getElementById('f-persistence').value);
    const e = Number(document.getElementById('f-expressiveness').value);
    document.getElementById('persistence-value').textContent = p.toFixed(1);
    document.getElementById('expressiveness-value').textContent = e.toFixed(1);
    document.getElementById('difficulty-preview').innerHTML = `
      <span>简单：抗拒 ${(p * 0.5).toFixed(1)} / 表达 ${Math.min(1, e * 1.3).toFixed(1)}</span>
      <span>中等：抗拒 ${p.toFixed(1)} / 表达 ${e.toFixed(1)}</span>
      <span>困难：抗拒 ${Math.min(1, p * 1.3).toFixed(1)} / 表达 ${(e * 0.7).toFixed(1)}</span>
    `;
  }

  function selectStyle(style) {
    document.querySelectorAll('.style-option').forEach(opt => {
      const radio = opt.querySelector('input');
      const active = radio.value === style;
      opt.classList.toggle('checked', active);
      radio.checked = active;
    });
  }

  function applyPreset(key) {
    const preset = personaPresets[key];
    if (!preset) return;

    document.querySelectorAll('.preset-option').forEach(btn => {
      btn.classList.toggle('checked', btn.dataset.preset === key);
    });
    setValue('f-id', makeSlug(preset.idPrefix));
    setValue('f-name', preset.name);
    setValue('f-age', preset.age);
    setValue('f-occupation', preset.occupation);
    setValue('f-income', preset.income_level);
    setValue('f-family', preset.family);
    setValue('f-mood', preset.initial_mood);
    setValue('f-persistence', preset.persistence);
    setValue('f-expressiveness', preset.expressiveness);
    setTags('existing_coverage', preset.existing_coverage);
    setTags('pain_points', preset.pain_points);
    concerns.splice(0, concerns.length);
    preset.concerns.forEach(type => concerns.push(makeConcern(type)));
    selectStyle(preset.style);
    renderConcerns();
    updateRangePreview();
  }

  function validate(payload) {
    if (!/^[a-z0-9_]{1,32}$/.test(payload.id)) {
      showBanner('error', '客户编号必须是小写字母 / 数字 / 下划线，长度 ≤ 32');
      return false;
    }
    if (!payload.name || !payload.occupation || !payload.family || !payload.income_level || !payload.initial_mood) {
      showBanner('error', '请填写所有标 * 的必填字段');
      return false;
    }
    if (!payload.hidden_concerns.length) {
      showBanner('error', '至少需要 1 条内心顾虑');
      return false;
    }
    for (let i = 0; i < payload.hidden_concerns.length; i++) {
      const hc = payload.hidden_concerns[i];
      if (!hc.label) {
        showBanner('error', `第 ${i + 1} 条顾虑的具体担心不能为空`);
        return false;
      }
      if (!hc.keywords.length) {
        showBanner('error', `第 ${i + 1} 条顾虑至少需要 1 个触发词`);
        return false;
      }
    }
    return true;
  }

  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.tag-input-row[data-tag-target]').forEach(setupTagRow);

    document.querySelectorAll('.preset-option').forEach(btn => {
      btn.addEventListener('click', () => applyPreset(btn.dataset.preset));
    });

    document.getElementById('add-concern-btn').addEventListener('click', () => {
      concerns.push(makeConcern('price_sensitive'));
      renderConcerns();
    });

    document.querySelectorAll('.style-option').forEach(opt => {
      const radio = opt.querySelector('input');
      opt.addEventListener('click', () => selectStyle(radio.value));
    });

    ['f-persistence', 'f-expressiveness'].forEach(id => {
      document.getElementById(id).addEventListener('input', updateRangePreview);
    });

    applyPreset('price_sensitive');

    document.getElementById('persona-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      if (!document.getElementById('f-id').value.trim()) {
        setValue('f-id', makeSlug('custom_customer'));
      }

      const payload = {
        id: document.getElementById('f-id').value.trim(),
        name: document.getElementById('f-name').value.trim(),
        age: Number(document.getElementById('f-age').value),
        occupation: document.getElementById('f-occupation').value.trim(),
        family: document.getElementById('f-family').value.trim(),
        income_level: document.getElementById('f-income').value.trim(),
        existing_coverage: (tagBuckets.existing_coverage || []).slice(),
        pain_points: (tagBuckets.pain_points || []).slice(),
        hidden_concerns: concerns.map((c, idx) => ({
          key: uniqueConcernKey(c.key, idx),
          label: c.label.trim(),
          keywords: (c.keywords || []).filter(Boolean),
          initial_stage: 'untouched',
        })),
        persistence: Number(document.getElementById('f-persistence').value),
        expressiveness: Number(document.getElementById('f-expressiveness').value),
        initial_mood: document.getElementById('f-mood').value.trim(),
        colloquial_style: document.querySelector('input[name="colloquial_style"]:checked').value,
      };

      if (!validate(payload)) return;

      const submitBtn = document.getElementById('submit-btn');
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<span class="loading"></span> 保存中...';

      try {
        const resp = await fetch('/api/personas', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        if (!resp.ok) {
          const err = await resp.json().catch(() => ({}));
          showBanner('error', '保存失败：' + (err.detail || resp.statusText));
          submitBtn.disabled = false;
          submitBtn.textContent = '保存并返回首页';
          return;
        }
        showBanner('success', '保存成功，正在返回首页...');
        setTimeout(() => { window.location.href = '/'; }, 600);
      } catch (err) {
        showBanner('error', '网络错误：' + err.message);
        submitBtn.disabled = false;
        submitBtn.textContent = '保存并返回首页';
      }
    });
  });
})();
