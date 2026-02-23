import Apify, { Actor, LoggerJson, log } from 'apify'
import { createPuppeteerRouter } from 'crawlee'
import fs from 'fs'

export const router = createPuppeteerRouter()

// router.addDefaultHandler(async ({ page, log, enqueueLinks }) => {
// })

router.addHandler('preload', async ({ request, page, log }) => {
  const pageUrl = request.loadedUrl ?? ''
  const pageTitle = await page.title()

  log.info(`preloading page: ${pageUrl} ${pageTitle}`)
})

type Inputs = {
  lookForwardWindow?: number
  maxItems?: number
  maxScrolls?: number
}

type ParsedCardItem = {
  url: string
  title: string
  date: string
  group: string
  attendies: string
  eventSeries: string[]
  nextEventSeries: string
}

type CardItem = {
  url: string
  title: string
  group: string
  dateTime: Date
  dateTimeText: string
  dateTimeSeries: Date[]
  dateTimeSeriesText: string[]
  host: string
  attendees: string
}

router.addHandler('search', async ({ page, log, enqueueLinks }) => {
  const pageUrl = page.url() ?? ''

  log.info(`processing search page: ${pageUrl}`)
  await new Promise(resolve => setTimeout(resolve, 1000))
  await page.setDefaultNavigationTimeout(30000)

  const input = await Actor.getInput<Inputs>()
  const lookForwardWindow = input?.lookForwardWindow ?? 7
  const maxItems = input?.maxItems ?? 10
  const maxScrolls = input?.maxScrolls ?? 10
  log.debug(`lookForwardWindow: ${lookForwardWindow}`)
  log.debug(`maxItems: ${maxItems}`)
  log.debug(`maxScrolls: ${maxScrolls}`)

  const targetDate = new Date()
  targetDate.setDate(targetDate.getDate() + lookForwardWindow)

  const pageContent = await page.content()

  // Take screenshot for debugging
  await page.screenshot({ path: 'storage/debug_search_page.png', fullPage: true })
  log.info('Screenshot saved to storage/debug_search_page.png')

  // Save HTML for debugging
  const htmlContent = await page.content()
  fs.writeFileSync('storage/debug_page.html', htmlContent)
  log.info('HTML saved to storage/debug_page.html')

  // Try to filter to in-person events (optional - if fails, continue anyway)
  try {
    await page.waitForSelector('button[id="event-type-filter-drop-down"]', { timeout: 10000 })
    await page.click('button[id="event-type-filter-drop-down"]')
    await page.waitForSelector('button[id="event-type-in-person-option"]', { timeout: 10000 })
    await page.click('button[id="event-type-in-person-option"]')
    log.info('Successfully filtered to in-person events')
  } catch (error) {
    log.warning('Could not filter to in-person events, continuing with all events', { error: (error as Error).message })
  }

  // Try to wait for event cards to load
  try {
    await page.waitForSelector('div[data-recommendationsource]', { timeout: 10000 })
  } catch (error) {
    log.warning('Selector div[data-recommendationsource] not found, trying alternative selectors')

    // Log available event card selectors
    const hasEventCardLinks = await page.$$('a[id=event-card-in-search-results]')
    log.info(`Found ${hasEventCardLinks.length} event cards with alternative selector`)

    if (hasEventCardLinks.length === 0) {
      throw new Error('No event cards found on the page with any selector')
    }
  }

  const pageContentAfterClick = await page.content()
  log.debug(`content length after click: ${pageContent.length} -> ${pageContentAfterClick.length}`)

  const scrollPageToBottom = async () => {
    await page.evaluate(() => {
      window.scrollTo(0, document.body.scrollHeight)
    })
  }

  const allCardItems: CardItem[] = []
  let emptyScrollCount = 0
  for (let i = 1; ; i++) {
    log.debug(`scrolling page to bottom: ${i}/${maxScrolls}`)
    await scrollPageToBottom()
    await new Promise(resolve => setTimeout(resolve, 2000))

    const pageContentAfterScroll = await page.content()
    log.debug(`content length after scroll: ${pageContent.length} -> ${pageContentAfterClick.length} -> ${pageContentAfterScroll.length}`)

    const locCardItems: CardItem[] = []

    // Extract data from Next.js __NEXT_DATA__ JSON
    const nextData = await page.evaluate(() => {
      const scriptEl = document.getElementById('__NEXT_DATA__')
      if (!scriptEl) return null
      return JSON.parse(scriptEl.textContent || '{}')
    })

    log.info(`Next.js data extracted: ${nextData ? 'yes' : 'no'}`)

    let parsedCardItems: ParsedCardItem[] = []

    // Extract events from Apollo state if available
    if (nextData && nextData.props && nextData.props.pageProps && nextData.props.pageProps.__APOLLO_STATE__) {
      const apolloState = nextData.props.pageProps.__APOLLO_STATE__
      log.info(`Apollo state keys count: ${Object.keys(apolloState).length}`)

      // Extract all Event objects from Apollo state
      const eventKeys = Object.keys(apolloState).filter(key => key.startsWith('Event:'))
      log.info(`Found ${eventKeys.length} events in Apollo state`)

      for (const eventKey of eventKeys) {
        const event = apolloState[eventKey]
        if (!event || !event.dateTime || !event.title) continue

        const dateTime = new Date(event.dateTime)
        const dateTimeText = toDateTimeText(dateTime)

        // Get group info
        let group = ''
        if (event.group && event.group.__ref) {
          const groupKey = event.group.__ref
          const groupData = apolloState[groupKey]
          if (groupData && groupData.name) {
            group = groupData.name
          }
        }

        parsedCardItems.push({
          url: event.eventUrl || '',
          title: event.title || '',
          date: dateTimeText,  // Store as formatted date for consistency
          group: group,
          attendies: event.rsvps?.totalCount?.toString() || '0',
          eventSeries: [],
          nextEventSeries: ''
        })
      }

      log.info(`Extracted ${parsedCardItems.length} events from Apollo state`)
    }

    // Fallback to DOM scraping if Apollo state extraction didn't work
    if (parsedCardItems.length === 0) {
      parsedCardItems = await page.$$eval('div[data-recommendationsource]', cardEls => {
      const items: any[] = []
      for (const el of cardEls) {
        const eventCardAEls = el.querySelectorAll('a[id=event-card-in-search-results]')
        if (eventCardAEls.length < 2) {
          continue
        }
        const url = eventCardAEls[1]?.getAttribute('href') ?? ''
        const date = eventCardAEls[1]?.parentElement?.querySelector('time[datetime]')?.textContent ?? ''
        const title = eventCardAEls[1]?.parentElement?.querySelector('h2.font-medium.text-base')?.textContent ?? ''
        const group = eventCardAEls[1]?.parentElement?.querySelector('p.text-gray6')?.textContent ?? ''
        const attendies = eventCardAEls[1]?.parentElement?.querySelector('div[aria-label]')?.textContent ?? ''
        const eventSeries: string[] = []
        let nextEventSeries = ''
        if (!date) {
          const eventSeriesBarEl = el?.parentElement?.querySelector('div.swiper-container-horizontal')
          const nextEventSeriesEls = eventSeriesBarEl?.querySelectorAll('a[data-event-label="recurring-events"]')
          nextEventSeriesEls?.forEach(el => {
            eventSeries.push(el?.textContent ?? '')
          })
          nextEventSeries = nextEventSeriesEls?.length ? (nextEventSeriesEls?.[0]?.textContent ?? '') : ''
        }

        items.push({
          url,
          title,
          date,
          group,
          attendies,
          eventSeries,
          nextEventSeries,
        })
      }
      return items
    })
    }  // Close the if (parsedCardItems.length === 0) block

    log.info(`processing ${parsedCardItems?.length} card items`)

    for (const item of parsedCardItems) {
      // log.debug(`processing card: ${item.url} ${item.title} ${item.nextEventSeries}`)

      let dateTime: Date, weekday, date
      if (item.date) {
        // Check if date is already in ISO format (from Apollo state)
        if (item.date.includes('T') && item.date.includes('Z') || item.date.match(/\d{4}-\d{2}-\d{2}T/)) {
          dateTime = new Date(item.date)
        } else {
          // Parse the formatted date from DOM scraping
          const dateParts = item.date.split(' · ') // "Wed, Jan 15", "5:30 PM EST"
          weekday = dateParts[0].split(',')[0].trim()
          const dateStr = dateParts[0].split(',')[1].trim()
          const timeStr = dateParts[1]
          dateTime = parseDateTime(dateStr, timeStr)
        }
        // log.debug(`parseDateTime: ${dateTime}`)
      } else {
        dateTime = parseEventSeriesDateTime(item.nextEventSeries)
        // log.debug(`parseEventSeriesDateTime: ${dateTime}`)
      }
      const dateTimeText = toDateTimeText(dateTime)
      const dateTimeSeries = item.eventSeries.map(e => parseEventSeriesDateTime(e))
      const dateTimeSeriesTexts = dateTimeSeries.map(d => toDateTimeText(d))

      const cardItem = {
        url: item.url,
        title: item.title,
        group: item.group,
        dateTime: dateTime,
        dateTimeText: dateTimeText,
        dateTimeSeries: dateTimeSeries,
        dateTimeSeriesText: dateTimeSeriesTexts,
        host: item.group,
        attendees: item.attendies,
      }
      locCardItems.push(cardItem)
    }

    log.debug(`processing ${locCardItems.length} card items`)

    // If no items found, skip this iteration
    if (locCardItems.length === 0) {
      log.warning('No card items found in this scroll iteration')
      emptyScrollCount++
      if (emptyScrollCount >= 3) {
        log.error('No card items found after 3 scrolls, breaking loop')
        break
      }
      continue
    }
    emptyScrollCount = 0  // Reset counter when items are found

    let breakCondition = false

    // compare the last card item date with the target date
    const lastCardItem = locCardItems[locCardItems.length - 1]
    const lastCardItemDate = lastCardItem.dateTime
    if (lastCardItemDate >= targetDate) {
      log.info(`Found target date: ${lastCardItemDate} >= ${targetDate}`)
      breakCondition = true
    }

    // check for max items
    if (maxItems && allCardItems.length + locCardItems.length >= maxItems) {
      log.info(`Max items reached: ${allCardItems.length + locCardItems.length} >= ${maxItems}`)
      breakCondition = true
    }

    // check for max scrolls
    if (i >= maxScrolls) {
      log.info(`Max scrolls reached: ${i} >= ${maxScrolls}`)
      breakCondition = true
    }

    if (breakCondition) {
      log.info(`breaking loop: ${locCardItems.length}/${maxItems} items discovered, ${lastCardItem.dateTime}/${targetDate} last date`)
      allCardItems.push(...locCardItems)
      break
    }
  }

  log.info(`enqueueing ${allCardItems.length} card items`)
  for (const item of allCardItems) {
    const url = item.url.split('?')[0]
    log.debug(`enqueueing item url (${url}) [${item.dateTimeText}]: ${item.title}`)

    const data = {
      url: url,
      title: item.title,
      group: item.group,
      dateTime: item.dateTimeText,
      dateTimeSeries: item.dateTimeSeriesText,
      host: item.host,
      attendees: item.attendees,
    }

    await enqueueLinks({
      urls: [url],
      label: 'event',
      userData: data,
    })
  }
})

router.addHandler('event', async ({ page, log }) => {
  const pageUrl = (await page.url()) ?? ''
  const pageTitle = await page.title()

  log.debug(`processing event page: ${pageUrl} ${pageTitle}`)
  await new Promise(resolve => setTimeout(resolve, 2000))

  // Extract event data from Next.js Apollo state
  const eventData = await page.evaluate(() => {
    const scriptEl = document.getElementById('__NEXT_DATA__')
    if (!scriptEl) return null
    const data = JSON.parse(scriptEl.textContent || '{}')
    const apolloState = data?.props?.pageProps?.__APOLLO_STATE__
    if (!apolloState) return null

    // Find the Event object in Apollo state
    const eventKey = Object.keys(apolloState).find(key => key.startsWith('Event:') && apolloState[key].__typename === 'Event')
    if (!eventKey) return null

    return apolloState[eventKey]
  })

  if (!eventData) {
    log.warning(`Could not extract event data from Apollo state for ${pageUrl}`)
    return
  }

  log.info(`Extracted event data from Apollo state: ${eventData.id}`)

  const title = eventData.title

  // Extract cover image
  const cover = eventData.featuredEventPhoto?.highRes || eventData.featuredEventPhoto?.baseUrl || ''

  // Extract date/time
  const dateStart = new Date(eventData.dateTime)
  const dateEnd = eventData.endTime ? new Date(eventData.endTime) : dateStart
  const dateStartText = toDateTimeText(dateStart)
  const dateEndText = toDateTimeText(dateEnd)

  // Extract venue info
  const venue = eventData.venue?.name || ''
  const address = [
    eventData.venue?.address,
    eventData.venue?.city,
    eventData.venue?.state
  ].filter(Boolean).join(', ')
  const isOnline = eventData.eventType === 'ONLINE'

  // Extract description
  const description = eventData.description || eventData.aeoDescription || ''

  // Extract host info (need to get from Apollo state)
  const hosts = await page.evaluate(() => {
    const scriptEl = document.getElementById('__NEXT_DATA__')
    if (!scriptEl) return []
    const data = JSON.parse(scriptEl.textContent || '{}')
    const apolloState = data?.props?.pageProps?.__APOLLO_STATE__
    if (!apolloState) return []

    // Find host members from RSVP data
    const hosts: string[] = []
    Object.keys(apolloState).forEach(key => {
      if (key.startsWith('Rsvp:')) {
        const rsvp = apolloState[key]
        if (rsvp.isHost && rsvp.member?.__ref) {
          const memberKey = rsvp.member.__ref
          const member = apolloState[memberKey]
          if (member?.name) hosts.push(member.name)
        }
      }
    })
    return hosts
  })
  const host = hosts[0] || ''

  // Extract tags (topics) from event data
  const tags: string[] = []  // Apollo state doesn't seem to have tags directly

  // Extract attendees count
  const attendees = eventData.rsvps?.totalCount?.toString() || '0'

  // Extract guests from RSVP data
  const guests = await page.evaluate(() => {
    const scriptEl = document.getElementById('__NEXT_DATA__')
    if (!scriptEl) return []
    const data = JSON.parse(scriptEl.textContent || '{}')
    const apolloState = data?.props?.pageProps?.__APOLLO_STATE__
    if (!apolloState) return []

    const guests: string[] = []
    Object.keys(apolloState).forEach(key => {
      if (key.startsWith('Rsvp:')) {
        const rsvp = apolloState[key]
        if (!rsvp.isHost && rsvp.member?.__ref) {
          const memberKey = rsvp.member.__ref
          const member = apolloState[memberKey]
          if (member?.name) guests.push(member.name)
        }
      }
    })
    return guests.slice(0, 20)  // Limit to first 20 guests
  })

  // Extract group info
  const groupData = await page.evaluate(() => {
    const scriptEl = document.getElementById('__NEXT_DATA__')
    if (!scriptEl) return { groupUrl: '', group: '' }
    const data = JSON.parse(scriptEl.textContent || '{}')
    const apolloState = data?.props?.pageProps?.__APOLLO_STATE__
    if (!apolloState) return { groupUrl: '', group: '' }

    // Find the Group object
    const groupKey = Object.keys(apolloState).find(key => key.startsWith('Group:'))
    if (!groupKey) return { groupUrl: '', group: '' }

    const groupObj = apolloState[groupKey]
    return {
      groupUrl: groupObj.urlname ? `https://www.meetup.com/${groupObj.urlname}/` : '',
      group: groupObj.name || ''
    }
  })
  const { groupUrl, group } = groupData

  // Extract event series info (if it's a recurring event)
  const eventSeriesDatesTexts: string[] = []
  if (eventData.series) {
    // Series data would be in Apollo state if available
    // For now, leave empty
  }

  // Extract price info from feeSettings
  let price = null
  let minPrice = null
  let maxPrice = null
  let spotsLeft = null

  if (eventData.feeSettings) {
    const amount = eventData.feeSettings.amount
    if (amount) {
      price = parseFloat(amount)
      minPrice = price
      maxPrice = price
    }
  }

  // Calculate spots left
  if (eventData.maxTickets && eventData.rsvps?.totalCount) {
    spotsLeft = eventData.maxTickets - eventData.rsvps.totalCount
    if (spotsLeft < 0) spotsLeft = 0
  }

  // Check waitlist status
  const waitlist = eventData.rsvpState === 'WAITLIST' || eventData.rsvpState === 'JOIN_WAITLIST'
  const registrationClosed = eventData.rsvpState === 'CLOSED' || eventData.rsvpState === 'PAST'

  const item = {
    url: pageUrl,
    dateStart: dateStartText,
    dateEnd: dateEndText,
    title,
    hosts: [host],
    group,
    address,
    guests,
    attendees,
    description,
    cover,
    tags,
    venue,
    online: isOnline,
    eventSeriesDates: eventSeriesDatesTexts,
    price,
    minPrice,
    maxPrice,
    spotsLeft,
    waitlist,
    registrationClosed,
  }

  log.info(`saving item (${item.url}): ${item.title}`)
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

// dateStr = "Wed, Jan 15" | "Wed, Jan 15, 2025"
// timeStr = '5:30 PM EST' | "5 PM EDT"
function parseDateTime(dateStr: string, timeStr: string): Date {
  const yearRegex = /\b(19|20)\d{2}\b/
  const currentYear = new Date().getFullYear()
  const timeStrFormatted = timeStr?.replace(/\s+/g, ' ').toUpperCase()
  const timeStrWithMinutes = timeStrFormatted.includes(':') ? timeStrFormatted : timeStrFormatted?.replace(' PM', ':00 PM')?.replace(' AM', ':00 AM')
  const dateTimeStr = yearRegex.test(dateStr) ? `${dateStr} ${timeStrWithMinutes}` : `${dateStr} ${currentYear} ${timeStrWithMinutes}`
  const parsedDate = Date.parse(dateTimeStr)
  return new Date(parsedDate)
}

// nextEventSeries = "Jan 15 @ 2 PM EST"
function parseEventSeriesDateTime(nextEventSeries: string): Date {
  const [dateStr, timeStr] = nextEventSeries.split(' @ ')
  return parseDateTime(dateStr, timeStr)
}

// datetime = 'Wednesday, January 15, 2025 <br> 5:30 PM to 8:30 PM EST'
// could be 'Saturday, January 18, 2025 1:00 PM<!-- --> to 2:30 PM<!-- --> <!-- -->EST'
// could also be: 'Thursday, January 16, 2025 at 6:00 PM<!-- --> to Thursday, January 16, 2025 at 8:00 PM<!-- --> <!-- -->EST'
export function parseDateTimeRange(dateTime: string): { dateStart: Date; dateEnd: Date } {
  const cleanedDatetime = dateTime?.replace(/<[^>]*?>/g, ' ')
  const dateRegex = /(\w+),\s+(\w+\s+\d{1,2},\s+\d{4})/
  const timeRegex = /(\d{1,2}:\d{2}\s+[APM]{2})/
  const timezoneRegex = /([A-Z]{3,4})/

  const splitDatetime = cleanedDatetime.split(' to ')
  const startDateMatch = splitDatetime[0].match(dateRegex)
  const endDateMatch = splitDatetime[1].match(dateRegex)
  const startTimeMatch = splitDatetime[0].match(timeRegex)
  const endTimeMatch = splitDatetime[1].match(timeRegex)
  const timezoneMatch = splitDatetime[1].match(timezoneRegex)

  if (!startDateMatch || !startTimeMatch || !endTimeMatch || !timezoneMatch) {
    throw new Error(`Invalid datetime format: ${dateTime}, ${cleanedDatetime}`)
  }

  const startDateStr = startDateMatch[2]
  const endDateStr = endDateMatch ? endDateMatch[2] : startDateStr
  const timeStartStr = `${startDateStr} ${startTimeMatch[1]} ${timezoneMatch[1]}`
  const timeEndStr = `${endDateStr} ${endTimeMatch[1]} ${timezoneMatch[1]}`

  const dateStart = new Date(Date.parse(timeStartStr))
  const dateEnd = new Date(Date.parse(timeEndStr))

  return { dateStart, dateEnd }
}
