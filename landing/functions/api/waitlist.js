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

  // Rate limit by IP (1 submission per IP per hour)
  const ip = request.headers.get('CF-Connecting-IP') || 'unknown';
  const rlKey = `rl:${ip}`;
  if (await env.WAITLIST.get(rlKey)) {
    return new Response(JSON.stringify({ error: 'Too many requests. Please try again later.' }), { status: 429, headers });
  }

  // Add to Brevo list
  const brevo = await addToBrevo(email, env);

  if (brevo.duplicate) {
    // Already signed up — return current count without incrementing
    const count = parseInt(await env.WAITLIST.get('count') || '0');
    return new Response(JSON.stringify({ success: true, count }), { status: 200, headers });
  }

  if (!brevo.ok) {
    return new Response(JSON.stringify({ error: brevo.error || 'Failed to join. Please try again.' }), { status: 500, headers });
  }

  // New signup — increment counter and set rate limit
  const current = parseInt(await env.WAITLIST.get('count') || '0');
  const newCount = current + 1;
  await Promise.all([
    env.WAITLIST.put('count', String(newCount)),
    env.WAITLIST.put(rlKey, '1', { expirationTtl: 3600 }),
  ]);

  return new Response(JSON.stringify({ success: true, count: newCount }), { status: 201, headers });
}

async function addToBrevo(email, env) {
  const apiKey = env.BREVO_API_KEY;
  const listId = parseInt(env.BREVO_LIST_ID || '0');

  if (!apiKey || !listId) {
    return { ok: false, error: 'Waitlist service not configured.' };
  }

  let res;
  try {
    res = await fetch('https://api.brevo.com/v3/contacts', {
      method: 'POST',
      headers: {
        'api-key': apiKey,
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify({ email, listIds: [listId], updateEnabled: false }),
    });
  } catch {
    return { ok: false, error: 'Network error reaching email service.' };
  }

  if (res.status === 201) return { ok: true };

  if (res.status === 400) {
    let data;
    try { data = await res.json(); } catch {}
    if (data?.code === 'duplicate_parameter') return { ok: true, duplicate: true };
    return { ok: false, error: 'Invalid request to email service.' };
  }

  return { ok: false, error: 'Email service error. Please try again.' };
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
