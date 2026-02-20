import { Actor, Dataset } from 'apify'
import { createPuppeteerRouter } from 'crawlee'

export const router = createPuppeteerRouter()

interface Input {
  maxItems?: number
  lookForwardWindow?: number
}

// Helper function to extract provider from URL
function extractProvider(url: string): string | null {
  try {
    const urlObj = new URL(url)
    const hostname = urlObj.hostname.toLowerCase()

    // Map hostnames to provider names
    const providerMap: Record<string, string> = {
      'luma.com': 'luma',
      'lu.ma': 'luma',
      'meetup.com': 'meetup',
      'eventbrite.com': 'eventbrite',
      'eventbrite.co.uk': 'eventbrite',
      'aicamp.ai': 'aicamp',
      'startupgrind.com': 'startupgrind',
      'partiful.com': 'partiful',
      'hopin.com': 'hopin',
    }

    // Check for exact match
    if (providerMap[hostname]) {
      return providerMap[hostname]
    }

    // Check for subdomain match (e.g., www.meetup.com)
    for (const [domain, provider] of Object.entries(providerMap)) {
      if (hostname.endsWith(domain)) {
        return provider
      }
    }

    // Return hostname if no match (fallback)
    return hostname
  } catch (err) {
    return null
  }
}

// Helper function to resolve gary.to redirects using HTTP fetch
async function resolveGaryToRedirect(garyToUrl: string): Promise<string> {
  try {
    // Use fetch with redirect:follow to get the final URL
    const response = await fetch(garyToUrl, {
      redirect: 'follow',
      headers: {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
      },
    })
    return response.url // This is the final redirected URL
  } catch (err) {
    console.error(`Error resolving ${garyToUrl}:`, err)
    return garyToUrl // Return original if resolution fails
  }
}

// Handler for listing page - extract event detail page links
router.addDefaultHandler(async ({ page, log, crawler }) => {
  const pageUrl = page.url() ?? ''
  log.info(`Processing Gary's Guide listing: ${pageUrl}`)

  // Wait for page to load completely
  await page.waitForSelector('a[href*="/events/"]', { timeout: 10000 })
  await new Promise(resolve => setTimeout(resolve, 1000))

  const input = await Actor.getInput<Input>()
  const maxItems = input?.maxItems ?? 10
  const lookForwardWindow = input?.lookForwardWindow ?? 14

  log.info(`Settings: maxItems=${maxItems}, lookForwardWindow=${lookForwardWindow} days`)

  // Scroll to load all events (Gary's Guide uses infinite scroll)
  log.info('Scrolling page to load events...')
  let previousHeight = 0
  let scrollAttempts = 0
  const maxScrollAttempts = 15 // Increased to ensure we get enough events

  while (scrollAttempts < maxScrollAttempts) {
    // Scroll down
    await page.evaluate(() => window.scrollBy(0, window.innerHeight * 2))
    await new Promise(resolve => setTimeout(resolve, 800))

    const currentHeight = await page.evaluate(() => document.body.scrollHeight)

    // Stop if no new content loaded after 2 consecutive attempts
    if (currentHeight === previousHeight) {
      scrollAttempts++
      if (scrollAttempts >= 2 && currentHeight === previousHeight) {
        log.info(`Stopping scroll: no new content loaded`)
        break
      }
    } else {
      scrollAttempts = 0 // Reset if content is loading
    }

    log.info(`Scroll attempt ${scrollAttempts}: height ${currentHeight}`)
    previousHeight = currentHeight
  }

  await new Promise(resolve => setTimeout(resolve, 2000))

  // Calculate cutoff date for filtering
  const cutoffDate = new Date()
  cutoffDate.setDate(cutoffDate.getDate() + lookForwardWindow)

  log.info(`Looking for events up to: ${cutoffDate.toISOString()}`)

  // Extract event detail page links with basic info from listing
  const eventDetailLinks = await page.evaluate(() => {
    const links: Array<{ url: string; date: string; title: string }> = []
    // Match links like /events/bbyt3ua or full URLs
    const anchors = document.querySelectorAll('a[href*="/events/"]')

    anchors.forEach((anchor) => {
      const href = (anchor as HTMLAnchorElement).href
      // Only include detail pages (with event ID), not the main /events page
      if (href && href.match(/\/events\/[a-z0-9]+/i)) {
        // Extract basic info from listing
        const eventCard = anchor.closest('[class*="event"], [class*="card"], li, div')
        let dateStr = ''
        let title = anchor.textContent?.trim() || ''

        if (eventCard) {
          // Look for time elements or date-related classes
          const timeEl = eventCard.querySelector('time')
          const dateEl = eventCard.querySelector('[class*="date"], [class*="time"]')
          dateStr = timeEl?.textContent?.trim() || dateEl?.textContent?.trim() || ''

          // Try to get title from event card if anchor text is not descriptive
          const titleEl = eventCard.querySelector('[class*="title"], h3, h4')
          if (titleEl && titleEl.textContent) {
            title = titleEl.textContent.trim()
          }
        }

        // Only add if not duplicate
        if (!links.find(l => l.url === href)) {
          links.push({ url: href, date: dateStr, title })
        }
      }
    })

    return links
  })

  log.info(`Found ${eventDetailLinks.length} event detail pages`)

  // Enqueue event detail pages (limit by maxItems)
  const linksToProcess = eventDetailLinks.slice(0, maxItems)
  for (const eventInfo of linksToProcess) {
    await crawler.addRequests([
      {
        url: eventInfo.url,
        label: 'event-detail-page',
        userData: {
          detailUrl: eventInfo.url,
          dateStr: eventInfo.date,
          title: eventInfo.title,
        },
      },
    ])
  }

  log.info(`Enqueued ${linksToProcess.length} event detail pages for processing`)
})

// Handler for event detail pages on garysguide.com - AGGREGATOR MODE
router.addHandler('event-detail-page', async ({ page, log, request }) => {
  const detailUrl = request.userData.detailUrl as string
  const listingTitle = request.userData.title as string
  const listingDate = request.userData.dateStr as string

  log.info(`Processing Gary's Guide detail page: ${detailUrl}`)

  await new Promise(resolve => setTimeout(resolve, 1000))

  // Extract metadata from Gary's Guide detail page (without visiting provider)
  const garyMetadata = await page.evaluate(() => {
    // Extract title from detail page
    const titleEl = document.querySelector('h1') || document.querySelector('[class*="title"]')
    const title = titleEl?.textContent?.trim() || ''

    // Extract date/time info
    const dateEl = document.querySelector('time') || document.querySelector('[class*="date"], [class*="time"]')
    const dateStr = dateEl?.textContent?.trim() || dateEl?.getAttribute('datetime') || ''

    // Extract location from detail page
    const locationEl = document.querySelector('[class*="location"], [class*="venue"], [class*="address"]')
    const location = locationEl?.textContent?.trim() || ''

    // Extract description snippet
    const descEl = document.querySelector('[class*="description"], [class*="summary"], p')
    const description = descEl?.textContent?.trim().substring(0, 500) || ''

    // Extract image
    const imgEl = document.querySelector('img[src*="event"], img[class*="cover"], meta[property="og:image"]')
    const imageUrl = imgEl
      ? (imgEl as HTMLImageElement).src || imgEl.getAttribute('content') || ''
      : ''

    // Extract gary.to registration link
    const registerLink = Array.from(document.querySelectorAll('a[href*="gary.to"]'))
      .find(a => a.textContent?.includes('Register') || a.textContent?.includes('RSVP'))

    const anyGaryToLink = document.querySelector('a[href*="gary.to"]')

    const garyToUrl = (registerLink as HTMLAnchorElement)?.href ||
                      (anyGaryToLink as HTMLAnchorElement)?.href || ''

    return {
      title,
      dateStr,
      location,
      description,
      imageUrl,
      garyToUrl,
    }
  })

  if (!garyMetadata.garyToUrl) {
    log.warning(`No gary.to link found on ${detailUrl}, skipping`)
    return
  }

  log.info(`Found registration link: ${garyMetadata.garyToUrl}`)

  // Resolve gary.to redirect to get final event URL (without visiting the page)
  const finalUrl = await resolveGaryToRedirect(garyMetadata.garyToUrl)
  log.info(`Final destination: ${finalUrl}`)

  // Detect provider from final URL
  const provider = extractProvider(finalUrl)
  log.info(`Detected provider: ${provider}`)

  // Extract event ID from Gary's Guide URL
  const eventIdMatch = detailUrl.match(/\/events\/([a-z0-9]+)/i)
  const eventId = eventIdMatch ? eventIdMatch[1] : detailUrl.split('/').pop() || 'unknown'

  // Save aggregator metadata to dataset (NO SCRAPING OF PROVIDER PAGE)
  const aggregatorData = {
    // Use title from detail page, fallback to listing title
    title: garyMetadata.title || listingTitle || 'Unknown Event',

    // URLs
    url: finalUrl, // Final destination URL (where user will end up)
    shortUrl: garyMetadata.garyToUrl, // gary.to short link
    aggregatorDetailUrl: detailUrl, // Gary's Guide detail page

    // Metadata from Gary's Guide
    dateStr: garyMetadata.dateStr || listingDate,
    location: garyMetadata.location,
    description: garyMetadata.description,
    imageUrl: garyMetadata.imageUrl,

    // Aggregator tracking
    source: 'garysguide', // This is from Gary's Guide
    originalProvider: provider, // But the event is on luma/meetup/etc.
    aggregatedFrom: 'garysguide',

    // Event ID
    eventId: eventId,

    // Metadata
    scrapedAt: new Date().toISOString(),
    isAggregated: true, // Flag indicating this is aggregated metadata only
  }

  await Dataset.pushData(aggregatorData)

  log.info(
    `Saved aggregated event: ${aggregatorData.title} (provider: ${provider}, id: ${eventId})`
  )
})
