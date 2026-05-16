const { app, BrowserWindow } = require('electron')
const { spawn } = require('child_process')
const path = require('path')
const net = require('net')
const fs = require('fs')

const isPacked = app.isPackaged
const RESOURCES_DIR = isPacked ? process.resourcesPath : path.join(__dirname, '..')
const FRONTEND_DIST = isPacked
  ? path.join(RESOURCES_DIR, 'frontend', 'dist')
  : path.join(__dirname, '..', 'frontend', 'dist')
const isWin = process.platform === 'win32'
const LOG_PATH = path.join(app.getPath('userData'), 'backend.log')
const STDERR_PATH = path.join(app.getPath('userData'), 'backend-stderr.log')

function log(...args) {
  try {
    fs.appendFileSync(LOG_PATH, args.map(String).join(' ') + '\n')
  } catch {}
}

function backendBinaryPath() {
  const name = isWin ? 'onboarding-api.exe' : 'onboarding-api'
  return path.join(process.resourcesPath, 'backend', name)
}

function findFreePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer()
    server.listen(0, '127.0.0.1', () => {
      const port = server.address().port
      server.close(() => resolve(port))
    })
    server.on('error', reject)
  })
}

function waitForBackend(port, maxRetries = 60, interval = 750) {
  return new Promise((resolve, reject) => {
    let tries = 0
    const check = () => {
      tries++
      const req = net.connect({ port, host: '127.0.0.1' })
      req.on('connect', () => { req.destroy(); resolve() })
      req.on('error', () => {
        req.destroy()
        if (tries >= maxRetries) reject(new Error(`Backend unreachable after ${tries} tries`))
        else setTimeout(check, interval)
      })
    }
    check()
  })
}

function showBackendError(win, msg, stderrContent, logPath, stderrPath) {
  const html = `<!DOCTYPE html>
<html><body style="font-family:-apple-system,system-ui,sans-serif;padding:48px;color:#1a1a2e;background:#f8f9fa">
<div style="max-width:640px;margin:0 auto">
<div style="width:48px;height:48px;border-radius:50%;background:#fee2e2;display:flex;align-items:center;justify-content:center;margin-bottom:16px">
<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#dc2626" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
</div>
<h2 style="margin:0 0 4px;font-size:20px;color:#111">Backend failed to start</h2>
<p style="margin:0 0 20px;color:#666;font-size:14px">${msg}</p>
<h3 style="font-size:14px;margin:0 0 8px;color:#374151">Stderr output</h3>
<pre style="background:#1e1e2e;color:#cdd6f4;padding:16px;border-radius:8px;font-size:12px;overflow:auto;max-height:200px">${stderrContent || '(no output)'}</pre>
<h3 style="font-size:14px;margin:16px 0 8px;color:#374151">Debugging</h3>
<pre style="background:#1e1e2e;color:#cdd6f4;padding:16px;border-radius:8px;font-size:12px;overflow:auto">
Electron log:  ${logPath}
Stderr file:   ${stderrPath}
Frontend dist: ${FRONTEND_DIST}
Dist exists:   ${fs.existsSync(FRONTEND_DIST)}
Binary:        ${isPacked ? backendBinaryPath() : 'N/A'}
Binary exists: ${isPacked ? fs.existsSync(backendBinaryPath()) : 'N/A'}
Binary perms:  ${isPacked ? (() => { try { return fs.statSync(backendBinaryPath()).mode.toString(8).slice(-3) } catch { return '?' } })() : 'N/A'}
</pre>
<p style="font-size:13px;color:#888;margin-top:16px">To debug from terminal:<br>
<code style="background:#e5e7eb;padding:2px 6px;border-radius:4px;font-size:12px">${isPacked ? backendBinaryPath() : 'N/A'}</code></p>
</div></body></html>`
  win.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(html)}`)
}

async function createWindow() {
  log('=== App started ===')
  log(`isPacked: ${isPacked}`)
  log(`Platform: ${process.platform} ${process.arch}`)
  log(`RESOURCES_DIR: ${RESOURCES_DIR}`)
  log(`FRONTEND_DIST: ${FRONTEND_DIST}`)
  log(`FRONTEND_DIST exists: ${fs.existsSync(FRONTEND_DIST)}`)

  const port = await findFreePort()
  log(`Free port: ${port}`)

  const win = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 960,
    minHeight: 600,
    show: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  })

  // Show loading screen immediately
  const loadingHtml = `<!DOCTYPE html>
<html><body style="font-family:-apple-system,system-ui,sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0;background:#f8f9fa">
<div style="text-align:center">
<div style="width:40px;height:40px;border:3px solid #e5e7eb;border-top-color:#6366f1;border-radius:50%;animation:spin 0.8s linear infinite;margin:0 auto 16px"></div>
<p style="color:#6b7280;font-size:14px">Starting backend… (up to 45s)</p>
<style>@keyframes spin{to{transform:rotate(360deg)}}</style>
</div></body></html>`
  win.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(loadingHtml)}`)
  win.show()

  // Use a clean minimal env — passing process.env can include vars
  // that break PyInstaller (DYLD_*, ELECTRON_*, etc.)
  const env = {
    PATH: '/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin:/opt/homebrew/bin',
    HOME: process.env.HOME || '',
    USER: process.env.USER || '',
    TMPDIR: process.env.TMPDIR || '/tmp',
    PORT: String(port),
    MODE: 'electron',
    FRONTEND_DIST_DIR: FRONTEND_DIST,
    UVICORN_WORKERS: '1',
  }

  // Pass through env vars the backend needs (only when non-empty).
  // The backend also loads .env from cwd (process.resourcesPath), so explicit
  // values here override that file — keep them empty to let .env take effect.
  if (isPacked) {
    env.FIREBASE_CREDENTIALS_PATH = 'service-account.json'
  } else {
    if (process.env.FIREBASE_CREDENTIALS_PATH) env.FIREBASE_CREDENTIALS_PATH = process.env.FIREBASE_CREDENTIALS_PATH
    if (process.env.GEMINI_API_KEY) env.GEMINI_API_KEY = process.env.GEMINI_API_KEY
  }

  let backendProcess
  let exitCode = null

  if (isPacked) {
    const binPath = backendBinaryPath()
    log(`Spawning binary: ${binPath}`)
    log(`Binary exists: ${fs.existsSync(binPath)}`)

    if (!fs.existsSync(binPath)) {
      showBackendError(win, 'Backend binary not found', '', LOG_PATH, STDERR_PATH)
      return
    }

    // Write stderr directly to a file (avoids pipe buffer issues)
    try { fs.unlinkSync(STDERR_PATH) } catch {}
    const stderrFd = fs.openSync(STDERR_PATH, 'a')

    backendProcess = spawn(binPath, [], { env, cwd: RESOURCES_DIR, stdio: ['ignore', 'ignore', stderrFd] })

    process.on('exit', () => { try { fs.closeSync(stderrFd) } catch {} })
  } else {
    const python = isWin ? 'python' : 'python3'
    log(`Dev mode: ${python} -m uvicorn app.main:app on port ${port}`)
    try { fs.unlinkSync(STDERR_PATH) } catch {}
    const stderrFd = fs.openSync(STDERR_PATH, 'a')

    backendProcess = spawn(python, [
      '-m', 'uvicorn', 'app.main:app',
      '--host', '127.0.0.1', '--port', String(port),
      '--workers', '1', '--loop', 'asyncio',
    ], {
      env,
      stdio: ['ignore', 'ignore', stderrFd],
      cwd: RESOURCES_DIR,
    })

    process.on('exit', () => { try { fs.closeSync(stderrFd) } catch {} })
  }

  backendProcess.on('error', (err) => {
    log(`spawn error: ${err.message}`)
    showBackendError(win, err.message, '', LOG_PATH, STDERR_PATH)
  })

  backendProcess.on('exit', (code, signal) => {
    exitCode = code
    log(`backend exit: code=${code} signal=${signal}`)
    try {
      const stderrContent = fs.readFileSync(STDERR_PATH, 'utf8')
      log(`stderr:\n${stderrContent}`)
    } catch {}
  })

  let started = false
  try {
    await waitForBackend(port, 60, 750) // ~45s total
    started = true
    log('Backend is ready')
  } catch (err) {
    log(`Backend failed: ${err.message}`)
  }

  if (started) {
    win.loadURL(`http://127.0.0.1:${port}`)
  } else {
    let stderrContent = ''
    try { stderrContent = fs.readFileSync(STDERR_PATH, 'utf8').substring(0, 5000) } catch {}

    const exitMsg = exitCode !== null ? `\nProcess exited with code ${exitCode}` : ''

    showBackendError(win,
      `Backend did not respond within 45 seconds.${exitMsg}`,
      stderrContent || '(no output)',
      LOG_PATH,
      STDERR_PATH
    )
  }

  win.on('closed', () => {
    if (backendProcess && !backendProcess.killed) backendProcess.kill()
  })
}

app.whenReady().then(createWindow)

app.on('window-all-closed', () => app.quit())
