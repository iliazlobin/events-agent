import { BrowserName, DeviceCategory } from '@crawlee/browser-pool'

import { router } from './routes.js'
import { Actor } from 'apify'
import { PuppeteerCrawler } from 'crawlee'
import dotenv from 'dotenv'

dotenv.config()

await Actor.init()

const input = await Actor.getInput<{ urls?: string[]; maxItems?: number }>()
const maxItems = input?.maxItems ?? 100

const proxyConfiguration = await Actor.createProxyConfiguration()
const chromeExecutablePath = process.env.CHROME_EXECUTABLE_PATH

const crawler = new PuppeteerCrawler({
  proxyConfiguration,
  requestHandler: router,
  maxRequestsPerCrawl: maxItems + 10, // maxItems + buffer for pagination
  maxRequestsPerMinute: 10, // Optimized for cloud runs (was 3)
  maxRequestRetries: 3,
  requestHandlerTimeoutSecs: 300, // 5 minutes to allow for extensive scrolling
  useSessionPool: true,
  sessionPoolOptions: {
    maxPoolSize: 5, // Reduced from 10 for better resource usage
    // https://docs.apify.com/academy/anti-scraping/techniques/rate-limiting
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
          // headless: false,
          executablePath: chromeExecutablePath,
          args: ['--no-sandbox', '--disable-setuid-sandbox', '--auto-open-devtools-for-tabs'],
          protocolTimeout: 30000,
        },
      }
    : { launchOptions: { protocolTimeout: 30000 } },
  // https://crawlee.dev/docs/guides/avoid-blocking
  browserPoolOptions: {
    useFingerprints: true,
    fingerprintOptions: {
      fingerprintGeneratorOptions: {
        browsers: [BrowserName.chrome, BrowserName.firefox],
        devices: [DeviceCategory.mobile],
        locales: ['en-US'],
      },
    },
  },
  autoscaledPoolOptions: {
    minConcurrency: 1, // Optimized from 2
    maxConcurrency: 5, // Reduced from 10 for better stability
  },
})

const defaultUrls = ['https://lu.ma/nyc']
const urls = input?.urls ?? defaultUrls

await crawler.run(urls)

// DEBUG: parsing paid event
// await crawler.run([{ url: 'https://lu.ma/DinnerTableHoleInTheWall', label: 'event' }])
// await crawler.run([{ url: 'https://lu.ma/qjzw9pmq', label: 'event' }])
// await crawler.run([{ url: 'https://lu.ma/0blj3br4', label: 'event' }])
// await crawler.run([{ url: 'https://lu.ma/sg679vkw', label: 'event' }])

await Actor.exit()
