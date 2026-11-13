const VERSION = "2026-11-13-license-v7";
const GITHUB_API = "https://api.github.com/repos/vpn-nusantara/Izinkan/contents/allowlist.txt?ref=main";

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
      "x-content-type-options": "nosniff"
    }
  });
}

function normalizeIP(value) {
  if (typeof value !== "string") return null;
  const ip = value.trim();
  const v4 = ip.split(".");
  if (v4.length === 4) {
    if (!v4.every(part => /^(0|[1-9][0-9]{0,2})$/.test(part) && Number(part) <= 255)) return null;
    return "4:" + v4.map(part => String(Number(part))).join(".");
  }
  if (!ip.includes(":") || ip.includes("%")) return null;
  let input = ip.toLowerCase();
  if (input.includes(".")) {
    const lastColon = input.lastIndexOf(":");
    if (lastColon < 0) return null;
    const embedded = normalizeIP(input.slice(lastColon + 1));
    if (!embedded || !embedded.startsWith("4:")) return null;
    const o = embedded.slice(2).split(".").map(Number);
    input = input.slice(0, lastColon + 1) + ((o[0] << 8) | o[1]).toString(16) + ":" + ((o[2] << 8) | o[3]).toString(16);
  }
  if ((input.match(/::/g) || []).length > 1) return null;
  const compressed = input.includes("::");
  const halves = input.split("::");
  const left = halves[0] ? halves[0].split(":") : [];
  const right = compressed && halves[1] ? halves[1].split(":") : [];
  const groups = [...left, ...right];
  if (groups.some(g => !/^[0-9a-f]{1,4}$/.test(g))) return null;
  if (compressed ? groups.length >= 8 : groups.length !== 8) return null;
  const full = [...left, ...Array(compressed ? 8 - groups.length : 0).fill("0"), ...right];
  if (full.length !== 8) return null;
  const words = full.map(g => parseInt(g, 16));
  // IPv4-mapped IPv6 (::ffff:a.b.c.d) harus cocok dengan entri IPv4.
  if (words.slice(0, 5).every(n => n === 0) && words[5] === 0xffff) {
    const a = words[6];
    const b = words[7];
    return "4:" + [(a >> 8) & 255, a & 255, (b >> 8) & 255, b & 255].join(".");
  }
  return "6:" + words.map(n => n.toString(16)).join(":");
}

function validDate(value) {
  if (typeof value !== "string" || !/^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(value)) return false;
  const date = new Date(value + "T00:00:00.000Z");
  return Number.isFinite(date.getTime()) && date.toISOString().slice(0, 10) === value;
}

function decodeContent(value) {
  const binary = atob(value.replace(/[\r\n\t ]/g, ""));
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i);
  }
  return new TextDecoder("utf-8", { fatal: true }).decode(bytes);
}

async function readAllowlist(token) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 12000);

  try {
    const response = await fetch(GITHUB_API, {
      method: "GET",
      headers: {
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
      },
      signal: controller.signal
    });

    if (!response.ok) {
      throw new Error("GitHub HTTP " + response.status);
    }

    const file = await response.json();
    if (file.type !== "file" || file.encoding !== "base64" || typeof file.content !== "string") {
      throw new Error("Invalid GitHub file response");
    }

    return decodeContent(file.content);
  } finally {
    clearTimeout(timeoutId);
  }
}

function findExpiry(contents, clientIP, today) {
  const normalizedClientIP = normalizeIP(clientIP);
  if (!normalizedClientIP) return null;
  let result = null;
  const lines = contents.split(/\r?\n/);

  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (line.length === 0 || line.startsWith("#")) continue;

    const fields = line.split("|");
    if (fields.length !== 2) continue;

    const ip = fields[0].trim();
    const expiry = fields[1].trim();

    if (normalizeIP(ip) !== normalizedClientIP || !validDate(expiry)) continue;
    if (expiry >= today && (result === null || expiry > result)) {
      result = expiry;
    }
  }

  return result;
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (request.method !== "GET") {
      return json({ ok: false, status: "METHOD_NOT_ALLOWED", version: VERSION }, 405);
    }

    if (url.pathname === "/health" || url.pathname === "/health/") {
      return json({ ok: true, status: "WORKER_ONLINE", version: VERSION });
    }

    if (url.pathname !== "/" && url.pathname !== "/check" && url.pathname !== "/check/") {
      return json({ ok: false, status: "NOT_FOUND", version: VERSION }, 404);
    }

    // Gunakan header tepercaya yang dipasang Cloudflare; jangan gunakan X-Forwarded-For
    // karena header tersebut dapat dikirim/dipalsukan oleh pemanggil.
    const clientIP = (request.headers.get("CF-Connecting-IP") || "").trim();
    const normalizedClientIP = normalizeIP(clientIP);
    if (!normalizedClientIP) {
      return json({
        ok: false,
        status: "INVALID_CLIENT_IP",
        received_ip: clientIP || null,
        cf_connecting_ip_present: clientIP.length > 0,
        version: VERSION
      }, 400);
    }

    if (!env || typeof env.GITHUB_TOKEN !== "string" || env.GITHUB_TOKEN.trim() === "") {
      return json({ ok: false, status: "SERVER_CONFIGURATION_ERROR", version: VERSION }, 503);
    }

    let contents;
    try {
      contents = await readAllowlist(env.GITHUB_TOKEN.trim());
    } catch (error) {
      return json({
        ok: false,
        status: "ALLOWLIST_UNAVAILABLE",
        detail: error && error.message ? error.message : "GitHub request failed",
        version: VERSION
      }, 503);
    }

    const today = new Date().toISOString().slice(0, 10);
    const expires = findExpiry(contents, clientIP, today);

    if (expires === null) {
      return json({
        ok: false,
        status: "DENIED",
        ip: clientIP,
        date_utc: today,
        version: VERSION
      }, 403);
    }

    return json({
      ok: true,
      status: "ALLOWED",
      ip: clientIP,
      expires: expires,
      date_utc: today,
      version: VERSION
    });
  }
};
