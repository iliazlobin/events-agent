import Apify, { Actor, LoggerJson, log } from 'apify'
import { createPuppeteerRouter } from 'crawlee'

export const router = createPuppeteerRouter()

type Inputs = {
  lookForwardWindow?: number
  maxItems?: number
  maxScrolls?: number
}

router.addDefaultHandler(async ({ page, log, crawler }) => {
  const pageUrl = page.url() ?? ''

  log.info(`processing default page: ${pageUrl}`)
  await new Promise(resolve => setTimeout(resolve, 1000))
  await page.setDefaultNavigationTimeout(30000)

  const input = await Actor.getInput<Inputs>()
  const lookForwardWindow = input?.lookForwardWindow ?? 7
  const maxItems = input?.maxItems ?? 100
  const maxScrolls = input?.maxScrolls ?? 10
  log.debug(`lookForwardWindow: ${lookForwardWindow}`)
  log.debug(`maxItems: ${maxItems}`)
  log.debug(`maxScrolls: ${maxScrolls}`)

  const targetDate = new Date()
  targetDate.setDate(targetDate.getDate() + (lookForwardWindow ?? 0))

  const scrollPageToBottom = async () => {
    await page.evaluate(() => {
      window.scrollTo(0, document.body.scrollHeight)
    })
    await new Promise(resolve => setTimeout(resolve, 3000))
  }

  for (let i = 1; ; i++) {
    log.debug(`scrolling page to bottom: ${i}/${maxScrolls}`)
    await scrollPageToBottom()

    const timelineItems: { date: string; weekday: string }[] = await page.$$eval('div.timeline-section', timelineEls => {
      const timelineItems = []
      for (const timelineEl of timelineEls) {
        // process timeline
        const date = timelineEl.querySelector('div.date')?.textContent ?? ''
        const weekday = timelineEl.querySelector('div.weekday')?.textContent ?? ''
        timelineItems.push({ date, weekday })
      }
      return timelineItems
    })

    const lastTimelineItem = timelineItems.reverse().find(item => item.date && item.weekday)

    if (!lastTimelineItem) {
      log.warning('No timeline items found')
      break
    }

    const lastTimelineDate = extractDateWithYear(lastTimelineItem.date)
    if (lastTimelineDate >= targetDate) {
      log.info(`Found target date: ${lastTimelineDate} >= ${targetDate}`)
      break
    }

    if (i >= maxScrolls) {
      log.warning(`Reached max scrolls: ${i}/${maxScrolls}, last timeline date: ${lastTimelineDate}/${targetDate}`)
      break
    }
  }

  const timelineItems = await page.$$eval('div.timeline-section', timelineEls => {
    const timelineItems: any[] = []
    for (const timelineEl of timelineEls) {
      const date = timelineEl.querySelector('div.date')?.textContent ?? ''
      const weekday = timelineEl.querySelector('div.weekday')?.textContent ?? ''

      const cardItems: any[] = []
      const cardEls = timelineEl.querySelectorAll('div.content-card')
      for (const el of cardEls) {
        const urlPath = el.querySelector('a.event-link')?.getAttribute('href') ?? ''
        const url = new URL(urlPath, window.location.href).href
        const title = el.querySelector('h3')?.textContent ?? ''
        const author = el.querySelector('div.text-ellipses.nowrap')?.textContent?.replace('By ', '') ?? ''
        const address = el.querySelectorAll('div.flex-start.text-tertiary-alpha')?.[1]?.textContent ?? ''
        const time = el.querySelector('div.text-ellipses')?.textContent ?? ''
        const cover = el.querySelector('img')?.getAttribute('src') ?? ''

        if (!urlPath || !title || !author || !address || !time || !cover) {
          // log.warning(`Skipping card with missing data: ${JSON.stringify({ url: urlPath, title, author: host, address, time, cover })}`)
          continue
        }

        cardItems.push({
          url,
          date,
          weekday,
          title,
          author,
          address, // e.g. 'New York, New York'
          time, // e.g. '5:30 PM'
          cover,
        })
      }
      timelineItems.push({ date, weekday, cardItems })
    }

    return timelineItems
  })

  const totalItems = timelineItems.reduce((acc, item) => acc + item.cardItems.length, 0)
  log.info(`processing ${timelineItems.length} timeline items with a total of ${totalItems} card items`)

  let enqueuedCount = 0
  for (const timelineItem of timelineItems) {
    log.info(`processing ${timelineItem.date} (${timelineItem.weekday}) timeline item that contains ${timelineItem.cardItems.length} card items`)
    for (const item of timelineItem.cardItems) {
      log.info(`enqueueing item url: ${item.url}`)

      const dateText = toDateText(extractDateWithYear(timelineItem.date))

      const data = {
        url: item.url,
        dateText,
        weekday: timelineItem.weekday,
        title: item.title,
        host: item.author,
        address: item.address,
        time: item.time,
        cover: item.cover,
      }

      try {
        await crawler.addRequests([{
          url: item.url,
          label: 'event',
          userData: data,
        }])
        enqueuedCount++
      } catch (error) {
        log.error(`Failed to enqueue ${item.url}: ${error}`)
      }
    }
  }
  log.info(`Total enqueued: ${enqueuedCount} event pages`)
})

router.addHandler('event', async ({ request, page, log }) => {
  const pageUrl = request.loadedUrl ?? ''
  const pageTitle = await page.title()
  const data = request.userData

  log.info(`processing event page (${pageUrl}): ${pageTitle}`)
  await new Promise(resolve => setTimeout(resolve, 1000))
  await page.setDefaultNavigationTimeout(30000)

  const { dateContent, timeContent } = await page.$$eval('div.icon-row.flex-center', els => {
    let dateContent = ''
    let timeContent = ''
    for (let i = 0; i < els.length; i++) {
      const el = els[i]
      dateContent = el.querySelector('div.title')?.textContent?.trim() ?? ''
      timeContent = el.querySelector('div.desc')?.textContent?.trim() ?? ''
      const dateParts = dateContent.split(', ')
      const weekday = dateParts[0]
      if (['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'].includes(weekday)) {
        break
      }
    }
    return { dateContent, timeContent }
  })
  if (!dateContent || !timeContent) {
    log.warning(`skipping event with missing date or time: ${JSON.stringify({ dateContent, timeContent })}`)
    return
  }
  const { dateStart, dateEnd } = parseDateTimeRange(dateContent, timeContent)
  const dateStartText = toDateTimeText(dateStart)
  const dateEndText = toDateTimeText(dateEnd)

  const title = await page.$eval('h1.title', el => el.textContent?.trim())
  const group = await page.$$eval('div.fs-xxs.text-tinted.reduced-line-height', els => {
    let anchor
    for (let i = 0; i < els.length; i++) {
      const el = els[i]
      if (el.textContent?.startsWith('Presented')) {
        anchor = el
        break
      }
    }
    if (!anchor) {
      return ''
    }
    return anchor.parentElement?.querySelector('a.title')?.querySelector('div.text-ellipses')?.textContent?.trim() ?? ''
  })

  const hosts = await page.$$eval('div.title-label.text-tinted.fs-sm', els => {
    let anchor
    for (let i = 0; i < els.length; i++) {
      const el = els[i]
      if (el.textContent?.startsWith('Hosted')) {
        anchor = el
        break
      }
    }
    if (!anchor) {
      return []
    }
    const hosts: string[] = []
    const hostEls = anchor.parentElement?.parentElement?.querySelectorAll('a.host-row') ?? []
    for (const el of hostEls) {
      const host = el.querySelector('div.fw-medium.text-ellipses')?.textContent?.trim()
      if (host) {
        hosts.push(host)
      }
    }
    return hosts
  })

  // const { addressContent, locationContent } = await page.$$eval('div.flex-1.min-width-0', els => {
  const { addressContent, locationContent } = await page.$$eval('div.icon-row.flex-center', els => {
    let addressEl
    for (let i = 0; i < els.length; i++) {
      const el = els[i]
      const dateContent = el.querySelector('div.title')?.textContent?.trim() ?? ''
      const dateParts = dateContent.split(', ')
      const weekday = dateParts[0]
      if (['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'].includes(weekday)) {
        addressEl = els[i + 1]
        break
      }
    }
    if (!addressEl) {
      return {}
    }
    const addressContent = addressEl.querySelector('div.title')?.textContent?.trim()
    const locationContent = addressEl.querySelector('div.desc')?.textContent?.trim()
    return { addressContent, locationContent }
  })

  // addressContent = "Register to See Address"
  // locationContent = "New York, New York"
  const streetAddress = addressContent === 'Register to See Address' ? undefined : addressContent
  const locationContentSplit = locationContent?.split(', ')
  const city = locationContentSplit?.[0]
  const state = locationContentSplit?.[1]
  const address = streetAddress ? `${streetAddress}, ${city}, ${state}` : `${city}, ${state}`

  const guestsContentExists = await page.$('div.guests-string')
  let guests: string[] = []
  let attendees = 0
  if (guestsContentExists) {
    const guestsContent = await page.$eval('div.guests-string', el => el.textContent?.trim() ?? '')
    // guestsContent = "Vance Dekker, Felipe Rubio and 150 others"
    guests = guestsContent.replace(/ and \d+ others/g, '').split(', ') ?? []
    const additionalAttendees = parseInt(guestsContent?.match(/ and (\d+) others/)?.[1] ?? '0')
    attendees = guests.length + additionalAttendees
  }

  const description = await page.$eval('div.spark-content', el => el.innerHTML.trim())

  const cover = await page.$eval('img[srcset]', img => img.src)

  const eventFullExists = await page.$('div.title.fw-medium')
  let waitlist = false
  if (eventFullExists) {
    const eventFullContent = await page.$eval('div.title.fw-medium', el => el?.textContent?.trim())
    waitlist = eventFullContent?.match(/ull/) ? true : false
    log.debug(`> eventFull: ${waitlist}`)
  }

  let price = null
  let maxPrice = null
  let minPrice = null
  const priceExists = await page.$('div.price-display')
  const price2Exists = await page.$('div.ticket-types')
  if (priceExists) {
    const priceContent = await page.$eval('div.price-display', el => el.querySelector('div.price')?.textContent?.trim())
    price = priceContent?.match(/\d+/)?.[0] ?? null
    log.debug(`price: ${price}`)
  } else if (price2Exists) {
    const priceContents = await page.$eval('div.ticket-types', el => {
      const priceEls = el.querySelectorAll('button.ticket-type-btn')
      const prices = []
      for (const priceEl of priceEls) {
        const price = priceEl?.querySelector('div.flex-start.flex-column')?.querySelectorAll('span')?.[2].textContent?.trim() ?? ''
        prices.push(price)
      }
      return prices
    })
    log.debug(`priceContent: ${priceContents}`)
    // priceContent = ["$10", "$20"]
    // Iterate over the array, find the maximum and minimum value and store it in variables
    const priceNumbers = priceContents.map(price => parseFloat(price.replace(/[^0-9.-]+/g, '')))
    maxPrice = Math.max(...priceNumbers)
    minPrice = Math.min(...priceNumbers)
    price = minPrice
    log.debug(`price: ${price}, maxPrice: ${maxPrice}, minPrice: ${minPrice}`)
  }

  const spotsLeftExists = await page.$('div.info-rows.one')
  let spotsLeft = null
  if (spotsLeftExists) {
    const spotsLeftContent = await page.$eval('div.info-rows.one', el => el.querySelector('div.title')?.textContent?.trim())
    const isSpotsRemaining = spotsLeftContent?.match(/emaining/)
    if (isSpotsRemaining!!) {
      spotsLeft = spotsLeftContent?.match(/\d+/)?.[0] ?? null
    }
    log.debug(`spotsLeft: ${spotsLeft}`)
  }

  const registrationClosedExists = await page.$('div.fs-xl.fw-medium')
  let registrationClosed = null
  if (registrationClosedExists) {
    const closedContent = await page.$eval('div.fs-xl.fw-medium', el => el.textContent?.trim())
    // closedContent = "Registration Closed"
    if (closedContent?.match(/egistration.*losed/) || closedContent?.match(/old.*ut/)) {
      registrationClosed = true
    }
    log.debug(`registrationClosed/soldOut: ${registrationClosed}`)
  }

  // Extract event ID from URL
  const urlParts = pageUrl.split('/').filter(Boolean)
  const eventId = urlParts[urlParts.length - 1] || 'unknown'

  // Parse address into city/state
  const addressParts = address ? address.split(',').map(s => s.trim()) : []
  let city: string | null = null
  let state: string | null = null

  if (addressParts.length >= 2) {
    // Last part is state, second to last is city
    state = addressParts[addressParts.length - 1] || null
    city = addressParts[addressParts.length - 2] || null
  } else if (addressParts.length === 1) {
    city = addressParts[0] || null
  }

  // Convert price to cents
  const priceCents = price ? Math.round(price * 100) : null
  const minPriceCents = minPrice ? Math.round(minPrice * 100) : null
  const maxPriceCents = maxPrice ? Math.round(maxPrice * 100) : null

  const item = {
    // Required fields
    eventId: eventId,
    source: 'luma',
    url: pageUrl,
    title: title,
    startDatetime: dateStartText,

    // Optional datetime
    endDatetime: dateEndText,

    // Location fields
    locationName: null, // Luma doesn't have venue name separate from address
    locationAddress: address,
    city: city,
    state: state,
    isOnline: false, // TODO: detect online events

    // Attendance
    attendeeCount: attendees,
    capacity: null,
    spotsRemaining: spotsLeft,

    // Pricing
    priceCents: priceCents,
    currency: 'USD',
    isFree: !price || price === 0,

    // Organizer/Host
    organizerName: group,
    hostName: hosts.length > 0 ? hosts[0] : null,

    // Content
    description: description,
    imageUrl: cover,

    // Enhanced fields (kept for reference, not in base model)
    hosts: hosts, // Full host list
    guests: guests, // Guest list
    minPriceCents: minPriceCents,
    maxPriceCents: maxPriceCents,
    waitlist: waitlist,
    registrationClosed: registrationClosed,

    // Metadata
    crawledAt: new Date().toISOString(),
    detailCrawled: true,
  }

  log.info(`saving item (${JSON.stringify(item.url)}): ${item.title}`)
  await Apify.Dataset.pushData(item)
})

function toDateText(date: Date): string {
  return date.toISOString().split('T')[0] // YYYY-MM-DD
}

function toTimeText(time: Date): string {
  return time.toISOString().split('T')[1] // HH:mm:ssZ
}

function toDateTimeText(date: Date): string {
  return date.toISOString() // YYYY-MM-DDTHH:mm:ssZ
}

// date = "Tomorrow" or "Jan 16" or "Jan 16, 2025"
function extractDateWithYear(date: string) {
  let result = new Date()
  if (date === 'Today') {
    result.setDate(result.getDate())
  } else if (date === 'Tomorrow') {
    result.setDate(result.getDate() + 1)
  } else if (date.includes(',')) {
    // TODO: check if the format is correct when looking into the next year (e.g, "Jan 16, 2025")
    result = new Date(date)
  } else {
    const lastDateParts = date.split(' ')
    const month = new Date(Date.parse(lastDateParts[0] + ' 1, 2022')).getMonth()
    const day = parseInt(lastDateParts[1])
    result = new Date(result.getFullYear(), month, day)
  }
  return result
}

// dateStr = "Tuesday, January 14"
// timeStr = "5:30 PM - 8:30 PM"
export function parseDateTimeRange(dateStr: string, timeStr: string): { dateStart: Date; dateEnd: Date } {
  const [timeStartStr, timeEndStr] = timeStr.split(' - ')

  const yearRegex = /\b\d{4}\b/
  const hasYear = yearRegex.test(dateStr)
  const currentYear = new Date().getFullYear()
  const dateStrWithYear = hasYear ? dateStr : `${dateStr}, ${currentYear}`

  const dateTimeStartStr = `${dateStrWithYear} ${timeStartStr}`
  const dateTimeEndStr = `${dateStrWithYear} ${timeEndStr}`

  let dateStart = new Date(Date.parse(dateTimeStartStr))
  let dateEnd = new Date(Date.parse(dateTimeEndStr))

  return { dateStart, dateEnd }
}
