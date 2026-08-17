// 飞书机器人事件回调 - 支持@机器人查询天气、充电提醒等
// 部署到 Vercel Serverless Functions

const fetch = require('node-fetch');

// ===== 配置 =====
const APP_ID = process.env.FEISHU_APP_ID || '';
const APP_SECRET = process.env.FEISHU_APP_SECRET || '';
const VERIFICATION_TOKEN = process.env.FEISHU_VERIFICATION_TOKEN || '';
const BOT_OPEN_ID = process.env.FEISHU_BOT_OPEN_ID || '';

// 成都经纬度
const CHENGDU_LAT = 30.5728;
const CHENGDU_LON = 104.0668;
const LOCATION_NAME = '成都市博雅城市广场A座';

// WMO天气代码映射
const WEATHER_CODE_MAP = {
  0: '晴', 1: '大部晴朗', 2: '局部多云', 3: '阴',
  45: '雾', 48: '雾凇',
  51: '小毛毛雨', 53: '毛毛雨', 55: '大毛毛雨',
  56: '冻毛毛雨', 57: '大冻毛毛雨',
  61: '小雨', 63: '中雨', 65: '大雨',
  66: '冻雨', 67: '大冻雨',
  71: '小雪', 73: '中雪', 75: '大雪', 77: '雪粒',
  80: '小阵雨', 81: '阵雨', 82: '大阵雨',
  85: '小阵雪', 86: '大阵雪',
  95: '雷暴', 96: '雷暴伴小冰雹', 99: '雷暴伴大冰雹',
};

// ===== 工具函数 =====
async function getTenantAccessToken() {
  const resp = await fetch('https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ app_id: APP_ID, app_secret: APP_SECRET }),
  });
  const data = await resp.json();
  if (data.code !== 0) {
    throw new Error('获取token失败: ' + JSON.stringify(data));
  }
  return data.tenant_access_token;
}

async function replyMessage(messageId, text) {
  const token = await getTenantAccessToken();
  const resp = await fetch(`https://open.feishu.cn/open-apis/im/v1/messages/${messageId}/reply`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify({
      msg_type: 'text',
      content: JSON.stringify({ text: text }),
    }),
  });
  const data = await resp.json();
  return data;
}

async function fetchWeather(dateOffset = 0) {
  const params = new URLSearchParams({
    latitude: CHENGDU_LAT,
    longitude: CHENGDU_LON,
    daily: 'weathercode,temperature_2m_max,temperature_2m_min,precipitation_probability_max,windspeed_10m_max,uv_index_max',
    current_weather: 'true',
    timezone: 'Asia/Shanghai',
    forecast_days: '2',
  });
  const resp = await fetch(`https://api.open-meteo.com/v1/forecast?${params}`);
  const data = await resp.json();
  const daily = data.daily;
  const current = data.current_weather;
  const idx = dateOffset;

  const weatherCode = daily.weathercode[idx];
  const weatherDesc = WEATHER_CODE_MAP[weatherCode] || `未知(${weatherCode})`;

  return {
    weather: weatherDesc,
    tempMax: daily.temperature_2m_max[idx],
    tempMin: daily.temperature_2m_min[idx],
    precipProb: daily.precipitation_probability_max[idx],
    windSpeed: daily.windspeed_10m_max[idx],
    uvIndex: daily.uv_index_max[idx],
    currentTemp: current.temperature,
    currentWeather: WEATHER_CODE_MAP[current.weathercode] || '未知',
    date: daily.time[idx],
  };
}

function formatWeather(w, isTomorrow = false) {
  const dateStr = w.date;
  const lines = [
    `${isTomorrow ? '明日' : '今日'}成都天气（${dateStr}）`,
    '',
    `天气：${w.weather}`,
    `气温：${w.tempMin}℃ ~ ${w.tempMax}℃${!isTomorrow ? `（当前 ${w.currentTemp}℃）` : ''}`,
    `降水概率：${w.precipProb}%`,
    `风力：${w.windSpeed} km/h`,
    `紫外线：${w.uvIndex}`,
    `地点：${LOCATION_NAME}`,
  ];

  const tips = [];
  if (w.precipProb >= 50) tips.push('🌧️ 可能下雨，记得带伞');
  if (w.tempMax >= 30) tips.push('🥵 气温较高，注意防暑');
  if (w.tempMin <= 10) tips.push('🧥 早晚较凉，注意添衣');
  if (w.uvIndex >= 6) tips.push('☀️ 紫外线较强，注意防晒');
  if (tips.length > 0) {
    lines.push('');
    lines.push('出行建议：' + tips.join('；'));
  }

  return lines.join('\n');
}

function isMentionedBot(event) {
  const mentions = event.message.mentions || [];
  if (mentions.length === 0) return false;
  if (BOT_OPEN_ID) {
    return mentions.some(m => m.id.open_id === BOT_OPEN_ID || m.id.user_id === BOT_OPEN_ID);
  }
  return mentions.length > 0;
}

function extractText(event) {
  try {
    const content = JSON.parse(event.message.content);
    let text = content.text || '';
    text = text.replace(/@_user_\d+/g, '').replace(/@_all/g, '').trim();
    return text;
  } catch (e) {
    return '';
  }
}

async function handleMessage(text) {
  const lowerText = text.toLowerCase();

  if (!text || lowerText.includes('帮助') || lowerText.includes('help') || lowerText === '?' || lowerText === '？') {
    return [
      '👋 我是天气小助手，你可以这样问我：',
      '',
      '• 「天气」- 查看今日成都天气',
      '• 「明天天气」- 查看明日成都天气',
      '• 「充电」- 获取充电提醒',
      '• 「帮助」- 查看此帮助',
      '',
      `地点：${LOCATION_NAME}`,
    ].join('\n');
  }

  if (lowerText.includes('充电')) {
    return [
      '🔋 充电提醒',
      '',
      '别忘了给手机、电脑、耳机充上电～',
      '🔌 电量满格，明天不慌',
      '☕ 好好休息，明天继续搬砖',
    ].join('\n');
  }

  if (lowerText.includes('明天') || lowerText.includes('明日')) {
    const w = await fetchWeather(1);
    return formatWeather(w, true);
  }

  if (lowerText.includes('天气') || lowerText.includes('气温') || lowerText.includes('下雨') || lowerText.includes('温度')) {
    const w = await fetchWeather(0);
    return formatWeather(w, false);
  }

  return [
    '🤔 没太理解你的意思，试试这些关键词：',
    '',
    '• 天气 - 今日天气',
    '• 明天天气 - 明日天气',
    '• 充电 - 充电提醒',
    '• 帮助 - 查看所有指令',
  ].join('\n');
}

// ===== Vercel Handler =====
module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  if (req.method === 'GET') {
    return res.status(200).json({ status: 'ok', service: 'feishu-weather-bot' });
  }

  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const body = req.body;

  if (body.type === 'url_verification') {
    console.log('URL验证:', body.challenge);
    return res.status(200).json({ challenge: body.challenge });
  }

  if (VERIFICATION_TOKEN && body.header && body.header.token !== VERIFICATION_TOKEN) {
    console.log('Token验证失败');
    return res.status(403).json({ error: 'Invalid token' });
  }

  const event = body.event;
  if (!event) {
    return res.status(200).json({ code: 0 });
  }

  if (body.header && body.header.event_type !== 'im.message.receive_v1') {
    return res.status(200).json({ code: 0 });
  }

  res.status(200).json({ code: 0 });

  (async () => {
    try {
      if (!isMentionedBot(event)) {
        console.log('未@机器人，忽略');
        return;
      }

      const text = extractText(event);
      console.log('收到消息:', text);

      const reply = await handleMessage(text);
      const messageId = event.message.message_id;
      const result = await replyMessage(messageId, reply);
      console.log('回复结果:', JSON.stringify(result));
    } catch (e) {
      console.error('处理消息失败:', e);
    }
  })();
};
