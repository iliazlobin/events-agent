import { BrowserName, DeviceCategory } from '@crawlee/browser-pool'

import { router } from './routes.js'
import { Actor } from 'apify'
import { PuppeteerCrawler } from 'crawlee'
import dotenv from 'dotenv'

dotenv.config()

await Actor.init()

interface Input {
  region?: string
  maxItems?: number
  lookForwardWindow?: number
}

const input = await Actor.getInput<Input>()
const region = input?.region ?? 'sf'
const maxItems = input?.maxItems ?? 10

const proxyConfiguration = await Actor.createProxyConfiguration()
const chromeExecutablePath = process.env.CHROME_EXECUTABLE_PATH

const crawler = new PuppeteerCrawler({
  proxyConfiguration,
  requestHandler: router,
  // listing page (1) + detail pages (maxItems) + final event pages (maxItems) + buffer (10)
  maxRequestsPerCrawl: 1 + maxItems * 2 + 10,
  maxRequestsPerMinute: 15, // Increased from 3 to allow collecting all events within timeout
  maxRequestRetries: 3,
  requestHandlerTimeoutSecs: 180, // 3 minutes to allow for scrolling but prevent hangs
  useSessionPool: true,
  sessionPoolOptions: {
    maxPoolSize: 5,
    sessionOptions: {
      maxUsageCount: 10,
      maxErrorScore: 5,
    },
  },
  retryOnBlocked: false,
  launchContext: chromeExecutablePath
    ? {
        useChrome: true,
        launchOptions: {
          executablePath: chromeExecutablePath,
          args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
            '--disable-blink-features=AutomationControlled',
          ],
          protocolTimeout: 30000,
        },
      }
    : {
        launchOptions: {
          args: [
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
            '--disable-blink-features=AutomationControlled',
          ],
          protocolTimeout: 30000,
        },
      },
  // Disable request blocking to allow gary.to redirects
  preNavigationHooks: [
    async ({ page, request }) => {
      // Disable various blocking mechanisms
      await page.setBypassCSP(true)
      await page.setRequestInterception(false)

      // If this is a gary.to link, navigate manually
      if (request.url.includes('gary.to')) {
        try {
          await page.goto(request.url, {
            waitUntil: 'networkidle2',
            timeout: 30000,
          })
        } catch (err) {
          // Log but don't throw - let Crawlee handle retries
          console.log(`Manual navigation for ${request.url}: ${err}`)
        }
      }
    },
  ],
  browserPoolOptions: {
    useFingerprints: true,
    fingerprintOptions: {
      fingerprintGeneratorOptions: {
        browsers: [BrowserName.chrome, BrowserName.firefox],
        devices: [DeviceCategory.desktop],
        locales: ['en-US'],
      },
    },
  },
  autoscaledPoolOptions: {
    minConcurrency: 1,
    maxConcurrency: 5,
  },
})

const startUrl = `https://www.garysguide.com/events?region=${region}`
await crawler.run([startUrl])

await Actor.exit()
