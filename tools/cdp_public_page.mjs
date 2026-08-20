const [url, waitArg] = process.argv.slice(2);

if (!url) {
  console.error("Usage: node tools/cdp_public_page.mjs URL [wait-ms]");
  process.exit(2);
}

const waitMs = Number(waitArg || 7000);
const tabs = await fetch("http://127.0.0.1:9333/json/list").then((response) => response.json());
const page = tabs.find((tab) => tab.type === "page");

if (!page) {
  throw new Error("No isolated public-research browser tab is available");
}

const socket = new WebSocket(page.webSocketDebuggerUrl);
const pending = new Map();
let requestId = 0;

socket.addEventListener("message", (event) => {
  const message = JSON.parse(event.data);
  if (!message.id || !pending.has(message.id)) return;
  const { resolve, reject } = pending.get(message.id);
  pending.delete(message.id);
  if (message.error) reject(new Error(JSON.stringify(message.error)));
  else resolve(message.result);
});

await new Promise((resolve, reject) => {
  socket.addEventListener("open", resolve, { once: true });
  socket.addEventListener("error", reject, { once: true });
});

function command(method, params = {}) {
  const id = ++requestId;
  socket.send(JSON.stringify({ id, method, params }));
  return new Promise((resolve, reject) => pending.set(id, { resolve, reject }));
}

await command("Page.enable");
await command("Runtime.enable");
await command("Page.navigate", { url });
await new Promise((resolve) => setTimeout(resolve, waitMs));

const result = await command("Runtime.evaluate", {
  expression: `JSON.stringify({
    title: document.title,
    url: location.href,
    text: document.documentElement.innerText,
    html: document.documentElement.outerHTML.slice(0, 5000),
    frames: [...document.querySelectorAll("iframe")].map(frame => frame.src),
    links: [...document.querySelectorAll("a")].map(a => ({text: a.innerText, href: a.href}))
  })`,
  returnByValue: true,
});

console.log(result.result.value);
socket.close();
