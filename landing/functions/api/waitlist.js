export async function onRequest(context) {
  const { request, env } = context;
  const url = new URL(request.url);

  if (request.method === 'OPTIONS') {
    return new Response(null, { status: 204, headers: corsHeaders() });
  }

  if (request.method === 'POST' && url.pathname === '/api/waitlist') {
    return handlePost(request, env);
  }
  if (request.method === 'GET' && url.pathname === '/api/waitlist') {
    return handleGetCount(env);
  }
  return new Response('Not found', { status: 404 });
}

async function handlePost(request, env) {
  const headers = { ...corsHeaders(), 'Content-Type': 'application/json' };

  let body;
  try {
    body = await request.json();
  } catch {
    return new Response(JSON.stringify({ error: 'Invalid JSON' }), { status: 400, headers });
  }

  const email = String(body.email || '').toLowerCase().trim();
  if (!isValidEmail(email)) {
    return new Response(JSON.stringify({ error: 'Please enter a valid email address.' }), { status: 400, headers });
  }

  const ip = request.headers.get('CF-Connecting-IP') || 'unknown';
  const rlKey = `rl:${ip}`;
  const rateHit = await env.WAITLIST.get(rlKey);
  if (rateHit) {
    return new Response(JSON.stringify({ error: 'Too many requests. Please try again later.' }), { status: 429, headers });
  }

  const emailKey = `email:${email}`;
  const existing = await env.WAITLIST.get(emailKey);
  if (existing) {
    const count = parseInt(await env.WAITLIST.get('count') || '0');
    return new Response(JSON.stringify({ success: true, count }), { status: 200, headers });
  }

  await env.WAITLIST.put(emailKey, JSON.stringify({ email, timestamp: new Date().toISOString() }));

  const currentCount = parseInt(await env.WAITLIST.get('count') || '0');
  const newCount = currentCount + 1;
  await env.WAITLIST.put('count', String(newCount));

  await env.WAITLIST.put(rlKey, '1', { expirationTtl: 3600 });

  return new Response(JSON.stringify({ success: true, count: newCount }), { status: 201, headers });
}

async function handleGetCount(env) {
  const count = parseInt(await env.WAITLIST.get('count') || '0');
  return new Response(JSON.stringify({ count }), {
    headers: {
      'Content-Type': 'application/json',
      'Cache-Control': 'public, max-age=60',
      ...corsHeaders(),
    },
  });
}

function isValidEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) && email.length <= 254;
}

function corsHeaders() {
  return {
    'Access-Control-Allow-Origin': 'https://irdoc.io',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
  };
}
