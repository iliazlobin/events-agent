import { router } from './routes.js'
import { Actor } from 'apify'
import { PuppeteerCrawler } from 'crawlee'
import dotenv from 'dotenv'

dotenv.config()

await Actor.init()

const proxyConfiguration = await Actor.createProxyConfiguration()
const chromeExecutablePath = process.env.CHROME_EXECUTABLE_PATH

// Read input to get maxItems
type Inputs = {
  urls?: string[]
  maxItems?: number
  lookForwardWindow?: number
  maxScrolls?: number
}
const input = await Actor.getInput<Inputs>()
const maxItems = input?.maxItems ?? 10

// TODO: Using proxies, bypassing Cloudflare browser checks
// https://docs.apify.com/academy/anti-scraping/mitigation/using-proxies

const crawler = new PuppeteerCrawler({
  proxyConfiguration,
  requestHandler: router,
  maxRequestsPerCrawl: maxItems + 10, // maxItems + buffer for search pages
  maxRequestsPerMinute: 10, // Optimized for cloud runs (was 3)
  maxRequestRetries: 3,
  requestHandlerTimeoutSecs: 120, // Increased from 60s for GraphQL reliability
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
        // https://pptr.dev/api/puppeteer.launchoptions
        launchOptions: {
          // headless: false,
          //   devtools: true,
          executablePath: chromeExecutablePath,
          // https://peter.sh/experiments/chromium-command-line-switches/
          args: ['--no-sandbox', '--disable-setuid-sandbox', '--auto-open-devtools-for-tabs'],
          // args: ['--no-sandbox', '--disable-setuid-sandbox'],
          protocolTimeout: 30000,
          //   userDataDir: './user-data',
        },
      }
    : {
        launchOptions: {
          protocolTimeout: 30000,
        },
      },
  //   https://crawlee.dev/docs/guides/avoid-blocking
  browserPoolOptions: {
    useFingerprints: true,
    fingerprintOptions: {
      fingerprintGeneratorOptions: {
        browsers: [{ name: 'chrome' }],
        devices: ['desktop'],
        operatingSystems: ['windows'],
      },
    },
  },
  autoscaledPoolOptions: {
    minConcurrency: 1, // Optimized from 2
    maxConcurrency: 5, // Reduced from 10 for better stability
  },
})

// start: search nyc
const defaultUrls = ['https://www.meetup.com/find/?location=us--ny--New%20York&source=EVENTS&sortField=DATETIME&eventType=all']
const urls = input?.urls ?? defaultUrls
const urlsWithLabel = urls.map(url => ({ url, label: 'search' }))

await crawler.run(urlsWithLabel)

// // DEBUG: test for event page
// await crawler.run([
//   {
//     url: 'https://www.meetup.com/aittg-nyc/events/305153410/?recId=4ad4af0f-6841-4392-a5a0-c7acc8a90563&recSource=ml-popular-events-nearby-offline&searchId=19fca5c2-5e3d-4d5a-b245-93459ad7bf7a&eventOrigin=find_page$inPerson',
//     label: 'event',
//   },
// ])
// DEBUG: test for event page
// await crawler.run([
//   {
//     url: 'https://www.meetup.com/dining-for-xennials/events/304959789/?recId=5a0e3104-2b50-4975-ac68-98156a80d5c4&recSource=ml-popular-events-nearby-offline&searchId=a94527b5-5cd7-4964-9185-f708418a5ab3&eventOrigin=find_page$inPerson',
//     label: 'event',
//   },
// ])
// DEBUG: test for event page with event series
// await crawler.run([
//   {
//     url: 'https://www.meetup.com/death-cafe-new-york-city/events/280542861/?recId=626fc1b1-9dd7-4284-a22b-9e9b4a68d6df&recSource=ml-popular-events-nearby-online&searchId=a2d35557-19a1-4060-9ce8-1a34c13bf409&eventOrigin=find_page$all',
//     label: 'event',
//   },
// ])
// DEBUG: test paid event page
// await crawler.run([
//   {
//     url: 'https://www.meetup.com/soccermates/events/305575909/?recId=9e50a9ae-e4c8-478a-9f04-87e8ba211423&recSource=ml-popular-events-nearby-offline&searchId=4fba75cf-c216-464f-b3df-8c2dbfd7ec29&eventOrigin=find_page$inPerson',
//     label: 'event',
//   },
// ])

await Actor.exit()
