(function () {
  const tags = [];
  let generatedDirty = false;

  const presets = {
    first_meet: {
      idPrefix: 'first_meet_scene',
      name: '办公室初次面谈',
      place: '客户办公室',
      relationship: '第一次见面，只是经朋友介绍认识',
      attitude: '礼貌但略微戒备，不想一上来就被推销',
      timeLimit: '只能预留 15 分钟',
      boundary: '不想当场做决定，对价格和健康告知比较敏感',
      tags: ['初次见面', '办公室'],
    },
    followup: {
      idPrefix: 'followup_scene',
      name: '咖啡馆二次跟进',
      place: '公司附近的咖啡馆',
      relationship: '之前见过一次，客户还记得代理人',
      attitude: '愿意听，但希望对方直接说重点',
      timeLimit: '可以聊 30 分钟左右',
      boundary: '客户上次觉得保费偏高，这次希望先听清楚价值',
      tags: ['二次跟进', '异议处理'],
    },
    phone_intro: {
      idPrefix: 'phone_intro_scene',
      name: '电话初次邀约',
      place: '电话中',
      relationship: '电话陌生触达，客户防备心较强',
      attitude: '比较忙，随时可能结束对话',
      timeLimit: '只能预留 5 分钟',
      boundary: '客户反感长篇推销，只有听到明确价值才愿意继续聊',
      tags: ['电话', '邀约'],
    },
    family_decision: {
      idPrefix: 'family_decision_scene',
      name: '家庭决策沟通',
      place: '客户家中客厅',
      relationship: '老客户转介绍，客户愿意给一点时间',
      attitude: '对保险兴趣不高，但愿意给一个解释机会',
      timeLimit: '可以聊 30 分钟左右',
      boundary: '客户需要和配偶商量，不希望被要求现场拍板',
      tags: ['家庭决策', '促成'],
    },
  };

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text == null ? '' : String(text);
    return div.innerHTML;
  }

  function makeSlug(prefix) {
    const suffix = Date.now().toString(36).slice(-6);
    return (prefix || 'custom_scene') + '_' + suffix;
  }

  function setValue(id, value) {
    const el = document.getElementById(id);
    if (el) el.value = value;
  }

  function renderTags() {
    const row = document.getElementById('tag-input-row');
    row.querySelectorAll('.tag-chip').forEach(n => n.remove());
    const input = document.getElementById('f-tag-input');
    tags.forEach((t, idx) => {
      const chip = document.createElement('span');
      chip.className = 'tag-chip';
      chip.innerHTML = `${escapeHtml(t)}<button type="button" class="remove" data-idx="${idx}" aria-label="移除">×</button>`;
      row.insertBefore(chip, input);
    });
    row.querySelectorAll('.remove').forEach(btn => {
      btn.addEventListener('click', () => {
        tags.splice(Number(btn.dataset.idx), 1);
        renderTags();
      });
    });
  }

  function setTags(values) {
    tags.splice(0, tags.length, ...Array.from(new Set((values || []).filter(Boolean))));
    renderTags();
  }

  function addTagsFromInput(value) {
    if (value == null) return;
    value.split(/[,，]/).map(s => s.trim()).filter(Boolean).forEach(p => {
      if (!tags.includes(p)) tags.push(p);
    });
    renderTags();
  }

  function showBanner(kind, text) {
    const b = document.getElementById('form-banner');
    b.className = 'form-banner show ' + kind;
    b.textContent = text;
    if (kind === 'success') {
      setTimeout(() => { b.classList.remove('show'); }, 3000);
    }
  }

  function currentGeneratedText() {
    const place = document.getElementById('f-place').value.trim();
    const relationship = document.getElementById('f-relationship').value.trim();
    const attitude = document.getElementById('f-attitude').value.trim();
    const timeLimit = document.getElementById('f-time-limit').value.trim();
    const boundary = document.getElementById('f-boundary').value.trim();

    const context = `你和这位代理人在${place}沟通。你们的关系是：${relationship}。你当前的状态是：${attitude}。`;
    const constraints = `${timeLimit}；${boundary || '不希望对方跳过需求了解直接推产品'}。代理人没有具体问到时，你不要主动透露家庭、收入、已有保障或隐藏顾虑。`;
    return { context, constraints };
  }

  function refreshGeneratedText(force) {
    if (generatedDirty && !force) return;
    const { context, constraints } = currentGeneratedText();
    setValue('f-context', context);
    setValue('f-constraints', constraints);
    document.getElementById('scenario-preview').innerHTML = `
      <div class="preview-title">生成预览</div>
      <div><strong>情境：</strong>${escapeHtml(context)}</div>
      <div><strong>约束：</strong>${escapeHtml(constraints)}</div>
    `;
  }

  function applyPreset(key) {
    const preset = presets[key];
    if (!preset) return;
    document.querySelectorAll('.preset-option').forEach(btn => {
      btn.classList.toggle('checked', btn.dataset.preset === key);
    });
    setValue('f-id', makeSlug(preset.idPrefix));
    setValue('f-name', preset.name);
    setValue('f-place', preset.place);
    setValue('f-relationship', preset.relationship);
    setValue('f-attitude', preset.attitude);
    setValue('f-time-limit', preset.timeLimit);
    setValue('f-boundary', preset.boundary);
    setTags(preset.tags);
    generatedDirty = false;
    refreshGeneratedText(true);
  }

  function validate(payload) {
    if (!/^[a-z0-9_]{1,32}$/.test(payload.id)) {
      showBanner('error', '场景编号必须是小写字母 / 数字 / 下划线，长度 ≤ 32');
      return false;
    }
    if (!payload.name || !payload.context || !payload.constraints) {
      showBanner('error', '请填写场景名称，并确保生成的情境与约束不为空');
      return false;
    }
    return true;
  }

  document.addEventListener('DOMContentLoaded', () => {
    const tagInput = document.getElementById('f-tag-input');
    tagInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ',' || e.key === '，') {
        e.preventDefault();
        addTagsFromInput(tagInput.value.trim());
        tagInput.value = '';
      } else if (e.key === 'Backspace' && tagInput.value === '' && tags.length) {
        tags.pop();
        renderTags();
      }
    });
    tagInput.addEventListener('blur', () => {
      addTagsFromInput(tagInput.value.trim());
      tagInput.value = '';
    });

    document.querySelectorAll('.preset-option').forEach(btn => {
      btn.addEventListener('click', () => applyPreset(btn.dataset.preset));
    });

    ['f-place', 'f-relationship', 'f-attitude', 'f-time-limit', 'f-boundary'].forEach(id => {
      document.getElementById(id).addEventListener('input', () => refreshGeneratedText(false));
      document.getElementById(id).addEventListener('change', () => refreshGeneratedText(false));
    });
    ['f-context', 'f-constraints'].forEach(id => {
      document.getElementById(id).addEventListener('input', () => {
        generatedDirty = true;
        document.getElementById('scenario-preview').innerHTML = `
          <div class="preview-title">生成预览</div>
          <div><strong>情境：</strong>${escapeHtml(document.getElementById('f-context').value.trim())}</div>
          <div><strong>约束：</strong>${escapeHtml(document.getElementById('f-constraints').value.trim())}</div>
        `;
      });
    });

    applyPreset('first_meet');

    document.getElementById('scenario-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      if (!document.getElementById('f-id').value.trim()) {
        setValue('f-id', makeSlug('custom_scene'));
      }
      refreshGeneratedText(false);

      const payload = {
        id: document.getElementById('f-id').value.trim(),
        name: document.getElementById('f-name').value.trim(),
        context: document.getElementById('f-context').value.trim(),
        constraints: document.getElementById('f-constraints').value.trim(),
        tags: tags.slice(),
      };

      if (!validate(payload)) return;

      const submitBtn = document.getElementById('submit-btn');
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<span class="loading"></span> 保存中...';

      try {
        const resp = await fetch('/api/scenarios', {
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
